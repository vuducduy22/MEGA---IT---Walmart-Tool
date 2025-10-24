# 🚀 WM-MEGA Deployment Guide

## 📋 Prerequisites

### Server Requirements:
- **OS**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **RAM**: Minimum 2GB (Recommended 4GB+)
- **Storage**: 10GB+ free space
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

## 🔧 Server Setup

### 1. Install Docker & Docker Compose
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. Clone Repository
```bash
git clone <your-repo-url>
cd WM-MEGA
```

## ⚙️ Configuration

### 1. Create Environment File
```bash
# Copy environment template
cp env.example .env

# Edit with your credentials
nano .env
```

### 2. Required Environment Variables
```bash
# MongoDB (Auto-configured)
MONGO_URI=mongodb://wm_mega_user:wm_mega@wm-mega-mongodb:27017/walmart

# MultiloginX (Required)
MLX_USERNAME=your_mlx_username
MLX_PASSWORD=your_mlx_password
MLX_SECRET_2FA=your_2fa_secret
MLX_WORKSPACE_EMAIL=your_workspace_email
FOLDER_ID=your_folder_id
WORKSPACE_ID=your_workspace_id

# AWS S3 (Optional)
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_BUCKET_NAME=mega.iart.group
AWS_FOLDER_NAME=images
AWS_REGION=us-east-2
```

### 3. Setup MultiloginX (Optional)
```bash
# Create multilogin directory
mkdir -p multilogin

# Upload multiloginx.deb file to multilogin/ directory
# (This file should be provided separately)
```

## 🚀 Deployment

### Method 1: Using Deploy Script (Recommended)
```bash
# Make script executable
chmod +x deploy.sh

# Start application
./deploy.sh start

# Check status
./deploy.sh status

# View logs
./deploy.sh logs
```

### Method 2: Direct Docker Compose
```bash
# Build and start
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🔍 Verification

### 1. Check Services
```bash
# Check containers
docker-compose ps

# Check logs
docker-compose logs wm-mega
docker-compose logs mongodb
```

### 2. Test Application
```bash
# Test Flask app
curl http://localhost:5000/

# Test MongoDB connection
docker exec wm-mega-mongodb mongo --eval "db.adminCommand('ismaster')"
```

### 3. Access Application
- **URL**: `http://your-server-ip:5000`
- **MongoDB**: `your-server-ip:27017`

## 🛠️ Management Commands

### Using Deploy Script
```bash
./deploy.sh start      # Start services
./deploy.sh stop       # Stop services
./deploy.sh restart    # Restart services
./deploy.sh status     # Check status
./deploy.sh logs       # View logs
./deploy.sh backup     # Create backup
./deploy.sh cleanup    # Clean up resources
```

### Using Docker Compose
```bash
docker-compose up -d           # Start services
docker-compose down            # Stop services
docker-compose restart         # Restart services
docker-compose ps              # Check status
docker-compose logs -f         # View logs
docker-compose down -v         # Stop and remove volumes
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Kill process on port 5000
sudo lsof -ti:5000 | xargs kill -9

# Or change port in docker-compose.yml
```

#### 2. MongoDB Connection Failed
```bash
# Check MongoDB container
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

#### 3. Permission Issues
```bash
# Fix permissions
sudo chown -R $USER:$USER .
chmod +x deploy.sh
```

#### 4. Out of Memory
```bash
# Check memory usage
docker stats

# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Logs Location
```bash
# Application logs
./logs/

# Docker logs
docker-compose logs wm-mega
docker-compose logs mongodb
```

## 🔒 Security

### Firewall Setup
```bash
# Allow only necessary ports
sudo ufw allow 22      # SSH
sudo ufw allow 5000    # Application
sudo ufw enable
```

### SSL/HTTPS (Optional)
```bash
# Install nginx reverse proxy
sudo apt install nginx

# Configure SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 📊 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:5000/

# Container health
docker-compose ps
```

### Resource Monitoring
```bash
# Container stats
docker stats

# System resources
htop
df -h
```

## 🔄 Updates

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
./deploy.sh update
```

### Backup Data
```bash
# Create backup
./deploy.sh backup

# Manual backup
docker exec wm-mega-mongodb mongodump --out /tmp/backup
```

## 📞 Support

If you encounter issues:
1. Check logs: `./deploy.sh logs`
2. Check status: `./deploy.sh status`
3. Restart services: `./deploy.sh restart`
4. Clean and rebuild: `./deploy.sh cleanup && ./deploy.sh start`
