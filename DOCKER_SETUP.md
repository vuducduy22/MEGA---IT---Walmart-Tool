# 🐳 Docker Setup Guide for Ubuntu Server

## 📋 Cài đặt Docker trên Ubuntu

### Bước 1: Cập nhật hệ thống
```bash
sudo apt update
sudo apt upgrade -y
```

### Bước 2: Cài đặt Docker
```bash
# Cài đặt dependencies
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Thêm Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Thêm Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cập nhật package list
sudo apt update

# Cài đặt Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### Bước 3: Cài đặt Docker Compose
```bash
# Tải Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Cấp quyền thực thi
sudo chmod +x /usr/local/bin/docker-compose

# Tạo symlink
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
```

### Bước 4: Cấu hình Docker
```bash
# Thêm user vào docker group
sudo usermod -aG docker $USER

# Khởi động Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Kiểm tra Docker
docker --version
docker-compose --version
```

### Bước 5: Logout và login lại
```bash
# Logout khỏi session hiện tại
exit

# SSH lại vào server
ssh dev3ubt@your-server-ip
```

## 🔧 Troubleshooting

### Nếu Docker vẫn không chạy:
```bash
# Kiểm tra Docker service
sudo systemctl status docker

# Khởi động Docker service
sudo systemctl start docker

# Kiểm tra Docker daemon
sudo dockerd --version
```

### Nếu gặp lỗi permission:
```bash
# Thêm user vào docker group
sudo usermod -aG docker $USER

# Logout và login lại
exit
# SSH lại
```

### Nếu gặp lỗi network:
```bash
# Restart Docker service
sudo systemctl restart docker

# Kiểm tra Docker network
docker network ls
```

## ✅ Verification

Sau khi cài đặt xong, chạy các lệnh sau để kiểm tra:

```bash
# Kiểm tra Docker
docker --version
docker-compose --version

# Kiểm tra Docker daemon
docker info

# Test Docker
docker run hello-world
```

## 🚀 Chạy WM-MEGA

Sau khi Docker đã hoạt động:

```bash
cd ~/MEGA---IT---Walmart-Tool
./deploy.sh start
```

## 📞 Nếu vẫn gặp vấn đề

```bash
# Kiểm tra logs
sudo journalctl -u docker

# Restart Docker
sudo systemctl restart docker

# Kiểm tra quyền
groups $USER
```
