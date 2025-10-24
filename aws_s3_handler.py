import boto3
import requests
import io
import os
import mimetypes
import concurrent.futures
from PIL import Image
from urllib.parse import urlparse
from botocore.exceptions import NoCredentialsError
from datetime import datetime
import re

# --- Cấu hình AWS ---
try:
    from config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME, AWS_FOLDER_NAME, AWS_REGION
    BUCKET_NAME = AWS_BUCKET_NAME
    FOLDER_NAME = AWS_FOLDER_NAME
    REGION = AWS_REGION
    BUCKET_HOSTING_URL = f"http://{BUCKET_NAME}.s3-website.{REGION}.amazonaws.com"
except ImportError:
    # Fallback nếu không import được config
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "YOUR_AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "YOUR_AWS_SECRET_KEY")
    BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "mega.iart.group")
    FOLDER_NAME = os.getenv("AWS_FOLDER_NAME", "images")
    REGION = os.getenv("AWS_REGION", "us-east-2")
    BUCKET_HOSTING_URL = f"http://{BUCKET_NAME}.s3-website.{REGION}.amazonaws.com"

# --- Cấu hình khác ---
MAX_WORKERS = 10        # số luồng tải ảnh song song
TIMEOUT = 15            # timeout request
COMPRESSION_QUALITY = 85  # chất lượng ảnh sau khi nén (0-100)

# --- Khởi tạo S3 client ---
try:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=REGION,
    )
except Exception as e:
    print(f"Lỗi khởi tạo S3 client: {e}")
    s3 = None

class AWSS3Uploader:
    def __init__(self):
        if not s3:
            raise Exception("S3 client chưa được khởi tạo. Vui lòng kiểm tra AWS credentials.")
        
        self.s3 = s3
        self.BUCKET_NAME = BUCKET_NAME
        self.FOLDER_NAME = FOLDER_NAME
        self.REGION = REGION
        self.BUCKET_HOSTING_URL = BUCKET_HOSTING_URL
        
        try:
            s3.head_bucket(Bucket=BUCKET_NAME)
            print(f"Kết nối S3 thành công với bucket: {BUCKET_NAME}")
        except Exception as e:
            raise Exception(f"Không thể kết nối tới S3 bucket '{BUCKET_NAME}': {str(e)}")

    def download_and_optimize_image(self, url):
        """Tải và nén ảnh trong memory, trả về (filename, content_bytes, content_type)."""
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            parsed = urlparse(url)
            file_name = os.path.basename(parsed.path) or f"image_{os.urandom(4).hex()}.jpg"
            content_type = response.headers.get("Content-Type") or mimetypes.guess_type(file_name)[0]

            # Mở ảnh bằng Pillow
            image = Image.open(io.BytesIO(response.content))
            image_format = image.format or "JPEG"

            # Nén ảnh vào memory buffer
            buffer = io.BytesIO()
            if image_format.upper() in ["JPEG", "JPG"]:
                image.save(buffer, format="JPEG", optimize=True, quality=COMPRESSION_QUALITY)
            elif image_format.upper() == "PNG":
                image = image.convert("P", palette=Image.ADAPTIVE)
                image.save(buffer, format="PNG", optimize=True)
            else:
                # convert các định dạng lạ sang JPEG
                rgb_im = image.convert("RGB")
                image_format = "JPEG"
                rgb_im.save(buffer, format="JPEG", optimize=True, quality=COMPRESSION_QUALITY)

            buffer.seek(0)
            return (file_name, buffer, f"image/{image_format.lower()}")

        except Exception as e:
            print(f"Lỗi khi tải {url}: {e}")
            return None

    def upload_to_s3(self, file_name, buffer, content_type):
        """Upload 1 ảnh lên S3 và trả về URL public."""
        try:
            s3_key = f"{FOLDER_NAME}/{file_name}"
            s3.upload_fileobj(
                Fileobj=buffer,
                Bucket=BUCKET_NAME,
                Key=s3_key,
                ExtraArgs={"ContentType": content_type},
            )
            return f"{BUCKET_HOSTING_URL}/{s3_key}"
        except Exception as e:
            print(f"Lỗi upload {file_name}: {e}")
            return None

    def batch_upload_images(self, products_with_images, folder_name=None):
        """Upload nhiều ảnh song song lên S3."""
        if not products_with_images:
            return {
                'success_count': 0,
                'failed_count': 0,
                'uploaded_files': [],
                'failed_files': [],
                'folders_created': []
            }

        # Tạo folder name nếu không có
        if not folder_name:
            folder_name = f"Product_Images_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Cập nhật FOLDER_NAME global
        global FOLDER_NAME
        original_folder = FOLDER_NAME
        FOLDER_NAME = folder_name

        uploaded_urls = []
        failed_uploads = []
        url_list = [item['url'] for item in products_with_images]

        print(f"Bắt đầu xử lý {len(url_list)} ảnh với {MAX_WORKERS} luồng...")

        # Bước 1: tải và nén song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(self.download_and_optimize_image, url_list))

        # Bước 2: upload lên S3 song song
        valid_results = [r for r in results if r is not None]

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(self.upload_to_s3, file_name, buffer, content_type)
                for (file_name, buffer, content_type) in valid_results
            ]
            for future in concurrent.futures.as_completed(futures):
                url = future.result()
                if url:
                    uploaded_urls.append(url)
                    print(f"Uploaded: {url}")
                else:
                    failed_uploads.append("Upload failed")

        # Khôi phục FOLDER_NAME
        FOLDER_NAME = original_folder

        print(f"\nHoàn thành! {len(uploaded_urls)}/{len(url_list)} ảnh đã upload.")
        
        return {
            'success_count': len(uploaded_urls),
            'failed_count': len(failed_uploads),
            'uploaded_files': uploaded_urls,
            'failed_files': failed_uploads,
            'folders_created': [folder_name]
        }

    def migrate_images_to_s3(self, url_list):
        """Tải, nén và upload nhiều ảnh song song lên S3."""
        uploaded_urls = []

        print(f"Bắt đầu xử lý {len(url_list)} ảnh với {MAX_WORKERS} luồng...")

        # Bước 1: tải và nén song song
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(self.download_and_optimize_image, url_list))

        # Bước 2: upload lên S3 song song
        valid_results = [r for r in results if r is not None]

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(self.upload_to_s3, file_name, buffer, content_type)
                for (file_name, buffer, content_type) in valid_results
            ]
            for future in concurrent.futures.as_completed(futures):
                url = future.result()
                if url:
                    uploaded_urls.append(url)
                    print(f"Uploaded: {url}")

        print(f"\nHoàn thành! {len(uploaded_urls)}/{len(url_list)} ảnh đã upload.")
        return uploaded_urls

    def create_safe_filename(self, product_name, product_id=None):
        """Tạo filename an toàn cho S3."""
        # Loại bỏ ký tự đặc biệt
        safe_filename = re.sub(r'[^\w\s-]', '', product_name)
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        
        if product_id:
            filename = f"{safe_filename}_{product_id}.jpg"
        else:
            filename = f"{safe_filename}_{os.urandom(4).hex()}.jpg"
        
        return filename

# --- Demo sử dụng ---
if __name__ == "__main__":
    try:
        uploader = AWSS3Uploader()
        
        image_urls = [
            "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d",
            "https://images.unsplash.com/photo-1498050108023-c5249f4df085",
            "https://images.unsplash.com/photo-1473186505569-9c61870c11f9",
        ]

        uploaded = uploader.migrate_images_to_s3(image_urls)

        print("\nDanh sách URL mới trên S3:")
        for url in uploaded:
            print("URL:", url)
            
    except Exception as e:
        print(f"Lỗi: {e}")
        print("Vui lòng kiểm tra AWS credentials và cấu hình.")
