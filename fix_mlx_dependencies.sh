#!/bin/bash

echo "🔧 Fixing MLX Agent Dependencies Conflict"
echo "========================================"

# Stop containers
echo "⏹️  Stopping containers..."
docker-compose down

# Fix dependencies manually in container
echo "🔨 Fixing dependencies..."
docker run --rm -v $(pwd):/app -w /app ubuntu:22.04 bash -c "
    apt update
    apt install -y libayatana-appindicator3-1 || apt install -y libappindicator3-1
    apt install -y libindicator3-7 libgtk-3-0 libgdk-pixbuf2.0-0
"

# Rebuild image
echo "🔨 Rebuilding Docker image..."
docker-compose build --no-cache

# Start containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for containers to start
echo "⏳ Waiting for containers to start..."
sleep 20

# Check container status
echo "📊 Checking container status..."
docker-compose ps

# Check MLX Agent logs
echo "📋 Checking MLX Agent logs..."
docker-compose logs wm-mega | grep -i "MLX Agent"

# Check if MLX Agent is running
echo "🔍 Checking MLX Agent process..."
docker exec wm-mega-app ps aux | grep -i mlx

# Check port 45001
echo "🔌 Checking port 45001..."
docker exec wm-mega-app netstat -tlnp | grep 45001

echo "✅ Fix completed!"
echo "💡 Check the logs above to see if MLX Agent started successfully."
