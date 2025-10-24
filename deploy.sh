#!/bin/bash

# WM-MEGA Docker Management Script
# Tối ưu hóa cho production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="wm-mega-app"
IMAGE_NAME="wm-mega"
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="wm-mega"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  WM-MEGA Docker Management${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if required files exist
check_requirements() {
    local missing_files=()
    
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi
    
    if [ ! -f "app.py" ]; then
        missing_files+=("app.py")
    fi
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Please create one with required environment variables."
    fi
    
    if [ ! -f "multilogin/multiloginx.deb" ]; then
        print_warning "multiloginx.deb not found. MultiloginX features will be disabled."
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "Missing required files: ${missing_files[*]}"
        exit 1
    fi
    
    print_success "All required files found"
}

# Build Docker image
build_image() {
    print_info "Building Docker image..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache
    print_success "Docker image built successfully"
}

# Start services
start_services() {
    print_info "Starting WM-MEGA services..."
    
    # Stop existing containers first
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down 2>/dev/null || true
    
    # Start services in background
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    
    # Wait for services to be ready
    print_info "Waiting for services to start..."
    sleep 10
    
    # Check if Flask app is responding
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:5000/ >/dev/null 2>&1; then
            print_success "WM-MEGA is running successfully!"
            print_info "Application URL: http://localhost:5000"
            return 0
        fi
        
        print_info "Waiting for application... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    print_error "Application failed to start within expected time"
    return 1
}

# Stop services
stop_services() {
    print_info "Stopping WM-MEGA services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    print_success "Services stopped"
}

# Show logs
show_logs() {
    print_info "Showing application logs..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
}

# Show status
show_status() {
    print_info "Container status:"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    
    echo ""
    print_info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" $CONTAINER_NAME 2>/dev/null || print_warning "Container not running"
}

# Clean up
cleanup() {
    print_info "Cleaning up..."
    
    # Stop and remove containers
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    print_success "Cleanup completed"
}

# Restart services
restart_services() {
    print_info "Restarting services..."
    stop_services
    sleep 2
    start_services
}

# Update application
update_app() {
    print_info "Updating application..."
    
    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        git pull origin main
    fi
    
    # Rebuild and restart
    build_image
    restart_services
}

# Backup data
backup_data() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    print_info "Creating backup in $backup_dir..."
    
    # Backup uploads
    if [ -d "uploads" ]; then
        cp -r uploads "$backup_dir/"
    fi
    
    # Backup logs
    if [ -d "logs" ]; then
        cp -r logs "$backup_dir/"
    fi
    
    # Backup database (if using local MongoDB)
    if docker ps | grep -q "wm-mega-mongodb"; then
        docker exec wm-mega-mongodb mongodump --out /tmp/backup
        docker cp wm-mega-mongodb:/tmp/backup "$backup_dir/mongodb"
    fi
    
    print_success "Backup created: $backup_dir"
}

# Main menu
show_menu() {
    echo ""
    echo -e "${BLUE}Available commands:${NC}"
    echo "  start     - Start WM-MEGA services"
    echo "  stop      - Stop WM-MEGA services"
    echo "  restart   - Restart WM-MEGA services"
    echo "  build     - Build Docker image"
    echo "  logs      - Show application logs"
    echo "  status    - Show container status"
    echo "  update    - Update and restart application"
    echo "  backup    - Create data backup"
    echo "  cleanup   - Clean up Docker resources"
    echo "  help      - Show this menu"
    echo ""
}

# Main script logic
main() {
    print_header
    
    # Check Docker
    check_docker
    
    # Check requirements
    check_requirements
    
    # Parse command
    case "${1:-help}" in
        "start")
            build_image
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "build")
            build_image
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "update")
            update_app
            ;;
        "backup")
            backup_data
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            show_menu
            ;;
    esac
}

# Run main function
main "$@"
