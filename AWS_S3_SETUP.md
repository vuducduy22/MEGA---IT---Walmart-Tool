# Hướng dẫn Setup AWS S3 cho Walmart Crawler

## 1. Tạo AWS Account và S3 Bucket

### Bước 1: Tạo AWS Account
1. Truy cập [AWS Console](https://aws.amazon.com/)
2. Đăng ký tài khoản AWS (nếu chưa có)
3. Đăng nhập vào AWS Console

### Bước 2: Tạo S3 Bucket
1. Vào **S3** service trong AWS Console
2. Click **"Create bucket"**
3. Đặt tên bucket: `mega.iart.group` (hoặc tên khác)
4. Chọn region: `us-east-2` (hoặc region khác)
5. **Quan trọng**: Bỏ tick **"Block all public access"** để cho phép public access
6. Click **"Create bucket"**

### Bước 3: Cấu hình Bucket cho Public Access
1. Vào bucket vừa tạo
2. Vào tab **"Permissions"**
3. Trong **"Block public access settings"**, click **"Edit"**
4. Bỏ tick tất cả các options và click **"Save changes"**
5. Trong **"Bucket policy"**, thêm policy sau:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        }
    ]
}
```

**Lưu ý**: Thay `YOUR_BUCKET_NAME` bằng tên bucket thực tế của bạn.

## 2. Tạo IAM User và Access Keys

### Bước 1: Tạo IAM User
1. Vào **IAM** service trong AWS Console
2. Click **"Users"** → **"Create user"**
3. Đặt tên user: `walmart-crawler-s3`
4. Chọn **"Programmatic access"**
5. Click **"Next"**

### Bước 2: Gán Permissions
1. Chọn **"Attach existing policies directly"**
2. Tìm và chọn **"AmazonS3FullAccess"**
3. Click **"Next"** → **"Create user"**

### Bước 3: Lấy Access Keys
1. Click vào user vừa tạo
2. Vào tab **"Security credentials"**
3. Click **"Create access key"**
4. Chọn **"Application running outside AWS"**
5. Lưu lại **Access Key ID** và **Secret Access Key**

## 3. Cấu hình Environment Variables

Tạo file `.env` trong thư mục gốc của project:

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

## 4. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

## 5. Test AWS S3 Connection

Chạy script test:

```bash
python aws_s3_handler.py
```

Nếu thành công, bạn sẽ thấy:
```
Kết nối S3 thành công với bucket: mega.iart.group
🚀 Bắt đầu xử lý 3 ảnh với 10 luồng...
✅ Uploaded: http://mega.iart.group.s3-website.us-east-2.amazonaws.com/images/...
```

## 6. Sử dụng trong Web App

### Upload ảnh lên S3:
- Route: `POST /api/download-images-to-s3`
- Body: `{"collection": "products", "folder_name": "Product_Images_20241220", "limit": 50}`

### Fill Excel với ảnh từ S3:
- Route: `POST /api/excel/fill-data`
- Body: `{"filename": "file.xlsx", "collection": "products", "fill_images_from_s3": true}`

## 7. Troubleshooting

### Lỗi "Access Denied":
- Kiểm tra bucket policy có cho phép public read không
- Kiểm tra IAM user có quyền S3FullAccess không

### Lỗi "Bucket not found":
- Kiểm tra tên bucket trong `.env` có đúng không
- Kiểm tra region có đúng không

### Lỗi "Invalid credentials":
- Kiểm tra AWS_ACCESS_KEY và AWS_SECRET_KEY trong `.env`
- Đảm bảo access keys còn hiệu lực

## 8. Cấu trúc S3 Bucket

```
mega.iart.group/
├── images/
│   ├── Product_Images_20241220_120000/
│   │   ├── product1_image.jpg
│   │   └── product2_image.jpg
│   └── Product_Images_20241220_130000/
│       └── product3_image.jpg
```

## 9. Cost Optimization

- S3 Standard storage: ~$0.023/GB/tháng
- S3 requests: ~$0.0004/1000 requests
- CloudFront CDN (optional): ~$0.085/GB transfer

**Ước tính chi phí**: Với 1000 ảnh (~1GB), chi phí khoảng $0.05/tháng.
