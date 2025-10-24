import time
from multix import *
from selenium.webdriver.common.by import By
import json
from selenium.webdriver.common.keys import Keys
import re
import logging
import pandas as pd
from pymongo import MongoClient
import dotenv
import os
from bson import ObjectId
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    filename="error.log",  # Tên file log
    level=logging.ERROR,  # Chỉ ghi log từ mức ERROR trở lên
    format="%(asctime)s - %(levelname)s - %(message)s"
)

dotenv.load_dotenv()

# Kết nối MongoDB
def open_profile(proxy: str = None):
    global active_driver
    token = signin()
    HEADERS.update({"Authorization": f"Bearer {token}"})
    driver = start_quick_profile(proxy)
    active_driver = driver  # Gán driver đang hoạt động
    return driver

def check(driver):
    """
    Executes a JavaScript script on the web page to check for the presence of specific
    text content in paragraph (`<p>`) elements. The script identifies if any `<p>`
    element contains the text "Activate and hold" or "you’re human".

    The JavaScript used in this method operates as follows:
    1. Collects all `<p>` elements from the document using `document.querySelectorAll`.
    2. Checks if any paragraph element contains one of the specified strings.
    3. Logs a message in the browser console if such a paragraph is found.
    4. Returns `true` if the text is found, and `false` otherwise.

    The function sends the script to the browser driver for execution.

    :return:
        A boolean value returned by the JavaScript. `True` if a paragraph
        with the specified text exists, otherwise `False`.
    :rtype: bool
    """
    script = """
    let found = Array.from(document.querySelectorAll('p')).some(p => {
      if (p.textContent.includes('Activate and hold') || p.textContent.includes('you’re human')) {
        console.log('Found <p> with text:', p);
        return true;
      }
      return false;
    });
    return found; 
    """
    logging.error(f"check - {driver.current_url}: %s")
    return driver.execute_script(script)

def hold(driver, times):
    """
    Simulates a user holding down the SPACE key after navigating through elements using TAB.

    This function introduces a delay, iterates through a specified number of elements
    to shift focus using the TAB key, and then utilizes an action chain to simulate
    pressing and holding the SPACE key. After a fixed period, the key press is released.

    :param times: Number of times to press the TAB key to navigate between elements
    :type times: int
    :return: None
    """
    try:
        time.sleep(2)
        for _ in range(times):
            driver.switch_to.active_element.send_keys(Keys.TAB)
        actions = webdriver.ActionChains(driver)
        actions.key_down(Keys.SPACE).perform()
        logging.error(f"hold - {times}: %s")
        time.sleep(10)
        actions.key_up(Keys.SPACE).perform()
        logging.error(f"hold - {times}: %s")
        time.sleep(20)
    except Exception as e:
        logging.error(f"hold - {times}: %s", e)
        time.sleep(20)

def get_browse(driver, department):
    print("1")
    driver.get(department)
    if check(driver):
        logging.error(f"Captcha - {department}: %s")
        hold(driver, 2)
        driver.get('https://www.walmart.com')
        logging.error(f"reload - {department}: %s")
        get_browse(driver, department)
    links = driver.find_elements(By.TAG_NAME, "a")
    browse = [link.get_attribute("href") for link in links if
                     link.get_attribute("href") and link.get_attribute("href").startswith(
                         "https://www.walmart.com/browse/")]
    return browse

def get_page(driver, url):
    """
    Retrieve the number of the last page of a paginated website.

    This function navigates to the specified URL with a web driver, performs
    a check and conditional navigation to ensure proper website access, and
    determines the last page number of a paginated section on the website.
    If the last page element cannot be found, it defaults to 1.

    :param url: The URL of the website to navigate to and retrieve the information from
    :type url: str
    :return: The number of the last page of the paginated section
    :rtype: int
    """
    driver.get(url)
    if check(driver):
        logging.error(f"Captcha - {url}: %s")
        hold(driver, 3)
        driver.get('https://www.walmart.com')
        logging.error(f"reload - {url}: %s")
        get_page(driver, url)
    try:
        products_count = driver.find_element(By.CSS_SELECTOR, '#results-container > div.flex.flex-column > section > div > div > div > div > h1 > span').text
    except:
        products_count = driver.find_element(By.CSS_SELECTOR, '#results-container > div.flex.flex-column > section > div > div > div > div > h2 > span').text
                                                              ##results-container > div.flex.flex-column > section > div > div > div > div > h2 > span
    number = int(re.search(r"\d+", products_count).group())
    pages = number // 40
    if pages > 10:
        pages = 10
    print(pages)
    return int(pages)


def get_link(driver, url, page):
    """
    Fetches links from a specified page of a given URL, adjusting for pagination and sorting.

    This function navigates to a specific URL with pagination and sorting parameters. It retrieves
    all product links with a specific prefix. If conditions necessitate a retry (controlled by
    external methods 'check' and 'hold'), the function recursively calls itself to fetch the
    correct links.

    :param url: The base URL to navigate for fetching links.
    :type url: str
    :param page: The current page number to navigate for fetching links.
    :type page: int
    :return: A list of hyperlinks extracted from the specified page.
    :rtype: list[str]
    """
    driver.get(url+f'&page={page}')
    if check(driver):
        logging.error(f"Captcha - {url}: %s")
        hold(driver, 3)
        driver.get('https://www.google.com')
        time.sleep(3)
        get_link(driver, url, page)
    walmart_links = []
    for i in range(1,42):
        try:
            a_element = driver.find_element(By.CSS_SELECTOR, rf'#\30  > section > div > div:nth-child({i}) > div > div > a')
            href_link = a_element.get_attribute("href")
            walmart_links.append(href_link)
        except:
            pass
    print(walmart_links)
    return walmart_links

def extract_options(driver, link):
    driver.get(link)
    if check(driver):
        logging.error(f"Captcha - {link}: %s")
        hold(driver, 3)
        driver.get('https://www.google.com')
        time.sleep(3)
        extract_options(driver, link)
    # target_url = "/".join(link.split("/")[:-1])
    # link_elements = driver.find_elements(By.TAG_NAME, "link")
    # options = [link.get_attribute("href") for link in link_elements if
    #                  link.get_attribute("href") and link.get_attribute("href").startswith(target_url)]
    try:
        container = driver.find_element(By.CSS_SELECTOR, "#item-page-variant-group-bg-div > div.dn")
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi với {link}: %s", e)
        return ([])
    links = container.find_elements(By.TAG_NAME, "a")
    options = [link.get_attribute("href") for link in links]
    print(options)
    return options


def start_crawl(driver, collection, link, url):
    print("==> start_crawl called with link:", link)
    """
    Starts crawling a webpage to extract data and save it to a database.

    The function navigates to a given link, performs checks and interactions on the webpage, and retrieves
    specific data such as shipping information, seller details, and other structured data embedded using
    ld+json. The extracted data is then stored in a MongoDB collection, either by updating an
    existing document or inserting a new one.

    :param link: The URL of the webpage to crawl.
    :type link: str
    :return: None
    """
    try:
        if collection.find_one({"link": link}):
            print("Link đã có trong MongoDB, bỏ qua...")
            return link, 'đã tồn tại trong cơ sở dữ liệu', 'My heart and sword. Alway! For Demacia!'
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi với {link}: %s", e)
        return link, e, None
    try:
        current_url = driver.current_url
        if current_url != link:
            driver.get(link)
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi với {link}: %s", e)
        return link, e, None
    if check(driver):
        logging.error(f"Captcha - {link}: %s")
        hold(driver, 2)
        driver.get('https://www.google.com')
        time.sleep(3)
        start_crawl(driver,collection, link, url)
    
    
    try:
        script_tag = driver.find_element(By.XPATH, '//script[@type="application/ld+json"][1]')
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi với {link}: %s", e)
        return link, e, None
    print(script_tag)
    json_data = script_tag.get_attribute("innerHTML")
    try:
        brand_name = driver.find_element(By.XPATH, '//a[@data-seo-id="brand-name"]').text
        print("Brand name found:", brand_name)
    except Exception as e:
        print("Brand name not found:", e)
        brand_name = "None"
    try:
        shipping = driver.find_element(By.CSS_SELECTOR, 'div:nth-child(1) > div > div > div:nth-child(9) > section > div > div > section:nth-child(1) > div > fieldset > div > div:nth-child(1) > span > label > div.f7.green.mt1.ws-normal.ttn.tc').text
    except:
        shipping = "None"
    try:
        shipping_intent = driver.find_element(By.CSS_SELECTOR, "div:nth-child(1) > div > div > div:nth-child(9) > section > div > div > section:nth-child(1) > div > fieldset > div > div:nth-child(1) > span > label > div.f7.mt1.ws-normal.ttn.b").text
    except:
        shipping_intent = "None"
    try:
        select = driver.find_elements(By.XPATH, '//*[not(self::script) and contains(text(), "selected")]')
        selected = [i.text for i in select]
    except:
        selected = []

    data = []

    try:
        compare = driver.find_element(By.CSS_SELECTOR, 'span.mb1 > span:nth-child(1) > button:nth-child(1)')
        compare.click()
        if check(driver):
            logging.error(f"Captcha - {link}: %s")
            hold(driver, 3)
            driver.get('https://www.google.com')
            time.sleep(3)
            start_crawl(driver, collection, link, url)
        time.sleep(3)
        # Chạy JavaScript trong trình duyệt để lấy số lượng div con
        js_script = """
        let parentElement = document.querySelector("div > div.w_GwjJ > div.w_uWu2.w_tZIt > div > div.w_g1_b > div > div > div");
        if (parentElement) {
            return parentElement.querySelectorAll(":scope > div").length;
        } else {
            return 2;
        }
        """
        child_div_count = driver.execute_script(js_script)
        print(child_div_count)
        for i in range(2,child_div_count+1):
            price = driver.find_element(By.XPATH, f'/html/body/div[2]/div/div[2]/div[1]/div/div[2]/div/div/div/div[{i}]/div/div[1]/div/div[1]/span/div/div').text
            shipping = driver.find_element(By.XPATH,f'/html/body/div[2]/div/div[2]/div[1]/div/div[2]/div/div/div/div[{i}]/div/div[1]/div/div[2]/span/div/span').text
            seller = driver.find_element(By.XPATH, f'/html/body/div[2]/div/div[2]/div[1]/div/div[2]/div/div/div/div[{i}]/div/div[1]/div/div[4]/div[1]/span/div/span/a')
            seller_link = seller.get_attribute('href')
            seller_name = seller.text
            ret = driver.find_element(By.XPATH, f'/html/body/div[2]/div/div[2]/div[1]/div/div[2]/div/div/div/div[{i}]/div/div[1]/div/div[4]/div[2]/span').text
            print(price)
            data.append({
                "price": price,
                "shipping": shipping,
                "seller": seller_name,
                "retailer": seller_link,
                "return": ret
            })
    except:
        print("không có seller options")
    try:
        json_dict = json.loads(json_data)
        if isinstance(json_dict, list):
            json_dict = json_dict[0]

        try:
            json_dict['product_type'] = re.search(r'browse/([^/]+)/([^/]+)', url).group(2)
        except:
            try:
                json_dict['product_type'] = re.search(r"q=([^&]+)", url).group(1)
            except:
                json_dict['product_type'] = "None"             
        json_dict['brand_name'] = brand_name
        json_dict['options'] = selected
        json_dict['link'] = link
        json_dict['shipping'] = shipping
        json_dict['shipping_intent'] = shipping_intent
        json_dict['reseller'] = data
        json_dict.pop('review', None)
        print("Saving to MongoDB:", json_dict)
        collection.update_one(
            {"link": json_dict.get("link")},
            {"$set": json_dict},
            upsert=True
        )

        print("Dữ liệu đã được lưu vào MongoDB")
        return link, "thành công", json_dict

    except Exception as e:
        print(f"Lỗi khi xử lý {link}: {e}")
        logging.error(f"Đã xảy ra lỗi với {link}: %s", e)
        return link, e, None

def get_products(collection_name):
    """
    Lấy danh sách sản phẩm từ MongoDB collection
    
    Args:
        collection_name (str): Tên collection MongoDB
    
    Returns:
        list: Danh sách sản phẩm
    """
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        collection = db[collection_name]
        
        # Debug info
        print(f"Checking collection '{collection_name}' in database 'walmart'")
        
        # Kiểm tra collection có tồn tại không
        if collection_name not in db.list_collection_names():
            print(f"Collection '{collection_name}' không tồn tại trong database 'walmart'")
            print(f"Available collections: {db.list_collection_names()}")
            return []
        
        # Đếm tổng số documents
        total_count = collection.count_documents({})
        print(f"Collection '{collection_name}' có {total_count} documents tổng cộng")
        
        # Lấy tất cả sản phẩm, bao gồm fields cần thiết cho images
        products = list(collection.find({}, {
            'name': 1, 
            '_id': 1,  # Cần _id cho filename 
            'image': 1, 
            'image_url': 1, 
            'hasVariant': 1  # Cần hasVariant để lấy images
        }))
        
        # Debug chi tiết
        products_with_name = [p for p in products if p.get('name')]
        print(f"Đã lấy {len(products)} documents, {len(products_with_name)} có field 'name'")
        
        if len(products) > 0:
            print(f"Sample data: {products[0]}")
        
        print(f"Returning {len(products_with_name)} products with names")
        return products
        
    except Exception as e:
        print(f"Error getting products from collection '{collection_name}': {str(e)}")
        return []

def get_trademark_collection():
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client['test']
    return db['trademark_ids']

def generate_unique_sku():
    """
    Tạo SKU unique 50 ký tự (chữ + số)
    Kiểm tra duplicate với database và lưu vào database
    """
    import random
    import string
    
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        sku_collection = db['generated_skus']  # Collection lưu SKU đã sinh
        
        # Characters để sinh SKU: chữ hoa + chữ thường + số
        chars = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
        
        max_attempts = 100  # Tối đa 100 lần thử
        
        for attempt in range(max_attempts):
            # Sinh SKU với cryptographically secure random (mạnh hơn UUID4)
            import secrets
            sku = ''.join(secrets.choice(chars) for _ in range(50))
            
            # Kiểm tra trùng lặp trong database
            existing = sku_collection.find_one({'sku': sku})
            
            if not existing:
                # SKU chưa tồn tại -> Lưu vào database và return
                sku_collection.insert_one({
                    'sku': sku,
                    'created_at': datetime.now(),
                    'used_count': 0
                })
                
                print(f"Generated unique SKU: {sku}")
                return sku
            else:
                print(f"SKU collision detected (attempt {attempt + 1}): {sku}")
        
        # Nếu sau 100 lần vẫn trùng -> fallback với timestamp (vẫn dùng secure random)
        import time
        import secrets
        timestamp_suffix = str(int(time.time() * 1000000))[-10:]  # 10 số cuối của microsecond
        sku = ''.join(secrets.choice(chars) for _ in range(40)) + timestamp_suffix
        
        sku_collection.insert_one({
            'sku': sku,
            'created_at': datetime.now(),
            'used_count': 0,
            'fallback': True
        })
        
        print(f"Generated fallback SKU: {sku}")
        return sku
        
    except Exception as e:
        print(f"Error generating SKU: {str(e)}")
        # Emergency fallback
        import time
        import uuid
        return f"SKU_{int(time.time())}_{str(uuid.uuid4())[:8]}".upper()[:50]

def mark_sku_used(sku):
    """
    Đánh dấu SKU đã được sử dụng trong database
    """
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        sku_collection = db['generated_skus']
        
        # Tăng used_count
        result = sku_collection.update_one(
            {'sku': sku},
            {
                '$inc': {'used_count': 1},
                '$set': {'last_used_at': datetime.now()}
            }
        )
        
        if result.modified_count > 0:
            print(f"Marked SKU as used: {sku}")
        else:
            print(f"Warning: SKU not found in database: {sku}")
            
    except Exception as e:
        print(f"Error marking SKU as used: {str(e)}")

def generate_batch_id():
    """
    Tạo Batch ID 5 ký tự unique cho mỗi lần fill file
    Tất cả dòng trong file sẽ có cùng Batch ID này 
    """
    import secrets
    import string
    
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        batch_collection = db['batch_ids']  # Collection lưu Batch ID đã sinh
        
        # Characters để sinh Batch ID: chữ hoa + số
        chars = string.ascii_uppercase + string.digits  # A-Z, 0-9
        
        max_attempts = 50  # Tối đa 50 lần thử (ít hơn SKU vì chỉ 5 ký tự)
        
        for attempt in range(max_attempts):
            # Sinh Batch ID với cryptographically secure random 5 ký tự
            batch_id = ''.join(secrets.choice(chars) for _ in range(5))
            
            # Kiểm tra trùng lặp trong database
            existing = batch_collection.find_one({'batch_id': batch_id})
            
            if not existing:
                # Batch ID chưa tồn tại -> Lưu vào database và return
                batch_record = {
                    'batch_id': batch_id,
                    'created_at': datetime.now(),
                    'used_count': 0,
                    'file_count': 0
                }
                batch_collection.insert_one(batch_record)
                
                print(f"Generated unique Batch ID: {batch_id}")
                return batch_id
            else:
                print(f"Batch ID collision detected (attempt {attempt + 1}): {batch_id}")
        
        # Nếu sau 50 lần vẫn trùng -> fallback với timestamp
        import time
        timestamp_suffix = str(int(time.time() * 1000))[-2:]  # 2 số cuối của timestamp
        batch_id = ''.join(secrets.choice(chars) for _ in range(3)) + timestamp_suffix
        
        batch_record = {
            'batch_id': batch_id,
            'created_at': datetime.now(),
            'used_count': 0,
            'file_count': 0,
            'fallback': True
        }
        batch_collection.insert_one(batch_record)
        
        print(f"Generated fallback Batch ID: {batch_id}")
        return batch_id
        
    except Exception as e:
        print(f"Error generating Batch ID: {str(e)}")
        # Emergency fallback với timestamp
        import time
        return f"B{str(int(time.time()))[-4:]}"  # B + 4 số cuối timestamp

def mark_batch_used(batch_id, rows_filled):
    """
    Đánh dấu Batch ID đã được sử dụng và cập nhật thống kê
    """
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        db = client['walmart']
        batch_collection = db['batch_ids']
        
        # Tăng used_count và file_count
        result = batch_collection.update_one(
            {'batch_id': batch_id},
            {
                '$inc': {
                    'used_count': rows_filled,
                    'file_count': 1
                },
                '$set': {'last_used_at': datetime.now()}
            }
        )
        
        if result.modified_count > 0:
            print(f"Marked Batch ID as used: {batch_id} ({rows_filled} rows)")
        else:
            print(f"Warning: Batch ID not found in database: {batch_id}")
            
    except Exception as e:
        print(f"Error marking Batch ID as used: {str(e)}")

def get_trademark_ids():
    collection = get_trademark_collection()
    document_id = ObjectId("68495b762247e71fc1652dab")

    doc = collection.find_one({"_id": document_id})
    if doc and "trademarks" in doc:
        return doc["trademarks"]
    return []

def add_trademark_id(new_id):
    if not new_id:
        return {"success": False, "message": "ID không được để trống"}
    
    collection = get_trademark_collection()
    document_id = ObjectId("68495b762247e71fc1652dab")

    current_ids = set(get_trademark_ids())
    if new_id in current_ids:
        return {"success": False, "message": "ID đã tồn tại"}

    current_ids.add(new_id)
    collection.replace_one(
        {"_id":document_id},
        {"trademarks":list(current_ids)}
    )
    return {"success":True, "message":"Thêm thành công", "total":len(current_ids)}

def upload_excel_trademark_ids(file_path):
    try:
        df = pd.read_excel(file_path)
        if "Item ID" not in df.columns:
            return {"success": False, "message":" Not found Item ID column"}

        item_ids = df["Item ID"].dropna().astype(str).tolist()
        current_ids = set(get_trademark_ids())
        new_ids = [id for id in item_ids if id not in current_ids]

        if new_ids:
            all_ids = current_ids.union(new_ids)
            collection = get_trademark_collection()
            document_id = ObjectId("68495b762247e71fc1652dab")
            collection.replace_one(
                {"_id":document_id},
                {"trademarks":list(all_ids)}
            )
        return {
            "success": True,
            "message":f"Upload success ! Add {len(new_ids)} new IDs to database",
            "total excel": len(item_ids),
            "new_added":len(new_ids),
            "total_after":len(all_ids) if new_ids else len(current_ids)
        }
    except Exception as e:
        return {"success":False, "message":f"Error: {e}"}

def delete_trademark_id(id):
    collection = get_trademark_collection()
    document_id = ObjectId("68495b762247e71fc1652dab")
    current_ids = set(get_trademark_ids())
    if id not in current_ids:
        return {"success":False, "message":f"ID {id} never exists"}
    
    current_ids.remove(id)
    collection.replace_one(
        {"_id":document_id},
        {"trademarks":list(current_ids)}
    )
    return {"success":True, "message":f"Delete {id} success !", "total":len(current_ids)}