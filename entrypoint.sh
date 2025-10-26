#!/bin/bash

# WM-MEGA Docker Entrypoint Script
# Optimized for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

# Cleanup function
cleanup() {
    log "Cleaning up processes..."
    pkill -f "Xvfb :99" 2>/dev/null || true
    pkill -f "mlx-agent" 2>/dev/null || true
    pkill -f "python3 /app/app.py" 2>/dev/null || true
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    log_success "Cleanup completed"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

log "🚀 Starting WM-MEGA Application..."

# 1. Setup Xvfb (Virtual Display)
log "Setting up Xvfb virtual display..."
pkill -f "Xvfb :99" 2>/dev/null || log "No existing Xvfb process found"

# Start Xvfb with optimized settings
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 3
export DISPLAY=:99

# Verify Xvfb is running
if xdpyinfo -display :99 >/dev/null 2>&1; then
    log_success "Xvfb ready on display :99"
else
    log_error "Failed to start Xvfb"
    exit 1
fi

# 2. Extract MultiloginX if available
if [ -f "/app/multilogin/multiloginx.deb" ]; then
    log "Extracting MultiloginX..."
    mkdir -p /app/multilogin/extracted
    
    if dpkg-deb -x /app/multilogin/multiloginx.deb /app/multilogin/extracted; then
        # Find and copy executable
        EXECUTABLE=$(find /app/multilogin/extracted -type f -executable | head -n 1)
        if [ -n "$EXECUTABLE" ]; then
            EXEC_NAME=$(basename "$EXECUTABLE")
            cp "$EXECUTABLE" "/app/multilogin/$EXEC_NAME"
            chmod +x "/app/multilogin/$EXEC_NAME"
            log_success "MultiloginX extracted: $EXEC_NAME"
        else
            log_warning "No executable found in MultiloginX package"
        fi
    else
        log_error "Failed to extract MultiloginX package"
    fi
else
    log_warning "MultiloginX .deb file not found, skipping..."
fi

# 3. Setup and Start MLX Agent
if [ -f "/app/multilogin/mlx" ]; then
    log "Setting up MLX Agent..."
    
    # Create /opt/mlx directory if not exists
    sudo mkdir -p /opt/mlx
    
    # Copy agent.bin to correct location if not exists
    if [ ! -f "/opt/mlx/agent.bin" ] && [ -f "/app/multilogin/extracted/opt/mlx/agent.bin" ]; then
        sudo cp /app/multilogin/extracted/opt/mlx/agent.bin /opt/mlx/agent.bin
        sudo chmod +x /opt/mlx/agent.bin
        log "Copied agent.bin to /opt/mlx/"
    fi
    
    # Install missing dependencies
    log "Installing MLX Agent dependencies..."
    sudo apt update -qq
    
    # Try to install dependencies, handle conflicts
    if sudo apt install -y libayatana-appindicator3-1 2>/dev/null; then
        log "Installed libayatana-appindicator3-1"
    elif sudo apt install -y libappindicator3-1 2>/dev/null; then
        log "Installed libappindicator3-1"
    else
        log_warning "Could not install appindicator library, trying alternative..."
        sudo apt install -y libindicator3-7 libgtk-3-0 libgdk-pixbuf2.0-0
    fi
    
    # Test MLX Agent
    if /app/multilogin/mlx --version >/dev/null 2>&1; then
        log "Starting MLX Agent..."
        nohup /app/multilogin/mlx > /app/logs/mlx.log 2>&1 &
        MLX_PID=$!
        sleep 2
        
        # Check if MLX Agent is running
        if ps -p $MLX_PID > /dev/null 2>&1; then
            log_success "MLX Agent started with PID: $MLX_PID"
        else
            log_warning "MLX Agent failed to start, check logs"
        fi
    else
        log_error "MLX Agent test failed, check dependencies"
    fi
else
    log_warning "MLX executable not found, skipping..."
fi

# 4. Clean Python cache
log "Cleaning Python cache..."
find /app -name "*.pyc" -delete 2>/dev/null || true
find /app -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 5. Create necessary directories
mkdir -p /app/uploads /app/logs

# 6. Start Flask application
log "Starting Flask application..."
log "Application will be available at: http://localhost:5000"

# Kill any existing process on port 5000
lsof -ti:5000 | xargs kill -9 2>/dev/null || log "Port 5000 is free"

# Start Flask app with proper error handling
exec python3 /app/app.py
