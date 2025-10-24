# 🔧 Hướng Dẫn Setup Google Drive API

## 📋 **BƯỚC 1: Tạo Google Cloud Project**

1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới hoặc chọn existing project
3. Ghi nhớ Project ID

## 📋 **BƯỚC 2: Enable Google Drive API**

1. Trong Google Cloud Console, vào **"APIs & Services"** > **"Library"**
2. Tìm kiếm **"Google Drive API"**
3. Click vào **"Google Drive API"** và nhấn **"Enable"**

## 📋 **BƯỚC 3: Tạo OAuth 2.0 Credentials**

1. Vào **"APIs & Services"** > **"Credentials"**
2. Click **"Create Credentials"** > **"OAuth client ID"**
3. Nếu chưa có OAuth consent screen:
   - Click **"Configure Consent Screen"**
   - Chọn **"External"** (nếu không phải G Suite)
   - Điền thông tin cơ bản:
     - App name: `Walmart Image Downloader`
     - User support email: email của bạn
     - Developer contact information: email của bạn
   - Click **"Save and Continue"** > **"Save and Continue"** > **"Back to Dashboard"**

4. Tạo OAuth client ID:
   - Application type: **"Desktop application"**
   - Name: `Walmart Image Downloader Desktop`
   - Click **"Create"**

5. Download file JSON credentials:
   - Click **"Download JSON"**
   - Rename file thành **`credentials.json`**
   - Đặt file này vào thư mục gốc của project (cùng cấp với `app.py`)

## 📋 **BƯỚC 4: Cài Đặt Dependencies**

```bash
pip install -r requirements.txt
```

## 📋 **BƯỚC 5: Test Setup**

```bash
python google_drive_handler.py
```

Lần đầu chạy sẽ:
1. Mở browser để authorize
2. Đăng nhập Google account
3. Cho phép app truy cập Google Drive
4. Tạo file `token.json` tự động

## 📁 **Cấu Trúc Files**

```
WM-MEGA/
├── app.py
├── google_drive_handler.py
├── credentials.json          ← File từ Google Cloud Console
├── token.json               ← Tự động tạo sau lần đầu authorize
└── requirements.txt
```

## 🚀 **Sử Dụng Tính Năng**

1. Chạy Flask app: `python app.py`
2. Vào **Crawl List** page
3. Chọn collection có hình ảnh
4. Click **"📱 Download to Google Drive"**
5. Nhập tên folder và số lượng hình ảnh
6. Đợi download hoàn thành

## ⚠️ **Troubleshooting**

### **Lỗi "credentials.json not found"**
- Đảm bảo file `credentials.json` đúng vị trí
- Kiểm tra tên file chính xác

### **Lỗi "Refresh token expired"**
- Xóa file `token.json`
- Chạy lại để re-authorize

### **Lỗi "Access denied"**
- Kiểm tra OAuth consent screen đã được setup
- Đảm bảo email của bạn được add vào test users (nếu app chưa published)

### **Lỗi "API not enabled"**
- Vào Google Cloud Console
- Enable Google Drive API cho project

## 🔒 **Bảo Mật**

- **KHÔNG** commit `credentials.json` và `token.json` vào git
- Thêm vào `.gitignore`:
  ```
  credentials.json
  token.json
  ```

- Chỉ chia sẻ credentials với người có quyền truy cập

## 📊 **Giới Hạn**

- **Free tier:** 1 billion requests/day
- **Upload size:** 5TB/file
- **Folder limit:** 500,000 items/folder
- **Rate limit:** 1000 requests/100 seconds/user

## 💡 **Tips**

- Tạo folder riêng cho mỗi collection
- Sử dụng naming convention có ngày tháng
- Monitor usage trong Google Cloud Console
- Regular cleanup old files nếu cần thiết
