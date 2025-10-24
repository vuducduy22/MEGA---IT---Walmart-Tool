# Hướng dẫn Setup Environment Variables

## Vấn đề hiện tại
AWS credentials chưa được cấu hình, nên ảnh không thể fill vào Excel.

## Giải pháp

### 1. Tạo file `.env` trong thư mục gốc của project:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY=your_access_key_here
AWS_SECRET_KEY=your_secret_key_here
AWS_BUCKET_NAME=mega.iart.group
AWS_FOLDER_NAME=images
AWS_REGION=us-east-2

# MongoDB Configuration (existing)
MONGO_URI=your_mongo_uri_here

# MultiloginX Configuration (existing)
MLX_USERNAME=your_mlx_username
MLX_PASSWORD=your_mlx_password
WORKSPACE_ID=your_workspace_id
FOLDER_ID=your_folder_id
```

### 2. Thay thế các giá trị:

- `your_access_key_here` → AWS Access Key ID thực tế
- `your_secret_key_here` → AWS Secret Access Key thực tế
- `your_mongo_uri_here` → MongoDB URI thực tế
- `your_mlx_username` → MultiloginX username thực tế
- `your_mlx_password` → MultiloginX password thực tế
- `your_workspace_id` → MultiloginX workspace ID thực tế
- `your_folder_id` → MultiloginX folder ID thực tế

### 3. Test kết nối:

```bash
python test_s3_connection.py
```

### 4. Nếu test thành công, chạy app:

```bash
python app.py
```

## Lưu ý
- File `.env` chứa thông tin nhạy cảm, không commit vào git
- Đảm bảo AWS credentials có quyền truy cập S3 bucket
- Kiểm tra bucket có ảnh trong folder `images/` không
