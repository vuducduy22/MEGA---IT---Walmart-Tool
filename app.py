import re
import os
from flask import Flask, session, render_template, request, jsonify, send_file
from werkzeug.exceptions import RequestEntityTooLarge
import threading
import time
from walmart import HEADERS, get_browse, get_link, extract_options, start_crawl, switch_workspace, add_trademark_id, upload_excel_trademark_ids, delete_trademark_id
from multix import get_automation_token_fast, start_quick_profile, initialize_multilogin_service
from import_excel import save_uploaded_file, process_uploaded_excel, get_uploaded_files
import requests
import uuid
from bson import json_util
from config import *
import json
from rapidfuzz import fuzz
from datetime import datetime
from config import collection_log
from selenium.webdriver.common.by import By

# Smart login system initialization
def initialize_smart_login():
    """
    Pre-initialize smart login system khi app khởi động
    Điều này giúp cached token sẵn sàng cho các request đầu tiên
    """
    try:
        print("Khởi tạo Smart Login System...")
        
        # Thử lấy automation token với smart login
        result = initialize_multilogin_service(
            email=USERNAME,
            password=PASSWORD,
            secret_2fa=os.getenv("MLX_SECRET_2FA"),
            workspace_id=WORKSPACE_ID,
            workspace_email=os.getenv("MLX_WORKSPACE_EMAIL"),
            use_smart_login=True
        )
        
        if result['success']:
            if result.get('from_cache'):
                print("Smart Login: Sử dụng cached token - App ready!")
            else:
                print("Smart Login: Đăng nhập lần đầu thành công - Token đã được cache!")
            
            # Cập nhật global headers
            HEADERS.update({"Authorization": f"Bearer {result['automation_token']}"})
            print("App sẵn sàng với Smart Login System")
            return True
        else:
            print(f"Smart Login khởi tạo thất bại: {result.get('error')}")
            print("App vẫn chạy được, nhưng mỗi lần mở profile sẽ phải đăng nhập")
            return False
            
    except Exception as e:
        print(f"Lỗi khởi tạo Smart Login: {str(e)}")
        print("App sẽ fallback về chế độ đăng nhập thường")
        return False

def scheduled_file_delete(file_path, delay_seconds=2):
    """Xóa file sau một khoảng thời gian delay (background task)"""
    def delete_after_delay():
        try:
            time.sleep(delay_seconds)
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Đã xóa file: {file_path} (attempt {attempt + 1})")
                    else:
                        print(f"File đã không tồn tại: {file_path}")
                    break
                except PermissionError:
                    if attempt == max_retries - 1:
                        print(f"Không thể xóa file sau {max_retries} lần thử: {file_path}")
                    else:
                        time.sleep(0.5)  # Đợi lâu hơn cho background task
        except Exception as e:
            print(f"Lỗi trong scheduled delete: {e}")
    
    # Chạy trong background thread
    thread = threading.Thread(target=delete_after_delay, daemon=True)
    thread.start()
    return thread

def count_similar_phrases(phrase, phrase_list, threshold=0.7):
    count = 0
    for p in phrase_list:
        similarity = fuzz.ratio(phrase, p) / 100  
        if similarity >= threshold:
            count += 1
    return count


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit for file uploads
crawl_sessions = {}

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]

def open_profile(state, proxy: str = None):
    """
    Mở profile với smart login system - tự động sử dụng cached token
    """
    try:
        # Sử dụng smart login với token caching
        state["products_data"].append({"link": None, "status": "Đang xác thực..."})
        
        token = get_automation_token_fast(
            email=USERNAME,
            password=PASSWORD,
            secret_2fa=os.getenv("MLX_SECRET_2FA"),  # Cần thêm vào .env
            workspace_id=WORKSPACE_ID,
            workspace_email=os.getenv("MLX_WORKSPACE_EMAIL")  # Cần thêm vào .env
        )
        
        if token is None:
            raise Exception("Lỗi đăng nhập MultiloginX - Kiểm tra thông tin 2FA")
        
        # Cập nhật headers với token mới (cached hoặc fresh)
        HEADERS.update({"Authorization": f"Bearer {token}"})
        
        state["products_data"].append({"link": None, "status": "Xác thực thành công - Đang tạo profile..."})
        
        # Tạo profile với token
        result = start_quick_profile(proxy)
        print(f"Tạo profile MLX: {result}")
        if result is None:
            raise Exception("Không thể tạo profile MLX - timeout hoặc lỗi server")
        
        driver, profile_info = result
        if driver is None:
            # Handle detailed error info từ improved error handling
            if isinstance(profile_info, dict) and profile_info.get("error"):
                error_details = profile_info
                # Get message with fallback - xử lý None an toàn
                error_msg = error_details.get("message", "Không rõ lỗi")
                detailed_msg = error_details.get("detailed_message", "")
                
                if detailed_msg:
                    error_msg = detailed_msg
                
                # Show suggestions
                suggestions = error_details.get("suggestion", [])
                if suggestions:
                    suggestion_text = " | ".join(suggestions[:2])  # Chỉ show 2 suggestions ngắn gọn
                    error_msg += f" Thử: {suggestion_text}"
                
                state["products_data"].append({"link": None, "status": error_msg})
                raise Exception(error_msg)
            else:
                # Fallback cho old format
                raise Exception(f"Tạo profile thất bại: {profile_info}")
        
        state["products_data"].append({"link": None, "status": f"Profile {profile_info} đã sẵn sàng"})
        state["active_driver"] = driver
        return driver
        
    except Exception as e:
        error_msg = f"Lỗi mở profile: {str(e)}"
        print(error_msg)
        state["products_data"].append({"link": None, "status": error_msg})
        raise

def is_stop_requested(state):
    if state["stop_flag"] and state["active_driver"]:
        try:
            state["active_driver"].close()
            state["active_driver"].quit()
        except:
            pass
        state["active_driver"] = None
        return True
    return state["stop_flag"]

def crawl_option1(department, collection, proxy, state, start, end):
    print("crawl_option1 started!")
    # Log crawl start
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "start_time": datetime.now(),
        "option": "option1",
        "status": "started"
    })
    
    driver = None
    try:
        driver = open_profile(state, proxy)
    except Exception as e:
        error_msg = f"lỗi mở profile, {e}"
        state["products_data"].append({"link": 'nan', "status": error_msg})
        # Reset session state when error occurs
        try:
            import requests
            requests.post('http://localhost:5000/reset-session', timeout=1)
        except:
            pass
        return
    
    try:
        product_type = get_browse(driver, department)
        print("Browse URLs:", product_type)
        state["products_data"].append({"link": department, "status": "extract link"})

        for url in product_type:
            if is_stop_requested(state):  # Check stop request in the loop
                break

            state["products_data"].append({"link": url, "status": "extract link"})

            for page in range(start, end+1):
                if is_stop_requested(state):  # Check stop request in the loop
                    break

                links = get_link(driver, url, page)
                print("Product links on page", page, ":", links)
                for link in links:
                    if is_stop_requested(state):  # Check stop request in the loop
                        break
                    print("Crawling link:", link)
                    crawl_link, crawl_status, json_dict = start_crawl(driver, collection, link, url)
                    print("Crawl status:", crawl_status)
                    json_dict = json.loads(json_util.dumps(json_dict))
                    print("Crawled data:", json_dict)
                    state["products_data"].append({"link": crawl_link, "status": crawl_status, "json": json_dict})
                    
    except Exception as e:
        error_msg = f"Lỗi trong quá trình quét: {str(e)}"
        state["products_data"].append({"link": "", "status": error_msg, "json": ""})
        print(f"Error in crawl_option1: {e}")
        
    finally:
        if driver:
            try:
                driver.close()
            except:
                pass
        
        state["products_data"].append({"link": "", "status": "Đã hoàn thành quét", "json": ""})
        state["stop_flag"] = True
        is_stop_requested(state)
        
        # Reset session state when crawling is complete
        try:
            import requests
            requests.post('http://localhost:5000/reset-session', timeout=1)
        except:
            pass  # Ignore if reset fails
        
        # Log crawl end
        collection_log.insert_one({
            "department": department,
            "collection": collection.name,
            "end_time": datetime.now(),
            "option": "option1",
            "status": "completed"
        })

def crawl_option2(department, collection, proxy, state, start, end):
    print("crawl_option2 started!")
    # Log crawl start
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "start_time": datetime.now(),
        "option": "option2",
        "status": "started"
    })
    try:
        driver = open_profile(state, proxy)
    except Exception as e:
        state["products_data"].append({"link": 'nan', "status": f"lỗi mở profile, {e}"})
        return

    for page in range(start, end+1):
        if is_stop_requested(state):
            break

        links = get_link(driver, department, page)
        print("Product links on page", page, ":", links)
        for link in links:
            if is_stop_requested(state):
                break
            crawl_link, crawl_status, json_dict = start_crawl(driver, collection, link, department)
            json_dict = json.loads(json_util.dumps(json_dict))
            state["products_data"].append({"link": crawl_link, "status": crawl_status, "json": json_dict})

    driver.close()
    state["products_data"].append({"link": "", "status": "Đã hoàn thành quét", "json": ""})
    state["stop_flag"] = True
    is_stop_requested(state)
    
    # Reset session state when crawling is complete
    try:
        import requests
        requests.post('http://localhost:5000/reset-session', timeout=1)
    except:
        pass  # Ignore if reset fails
    
    # Log crawl end
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "end_time": datetime.now(),
        "option": "option2",
        "status": "completed"
    })

def crawl_option3(department, collection, proxy, state, start, end):
    # Log crawl start
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "start_time": datetime.now(),
        "option": "option3",
        "status": "started"
    })
    try:
        driver = open_profile(state, proxy)
    except Exception as e:
        state["products_data"].append({"link": 'nan', "status": f"lỗi mở profile, {e}"})
        return
    product_type = get_browse(driver, department)
    state["products_data"].append({"link": department, "status": "extract link"})
    for url in product_type:
        if is_stop_requested(state):
            break
        state["products_data"].append({"link": url, "status": "extract link"})
        for page in range(start, end+1):
            if is_stop_requested(state):
                break
            links = get_link(driver, url, page)
            for link in links:
                if is_stop_requested(state):
                    break
                options = extract_options(driver, link)
                state["products_data"].append({"link": url, "status": "extract options", "options": options})
                for option in options:
                    if is_stop_requested(state):
                        break
                    crawl_link, crawl_status, json_dict = start_crawl(driver, collection, option, url)
                    json_dict = json.loads(json_util.dumps(json_dict))
                    state["products_data"].append({"link": crawl_link, "status": crawl_status, "json": json_dict})
    driver.close()
    state["products_data"].append({"link": "", "status": "Đã hoàn thành quét", "json": ""})
    state["stop_flag"] = True
    is_stop_requested(state)
    
    # Reset session state when crawling is complete
    try:
        import requests
        requests.post('http://localhost:5000/reset-session', timeout=1)
    except:
        pass  # Ignore if reset fails
    
    # Log crawl end
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "end_time": datetime.now(),
        "option": "option3",
        "status": "completed"
    })

def crawl_option4(department, collection, proxy, state, start, end):
    # Log crawl start
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "start_time": datetime.now(),
        "option": "option4",
        "status": "started"
    })
    try:
        driver = open_profile(state, proxy)
    except Exception as e:
        state["products_data"].append({"link": 'nan', "status": f"lỗi mở profile, {e}"})
        return
    for page in range(start, end+1):
        if is_stop_requested(state):
            break
        links = get_link(driver, department, page)
        for link in links:
            if is_stop_requested(state):
                break
            options = extract_options(driver, link)
            state["products_data"].append({"link": link, "status": "extract link", "json": options})
            for option in options:
                if is_stop_requested(state):
                    break
                crawl_link, crawl_status, json_dict = start_crawl(driver, collection, option, department)
                json_dict = json.loads(json_util.dumps(json_dict))
                state["products_data"].append({"link": crawl_link, "status": crawl_status, "json": json_dict})
    driver.close()
    state["products_data"].append({"link": "", "status": "Đã hoàn thành quét", "json": ""})
    state["stop_flag"] = True
    is_stop_requested(state)
    
    # Reset session state when crawling is complete
    try:
        import requests
        requests.post('http://localhost:5000/reset-session', timeout=1)
    except:
        pass  # Ignore if reset fails
    
    # Log crawl end
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "end_time": datetime.now(),
        "option": "option4",
        "status": "completed"
    })

def crawl_option5(department, collection, proxy, state):
    # Log crawl start
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "start_time": datetime.now(),
        "option": "option5",
        "status": "started"
    })
    try:
        driver = open_profile(state, proxy)
    except Exception as e:
        state["products_data"].append({"link": 'nan', "status": f"lỗi mở profile, {e}"})
        return
    options = extract_options(driver, department)
    state["products_data"].append({"link": department, "status": "extract link", "json": options})
    for option in options:
        if is_stop_requested(state):
            break
        crawl_link, crawl_status, json_dict = start_crawl(driver, collection, option, department)
        json_dict = json.loads(json_util.dumps(json_dict))
        state["products_data"].append({"link": crawl_link, "status": crawl_status, "json": json_dict})
    driver.close()
    state["products_data"].append({"link": "", "status": "Đã hoàn thành quét", "json": ""})
    state["stop_flag"] = True
    is_stop_requested(state)
    
    # Reset session state when crawling is complete
    try:
        import requests
        requests.post('http://localhost:5000/reset-session', timeout=1)
    except:
        pass  # Ignore if reset fails
    
    # Log crawl end
    collection_log.insert_one({
        "department": department,
        "collection": collection.name,
        "end_time": datetime.now(),
        "option": "option5",
        "status": "completed"
    })

@app.route('/')
def index():
    session_id = get_session_id()
    if session_id not in crawl_sessions:
        crawl_sessions[session_id] = {
            "is_crawling": False,
            "stop_flag": False,
            "driver": None,
            "products_data": []
        }
    return render_template('index.html')

@app.route('/products')
def fetch_products():
    session_id = get_session_id()
    session_data = crawl_sessions.get(session_id, {})
    return jsonify(session_data.get("products_data", []))

@app.route('/crawl', methods=['POST'])
def crawl():
    session_id = get_session_id()
    if session_id in crawl_sessions and crawl_sessions[session_id]["is_crawling"]:
        return jsonify({"error": "A crawl is already in progress for this session"}), 400

    data = request.json
    collection_name = data.get('collection')
    proxy = data.get('proxy')
    department = data.get('department')
    option = data.get('option')
    start = data.get('start', '1')
    end = data.get('end', '10')
    
    # Convert to integers, defaulting to 1 and 10 if empty or invalid
    try:
        start = int(start) if start else 1
    except (ValueError, TypeError):
        start = 1
        
    try:
        end = int(end) if end else 10
    except (ValueError, TypeError):
        end = 10

    if not department or not option:
        return jsonify({"error": "Missing 'department' or 'option'"}), 400

    collection = db[collection_name]
    crawl_data = []
    # Khởi tạo session crawl
    crawl_sessions[session_id] = {
        "is_crawling": False,
        "stop_flag": False,
        "active_driver": None,
        "products_data": crawl_data, 
        
        }
    def wrapper():
        print("Thread started!")
        state = crawl_sessions[session_id]
        try:
            state["is_crawling"] = True
            crawl_options = {
                "option1": lambda: crawl_option1(department, collection, proxy, state, start, end),
                "option2": lambda: crawl_option2(department, collection, proxy, state, start, end),
                "option3": lambda: crawl_option3(department, collection, proxy, state, start, end),
                "option4": lambda: crawl_option4(department, collection, proxy, state, start, end),
                "option5": lambda: crawl_option5(department, collection, proxy, state),
            }
            crawl_func = crawl_options.get(option)
            if crawl_func:
                crawl_func()
        except Exception as e:
            # Log lỗi và reset session khi có exception
            print(f"Error in crawl wrapper: {e}")
            state["products_data"].append({"link": "", "status": f"Lỗi hệ thống: {str(e)}", "json": ""})
            state["stop_flag"] = True
            state["is_crawling"] = False
            
            # Reset session state when error occurs
            try:
                import requests
                requests.post('http://localhost:5000/reset-session', timeout=1)
            except:
                pass  # Ignore if reset fails
        finally:
            state["is_crawling"] = False


    threading.Thread(target=wrapper).start()

    return jsonify({"message": f"Crawling started with {option} for department: {department}"}), 200

@app.route('/stop', methods=['POST'])
def stop():
    session_id = get_session_id()
    if session_id not in crawl_sessions:
        return jsonify({"error": "No crawl session found"}), 400

    session_data = crawl_sessions[session_id]
    session_data["stop_flag"] = True
    session_data["is_crawling"] = False

    driver = session_data.get("active_driver")
    if driver:
        try:
            driver.close()
            driver.quit()
        except:
            pass
        session_data["active_driver"] = None

    return jsonify({"message": "Crawl process stopped for your session."})

@app.route('/reset-session', methods=['POST'])
def reset_session():
    session_id = get_session_id()
    if session_id in crawl_sessions:
        crawl_sessions[session_id] = {
            "is_crawling": False,
            "stop_flag": False,
            "active_driver": None,
            "products_data": []
        }
    return jsonify({"message": "Session reset successfully"})


@app.route("/check-proxy", methods=["POST"])
def check_proxy():
    data = request.get_json()
    raw_proxy = data.get("proxy")  # Ví dụ: "160.250.185.123:41361" hoặc "160.250.185.123:41361:user:pass"

    if not raw_proxy:
        return jsonify({"message": "❌ Vui lòng nhập proxy"}), 400

    try:
        parts = raw_proxy.strip().split(":")
        
        if len(parts) == 2:
            ip, port = parts
            proxy_url = f"http://{ip}:{port}"
            auth_info = "Không có authentication"
        elif len(parts) == 4:
            ip, port, user, password = parts
            proxy_url = f"http://{user}:{password}@{ip}:{port}"
            auth_info = f"Username: {user}"
        else:
            return jsonify({
                "message": "❌ Định dạng proxy không hợp lệ.",
                "help": "Định dạng đúng: 'ip:port' hoặc 'ip:port:username:password'"
            }), 400

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        print(f"🔍 Testing proxy: {ip}:{port}")
        print(f"🔐 Auth: {auth_info}")

        # Test với timeout dài hơn và nhiều endpoints
        test_urls = [
            "http://httpbin.org/ip",
            "http://icanhazip.com", 
            "http://ipinfo.io/ip"
        ]

        for test_url in test_urls:
            try:
                print(f"📡 Testing {test_url}...")
                response = requests.get(test_url, proxies=proxies, timeout=15)
                
                print(f"📊 Status: {response.status_code}")
                print(f"📝 Response: {response.text[:100]}...")

                if response.status_code == 200:
                    # Xử lý response tùy theo endpoint
                    if "httpbin.org" in test_url:
                        try:
                            result = response.json()
                            return jsonify({
                                "message": "✅ Proxy hoạt động!",
                                "ip": result.get("origin", "Unknown"),
                                "proxy": f"{ip}:{port}",
                                "auth": auth_info,
                                "test_url": test_url
                            })
                        except:
                            # httpbin trả về JSON lỗi, lấy IP từ text
                            ip_result = response.text.strip()
                    else:
                        # icanhazip.com và ipinfo.io trả về plain text IP
                        ip_result = response.text.strip()
                    
                    return jsonify({
                        "message": "✅ Proxy hoạt động!",
                        "ip": ip_result,
                        "proxy": f"{ip}:{port}",
                        "auth": auth_info,
                        "test_url": test_url
                    })
                    
                elif response.status_code == 407:
                    return jsonify({
                        "message": "❌ Proxy yêu cầu xác thực!",
                        "error": "Proxy Authentication Required (407)",
                        "help": "Vui lòng sử dụng định dạng: ip:port:username:password",
                        "proxy": f"{ip}:{port}",
                        "status_code": 407
                    }), 407
                    
                elif response.status_code == 403:
                    return jsonify({
                        "message": "❌ Proxy từ chối kết nối!",
                        "error": "Forbidden (403)",
                        "help": "IP của bạn có thể bị block hoặc proxy không cho phép truy cập",
                        "proxy": f"{ip}:{port}",
                        "status_code": 403
                    }), 403
                    
                else:
                    print(f"⚠️ Unexpected status: {response.status_code}")
                    continue  # Thử endpoint khác
                    
            except requests.exceptions.ConnectTimeout:
                print(f"⏰ Timeout connecting to {test_url}")
                continue
            except requests.exceptions.ProxyError as e:
                print(f"🔌 Proxy error with {test_url}: {e}")
                continue
            except Exception as e:
                print(f"❌ Error with {test_url}: {e}")
                continue

        # Nếu tất cả endpoints đều fail
        return jsonify({
            "message": "❌ Proxy không phản hồi từ tất cả test endpoints",
            "proxy": f"{ip}:{port}",
            "auth": auth_info,
            "tested_urls": test_urls,
            "help": "Kiểm tra lại proxy hoặc thử với username:password nếu cần"
        }), 502

    except requests.exceptions.ConnectTimeout:
        return jsonify({
            "message": "⏰ Proxy timeout - Kết nối quá chậm",
            "help": "Proxy có thể đang quá tải hoặc không hoạt động"
        }), 408
        
    except requests.exceptions.ProxyError as e:
        return jsonify({
            "message": f"🔌 Lỗi proxy: {str(e)}",
            "help": "Kiểm tra lại địa chỉ proxy và port"
        }), 502
        
    except requests.exceptions.ConnectionError as e:
        return jsonify({
            "message": "🌐 Không thể kết nối đến proxy",
            "error": str(e),
            "help": "Kiểm tra kết nối internet hoặc proxy server"
        }), 503

    except Exception as e:
        return jsonify({
            "message": f"❌ Lỗi không xác định: {str(e)}",
            "help": "Vui lòng thử lại hoặc kiểm tra định dạng proxy"
        }), 500


# Route lấy dữ liệu sản phẩm (cập nhật bảng ở frontend)
@app.route('/get_products', methods=['GET'])
def get_products():
    session_id = get_session_id()
    session_data = crawl_sessions.get(session_id)
    if not session_data:
        return jsonify([])

    products = session_data.get("products_data", [])
    safe_products = [p for p in products if is_jsonable(p)]
    return jsonify(safe_products)

from flask import render_template, request, jsonify


# Route: Hiển thị trang lọc sản phẩm (cũ)
@app.route('/crawl_data')
def product_filter():
    """
    Render giao diện hiển thị và lọc sản phẩm.
    """
    return render_template('crawl_data.html')  # Render file HTML mới

# Route: Danh sách crawl mới (riêng biệt)
@app.route('/crawl-list')
def crawl_list():
    """
    Render giao diện danh sách crawl mới - có thể tùy chỉnh logic riêng
    """
    return render_template('crawl_list.html')

trademark_ids_cache = set()
slug_trie_cache = []
entities_cache = []

def load_trademark_data():
    global trademark_ids_cache, slug_trie_cache, entities_cache
    try:
        db_test = client["test"]

        trademark_doc = db_test["trademark_ids"].find_one({"trademarks": {"$exists": True}})
        trademark_ids_cache = set(trademark_doc.get("trademarks", [])) if trademark_doc else set()

        slug_trie_cache = []
        slug_docs = db_test["trademark_ids"].find({"slug": {"$exists": True}})
        for doc in slug_docs:
            slug = doc.get("slug", "").lower()
            if slug:
                slug_trie_cache.append(slug)
        entities_doc = db_test["trademark_ids"].find_one({"entities": {"$exists": True}})
        entities_cache = entities_doc.get("entities", []) if entities_doc else []
        
        print("Trademark data loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load trademark data from MongoDB: {e}")
        print("Continuing without trademark data...")
        trademark_ids_cache = set()
        slug_trie_cache = []
        entities_cache = []

# Load trademark data at startup, but don't fail if MongoDB is not available
try:
    load_trademark_data()
except Exception as e:
    print(f"Warning: Failed to load trademark data at startup: {e}")

def is_entity_matched(product_name, brand_name=None):
    if not product_name or not entities_cache:
        return False
    product_name_lower = product_name.lower()
    brand_name_lower = brand_name.lower() if brand_name else ""

    # Check product name
    product_match = any(entity.lower() in product_name_lower for entity in entities_cache)

        # Check brand name
    brand_match = any(entity.lower() in brand_name_lower for entity in entities_cache) if brand_name else False

    return product_match or brand_match


@app.route('/api/products', methods=['GET'])
def get_all_products():
    page = int(request.args.get('page', 1))
    limit = 20
    skip = (page - 1) * limit

    collection_name = request.args.get('collection', 'products')
    if collection_name not in db.list_collection_names():
        return jsonify({"error": "Collection not found"})
    print("COLLECTION:", collection_name)
    collection = db[collection_name]
    product_type = request.args.get('type', None)
    reseller_only = request.args.get('resellerOnly', 'false').lower() == 'true'

    # Lọc theo loại sản phẩm
    if product_type == 'variant':
        product_type_filter = {"hasVariant": {"$exists": True, "$ne": []}}
    elif product_type == 'single':
        product_type_filter = {"hasVariant": {"$exists": False}}
    else:
        product_type_filter = None

    # Lọc theo giá
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price

    if price_filter:
        price_condition = {
            "$or": [
                {"hasVariant.0.offers.0.price": price_filter},
                {"offers.0.price": price_filter}
            ]
        }
    else:
        price_condition = None

    if reseller_only:
        reseller_condition = {"reseller": {"$exists": True, "$ne": []}}
    else:
        reseller_condition = None

    conditions = []
    if product_type_filter:
        conditions.append(product_type_filter)
    if price_condition:
        conditions.append(price_condition)
    if reseller_condition:
        conditions.append(reseller_condition)

    filter_query = {"$and": conditions} if conditions else {}

    print("FILTER:", filter_query)

    products_cursor = collection.find(filter_query).sort('_id', -1).skip(skip).limit(limit)
    products = list(products_cursor)

    results = []
    for product in products:
        timestamp = product['_id'].generation_time
        product['_id'] = str(product['_id'])
        if 'hasVariant' in product and isinstance(product['hasVariant'], list) and product['hasVariant']:
            variant = product['hasVariant'][0]
            link_check = product.get('link', '')
            match = re.search(r"/ip/(.*?)/\d+", link_check)
            slug_part = match.group(1) if match else ""

            is_violated = count_similar_phrases(slug_part, slug_trie_cache) > 0
            is_entity_violated = is_entity_matched(
                variant.get('name', product.get('name', 'N/A')), 
                product.get('brand_name', 'N/A')
            )

            results.append({
                'name': variant.get('name', product.get('name', 'N/A')),
                'sku': variant.get('sku', 'N/A'),
                'link': product.get('link', 'N/A'),
                'reseller': product.get('reseller', 'N/A'),
                'gtin13': variant.get('gtin13', 'N/A'),
                'color': variant.get('color', 'N/A'),
                'size': variant.get('size', 'N/A'),
                'image': variant.get('image', ''),
                'price': variant.get('offers', [{}])[0].get('price', 'N/A'),
                "note": product.get('note', ''),
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "trademark": "trademark" if is_violated else "clear",
                "entity_warning": "warning" if is_entity_violated else "clear",
                'brand_name': product.get('brand_name', 'N/A'),
                'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            # existing_product = collection.find_one({"name": product.get("name")})
            link_check = product.get('link', '')
            match = re.search(r"/ip/(.*?)/\d+", link_check)
            slug_part = match.group(1) if match else ""

            is_violated = count_similar_phrases(slug_part, slug_trie_cache) > 0
            is_entity_violated = is_entity_matched(
                product.get('name', 'N/A'), 
                product.get('brand_name', 'N/A')
            )
            results.append({
                'name': product.get('name', 'N/A'),
                'link': product.get('link', 'N/A'),
                'sku': product.get('sku', 'N/A'),
                'reseller': product.get('reseller', 'N/A'),
                'color': product['options'][0] if len(product['options']) > 0 and len(product['options'][0]) < 50 else 'N/A',
                'size': product['options'][1] if len(product['options']) > 1 else 'N/A',
                'gtin13': str(product.get('gtin13', 'N/A')),
                'image': product.get('image', ''),
                'price': product.get('offers', [{}])[0].get('price', 'N/A'),
                "note": product.get('note', ''),
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "trademark": "trademark" if is_violated else "clear",
                "entity_warning": "warning" if is_entity_violated else "clear",
                'brand_name': product.get('brand_name', 'N/A'),
                'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

    total_products = collection.count_documents(filter_query)
    total_pages = (total_products + limit - 1) // limit

    return jsonify({
        'products': results,
        'page': page,
        'total_pages': total_pages,
        'total_products': total_products,
    })


@app.route('/collections')
def get_collections():
    # Lấy danh sách collections (loại trừ system collections và internal collections)
    excluded_collections = {'batch_ids', 'generated_skus', 'logs'}
    collections = []
    for collection_name in db.list_collection_names():
        if not collection_name.startswith('system.') and collection_name not in excluded_collections:
            collections.append(collection_name)
    return jsonify({"collections": collections})


@app.route('/add-collection', methods=['POST'])
def add_collection():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Thiếu tên collection"})

    if name in db.list_collection_names():
        return jsonify({"success": True, "message": "Đã tồn tại"})

    db.create_collection(name)
    return jsonify({"success": True, "message": "Tạo thành công"})

current_collection = db['default']  # Mặc định, hoặc chọn từ danh sách

@app.route('/set-collection', methods=['POST'])
def set_collection():
    global current_collection
    data = request.json
    name = data.get('name')

    if name not in db.list_collection_names():
        return jsonify({'error': 'Collection không tồn tại'}), 400

    current_collection = db[name]
    return jsonify({'message': f'Đã chuyển sang collection: {name}'}), 200


@app.route('/api/products/note', methods=['POST'])
def save_note():
    try:
        data = request.json
        link = data.get('link')                  # Lấy link của sản phẩm
        note = data.get('note')                  # Lấy ghi chú từ frontend
        collection_name = data.get('collection') # Lấy collection

        if not link or note is None or not collection_name:
            return jsonify({"success": False, "message": "Thiếu thông tin bắt buộc."}), 400

        # Kết nối tới collection tương ứng
        collection = db[collection_name]

        # Cập nhật ghi chú dựa trên `link`
        result = collection.update_one(
            {"link": link},                     # Điều kiện dựa trên link
            {"$set": {"note": note}},           # Cập nhật ghi chú
            upsert=True                         # Tạo tài liệu mới nếu không tìm thấy
        )

        if result.matched_count == 0 and not result.upserted_id:
            return jsonify({"success": False, "message": "Không tìm thấy sản phẩm với link được cung cấp."}), 404

        return jsonify({"success": True, "message": "Ghi chú đã được lưu thành công."})

    except Exception as e:
        print(f"Lỗi xảy ra: {e}")
        return jsonify({"success": False, "message": "Lỗi khi xử lý yêu cầu."}), 500

@app.route('/api/trademark', methods=['GET'])
def get_trademarks():
    from walmart import get_trademark_ids
    ids = get_trademark_ids()
    return jsonify({"success": True, "data": ids, "total": len(ids)})

@app.route('/api/trademark/add', methods=['POST'])
def add_trademark():
    new_id = request.json.get('id')
    result = add_trademark_id(new_id)
    return jsonify(result)

@app.route('/api/trademark/upload', methods=['POST'])
def upload_trademark():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "Không có file được upload"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "Không có file được chọn"})
        
        file.save('temp.xlsx')
        result = upload_excel_trademark_ids('temp.xlsx')
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi server: {str(e)}"})

@app.route('/api/trademark/delete', methods=['DELETE'])
def delete_trademark():
    id = request.json.get('id')
    result = delete_trademark_id(id)
    return jsonify(result)



@app.route('/profiles', methods=['GET'])
def get_profiles():
    try:
        from multix import get_all_profile_status
        print(f"Lấy tất cả trạng thái profile")
        profiles_data = get_all_profile_status()
        print(profiles_data)
        if profiles_data:
            profiles = []
            # Handle the actual Multilogin API response format
            for profile_id, profile_info in profiles_data.items():
                if isinstance(profile_info, dict):
                    profiles.append({
                        "id": profile_id,
                        "name": profile_info.get("name", "Unnamed Profile"),
                        "status": profile_info.get("status", "unknown"),
                        "browser_type": profile_info.get("browser_type", "unknown"),
                        "os_type": "linux",  # Default since it's not in the response
                        "port": profile_info.get("port"),
                        "message": profile_info.get("message", ""),
                        "core_version": profile_info.get("core_version"),
                        "folder_id": profile_info.get("folder_id"),
                        "workspace_id": profile_info.get("workspace_id"),
                        "is_quick": profile_info.get("is_quick"),
                        "timestamp": profile_info.get("timestamp"),
                        "in_use_by": profile_info.get("in_use_by"),
                        "last_launched_by": profile_info.get("last_launched_by"),
                        "last_launched_on": profile_info.get("last_launched_on")
                    })
            return jsonify({"success": True, "profiles": profiles})
        else:
            return jsonify({"success": False, "message": "Failed to fetch profiles"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/profile/start/<profile_id>', methods=['POST'])
def start_profile_route(profile_id):
    try:
        from multix import start_profile
        driver = start_profile(profile_id)
        if driver:
            return jsonify({"success": True, "message": f"Profile {profile_id} started successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to start profile"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/profile/stop/<profile_id>', methods=['POST'])
def stop_profile_route(profile_id):

    from multix import stop_profile
    stop_profile(profile_id)
    return jsonify({"success": True, "message": f"Profile {profile_id} stopped successfully"})

# Excel Upload Routes  
@app.route('/excel-upload')
def excel_upload_page():
    """Trang upload Excel"""
    return render_template('excel_upload.html')

@app.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    """API upload file Excel"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Không có file được chọn'}), 400
        
        file = request.files['file']
        
        # Lưu file
        file_info = save_uploaded_file(file)
        
        if not file_info['success']:
            return jsonify(file_info), 400
        
        # Xử lý file Excel
        result = process_uploaded_excel(file_info)
        
        return jsonify(result)
        
    except RequestEntityTooLarge:
        return jsonify({'success': False, 'error': 'File quá lớn! Kích thước tối đa là 100MB'}), 413
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/files', methods=['GET'])
def get_excel_files():
    """Lấy danh sách files Excel đã upload"""
    try:
        files = get_uploaded_files()
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/download-and-delete/<filename>', methods=['POST'])
def download_and_delete_excel(filename):
    """Download file và tự động xóa"""
    try:
        print(f"Attempting to download: {filename}")
        file_path = os.path.join('uploads', filename)
        print(f"File path: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"File không tồn tại: {file_path}")
            return jsonify({'success': False, 'error': f'File không tồn tại: {filename}'}), 404
        
        # Kiểm tra file size
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size} bytes")
        
        # Đọc file vào memory trước khi xóa
        print(f"Reading file into memory...")
        with open(file_path, 'rb') as f:
            file_data = f.read()
        print(f"File read successfully: {len(file_data)} bytes")
        
        # Schedule xóa file sau khi download (tránh file locking trên Windows)
        scheduled_file_delete(file_path, delay_seconds=1)
        print(f"Đã schedule xóa file: {filename} sau 1 giây")
        
        # Tạo response từ memory
        from io import BytesIO
        file_like = BytesIO(file_data)
        
        # Xác định mimetype dựa trên extension
        if filename.lower().endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xls'):
            mimetype = 'application/vnd.ms-excel'
        elif filename.lower().endswith('.csv'):
            mimetype = 'text/csv'
        else:
            mimetype = 'application/octet-stream'
        
        print(f"Sending file with mimetype: {mimetype}")
        
        response = send_file(
            file_like,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
        print(f"Download response created successfully")
        return response
        
    except Exception as e:
        print(f"Error in download_and_delete_excel: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Lỗi server: {str(e)}'}), 500

# Route: Fill data into Excel file
@app.route('/api/excel/fill-data', methods=['POST'])
def fill_excel_data():
    """API endpoint để fill dữ liệu từ database vào file Excel"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        collection = data.get('collection')
        column = data.get('column', 'E')
        sku_column = data.get('sku_column', 'A')
        batch_column = data.get('batch_column', 'CU')
        image_column = data.get('image_column', 'T')
        fill_images_from_s3 = data.get('fill_images_from_s3', False)  # Changed from fill_images_from_drive
        start_row = data.get('start_row', 7)
        fill_mode = data.get('fill_mode', 'repeat')  # 'repeat' or 'duplicate'
        
        if not filename or not collection:
            return jsonify({'success': False, 'error': 'Thiếu thông tin filename hoặc collection'}), 400
        
        # Get products from database
        from walmart import get_products
        products = get_products(collection)
        
        if not products:
            return jsonify({'success': False, 'error': 'Không tìm thấy sản phẩm trong collection'}), 400
        
        print(f"Đã lấy {len(products)} sản phẩm từ collection '{collection}'")
        print(f"Fill mode: {fill_mode}")
        print(f"Product name column: {column}, SKU column: {sku_column}, Batch ID column: {batch_column}")
        if fill_images_from_s3:
            print(f"Image column: {image_column} (fill from AWS S3: ON)")
        print(f"Sẽ tự động fill từ dòng {start_row} đến cuối file")
        
        # Read Excel file and fill data
        from import_excel import fill_excel_with_data
        result = fill_excel_with_data(filename, products, column, start_row, fill_mode, sku_column, batch_column, image_column, fill_images_from_s3)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in fill_excel_data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/excel/download/<filename>')
def download_file_only(filename):
    """API endpoint để download file (không tự động xóa)"""
    try:
        file_path = os.path.join('uploads', filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File không tồn tại'}), 404
        
        # Xác định mimetype dựa trên extension
        if filename.lower().endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xls'):
            mimetype = 'application/vnd.ms-excel'
        elif filename.lower().endswith('.csv'):
            mimetype = 'text/csv'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        print(f"Error in download_file_only: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route: Get collections from MongoDB
@app.route('/api/collections')
def get_collections_api():
    """API endpoint để lấy danh sách collections từ MongoDB"""
    try:
        from pymongo import MongoClient
        import os
        
        # Kết nối MongoDB
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        
        # Lấy danh sách collections (loại trừ system collections và internal collections)
        # Collections bị loại trừ: system collections, batch_ids, generated_skus, logs
        excluded_collections = {'batch_ids', 'generated_skus', 'logs'}
        collections = []
        for collection_name in db.list_collection_names():
            if not collection_name.startswith('system.') and collection_name not in excluded_collections:
                collections.append(collection_name)
        
        print(f"Tìm thấy {len(collections)} collections: {collections}")
        
        return jsonify({
            'success': True,
            'collections': collections
        })
        
    except Exception as e:
        print(f"Error getting collections: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'collections': []
        }), 500

# Route: Download images to AWS S3
@app.route('/api/download-images-to-s3', methods=['POST'])
def download_images_to_s3():
    """API endpoint để download hình ảnh từ database lên AWS S3"""
    try:
        data = request.get_json()
        collection_name = data.get('collection')
        folder_name = data.get('folder_name', f'Product_Images_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        limit = data.get('limit', 50)  # Giới hạn số ảnh download
        
        if not collection_name:
            return jsonify({'success': False, 'error': 'Thiếu thông tin collection'}), 400
        
        # Import AWS S3 handler
        try:
            from aws_s3_handler import AWSS3Uploader
        except ImportError as e:
            return jsonify({
                'success': False, 
                'error': 'AWS S3 handler chưa được setup. Vui lòng cài đặt dependencies và credentials.'
            }), 500
        
        # Get products from database
        from walmart import get_products
        products = get_products(collection_name)
        
        if not products:
            return jsonify({'success': False, 'error': 'Không tìm thấy sản phẩm trong collection'}), 400
        
        # Filter products có hình ảnh
        products_with_images = []
        for product in products[:limit]:  # Giới hạn số lượng
            image_url = None
            
            # Check multiple possible image locations
            if product.get('image_url'):
                image_url = product.get('image_url')
            elif product.get('image'):
                image_url = product.get('image')
            elif product.get('hasVariant') and len(product['hasVariant']) > 0:
                # Check first variant for image
                variant = product['hasVariant'][0]
                if variant.get('image'):
                    image_url = variant.get('image')
            
            if image_url and image_url.strip():  # Make sure URL is not empty
                product_name = product.get('name', 'Unknown Product')
                
                # Tạo filename safe
                import re
                safe_filename = re.sub(r'[^\w\s-]', '', product_name)
                safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
                filename = f"{safe_filename}_{product.get('_id', 'unknown')}.jpg"
                
                products_with_images.append({
                    'url': image_url,
                    'filename': filename,
                    'product_name': product_name
                })
        
        print(f"Found {len(products_with_images)} products with images")
        
        if not products_with_images:
            return jsonify({'success': False, 'error': 'Không tìm thấy sản phẩm nào có hình ảnh'}), 400
        
        # Initialize AWS S3 uploader
        try:
            uploader = AWSS3Uploader()
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'error': 'AWS credentials không tìm thấy. Vui lòng setup AWS credentials.',
                'setup_guide': 'Cài đặt AWS credentials trong environment variables'
            }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Lỗi khi kết nối AWS S3: {str(e)}'
            }), 500
        
        # Batch upload images
        results = uploader.batch_upload_images(products_with_images, folder_name)
        
        # Prepare response
        response_data = {
            'success': True,
            'folder_name': folder_name,
            'total_products': len(products_with_images),
            'successful_uploads': results['success_count'],
            'failed_uploads': results['failed_count'],
            'uploaded_files': results['uploaded_files'],
            'failed_files': results['failed_files'],
            'folders_created': results.get('folders_created', []),
            'total_folders': len(results.get('folders_created', []))
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in download_images_to_s3: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Khởi tạo Smart Login System trước khi chạy app
    print("=" * 60)
    print("WALMART CRAWLER với Smart Login System")
    print("=" * 60)
    
    initialize_smart_login()
    
    print("=" * 60)
    print("Starting Flask App...")
    print("App URL: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
