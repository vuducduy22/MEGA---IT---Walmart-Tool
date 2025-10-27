from selenium import webdriver
import undetected_chromedriver as uc
from config import *
import requests
import hashlib
import json
import logging
import time
import pyotp
from datetime import datetime, timedelta
from selenium.webdriver.chromium.options import ChromiumOptions
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class MultiloginService:
    """Service class cho việc xử lý đăng nhập và quản lý Multilogin"""
    
    def __init__(self, email=None, password=None, secret_2fa=None, workspace_id=None, workspace_email=None):
        """
        Khởi tạo MultiloginService
        
        Args:
            email: Email đăng nhập chính
            password: Mật khẩu 
            secret_2fa: Secret key cho 2FA (TOTP)
            workspace_id: ID của workspace cần chuyển đến
            workspace_email: Email của workspace
        """
        self.email = email or USERNAME
        self.password = password or PASSWORD
        self.secret_2fa = secret_2fa
        self.workspace_id = workspace_id or WORKSPACE_ID
        self.workspace_email = workspace_email
        self.base_url = MLX_BASE
        
        # Tokens
        self.auth_token = None
        self.refresh_token = None
        self.workspace_token = None
        self.automation_token = None
        
        # Session để tái sử dụng connections với SSL configuration
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        # Cấu hình SSL và retry strategy
        self._configure_ssl_session()
    
    def _configure_ssl_session(self):
        """Cấu hình SSL session để xử lý lỗi SSL"""
        try:
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Tạo retry strategy với exponential backoff
            retry_strategy = Retry(
                total=5,  # Tăng số lần retry
                backoff_factor=2,  # Tăng thời gian chờ giữa các retry
                status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
                method_whitelist=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
                raise_on_status=False  # Không raise exception khi gặp status code trong list
            )
            
            # Tạo adapter với SSL configuration
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,  # Tăng pool connections
                pool_maxsize=50,  # Tăng pool maxsize
                pool_block=False  # Không block khi pool đầy
            )
            
            # Mount adapter cho HTTP và HTTPS
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Cấu hình SSL verification
            self.session.verify = False  # Tạm thời disable SSL verification
            
            # Set timeout ngắn hơn để tránh hang
            self.session.timeout = 10  # Giảm timeout xuống 10 giây
            
            # Thêm User-Agent để tránh bị block
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            logging.info("SSL session configured with enhanced retry strategy and timeout")
            
        except Exception as e:
            logging.error(f"Error configuring SSL session: {e}")
            # Fallback configuration
            self.session.verify = False
            self.session.timeout = 30
    
    def signin(self):
        """Đăng nhập vào tài khoản Multilogin"""
        try:
            # Hash password với MD5
            hashed_password = hashlib.md5(self.password.encode('utf-8')).hexdigest()
            
            url = f"{self.base_url}/user/signin"
            data = {
                "email": self.email,
                "password": hashed_password
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            status = result.get('status', {})
            message = status.get('message', '')
            
            # Kiểm tra nếu cần 2FA
            if message == "Proceed to 2FA":
                data_response = result.get('data', {})
                self.auth_token = data_response.get('token')
                self.refresh_token = data_response.get('refresh_token')
                logging.info("Cần xác thực 2FA")
                return {
                    'success': True,
                    'requires_2fa': True,
                    'token': self.auth_token,
                    'refresh_token': self.refresh_token
                }
            
            # Kiểm tra đăng nhập thành công không cần 2FA
            if status.get('http_code') == 200 and message == "Successful signin":
                data_response = result.get('data', {})
                self.auth_token = data_response.get('token')
                self.refresh_token = data_response.get('refresh_token')
                # Cập nhật headers cho các request tiếp theo
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                logging.info("Đăng nhập thành công")
                return {
                    'success': True,
                    'token': self.auth_token,
                    'refresh_token': self.refresh_token
                }
                
        except Exception as e:
            logging.error(f"Lỗi đăng nhập: {str(e)}")
            return {'success': False, 'error': str(e)}

    def verify_2fa(self):
        """Xác thực 2FA"""
        if not self.secret_2fa:
            return {'success': False, 'error': 'Chưa cung cấp secret 2FA'}
            
        try:
            totp = pyotp.TOTP(self.secret_2fa)
            otp_code = totp.now()
            
            url = f"{self.base_url}/user/verify_2fa_otp"
            data = {
                "temp_token": self.auth_token,
                "totp_code": otp_code,
                "is_backup": False
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            status = result.get('status', {})
            
            if status.get('http_code') == 200 and status.get('message') == "Successful signin":
                data_response = result.get('data', {})
                self.auth_token = data_response.get('token')
                self.refresh_token = data_response.get('refresh_token')
                # Cập nhật headers
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                logging.info("Xác thực 2FA thành công")
                return {
                    'success': True,
                    'token': self.auth_token,
                    'refresh_token': self.refresh_token
                }
            else:
                error_msg = status.get('message', 'Xác thực 2FA thất bại')
                logging.error(f"2FA thất bại: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logging.error(f"Lỗi xác thực 2FA: {str(e)}")
            return {'success': False, 'error': str(e)}

    def switch_workspace(self):
        """Chuyển đến workspace cụ thể"""
        try:
            url = f"{self.base_url}/user/refresh_token"
            
            data = {
                "email": self.workspace_email or self.email,
                "refresh_token": self.refresh_token,
                "workspace_id": self.workspace_id
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.auth_token}'
            }
            
            response = self.session.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status', {}).get('http_code') == 200:
                data_response = result.get('data', {})
                self.workspace_token = data_response.get('token')
                # Cập nhật headers với workspace token
                self.session.headers.update({"Authorization": f"Bearer {self.workspace_token}"})
                logging.info(f"Chuyển workspace thành công: {self.workspace_id}")
                return {
                    'success': True,
                    'workspace_token': self.workspace_token
                }
            else:
                error_msg = result.get('status', {}).get('message', 'Chuyển workspace thất bại')
                logging.error(f"Chuyển workspace thất bại: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logging.error(f"Lỗi khi chuyển workspace: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_automation_token(self, expiration_period="no_exp"):
        """
        Lấy automation token cho các thao tác với browser
        
        Args:
            expiration_period: Thời gian hết hạn ("no_exp" hoặc "no_exp")
        """
        try:
            url = f"{self.base_url}/workspace/automation_token"
            params = {
                "expiration_period": expiration_period
            }
            
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.workspace_token}'
            }
            
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status', {}).get('http_code') == 200:
                data_response = result.get('data', {})
                self.automation_token = data_response.get('token')
                
                logging.info("Lấy automation token thành công")
                return {
                    'success': True,
                    'automation_token': self.automation_token
                }
            else:
                error_msg = result.get('status', {}).get('message', 'Lấy automation token thất bại')
                logging.error(f"Lấy automation token thất bại: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logging.error(f"Lỗi khi lấy automation token: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def full_login_process(self):
        """Thực hiện toàn bộ quy trình đăng nhập"""
        print("🔐 Bắt đầu quy trình đăng nhập...")
        
        # Bước 1: Đăng nhập
        login_result = self.signin()
        if not login_result['success']:
            print(f"❌ Đăng nhập thất bại: {login_result['error']}")
            return login_result

        # Bước 2: Xác thực 2FA (nếu cần)
        if login_result.get('requires_2fa'):
            print("🔢 Đang xác thực 2FA...")
            verify_result = self.verify_2fa()
            if not verify_result['success']:
                print(f"❌ Xác thực 2FA thất bại: {verify_result['error']}")
                return verify_result
            print("✅ Xác thực 2FA thành công")

        # Bước 3: Chuyển workspace (nếu có)
        if self.workspace_id:
            print("🔄 Đang chuyển workspace...")
            switch_result = self.switch_workspace()
            if not switch_result['success']:
                print(f"❌ Chuyển workspace thất bại: {switch_result['error']}")
                return switch_result
            print("✅ Chuyển workspace thành công")

        # Bước 4: Lấy automation token
        print("🎫 Đang lấy automation token...")
        token_result = self.get_automation_token()
        if not token_result['success']:
            print(f"❌ Lấy automation token thất bại: {token_result['error']}")
            return token_result
        
        print("✅ Hoàn thành quy trình đăng nhập!")
        print(f"🎯 Automation token: {token_result['automation_token'][:20]}...")
        
        # Cập nhật headers toàn cục
        HEADERS.update({"Authorization": f"Bearer {self.workspace_token or self.auth_token}"})
        
        # Lưu automation_token vào database để sử dụng lại
        if self.automation_token:
            save_automation_token_to_db(
                workspace_id=self.workspace_id,
                email=self.workspace_email or self.email,
                automation_token=self.automation_token,
                expiration_period="no_exp"
            )
        
        return {
            'success': True,
            'auth_token': self.auth_token,
            'refresh_token': self.refresh_token,
            'workspace_token': self.workspace_token,
            'automation_token': self.automation_token
        }
    
    def get_cached_automation_token(self):
        """Lấy automation_token từ cache/database nếu còn hạn"""
        try:
            cached_token = get_automation_token_from_db(
                workspace_id=self.workspace_id,
                email=self.workspace_email or self.email
            )
            
            if cached_token and is_token_valid(cached_token):
                self.automation_token = cached_token['token']
                logging.info("✅ Sử dụng cached automation token")
                return {
                    'success': True,
                    'automation_token': self.automation_token,
                    'from_cache': True
                }
            else:
                logging.info("🔄 Cached token hết hạn hoặc không tồn tại")
                return {'success': False, 'error': 'Token không hợp lệ hoặc hết hạn'}
                
        except Exception as e:
            logging.error(f"Lỗi khi lấy cached token: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def smart_login_process(self):
        """Quy trình đăng nhập thông minh - ưu tiên sử dụng cached token"""
        print("🧠 Bắt đầu quy trình đăng nhập thông minh...")
        
        # Bước 1: Kiểm tra cached automation token
        print("🔍 Kiểm tra automation token có sẵn...")
        cached_result = self.get_cached_automation_token()
        
        if cached_result['success']:
            print("⚡ Sử dụng automation token có sẵn - Bỏ qua đăng nhập!")
            print(f"🎯 Automation token: {cached_result['automation_token'][:20]}...")
            
            # Cập nhật headers toàn cục
            HEADERS.update({"Authorization": f"Bearer {self.automation_token}"})
            
            return {
                'success': True,
                'automation_token': self.automation_token,
                'from_cache': True,
                'message': 'Sử dụng cached token'
            }
        
        # Bước 2: Nếu không có token hợp lệ, thực hiện full login
        print("🔐 Không có token hợp lệ - Thực hiện đăng nhập đầy đủ...")
        return self.full_login_process()


# ============================================================================
# DATABASE FUNCTIONS - Quản lý Automation Token
# ============================================================================

def save_automation_token_to_db(workspace_id, email, automation_token, expiration_period="no_exp"):
    """
    Lưu automation_token vào MongoDB với thông tin thời hạn
    
    Args:
        workspace_id: ID của workspace
        email: Email của user
        automation_token: Token cần lưu
        expiration_period: Thời gian hết hạn ("no_exp")
    """
    try:
        # Tính toán expiration_date
        if expiration_period == "no_exp":
            expiration_date = datetime.now() + timedelta(days=365)
        else:  # "no_exp" hoặc mặc định
            expiration_date = datetime.now() + timedelta(days=30)
        
        # Tạo document để lưu
        token_doc = {
            "workspace_id": workspace_id,
            "email": email,
            "automation_token": automation_token,
            "expiration_period": expiration_period,
            "expiration_date": expiration_date,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Sử dụng upsert để update hoặc insert
        collection_log.update_one(
            {
                "workspace_id": workspace_id,
                "email": email,
                "type": "automation_token"
            },
            {
                "$set": {
                    **token_doc,
                    "type": "automation_token"
                }
            },
            upsert=True
        )
        
        logging.info(f"Đã lưu automation token vào database - expires: {expiration_date}")
        print(f"Đã lưu automation token vào database")
        
    except Exception as e:
        logging.error(f"Lỗi khi lưu automation token: {str(e)}")
        print(f" Lỗi khi lưu token: {str(e)}")


def get_automation_token_from_db(workspace_id, email):
    """
    Lấy automation_token từ MongoDB
    
    Args:
        workspace_id: ID của workspace
        email: Email của user
        
    Returns:
        Dict chứa token info hoặc None
    """
    try:
        token_doc = collection_log.find_one({
            "workspace_id": workspace_id,
            "email": email,
            "type": "automation_token"
        })
        
        if token_doc:
            logging.info(f"Tìm thấy automation token trong database")
            return {
                "token": token_doc.get("automation_token"),
                "expiration_date": token_doc.get("expiration_date"),
                "expiration_period": token_doc.get("expiration_period"),
                "created_at": token_doc.get("created_at")
            }
        else:
            logging.info(f"Không tìm thấy automation token trong database")
            return None
            
    except Exception as e:
        logging.error(f"Lỗi khi lấy automation token: {str(e)}")
        return None


def is_token_valid(token_info):
    """
    Kiểm tra automation_token còn hạn sử dụng không
    
    Args:
        token_info: Dict chứa thông tin token từ database
        
    Returns:
        bool: True nếu token còn hạn
    """
    try:
        if not token_info or not token_info.get("token"):
            return False
            
        expiration_date = token_info.get("expiration_date")
        if not expiration_date:
            return False
            
        # Kiểm tra thời hạn với buffer 1 ngày để tránh token hết hạn đột ngột
        buffer_time = datetime.now() + timedelta(days=1)
        
        if expiration_date > buffer_time:
            remaining_days = (expiration_date - datetime.now()).days
            logging.info(f"Token còn hạn {remaining_days} ngày")
            return True
        else:
            logging.info(f"Token đã hết hạn hoặc sắp hết hạn")
            return False
            
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra token validity: {str(e)}")
        return False


def clean_expired_tokens():
    """Xóa các token đã hết hạn từ database"""
    try:
        result = collection_log.delete_many({
            "type": "automation_token",
            "expiration_date": {"$lt": datetime.now()}
        })
        
        if result.deleted_count > 0:
            logging.info(f"Đã xóa {result.deleted_count} token hết hạn")
            print(f"Đã xóa {result.deleted_count} token hết hạn")
            
    except Exception as e:
        logging.error(f"Lỗi khi xóa expired tokens: {str(e)}")


# Tạo instance global của service
ml_service = None


def initialize_multilogin_service(email=None, password=None, secret_2fa=None, workspace_id=None, workspace_email=None, use_smart_login=True):
    """
    Khởi tạo và đăng nhập MultiloginService
    
    Args:
        use_smart_login: Nếu True, sử dụng cached token trước khi đăng nhập mới
    """
    global ml_service
    
    # Dọn dẹp expired tokens trước khi bắt đầu
    clean_expired_tokens()
    
    ml_service = MultiloginService(
        email=email,
        password=password,
        secret_2fa=secret_2fa,
        workspace_id=workspace_id,
        workspace_email=workspace_email
    )
    
    if use_smart_login:
        return ml_service.smart_login_process()
    else:
        return ml_service.full_login_process()


# Các hàm wrapper để tương thích với code cũ
def signin() -> str:
    """Wrapper function để tương thích với code cũ"""
    global ml_service
    
    if not ml_service:
        ml_service = MultiloginService()
    
    result = ml_service.signin()
    if not result['success']:
        logging.error(f"Error during login: {result['error']}")
        print(f"Error during login: {result['error']}")
        return None, None
    
    token = result.get('token')
    refresh_token = result.get('refresh_token')
    HEADERS.update({"Authorization": f"Bearer {token}"})
    return token, refresh_token


def switch_workspace(refresh_token: str) -> str:
    """Wrapper function để tương thích với code cũ"""
    global ml_service
    
    if not ml_service:
        ml_service = MultiloginService()
        ml_service.refresh_token = refresh_token
    
    result = ml_service.switch_workspace()
    if not result['success']:
        logging.error(f"Error during workspace switch: {result['error']}")
        print(f"Error during workspace switch: {result['error']}")
        return None
    
    token = result.get('workspace_token')
    HEADERS.update({"Authorization": f"Bearer {token}"})
    return token


def get_status(p):
    try:
        ssl_session = create_ssl_session()
        r = ssl_session.get(f"{MLX_LAUNCHER}/profile/status/p/{p}")
    except Exception as e:
        print(f"SSL Error in get_status: {e}")
        r = requests.get(f"{MLX_LAUNCHER}/profile/status/p/{p}", headers=HEADERS, verify=False)
    response = r.json()
    return response["data"]["status"]

def get_port(p):
    r = requests.post(
        f"https://api.multilogin.com/profile/metas",
        json = {"ids": p},
        headers = HEADERS,
    )
    response = r.json()
    port = response["data"]["profiles"][0]["parameters"]["proxy"]["port"]
    return port

def start_profile(p) -> webdriver:
    try:
        ssl_session = create_ssl_session()
        r = ssl_session.get(f"{MLX_LAUNCHER_V2}/profile/f/{FOLDER_ID}/p/{p}/start?automation_type=selenium")
    except Exception as e:
        print(f"SSL Error in start_profile: {e}")
        r = requests.get(f"{MLX_LAUNCHER_V2}/profile/f/{FOLDER_ID}/p/{p}/start?automation_type=selenium", headers=HEADERS, verify=False)
    response = r.json()
    if r.status_code != 200:
        print(f"\nError while starting profile: {r.text}\n")
    else:
        print(f"\nProfile {p} started.\n")
    selenium_port = response["data"]["port"]
    options = ChromiumOptions()
    options.add_argument("--headless")
    driver = webdriver.Remote(
        command_executor=f"{LOCALHOST}:{selenium_port}", options=options
    )
    return driver


def stop_profile(p) -> None:
    try:
        ssl_session = create_ssl_session()
        r = ssl_session.get(f"{MLX_LAUNCHER}/profile/stop/p/{p}")
    except Exception as e:
        print(f"SSL Error in stop_profile: {e}")
        r = requests.get(f"{MLX_LAUNCHER}/profile/stop/p/{p}", headers=HEADERS, verify=False)
    if r.status_code != 200:
        print(f"\nError while stopping profile: {r.text}\n")
    else:
        print(f"\nProfile {p} stopped.\n")


def create_ssl_session():
    """Tạo session với SSL configuration để xử lý lỗi SSL"""
    session = requests.Session()
    
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Tạo retry strategy với exponential backoff
    retry_strategy = Retry(
        total=5,  # Tăng số lần retry
        backoff_factor=2,  # Tăng thời gian chờ giữa các retry
        status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        raise_on_status=False  # Không raise exception khi gặp status code trong list
    )
    
    # Tạo adapter với SSL configuration
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,  # Tăng pool connections
        pool_maxsize=50,  # Tăng pool maxsize
        pool_block=False  # Không block khi pool đầy
    )
    
    # Mount adapter cho HTTP và HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Cấu hình SSL verification
    session.verify = False  # Tạm thời disable SSL verification
    
    # Set timeout ngắn hơn để tránh hang
    session.timeout = 10  # Giảm timeout xuống 10 giây
    
    # Set headers
    session.headers.update(HEADERS)
    
    # Thêm User-Agent để tránh bị block
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return session

def check_mlx_launcher_ready(max_wait=10):
    """Kiểm tra MLX Launcher có sẵn sàng nhận request không"""
    print(f"Kiểm tra MLX Launcher có sẵn sàng tại {MLX_LAUNCHER}...")
    
    for i in range(max_wait):
        try:
            # Test với một GET request đơn giản
            response = requests.get(
                f"{MLX_LAUNCHER}/profile/statuses", 
                headers=HEADERS, 
                timeout=5,
                verify=False  # Disable SSL verification
            )
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print("MLX Launcher sẵn sàng!")
                return True
            else:
                print(f"Status {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")
            pass
        
        if i < max_wait - 1:
            print(f"Đợi MLX Launcher sẵn sàng ({i+1}/{max_wait})...")
            time.sleep(1)
    
    print(f"MLX Launcher chưa sẵn sàng sau 10 giây")
    return False

def start_quick_profile(proxy: str = None):
    # Kiểm tra MLX Launcher có sẵn sàng không
    if not check_mlx_launcher_ready():
        return None, {
            "error": True,
            "status_code": 503,
            "error_code": "SERVICE_UNAVAILABLE",
            "message": "MLX Launcher chưa sẵn sàng. Vui lòng đợi vài giây.",
            "detailed_message": f"MLX Launcher không phản hồi sau 10 giây. URL: {MLX_LAUNCHER}/profile/statuses",
            "suggestion": [
                "Đợi 10-20 giây và thử lại",
                "Kiểm tra logs MLX: docker exec wm-mega-app tail -f /app/logs/mlx.log",
                "Restart MLX: docker-compose restart wm-mega"
            ]
        }
    
    
    payload = {
        "browser_type": "mimic",
        "name": "QuickProfile",
        "os_type": "linux",
        "automation": "selenium",
        "is_headless": True,
        "browser_version": "mimic_141.3",
        "core_version": 141,
        "parameters": {
            "fingerprint": {},
            "flags": {
                "navigator_masking": "mask",
                "audio_masking": "mask",
                "localization_masking": "mask",
                "geolocation_popup": "prompt",
                "geolocation_masking": "mask",
                "timezone_masking": "mask",
                "graphics_noise": "mask",
                "graphics_masking": "mask",
                "webrtc_masking": "mask",
                "fonts_masking": "mask",
                "media_devices_masking": "mask",
                "screen_masking": "mask",
                "proxy_masking": "disabled" if proxy is None else "custom",
                "ports_masking": "mask",
                "canvas_noise": "mask",
                "startup_behavior": "custom"
            },
            "storage": {
                "is_local": False,
                "save_service_worker": True
            },
            "custom_start_urls": [
                "https://www.google.com/"
            ]
        },
        "quickProfilesCount": 1
    }
    
    if proxy is not None:
        proxy_parts = proxy.split(":")
        if len(proxy_parts) >= 2:
            # Format: host:port hoặc host:port:username:password hoặc host:port:username:password:extras
            # Proxy phải nằm trong parameters, không phải root level
            payload["parameters"]["proxy"] = {
                "host": proxy_parts[0],
                "type": "http",
                "port": int(proxy_parts[1])
            }
            # Thêm username/password nếu có
            if len(proxy_parts) >= 4:
                payload["parameters"]["proxy"]["username"] = proxy_parts[2]
                payload["parameters"]["proxy"]["password"] = proxy_parts[3]
        else:
            raise ValueError(f"Invalid proxy format: {proxy}. Expected format: 'host:port' or 'host:port:username:password'")
    
    # Tạo 2 phiên bản payload: full (cho local) và minimal (cho server)
    payload_full = payload.copy()
    payload_minimal = {
        "browser_type": payload["browser_type"],
        "os_type": payload["os_type"],
        "automation": payload["automation"],
        "is_headless": payload["is_headless"],
        "browser_version": payload.get("browser_version", "mimic_141.3"),
        "core_version": payload.get("core_version", 141),
        "parameters": {
            "flags": payload["parameters"]["flags"],
            "storage": payload["parameters"]["storage"],
            "custom_start_urls": payload["parameters"]["custom_start_urls"]
        }
    }
    
    # Add proxy if exists - proxy phải nằm trong parameters
    if "proxy" in payload.get("parameters", {}):
        payload_minimal["parameters"]["proxy"] = payload["parameters"]["proxy"]
    
    # Debug: In cả 2 payloads
    print("📦 Payload FULL:", json.dumps(payload_full, indent=2))
    print("📦 Payload MINIMAL:", json.dumps(payload_minimal, indent=2))
    
    # MLX Launcher chạy trên IPv6 (:::45001), CHỈ chấp nhận HTTPS!
    # Thứ tự ưu tiên: IPv6 -> IPv4
    urls_to_try = [
        f"https://[::1]:45001/api/v2/profile/quick",  # IPv6 localhost - ƯU TIÊN
        f"https://127.0.0.1:45001/api/v2/profile/quick",  # IPv4 localhost - FALLBACK
        f"{MLX_LAUNCHER_V2}/profile/quick",  # Config từ config.py
    ]
    
    last_error = None
    response = None
    
    # Thử cả 2 phiên bản payload
    payloads_to_try = [
        ("full", payload_full),
        ("minimal", payload_minimal)
    ]
    
    for payload_name, test_payload in payloads_to_try:
        payload_json = json.dumps(test_payload)
        print(f"Thử payload: {payload_name}")
        print(f"📝 JSON gửi đi: {payload_json[:500]}...")  # Debug payload thực tế
        
        for i, url in enumerate(urls_to_try):
            try:
                print(f"[{i+1}/{len(urls_to_try)}] Thử kết nối: {url}")
                # Dùng HTTPS với SSL verification disabled
                response = requests.post(
                    url, 
                    headers=HEADERS, 
                    data=payload_json, 
                    timeout=30,
                    verify=False  # Disable SSL verification cho self-signed cert
                )
                
                print(f"Response status: {response.status_code}")
                
                # Kiểm tra response
                if response.status_code == 200:
                    # Parse JSON để kiểm tra status code từ MLX
                    try:
                        result = response.json()
                        if result.get("status", {}).get("http_code") == 200:
                            print(f"Kết nối thành công với: {url} (payload: {payload_name})")
                            break
                        else:
                            print(f"MLX response: {result}")
                    except:
                        pass
                    
                    # Nếu status code là 200 nhưng không parse được JSON
                    break
                elif response.status_code == 400:
                    # Lỗi 400 có thể là BAD_REQUEST_VALUES hoặc BROWSER_VERSION_NOT_FOUND
                    print(f"HTTP {response.status_code}: {response.text[:200]}")
                    if "BAD_REQUEST_VALUES" in response.text or "browser version" in response.text:
                        print(f"Thử payload khác...")
                        break
                    else:
                        if i < len(urls_to_try) - 1:
                            print("Thử URL tiếp theo...")
                            time.sleep(0.5)
                            continue
                else:
                    print(f"HTTP {response.status_code}: {response.text[:200]}")
                    if i < len(urls_to_try) - 1:
                        print("Thử URL tiếp theo...")
                        time.sleep(0.5)  # Delay ngắn giữa các lần thử
                        continue
                        
            except Exception as e:
                last_error = e
                print(f"Lỗi: {e}")
                if i < len(urls_to_try) - 1:
                    print("Thử URL tiếp theo...")
                    time.sleep(0.5)  # Delay ngắn giữa các lần thử
                    continue
        
        # Nếu thành công với payload này, dừng
        if response is not None and response.status_code == 200:
            break
    
    # Nếu tất cả payloads và URLs đều fail
    if response is None or response.status_code != 200:
            return None, {
                "error": True,
                "status_code": 500,
                "error_code": "CONNECTION_FAILED",
            "message": f"Không thể kết nối đến Multilogin Launcher sau khi thử {len(urls_to_try)} URLs",
            "detailed_message": f"Lỗi cuối cùng: {last_error}",
                "suggestion": [
                    "Kiểm tra Multilogin Launcher có đang chạy không",
                    "Kiểm tra kết nối mạng",
                    "Thử restart Multilogin Launcher",
                "Kiểm tra firewall settings",
                "Kiểm tra port 45001 có bị block không",
                "Thử chạy Multilogin Launcher trên localhost"
                ]
            }
    print(response.json())
    if response.json()["status"]["http_code"] == 200:
        selenium_port = response.json()["data"]["port"]
        option = ChromiumOptions()
        driver = webdriver.Remote(
            command_executor=f"{LOCALHOST}:{selenium_port}", options=option
        )
        tabs = driver.window_handles
        if len(tabs) > 1:
            main_tab = tabs[0]
            # duyệt qua các tab khác để đóng
            for tab in tabs[1:]:
                driver.switch_to.window(tab)
                driver.close()
            # quay lại tab chính
            driver.switch_to.window(main_tab)
        print(f"Profile {response.json()['data']['id']} đã được tạo thành công")
        return driver, response.json()["data"]["id"]
    elif response.json()["status"]["http_code"] == 401:
        print("Token hết hạn, vui lòng đăng nhập lại")
        logging.error("Token hết hạn, vui lòng đăng nhập lại")
        # signin()
        return start_quick_profile()
    else:
        # Detailed error handling cho các status codes khác nhau
        status_info = response.json().get("status", {})
        status_code = status_info.get("http_code", response.status_code)
        error_message = status_info.get("message", "Unknown error")
        error_code = status_info.get("error_code", "UNKNOWN")
        
        # Custom error messages tùy theo status code
        if status_code == 500:
            if "internal core error" in error_message.lower():
                detailed_msg = "Multilogin server đang gặp sự cố nội bộ. Thử lại sau vài phút."
            else:
                detailed_msg = f"Lỗi server Multilogin (500): {error_message}"
        elif status_code == 403:
            detailed_msg = "Không có quyền tạo profile - Kiểm tra workspace/folder permissions"
        elif status_code == 429:
            detailed_msg = "Quá nhiều request - Đợi một chút rồi thử lại"
        elif status_code == 422:
            detailed_msg = "Dữ liệu profile không hợp lệ - Kiểm tra cấu hình"
        else:
            detailed_msg = f"Lỗi tạo profile: {error_message} (Code: {status_code})"
        
        print(f"Tạo profile thất bại:")
        print(f"   Status Code: {status_code}")
        print(f"   Error Code: {error_code}")
        print(f"   Message: {error_message}")
        print(f"   Suggestion: {detailed_msg}")
        
        logging.error(f"Profile creation failed - Status: {status_code}, Error: {error_code}, Message: {error_message}")
        
        # Trả về detailed error info
        return None, {
            "error": True,
            "status_code": status_code,
            "error_code": error_code,
            "message": error_message,
            "detailed_message": detailed_msg,
            "suggestion": get_error_suggestion(status_code, error_code, error_message)
        }


def get_error_suggestion(status_code, error_code, error_message):
    """
    Đưa ra gợi ý khắc phục dựa trên error code
    """
    suggestions = []
    
    if status_code == 500:
        if "internal core error" in error_message.lower():
            suggestions = [
                "Thử lại sau 2-3 phút",
                "Kiểm tra Multilogin Launcher có đang chạy không",
                "Restart Multilogin app nếu cần",
                "Kiểm tra kết nối internet",
                "Liên hệ support nếu lỗi tiếp tục"
            ]
        else:
            suggestions = [
                "Thử lại request",
                "Kiểm tra Multilogin service status", 
                "Restart Multilogin application"
            ]
    elif status_code == 403:
        suggestions = [
            "Kiểm tra quyền workspace",
            "Verify folder permissions",
            "Refresh authentication token"
        ]
    elif status_code == 429:
        suggestions = [
            "Đợi 30-60 giây rồi thử lại",
            "Giảm số lượng concurrent requests"
        ]
    elif status_code == 422:
        suggestions = [
            "Kiểm tra profile payload",
            "Verify proxy format nếu có",
            "Check browser settings"
        ]
    else:
        suggestions = [
            "Thử lại sau vài giây",
            "Kiểm tra logs chi tiết",
            "Debug network connectivity"
        ]
    
    return suggestions


def get_profile_status(profile_id):
    try:
        ssl_session = create_ssl_session()
        response = ssl_session.get(f"{MLX_LAUNCHER}/profile/status/p/{profile_id}")
    except Exception as e:
        print(f"SSL Error in get_profile_status: {e}")
        response = requests.get(f"{MLX_LAUNCHER}/profile/status/p/{profile_id}", headers=HEADERS, verify=False)
    try:
        response_data = response.json()
        if response_data and "status" in response_data and response_data["status"]["http_code"] == 200:
            return response_data["data"]
        else:
            return None
    except (ValueError, KeyError) as e:
        return None
    
def stop_all_profiles():
    try:
        ssl_session = create_ssl_session()
        response = ssl_session.get(f"{MLX_LAUNCHER}/profile/stop_all?type=all")
    except Exception as e:
        print(f"SSL Error in stop_all_profiles: {e}")
        response = requests.get(f"{MLX_LAUNCHER}/profile/stop_all?type=all", headers=HEADERS, verify=False)
    try:
        response_data = response.json()
        if response_data and "status" in response_data and response_data["status"]["http_code"] == 200:
            return response_data
        else:
            return None
    except (ValueError, KeyError) as e:
        return None

def get_all_profile_status():
    print(f"Lấy tất cả trạng thái profile")
    try:
        ssl_session = create_ssl_session()
        response = ssl_session.get(f"{MLX_LAUNCHER}/profile/statuses")
    except Exception as e:
        print(f"SSL Error in get_all_profile_status: {e}")
        response = requests.get(f"{MLX_LAUNCHER}/profile/statuses", headers=HEADERS, verify=False)
    print(response.json())
    if response.json()["status"]["http_code"] == 200:
        print(response.json())
        return response.json()["data"]["states"]
    else:
        print(f"Lỗi khi lấy tất cả trạng thái profile: {response.json()}")
        return {"error": response}


# ============================================================================
# EXAMPLE: Cách sử dụng MultiloginService mới
# ============================================================================

def get_automation_token_fast(email=None, password=None, secret_2fa=None, workspace_id=None, workspace_email=None):
    """
    Hàm tiện ích để lấy automation token nhanh nhất có thể
    Ưu tiên sử dụng cached token, chỉ đăng nhập khi cần thiết
    
    Returns:
        str: automation_token nếu thành công, None nếu thất bại
    """
    try:
        result = initialize_multilogin_service(
            email=email,
            password=password,
            secret_2fa=secret_2fa,
            workspace_id=workspace_id,
            workspace_email=workspace_email,
            use_smart_login=True  # Luôn sử dụng smart login
        )
        
        if result['success']:
            return result['automation_token']
        else:
            print(f"Lỗi lấy token: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None


def demo_new_login_system():
    """
    Demo cách sử dụng hệ thống đăng nhập mới với 2FA và caching
    """
    print("=" * 70)
    print("DEMO: Hệ thống đăng nhập thông minh với Token Caching")
    print("=" * 70)
    
    # Cách 1: Smart Login (khuyến nghị) - Tự động sử dụng cached token
    print("\nCÁCH 1: Smart Login (Ưu tiên cached token)")
    print("-" * 50)
    
    result = initialize_multilogin_service(
        email="quytv@iart.asia",
        password="12345679Qaz!",
        secret_2fa="UBEOVFAKXD7ZV7GNUW3F7TBSHLY5HAGP",
        workspace_id="edfa065b-4274-4742-9783-d1284ea0262a",
        workspace_email="phuonganht93@iart.asia",
        use_smart_login=True  # Mặc định
    )
    
    if result['success']:
        if result.get('from_cache'):
            print("Sử dụng token có sẵn - Cực nhanh!")
        else:
            print("Đã đăng nhập và tạo token mới")
        print(f"Automation Token: {result['automation_token'][:25]}...")
    else:
        print(f"Lỗi: {result['error']}")
    
    print("\nCÁCH 2: Hàm tiện ích nhanh")
    print("-" * 50)
    
    # Chạy lại để demo cached token
    token = get_automation_token_fast(
        email="quytv@iart.asia",
        password="12345679Qaz!",
        secret_2fa="UBEOVFAKXD7ZV7GNUW3F7TBSHLY5HAGP",
        workspace_id="edfa065b-4274-4742-9783-d1284ea0262a",
        workspace_email="phuonganht93@iart.asia"
    )
    
    if token:
        print(f"Token lấy siêu nhanh: {token[:25]}...")
    
    print("\nCÁCH 3: Full Login (Bỏ qua cache)")
    print("-" * 50)
    
    result_full = initialize_multilogin_service(
        email="quytv@iart.asia",
        password="12345679Qaz!",
        secret_2fa="UBEOVFAKXD7ZV7GNUW3F7TBSHLY5HAGP",
        workspace_id="edfa065b-4274-4742-9783-d1284ea0262a",
        workspace_email="phuonganht93@iart.asia",
        use_smart_login=False  # Bỏ qua cache
    )
    
    if result_full['success']:
        print("Đã thực hiện full login (bỏ qua cache)")
        print(f"New Token: {result_full['automation_token'][:25]}...")
    
    print("\n" + "=" * 70)
    print("TIP: Lần đầu sẽ đăng nhập đầy đủ, các lần sau sẽ dùng cached token!")
    print("Smart login giúp tăng tốc đáng kể việc mở profile!")
    print("=" * 70)


# Uncomment dòng dưới để chạy demo
# if __name__ == "__main__":
#     demo_new_login_system()