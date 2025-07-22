#!/bin/bash

# Setup script for Resume ATS application
# This script prepares the environment for deployment

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS"
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_success "Docker is already installed"
        return 0
    fi
    
    case $OS in
        "linux")
            # Install Docker on Linux
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            ;;
        "macos")
            log_warning "Please install Docker Desktop for Mac from https://docs.docker.com/desktop/mac/install/"
            log_warning "After installation, run this script again."
            exit 1
            ;;
        "windows")
            log_warning "Please install Docker Desktop for Windows from https://docs.docker.com/desktop/windows/install/"
            log_warning "After installation, run this script again."
            exit 1
            ;;
    esac
    
    log_success "Docker installed successfully"
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose is already installed"
        return 0
    fi
    
    case $OS in
        "linux")
            # Install Docker Compose on Linux
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            ;;
        "macos"|"windows")
            log_info "Docker Compose is included with Docker Desktop"
            ;;
    esac
    
    log_success "Docker Compose installed successfully"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    cd "$PROJECT_ROOT"
    
    directories=(
        "logs"
        "data"
        "uploads"
        "backups"
        "deployment/nginx/ssl"
        "deployment/monitoring"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    log_success "Directories created successfully"
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    cd "$PROJECT_ROOT"
    
    if [ ! -f ".env" ]; then
        cp ".env.example" ".env"
        log_success "Created .env file from template"
        
        # Generate JWT secret key
        jwt_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "your_jwt_secret_key_here_make_it_long_and_random")
        
        # Update .env file with generated values
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed syntax
            sed -i '' "s/your_jwt_secret_key_here_make_it_long_and_random/$jwt_secret/" .env
        else
            # Linux sed syntax
            sed -i "s/your_jwt_secret_key_here_make_it_long_and_random/$jwt_secret/" .env
        fi
        
        log_warning "Please edit .env file and configure your API keys and other settings"
    else
        log_success ".env file already exists"
    fi
}

# Setup SSL certificates (self-signed for development)
setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    ssl_dir="$PROJECT_ROOT/deployment/nginx/ssl"
    
    if [ ! -f "$ssl_dir/cert.pem" ] || [ ! -f "$ssl_dir/key.pem" ]; then
        log_info "Generating self-signed SSL certificate..."
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/key.pem" \
            -out "$ssl_dir/cert.pem" \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        log_success "SSL certificate generated"
        log_warning "This is a self-signed certificate for development only"
    else
        log_success "SSL certificates already exist"
    fi
}

# Create Nginx configuration
create_nginx_config() {
    log_info "Creating Nginx configuration..."
    
    nginx_dir="$PROJECT_ROOT/deployment/nginx"
    mkdir -p "$nginx_dir"
    
    cat > "$nginx_dir/nginx.conf" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name localhost;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_min_length 1024;
        gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

        # Client max body size
        client_max_body_size 10M;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /health {
            proxy_pass http://app/health;
            access_log off;
        }

        # Static files (if serving from Nginx)
        location /static/ {
            alias /app/frontend/dist/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF
    
    log_success "Nginx configuration created"
}

# Create monitoring configuration
create_monitoring_config() {
    log_info "Creating monitoring configuration..."
    
    monitoring_dir="$PROJECT_ROOT/deployment/monitoring"
    mkdir -p "$monitoring_dir/grafana/dashboards" "$monitoring_dir/grafana/datasources"
    
    # Prometheus configuration
    cat > "$monitoring_dir/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'resume-ats'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/api/v1/monitoring/metrics'
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

    # Grafana datasource configuration
    cat > "$monitoring_dir/grafana/datasources/prometheus.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    log_success "Monitoring configuration created"
}

# Set file permissions
set_permissions() {
    log_info "Setting file permissions..."
    
    cd "$PROJECT_ROOT"
    
    # Make scripts executable
    chmod +x deployment/scripts/*.sh
    
    # Set appropriate permissions for data directories
    chmod 755 logs data uploads backups
    
    log_success "File permissions set"
}

# Validate setup
validate_setup() {
    log_info "Validating setup..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        return 1
    fi
    
    # Check required files
    required_files=(
        ".env"
        "docker-compose.yml"
        "Dockerfile"
        "deployment/nginx/nginx.conf"
        "deployment/monitoring/prometheus.yml"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_ROOT/$file" ]; then
            log_error "Required file missing: $file"
            return 1
        fi
    done
    
    log_success "Setup validation passed"
}

# Main setup function
main() {
    log_info "Starting Resume ATS setup..."
    
    detect_os
    install_docker
    install_docker_compose
    create_directories
    setup_environment
    setup_ssl
    create_nginx_config
    create_monitoring_config
    set_permissions
    
    if validate_setup; then
        log_success "Setup completed successfully!"
        echo ""
        log_info "Next steps:"
        echo "1. Edit .env file with your configuration"
        echo "2. Run: ./deployment/scripts/deploy.sh"
        echo ""
        log_info "For development:"
        echo "  ./deployment/scripts/deploy.sh development"
        echo ""
        log_info "For production:"
        echo "  ./deployment/scripts/deploy.sh production"
    else
        log_error "Setup validation failed"
        exit 1
    fi
}

# Run main function
main