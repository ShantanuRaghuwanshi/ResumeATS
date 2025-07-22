# Resume ATS Deployment Guide

This guide provides comprehensive instructions for deploying the Resume ATS application in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Deployment Options](#deployment-options)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB recommended for production)
- **Storage**: Minimum 10GB free space
- **Network**: Internet connection for downloading dependencies

### Required Software

- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Git**: For cloning the repository
- **curl**: For health checks and API testing

### Optional Software

- **jq**: For JSON processing in scripts
- **openssl**: For SSL certificate generation

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd resume-ats
```

### 2. Run Setup Script

```bash
chmod +x deployment/scripts/setup.sh
./deployment/scripts/setup.sh
```

This script will:

- Install Docker and Docker Compose (if needed)
- Create necessary directories
- Generate SSL certificates
- Create configuration files
- Set up environment variables

### 3. Configure Environment

Edit the `.env` file with your settings:

```bash
nano .env
```

**Required configurations:**

- `JWT_SECRET_KEY`: Set a secure random key
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (if using Claude)

### 4. Deploy Application

```bash
chmod +x deployment/scripts/deploy.sh
./deployment/scripts/deploy.sh production
```

### 5. Verify Deployment

```bash
chmod +x deployment/scripts/health-check.sh
./deployment/scripts/health-check.sh
```

## Environment Configuration

### Environment Variables

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed.

#### Core Settings

```env
# Application
NODE_ENV=production
DEBUG=false
LOG_LEVEL=INFO
APP_PORT=8000

# Security
JWT_SECRET_KEY=your_secure_jwt_secret_key
CORS_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/resumeats
# Or for SQLite: sqlite:///app/data/app.db

# Redis
REDIS_URL=redis://redis:6379
```

#### LLM Provider Configuration

```env
# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Google
GOOGLE_API_KEY=your-google-api-key

# Ollama (for local LLM)
OLLAMA_BASE_URL=http://ollama:11434
```

#### Optional Features

```env
# Monitoring
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Email Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Upload Limits
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=pdf,docx,txt
```

## Deployment Options

### Development Deployment

For development with hot reloading and debugging:

```bash
./deployment/scripts/deploy.sh development
```

Features:

- Hot reloading enabled
- Debug mode active
- Detailed logging
- No SSL/HTTPS
- Single worker process

### Production Deployment

For production with full security and monitoring:

```bash
./deployment/scripts/deploy.sh production
```

Features:

- SSL/HTTPS enabled
- Nginx reverse proxy
- Multiple worker processes
- Monitoring with Prometheus/Grafana
- Security headers
- Log rotation

### Docker Compose Profiles

The application supports different Docker Compose profiles:

```bash
# Basic deployment
docker-compose up -d

# With production features (Nginx, SSL)
docker-compose --profile production up -d

# With local LLM support
docker-compose --profile local-llm up -d

# With monitoring stack
docker-compose --profile monitoring up -d

# Combined profiles
docker-compose --profile production --profile monitoring up -d
```

## Monitoring and Health Checks

### Health Check Endpoints

- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /api/v1/monitoring/health`
- **System Metrics**: `GET /api/v1/monitoring/metrics`
- **Service Status**: `GET /api/v1/monitoring/services/status`

### Automated Health Checks

Run comprehensive health checks:

```bash
./deployment/scripts/health-check.sh
```

Available check types:

- `basic`: Basic application health
- `detailed`: Detailed service health
- `containers`: Docker container status
- `database`: Database connectivity
- `redis`: Redis connectivity
- `websocket`: WebSocket functionality

### Monitoring Stack

When deployed with the monitoring profile:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Log Management

Logs are stored in the `logs/` directory:

- `application.log`: General application logs
- `errors.log`: Error logs only
- `performance.log`: Performance metrics
- `audit.log`: Security and audit events
- `websocket.log`: WebSocket events
- Service-specific logs for each component

## Backup and Recovery

### Automated Backups

Create a backup:

```bash
./deployment/scripts/deploy.sh backup
```

This creates:

- Database dump
- Application data archive
- Uploaded files archive
- Configuration backup

### Manual Backup

```bash
# Database backup
docker-compose exec postgres pg_dump -U resumeats resumeats > backup_$(date +%Y%m%d).sql

# Data volumes backup
docker run --rm -v resumeats_app_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/app_data_$(date +%Y%m%d).tar.gz -C /data .
```

### Recovery

```bash
# Restore database
docker-compose exec -T postgres psql -U resumeats resumeats < backup_20231201.sql

# Restore data volumes
docker run --rm -v resumeats_app_data:/data -v $(pwd)/backups:/backup alpine tar xzf /backup/app_data_20231201.tar.gz -C /data
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000

# Kill the process or change the port in .env
APP_PORT=8001
```

#### 2. Docker Permission Denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

#### 3. SSL Certificate Issues

```bash
# Regenerate SSL certificates
rm -rf deployment/nginx/ssl/*
./deployment/scripts/setup.sh
```

#### 4. Database Connection Failed

```bash
# Check database container
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### 5. Out of Memory

```bash
# Check container memory usage
docker stats

# Increase Docker memory limit or server resources
```

### Debug Mode

Enable debug mode for troubleshooting:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Container Logs

View logs for specific services:

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# Redis logs
docker-compose logs -f redis

# All logs
docker-compose logs -f
```

### Performance Issues

1. **Check system resources**:

   ```bash
   docker stats
   df -h
   free -h
   ```

2. **Monitor application metrics**:

   - Visit `/api/v1/monitoring/metrics`
   - Check Grafana dashboards (if enabled)

3. **Optimize configuration**:
   - Increase worker processes
   - Tune database connections
   - Enable caching

## Security Considerations

### Production Security Checklist

- [ ] Change default passwords
- [ ] Use strong JWT secret key
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Set up proper CORS origins
- [ ] Enable rate limiting
- [ ] Configure secure headers
- [ ] Set up log monitoring
- [ ] Regular security updates
- [ ] Backup encryption

### Network Security

```bash
# Firewall configuration (example for Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### SSL/TLS Configuration

For production, replace self-signed certificates with proper SSL certificates:

```bash
# Using Let's Encrypt (example)
certbot certonly --webroot -w /var/www/html -d yourdomain.com
```

### Environment Security

- Store sensitive data in environment variables
- Use Docker secrets for production
- Regularly rotate API keys
- Monitor for security vulnerabilities

## Scaling and Performance

### Horizontal Scaling

For high-traffic deployments:

1. **Load Balancer**: Use multiple app instances behind a load balancer
2. **Database Scaling**: Use read replicas or database clustering
3. **Redis Clustering**: For session and cache scaling
4. **CDN**: For static asset delivery

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G
```

### Performance Tuning

1. **Database Optimization**:

   - Tune PostgreSQL settings
   - Add appropriate indexes
   - Use connection pooling

2. **Caching Strategy**:

   - Enable Redis caching
   - Configure cache TTL
   - Use CDN for static assets

3. **Application Tuning**:
   - Increase worker processes
   - Optimize LLM API calls
   - Enable compression

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**:

   - Check system health
   - Review error logs
   - Monitor disk space

2. **Monthly**:

   - Update dependencies
   - Rotate logs
   - Performance review

3. **Quarterly**:
   - Security audit
   - Backup testing
   - Capacity planning

### Getting Help

- Check the troubleshooting section
- Review application logs
- Run health checks
- Check system resources

For additional support, please refer to the main project documentation or contact the development team.
