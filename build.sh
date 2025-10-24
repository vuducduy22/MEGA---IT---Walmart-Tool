#!/bin/bash

set -e  # Exit on any error

ENV_NAME="myenv"

# Initialize conda
echo "🔧 Initializing conda..."
eval "$(conda shell.bash hook)"

# Kiểm tra xem môi trường đã tồn tại chưa
if conda env list | grep -qE "^$ENV_NAME\s"; then
    echo "✅ Môi trường Conda '$ENV_NAME' đã tồn tại. Bỏ qua bước tạo."
else
    echo "🚀 Tạo môi trường Conda: $ENV_NAME (Python 3.10)..."
    conda create -n $ENV_NAME python=3.10 -y
    echo "✅ Đã tạo môi trường $ENV_NAME!"
fi

# Kích hoạt môi trường
echo "⚙️  Kích hoạt môi trường..."
conda activate $ENV_NAME

# Cài đặt thư viện từ requirements.txt
echo "📦 Cài đặt các gói trong requirements.txt..."
if [ -f "requirements.txt" ]; then
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

# Set trap for cleanup on exit
trap cleanup EXIT

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
    python3 app.py
else
    echo "❌ Error: app.py not found!"
    exit 1
fi

