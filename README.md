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

# Các lệnh quản lý
./deploy.sh start      # Khởi động
./deploy.sh stop       # Dừng
./deploy.sh restart    # Khởi động lại
./deploy.sh status     # Kiểm tra trạng thái
./deploy.sh logs       # Xem logs
./deploy.sh backup     # Tạo backup
./deploy.sh cleanup    # Dọn dẹp

# Dừng containers
sudo docker-compose down

# Hoặc xem logs của container cụ thể
sudo docker-compose logs -f wm-mega
sudo docker-compose logs -f mongodb

# Hoặc xóa tất cả lock files
sudo rm -f /tmp/.X*-lock

sudo docker exec wm-mega-app /app/multilogin/extracted/opt/mlx/agent.bin

sudo docker-compose up -d --build

docker network inspect mega---it---walmart-tool_wm-mega-network

docker-compose restart wm-mega

# Lệnh nhanh
docker-compose down && docker-compose build --no-cache wm-mega && docker-compose up -d

docker exec -it wm-mega-app /bin/bash


curl -v -X POST http://127.0.0.1:45001/api/v2/profile/quick      -H "Content-Type: application/json"      -H "Authorization: Bearer eyJhbGciOiJIUzUxMiJ9.eyJicGRzLmJ1Y2tldCI6Im1seC1icGRzLXByb2QtZXUtMSIsIm1hY2hpbmVJRCI6IiIsInByb2R1Y3RJRCI6IiIsIndvcmtzcGFjZVJvbGUiOiJvd25lciIsInZlcmlmaWVkIjp0cnVlLCJzaGFyZElEIjoiY2JlMTM4MDAtYmJhZi00YzhmLTgwYjMtMTk3Zjg5NjM5NGYyIiwidXNlcklEIjoiMTAxZjlmOTctMDI2ZC00MTUxLWEyYjgtZTkzZGI5OTI0OThjIiwiZW1haWwiOiJwaHVvbmdhbmh0OTNAaWFydC5hc2lhIiwiaXNBdXRvbWF0aW9uIjp0cnVlLCJ3b3Jrc3BhY2VJRCI6ImVkZmEwNjViLTQyNzQtNDc0Mi05NzgzLWQxMjg0ZWEwMjYyYSIsImp0aSI6IjU1NjMxNTc0LTNiZjMtNDE3Yy04M2VhLTYxYWMzZjdhYmUyMiIsInN1YiI6Ik1MWCIsImlzcyI6IjEwMWY5Zjk3LTAyNmQtNDE1MS1hMmI4LWU5M2RiOTkyNDk4YyIsImlhdCI6MTc2MTI5ODk3NCwiZXhwIjoyMDgyNzA2OTc0fQ.TGp3NDXC9gIMaF9zPrVyY3JXQXTYalkK6e5Piw7WzXgF2uI3pwKNwmNZ88w38gChKKisyULtCfdlRrOOqJo7Xw"      -d '{
           "browser_type":"mimic",
           "name":"QuickProfile",
           "os":"linux"
         }'