#!/bin/bash

# Health check script for Resume ATS application
# This script performs comprehensive health checks

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_URL="${APP_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-30}"

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

# Check if service is responding
check_service_response() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    log_info "Checking $description..."
    
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response --max-time "$TIMEOUT" "$APP_URL$endpoint" || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        log_success "$description is healthy"
        return 0
    else
        log_error "$description failed (HTTP $response)"
        if [ -f /tmp/health_response ]; then
            cat /tmp/health_response
        fi
        return 1
    fi
}

# Check JSON response
check_json_response() {
    local endpoint="$1"
    local expected_field="$2"
    local expected_value="$3"
    local description="$4"
    
    log_info "Checking $description..."
    
    response=$(curl -s --max-time "$TIMEOUT" "$APP_URL$endpoint" || echo "{}")
    
    if command -v jq &> /dev/null; then
        actual_value=$(echo "$response" | jq -r ".$expected_field" 2>/dev/null || echo "null")
        
        if [ "$actual_value" = "$expected_value" ]; then
            log_success "$description is healthy"
            return 0
        else
            log_error "$description failed (expected: $expected_value, got: $actual_value)"
            echo "Response: $response"
            return 1
        fi
    else
        # Fallback without jq
        if echo "$response" | grep -q "\"$expected_field\".*\"$expected_value\""; then
            log_success "$description is healthy"
            return 0
        else
            log_error "$description failed"
            echo "Response: $response"
            return 1
        fi
    fi
}

# Check Docker containers
check_docker_containers() {
    log_info "Checking Docker containers..."
    
    cd "$PROJECT_ROOT"
    
    # Check if containers are running
    containers=$(docker-compose ps -q)
    
    if [ -z "$containers" ]; then
        log_error "No containers are running"
        return 1
    fi
    
    # Check each container status
    failed_containers=()
    
    while IFS= read -r container; do
        if [ -n "$container" ]; then
            status=$(docker inspect --format='{{.State.Status}}' "$container")
            name=$(docker inspect --format='{{.Name}}' "$container" | sed 's/^\///')
            
            if [ "$status" = "running" ]; then
                log_success "Container $name is running"
            else
                log_error "Container $name is not running (status: $status)"
                failed_containers+=("$name")
            fi
        fi
    done <<< "$containers"
    
    if [ ${#failed_containers[@]} -eq 0 ]; then
        return 0
    else
        log_error "Failed containers: ${failed_containers[*]}"
        return 1
    fi
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    cd "$PROJECT_ROOT"
    
    # Try to connect to database through the app
    if docker-compose exec -T app python -c "
import sys
sys.path.append('/app/backend')
try:
    from app.database import get_database
    db = get_database()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "Database is accessible"
        return 0
    else
        log_error "Database connection failed"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    cd "$PROJECT_ROOT"
    
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is accessible"
        return 0
    else
        log_error "Redis connection failed"
        return 1
    fi
}

# Check WebSocket connectivity
check_websocket() {
    log_info "Checking WebSocket connectivity..."
    
    # Use a simple WebSocket test
    ws_url="${APP_URL/http/ws}/api/v1/ws/general"
    
    # This is a basic check - in production you might want a more sophisticated test
    if curl -s --max-time 5 -H "Connection: Upgrade" -H "Upgrade: websocket" "$ws_url" &>/dev/null; then
        log_success "WebSocket endpoint is accessible"
        return 0
    else
        log_warning "WebSocket connectivity check inconclusive"
        return 0  # Don't fail the health check for this
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    # Check available disk space (require at least 1GB free)
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    required_space=1048576  # 1GB in KB
    
    if [ "$available_space" -gt "$required_space" ]; then
        log_success "Sufficient disk space available ($(($available_space / 1024))MB free)"
        return 0
    else
        log_warning "Low disk space ($(($available_space / 1024))MB free)"
        return 1
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."
    
    # Get memory usage of Docker containers
    cd "$PROJECT_ROOT"
    
    total_memory=$(docker stats --no-stream --format "table {{.MemUsage}}" | tail -n +2 | awk -F'/' '{sum += $1} END {print sum}' || echo "0")
    
    if [ "$total_memory" != "0" ]; then
        log_success "Container memory usage: ${total_memory}MB"
        return 0
    else
        log_warning "Could not determine memory usage"
        return 0  # Don't fail for this
    fi
}

# Generate health report
generate_report() {
    local overall_status="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > /tmp/health_report.json << EOF
{
    "timestamp": "$timestamp",
    "overall_status": "$overall_status",
    "app_url": "$APP_URL",
    "checks": {
        "basic_health": $basic_health_status,
        "detailed_health": $detailed_health_status,
        "docker_containers": $docker_status,
        "database": $database_status,
        "redis": $redis_status,
        "websocket": $websocket_status,
        "disk_space": $disk_status,
        "memory": $memory_status
    }
}
EOF
    
    log_info "Health report generated: /tmp/health_report.json"
}

# Main health check function
main() {
    log_info "Starting comprehensive health check..."
    log_info "Target URL: $APP_URL"
    log_info "Timeout: ${TIMEOUT}s"
    echo ""
    
    # Initialize status variables
    basic_health_status="false"
    detailed_health_status="false"
    docker_status="false"
    database_status="false"
    redis_status="false"
    websocket_status="false"
    disk_status="false"
    memory_status="false"
    
    overall_healthy=true
    
    # Basic health check
    if check_service_response "/health" "200" "Basic health endpoint"; then
        basic_health_status="true"
    else
        overall_healthy=false
    fi
    
    # Detailed health check
    if check_json_response "/api/v1/monitoring/health" "status" "healthy" "Detailed health endpoint"; then
        detailed_health_status="true"
    else
        overall_healthy=false
    fi
    
    # Docker containers check
    if check_docker_containers; then
        docker_status="true"
    else
        overall_healthy=false
    fi
    
    # Database check
    if check_database; then
        database_status="true"
    else
        overall_healthy=false
    fi
    
    # Redis check
    if check_redis; then
        redis_status="true"
    else
        overall_healthy=false
    fi
    
    # WebSocket check
    if check_websocket; then
        websocket_status="true"
    fi
    
    # Disk space check
    if check_disk_space; then
        disk_status="true"
    else
        overall_healthy=false
    fi
    
    # Memory check
    if check_memory; then
        memory_status="true"
    fi
    
    echo ""
    
    # Generate report
    if $overall_healthy; then
        generate_report "healthy"
        log_success "All health checks passed!"
        exit 0
    else
        generate_report "unhealthy"
        log_error "Some health checks failed!"
        exit 1
    fi
}

# Handle script arguments
case "${1:-check}" in
    "check")
        main
        ;;
    "basic")
        check_service_response "/health" "200" "Basic health endpoint"
        ;;
    "detailed")
        check_json_response "/api/v1/monitoring/health" "status" "healthy" "Detailed health endpoint"
        ;;
    "containers")
        check_docker_containers
        ;;
    "database")
        check_database
        ;;
    "redis")
        check_redis
        ;;
    "websocket")
        check_websocket
        ;;
    *)
        echo "Usage: $0 [check|basic|detailed|containers|database|redis|websocket]"
        echo "  check      - Run all health checks (default)"
        echo "  basic      - Basic health endpoint check"
        echo "  detailed   - Detailed health endpoint check"
        echo "  containers - Docker containers check"
        echo "  database   - Database connectivity check"
        echo "  redis      - Redis connectivity check"
        echo "  websocket  - WebSocket connectivity check"
        exit 1
        ;;
esac