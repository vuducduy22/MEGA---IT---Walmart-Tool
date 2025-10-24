"""
Google Drive Handler cho việc upload hình ảnh sản phẩm
Hỗ trợ batch upload và folder management
"""

import os
import io
import requests
from typing import List, Optional, Dict
import tempfile
from datetime import datetime

# Google Drive API imports
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError


class GoogleDriveUploader:
    """Class để handle Google Drive operations"""
    
    # OAuth 2.0 scopes cần thiết
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """
        Initialize Google Drive uploader
        
        Args:
            credentials_file: Path đến file credentials.json từ Google Cloud Console
            token_file: Path đến file token.json (sẽ được tạo tự động)
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate với Google Drive API"""
        creds = None
        
        # Token file chứa access và refresh tokens của user
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # Nếu không có valid credentials, thực hiện OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    print("Refresh token expired. Need to re-authenticate.")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Lưu credentials cho lần chạy tiếp theo
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        # Build service object
        self.service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive authentication successful!")
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Tạo folder trên Google Drive
        
        Args:
            folder_name: Tên folder
            parent_folder_id: ID của parent folder (None = root)
            
        Returns:
            str: ID của folder mới tạo
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            print(f"✅ Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except Exception as e:
            print(f"❌ Error creating folder '{folder_name}': {str(e)}")
            raise
    
    def find_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Tìm folder theo tên
        
        Args:
            folder_name: Tên folder cần tìm
            parent_folder_id: ID của parent folder
            
        Returns:
            Optional[str]: ID của folder nếu tìm thấy, None nếu không
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            return None
            
        except Exception as e:
            print(f"❌ Error finding folder '{folder_name}': {str(e)}")
            return None
    
    def get_or_create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Lấy folder ID hoặc tạo mới nếu chưa tồn tại
        
        Args:
            folder_name: Tên folder
            parent_folder_id: ID của parent folder
            
        Returns:
            str: ID của folder
        """
        folder_id = self.find_folder(folder_name, parent_folder_id)
        if folder_id:
            print(f"📁 Found existing folder '{folder_name}': {folder_id}")
            return folder_id
        else:
            return self.create_folder(folder_name, parent_folder_id)
    
    def download_image_from_url(self, image_url: str) -> Optional[io.BytesIO]:
        """
        Download hình ảnh từ URL
        
        Args:
            image_url: URL của hình ảnh
            
        Returns:
            Optional[io.BytesIO]: Image data nếu thành công, None nếu lỗi
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Kiểm tra content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"⚠️ Warning: URL may not be an image: {content_type}")
            
            return io.BytesIO(response.content)
            
        except Exception as e:
            print(f"❌ Error downloading image from {image_url}: {str(e)}")
            return None
    
    def upload_image_from_url(self, image_url: str, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        Download hình ảnh từ URL và upload lên Google Drive
        
        Args:
            image_url: URL của hình ảnh
            filename: Tên file khi lưu trên Drive
            folder_id: ID của folder để lưu (None = root)
            
        Returns:
            Optional[str]: ID của file đã upload, None nếu lỗi
        """
        try:
            # Download image
            image_data = self.download_image_from_url(image_url)
            if not image_data:
                return None
            
            # Prepare file metadata
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Upload to Drive
            media = MediaIoBaseUpload(image_data, mimetype='image/jpeg', resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            print(f"✅ Uploaded '{filename}' to Google Drive: {file_id}")
            return file_id
            
        except Exception as e:
            print(f"❌ Error uploading image '{filename}': {str(e)}")
            return None
    
    def batch_upload_images(self, image_data_list: List[Dict], base_folder_name: str = None, group_by_product: bool = True) -> Dict:
        """
        Batch upload multiple images
        
        Args:
            image_data_list: List of dicts với keys: 'url', 'filename', 'product_name'
            base_folder_name: Tên folder chính để chứa tất cả (None = root)
            group_by_product: Nếu True, tạo subfolder cho mỗi product
            
        Returns:
            Dict: Results với success_count, failed_count, uploaded_files
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'uploaded_files': [],
            'failed_files': [],
            'folders_created': []
        }
        
        try:
            # Tạo base folder nếu cần
            base_folder_id = None
            if base_folder_name:
                base_folder_id = self.get_or_create_folder(base_folder_name)
            
            print(f"🚀 Starting batch upload of {len(image_data_list)} images...")
            
            if group_by_product:
                # Group images by product name
                product_groups = {}
                for image_data in image_data_list:
                    product_name = image_data.get('product_name', 'Unknown Product')
                    # Clean product name for folder name
                    import re
                    clean_name = re.sub(r'[^\w\s-]', '', product_name)
                    clean_name = re.sub(r'[-\s]+', '_', clean_name).strip('_')
                    
                    if clean_name not in product_groups:
                        product_groups[clean_name] = []
                    product_groups[clean_name].append(image_data)
                
                print(f"📁 Grouped into {len(product_groups)} product folders")
                
                # Create subfolders and upload images
                product_folder_cache = {}
                
                for product_name, images in product_groups.items():
                    print(f"\n📁 Processing product: {product_name} ({len(images)} images)")
                    
                    # Create product subfolder
                    if product_name not in product_folder_cache:
                        product_folder_id = self.get_or_create_folder(product_name, base_folder_id)
                        product_folder_cache[product_name] = product_folder_id
                        results['folders_created'].append(product_name)
                        print(f"📁 Created subfolder: {product_name}")
                    else:
                        product_folder_id = product_folder_cache[product_name]
                    
                    # Upload images to product subfolder
                    for i, image_data in enumerate(images, 1):
                        image_url = image_data.get('url')
                        filename = image_data.get('filename', f'image_{i}.jpg')
                        
                        if not image_url:
                            print(f"⚠️ Skipping {filename}: No image URL")
                            results['failed_count'] += 1
                            results['failed_files'].append({
                                'filename': filename,
                                'error': 'No image URL',
                                'product': product_name
                            })
                            continue
                        
                        # Upload image to product subfolder
                        file_id = self.upload_image_from_url(image_url, filename, product_folder_id)
                        
                        if file_id:
                            results['success_count'] += 1
                            results['uploaded_files'].append({
                                'filename': filename,
                                'file_id': file_id,
                                'product_name': product_name,
                                'folder': f"{base_folder_name}/{product_name}" if base_folder_name else product_name
                            })
                            print(f"✅ {filename} → {product_name}/")
                        else:
                            results['failed_count'] += 1
                            results['failed_files'].append({
                                'filename': filename,
                                'error': 'Upload failed',
                                'product': product_name
                            })
                            print(f"❌ Failed: {filename}")
            
            else:
                # Original logic - no grouping
                for i, image_data in enumerate(image_data_list, 1):
                    print(f"\n📷 Processing image {i}/{len(image_data_list)}: {image_data.get('filename', 'Unknown')}")
                    
                    image_url = image_data.get('url')
                    filename = image_data.get('filename', f'image_{i}.jpg')
                    
                    if not image_url:
                        print(f"⚠️ Skipping item {i}: No image URL")
                        results['failed_count'] += 1
                        results['failed_files'].append({
                            'filename': filename,
                            'error': 'No image URL'
                        })
                        continue
                    
                    # Upload image
                    file_id = self.upload_image_from_url(image_url, filename, base_folder_id)
                    
                    if file_id:
                        results['success_count'] += 1
                        results['uploaded_files'].append({
                            'filename': filename,
                            'file_id': file_id,
                            'product_name': image_data.get('product_name', '')
                        })
                    else:
                        results['failed_count'] += 1
                        results['failed_files'].append({
                            'filename': filename,
                            'error': 'Upload failed'
                        })
            
            print(f"\n🎉 Batch upload completed!")
            print(f"📁 Created {len(results.get('folders_created', []))} product folders")
            print(f"✅ Successful uploads: {results['success_count']}")
            print(f"❌ Failed uploads: {results['failed_count']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in batch upload: {str(e)}")
            return results


def setup_google_drive_credentials():
    """
    Hướng dẫn setup Google Drive credentials
    """
    print("""
🔧 HƯỚNG DẪN SETUP GOOGLE DRIVE API:

1. Vào Google Cloud Console: https://console.cloud.google.com/
2. Tạo project mới hoặc chọn existing project
3. Enable Google Drive API:
   - Vào "APIs & Services" > "Library"
   - Tìm "Google Drive API" và enable
4. Tạo credentials:
   - Vào "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop application"
   - Download file JSON và rename thành "credentials.json"
   - Đặt file này vào thư mục gốc của project

5. Chạy script lần đầu sẽ mở browser để authorize
6. File "token.json" sẽ được tạo tự động cho lần sau

📁 Files cần có:
- credentials.json (từ Google Cloud Console)
- token.json (tự động tạo sau lần đầu authorize)
""")


if __name__ == "__main__":
    # Demo usage
    setup_google_drive_credentials()
    
    # Test Google Drive connection
    print("\n🚀 Testing Google Drive connection...")
    try:
        uploader = GoogleDriveUploader()
        print("🎉 Google Drive connection successful!")
        print("✅ Setup completed! You can now use Google Drive features.")
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print("💡 Make sure you have completed all setup steps above.")
