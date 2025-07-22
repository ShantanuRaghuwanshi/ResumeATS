#!/bin/bash

# Deployment script for Resume ATS application
# This script handles the complete deployment process

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_ENV="${1:-production}"
COMPOSE_FILE="docker-compose.yml"

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

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

# Validate environment configuration
validate_environment() {
    log_info "Validating environment configuration..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_warning ".env file not found. Creating from template..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log_warning "Please edit .env file with your configuration before continuing."
        exit 1
    fi
    
    # Source environment variables
    source "$PROJECT_ROOT/.env"
    
    # Check required variables
    required_vars=("JWT_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Environment configuration is valid"
}

# Build application images
build_images() {
    log_info "Building application images..."
    
    cd "$PROJECT_ROOT"
    
    # Build with no cache for production
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        docker-compose -f "$COMPOSE_FILE" build --no-cache
    else
        docker-compose -f "$COMPOSE_FILE" build
    fi
    
    log_success "Images built successfully"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_ROOT"
    
    # Start database services first
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    docker-compose -f "$COMPOSE_FILE" run --rm app python backend/app/database/migrations.py
    
    log_success "Database migrations completed"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Set the appropriate profile based on environment
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        export COMPOSE_PROFILES="production"
    elif [ "$DEPLOYMENT_ENV" = "development" ]; then
        export COMPOSE_PROFILES=""
    fi
    
    # Stop existing containers
    docker-compose -f "$COMPOSE_FILE" down
    
    # Start all services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Application deployed successfully"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait for application to start
    sleep 30
    
    # Check application health
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:${APP_PORT:-8000}/health > /dev/null 2>&1; then
            log_success "Application is healthy"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Show deployment status
show_status() {
    log_info "Deployment status:"
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log_info "Application URLs:"
    echo "  - Main application: http://localhost:${APP_PORT:-8000}"
    echo "  - Health check: http://localhost:${APP_PORT:-8000}/health"
    echo "  - API documentation: http://localhost:${APP_PORT:-8000}/docs"
    
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        echo "  - Nginx proxy: http://localhost:${NGINX_PORT:-80}"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    
    cd "$PROJECT_ROOT"
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this in production)
    if [ "$DEPLOYMENT_ENV" != "production" ]; then
        docker volume prune -f
    fi
    
    log_success "Cleanup completed"
}

# Backup function
backup_data() {
    log_info "Creating data backup..."
    
    cd "$PROJECT_ROOT"
    
    # Create backup directory
    backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup database
    if docker-compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U ${POSTGRES_USER:-resumeats} ${POSTGRES_DB:-resumeats} > "$backup_dir/database.sql"
    fi
    
    # Backup application data
    docker run --rm -v resumeats_app_data:/data -v "$PROJECT_ROOT/$backup_dir":/backup alpine tar czf /backup/app_data.tar.gz -C /data .
    
    # Backup uploads
    docker run --rm -v resumeats_app_uploads:/data -v "$PROJECT_ROOT/$backup_dir":/backup alpine tar czf /backup/uploads.tar.gz -C /data .
    
    log_success "Backup created in $backup_dir"
}

# Main deployment function
main() {
    log_info "Starting deployment for environment: $DEPLOYMENT_ENV"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run deployment steps
    check_dependencies
    validate_environment
    
    # Create backup before deployment (production only)
    if [ "$DEPLOYMENT_ENV" = "production" ]; then
        backup_data
    fi
    
    build_images
    run_migrations
    deploy_application
    
    # Perform health check
    if health_check; then
        show_status
        log_success "Deployment completed successfully!"
    else
        log_error "Deployment failed health check"
        exit 1
    fi
    
    # Cleanup (development only)
    if [ "$DEPLOYMENT_ENV" = "development" ]; then
        cleanup
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "backup")
        backup_data
        ;;
    "cleanup")
        cleanup
        ;;
    "health")
        health_check
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 [deploy|backup|cleanup|health|status] [environment]"
        echo "  deploy    - Full deployment (default)"
        echo "  backup    - Create data backup"
        echo "  cleanup   - Clean up unused Docker resources"
        echo "  health    - Perform health check"
        echo "  status    - Show deployment status"
        echo ""
        echo "Environment options: production (default), development"
        exit 1
        ;;
esac