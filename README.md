# 2sd-inventory
## Giới thiệu
Dự án này là một hệ thống trích xuất dữ liệu từ các trang web mmo
## Công nghệ sử dụng
### Backend
- Python 3.10
- Flask: Framework API hiện đại, hiệu suất cao
- MongoDB: Cơ sở dữ liệu NoSQL chính
- Multilogin: Quản lý profile trình duyệt
### Frontend
- HTML:
- Java script
- CSS: Giao diện được tùy chỉnh với hiệu ứng cyber
- Fetch: Gọi API

### cấu trúc

### backend
```README.md
crawler-walmart/
├── app.py
├── build.sh
├── config.py
├── mlx.log
└── multix.py
```

### Frontend
```
crawler-walmart/
├── static
│         └── styles.css
├── templates
│         ├── crawl_data.html
│         ├── index.html
└── walmart.py
```

## Các tính năng chính
### 1.quản lý cơ sở dữ liệu
### 2.trích xuất dữ liệu từ walmart

## Hướng dẫn cài đặt và triển khai
### cài đặt backend
1. cấu hình các biến môi trường
2. chạy script build: `./build.sh`

### cấu hình multilogin
1. Đảm bảo Multilogin đã được cài đặt và cấu hình đúng

### Cấu hình Database
1. Cài đặt và cấu hình MongoDB
3. Đảm bảo kết nối từ backend đến các database

## Các lưu ý quan trọng
### Tương thích
- Backend chạy trên Python 3.10
- Conda được sử dụng để đảm bảo môi trường nhất quán


© 2025 2sd-inventory Automation by [@chicanancom](https://github.com/chicanancom). Tất cả các quyền được bảo lưu.
