#!/bin/bash

set -e  # Exit on any error

ENV_NAME="env"

# Kiểm tra và cài đặt dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 không tìm thấy. Đang cài đặt..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip xvfb
fi

# Cài Xvfb nếu chưa có
if ! command -v Xvfb &> /dev/null; then
    echo "📦 Cài đặt Xvfb..."
    sudo apt install -y xvfb x11-utils
fi

# Kiểm tra và cài MongoDB
if ! command -v mongod &> /dev/null; then
    echo "📦 Cài đặt MongoDB..."
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt update
    sudo apt install -y mongodb-org
    echo "✅ MongoDB đã được cài đặt"
else
    echo "✅ MongoDB đã được cài đặt từ trước"
fi

# Khởi động MongoDB (KHÔNG có authentication để đơn giản)
echo "🚀 Start MongoDB..."

# Lấy IP của server
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "🔍 Server IP: $SERVER_IP"

# Stop MongoDB
sudo systemctl stop mongod 2>/dev/null || true

# Config MongoDB để bind IP server
echo "🔧 Config MongoDB to bind to server IP..."
sudo sed -i "s/bindIp: 127.0.0.1/bindIp: 127.0.0.1,$SERVER_IP/g" /etc/mongod.conf || sudo sed -i "/net:/a \  bindIp: 0.0.0.0" /etc/mongod.conf

# Tắt authentication
echo "🔓 Disable MongoDB authentication..."
sudo sed -i 's/^  authorization: enabled/#  authorization: disabled/g' /etc/mongod.conf || true
sudo sed -i 's/^    authorization: enabled/#    authorization: disabled/g' /etc/mongod.conf || true

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
sleep 3

echo "✅ MongoDB setup complete (no authentication, bind $SERVER_IP)!"

# Lấy version Python
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "🔍 Detected Python version: $PYTHON_VERSION"

# Tạo virtual environment nếu chưa có
if [ ! -d "$ENV_NAME" ]; then
    echo "🚀 Tạo virtual environment: $ENV_NAME..."
    python3 -m venv $ENV_NAME
    echo "✅ Đã tạo môi trường $ENV_NAME!"
fi

# Kích hoạt môi trường
echo "⚙️  Kích hoạt môi trường..."
source $ENV_NAME/bin/activate

# Upgrade pip
echo "📦 Upgrade pip..."
pip install --upgrade pip

# Cài đặt thư viện từ requirements.txt
echo "📦 Cài đặt các gói trong requirements.txt..."
if [ -f "requirements.txt" ]; then
    # Cài setuptools trước (vì distutils đã bị remove trong Python 3.12)
    pip install --upgrade setuptools
    pip install -r requirements.txt
else
    echo "⚠️  Warning: requirements.txt not found. Skipping package installation."
fi

# Giải nén file .deb để lấy file thực thi
DEB_FILE="./multilogin/multiloginx.deb"
EXTRACT_DIR="./multilogin/extracted"

if [ ! -f "$DEB_FILE" ]; then
    echo "Error: $DEB_FILE not found!"
    exit 1
fi

echo "Extracting $DEB_FILE..."
mkdir -p "$EXTRACT_DIR"
dpkg-deb -x "$DEB_FILE" "$EXTRACT_DIR"

# Tìm file thực thi bất kỳ trong thư mục giải nén
EXECUTABLE=$(find "$EXTRACT_DIR" -type f -executable | head -n 1)
if [ -z "$EXECUTABLE" ]; then
    echo "Error: Could not find any executable in $DEB_FILE!"
    echo "Listing contents of $EXTRACT_DIR for debugging:"
    ls -lR "$EXTRACT_DIR"
    exit 1
fi

# Sao chép file thực thi về thư mục chạy
EXEC_NAME=$(basename "$EXECUTABLE")
cp "$EXECUTABLE" "./multilogin/$EXEC_NAME"
chmod +x "./multilogin/$EXEC_NAME"

# Chạy nền ứng dụng
echo "Starting $EXEC_NAME in the background..."
nohup "./multilogin/$EXEC_NAME" > multiloginx.log 2>&1 &

echo "Cleaning Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -exec rm -r {} +

echo "🎉 Hoàn tất! Môi trường $ENV_NAME đã được kích hoạt và cài đặt thư viện đầy đủ."

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up processes..."
    pkill -f "Xvfb :99" 2>/dev/null || true
    pkill -f "mlx-agent" 2>/dev/null || true
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
}

# Set trap for cleanup on exit (chỉ trap ERROR, không trap EXIT vì app chạy nền)
trap cleanup ERR INT TERM

echo "Đóng Xvfb hiện tại nếu có..."
pkill -f "Xvfb :99" 2>/dev/null || echo "Không có Xvfb nào đang chạy trên display :99"

# Khởi động Xvfb (X virtual framebuffer)
echo "Khởi động Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2

# Export DISPLAY cho phiên render ảo
export DISPLAY=:99
echo "Đã export DISPLAY=:99"

# Chạy agent MLX với sudo + nohup để chạy ngầm
echo "Khởi chạy mlx agent..."
if command -v mlx-agent &> /dev/null; then
    nohup sudo mlx-agent > mlx.log 2>&1 &
    MLX_PID=$!
    echo "MLX agent started with PID: $MLX_PID"
else
    echo "⚠️  Warning: mlx-agent command not found. Skipping MLX agent startup."
fi

sleep 5

# Chạy Flask app (giả sử là app.py)
echo "Killing any process running on port 5000..."
lsof -ti:5000 | xargs kill -9 2>/dev/null || echo "No process running on port 5000"

echo "Chạy Flask app..."
if [ -f "app.py" ]; then
    # Chạy app với nohup để nó không bị tắt khi SSH disconnect
    nohup python3 app.py > app.log 2>&1 &
    APP_PID=$!
    echo "✅ Flask app started with PID: $APP_PID"
    echo "🌐 App available at: http://localhost:5000"
    echo "📋 Logs: tail -f app.log"
    
    # Không dùng wait để script không bị block
    sleep 2
    echo "✅ App đang chạy nền - Có thể thoát SSH an toàn"
    echo "💡 Để xem logs: tail -f app.log"
    echo "💡 Để dừng app: pkill -f 'python.*app.py'"
else
    echo "❌ Error: app.py not found!"
    exit 1
fi

