# PowerShell deployment script for Resume ATS application
# Windows-compatible version of deploy.sh

param(
    [string]$Environment = "production",
    [string]$Action = "deploy"
)

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ComposeFile = "docker-compose.yml"

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
}

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

# Check if required tools are installed
function Test-Dependencies {
    Write-Info "Checking dependencies..."
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    }
    
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    Write-Success "All dependencies are installed"
}

# Validate environment configuration
function Test-Environment {
    Write-Info "Validating environment configuration..."
    
    $envFile = Join-Path $ProjectRoot ".env"
    
    if (-not (Test-Path $envFile)) {
        Write-Warning ".env file not found. Creating from template..."
        $envExample = Join-Path $ProjectRoot ".env.example"
        Copy-Item $envExample $envFile
        Write-Warning "Please edit .env file with your configuration before continuing."
        exit 1
    }
    
    # Check for required variables
    $envContent = Get-Content $envFile
    $jwtSecretLine = $envContent | Where-Object { $_ -match "^JWT_SECRET_KEY=" }
    
    if (-not $jwtSecretLine -or $jwtSecretLine -match "your_jwt_secret_key_here") {
        Write-Error "JWT_SECRET_KEY is not properly configured in .env file"
        exit 1
    }
    
    Write-Success "Environment configuration is valid"
}

# Build application images
function Build-Images {
    Write-Info "Building application images..."
    
    Set-Location $ProjectRoot
    
    if ($Environment -eq "production") {
        docker-compose -f $ComposeFile build --no-cache
    } else {
        docker-compose -f $ComposeFile build
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build images"
        exit 1
    }
    
    Write-Success "Images built successfully"
}

# Run database migrations
function Invoke-Migrations {
    Write-Info "Running database migrations..."
    
    Set-Location $ProjectRoot
    
    # Start database services first
    docker-compose -f $ComposeFile up -d postgres redis
    
    # Wait for database to be ready
    Write-Info "Waiting for database to be ready..."
    Start-Sleep -Seconds 10
    
    # Run migrations
    docker-compose -f $ComposeFile run --rm app python backend/app/database/migrations.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Database migrations failed"
        exit 1
    }
    
    Write-Success "Database migrations completed"
}

# Deploy application
function Deploy-Application {
    Write-Info "Deploying application..."
    
    Set-Location $ProjectRoot
    
    # Set the appropriate profile based on environment
    if ($Environment -eq "production") {
        $env:COMPOSE_PROFILES = "production"
    } else {
        $env:COMPOSE_PROFILES = ""
    }
    
    # Stop existing containers
    docker-compose -f $ComposeFile down
    
    # Start all services
    docker-compose -f $ComposeFile up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to deploy application"
        exit 1
    }
    
    Write-Success "Application deployed successfully"
}

# Health check
function Test-Health {
    Write-Info "Performing health check..."
    
    # Wait for application to start
    Start-Sleep -Seconds 30
    
    # Check application health
    $maxAttempts = 10
    $attempt = 1
    
    while ($attempt -le $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "Application is healthy"
                return $true
            }
        } catch {
            # Continue to retry
        }
        
        Write-Info "Health check attempt $attempt/$maxAttempts failed, retrying..."
        Start-Sleep -Seconds 10
        $attempt++
    }
    
    Write-Error "Health check failed after $maxAttempts attempts"
    return $false
}

# Show deployment status
function Show-Status {
    Write-Info "Deployment status:"
    
    Set-Location $ProjectRoot
    docker-compose -f $ComposeFile ps
    
    Write-Host ""
    Write-Info "Application URLs:"
    Write-Host "  - Main application: http://localhost:8000"
    Write-Host "  - Health check: http://localhost:8000/health"
    Write-Host "  - API documentation: http://localhost:8000/docs"
    
    if ($Environment -eq "production") {
        Write-Host "  - Nginx proxy: http://localhost:80"
    }
}

# Backup function
function Backup-Data {
    Write-Info "Creating data backup..."
    
    Set-Location $ProjectRoot
    
    # Create backup directory
    $backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup database
    $postgresRunning = docker-compose -f $ComposeFile ps postgres | Select-String "Up"
    if ($postgresRunning) {
        docker-compose -f $ComposeFile exec -T postgres pg_dump -U resumeats resumeats > "$backupDir\database.sql"
    }
    
    # Backup application data
    docker run --rm -v resumeats_app_data:/data -v "${PWD}\${backupDir}:/backup" alpine tar czf /backup/app_data.tar.gz -C /data .
    
    # Backup uploads
    docker run --rm -v resumeats_app_uploads:/data -v "${PWD}\${backupDir}:/backup" alpine tar czf /backup/uploads.tar.gz -C /data .
    
    Write-Success "Backup created in $backupDir"
}

# Cleanup function
function Remove-UnusedResources {
    Write-Info "Cleaning up..."
    
    Set-Location $ProjectRoot
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this in production)
    if ($Environment -ne "production") {
        docker volume prune -f
    }
    
    Write-Success "Cleanup completed"
}

# Main deployment function
function Invoke-Deploy {
    Write-Info "Starting deployment for environment: $Environment"
    
    # Change to project root
    Set-Location $ProjectRoot
    
    # Run deployment steps
    Test-Dependencies
    Test-Environment
    
    # Create backup before deployment (production only)
    if ($Environment -eq "production") {
        Backup-Data
    }
    
    Build-Images
    Invoke-Migrations
    Deploy-Application
    
    # Perform health check
    if (Test-Health) {
        Show-Status
        Write-Success "Deployment completed successfully!"
    } else {
        Write-Error "Deployment failed health check"
        exit 1
    }
    
    # Cleanup (development only)
    if ($Environment -eq "development") {
        Remove-UnusedResources
    }
}

# Handle script actions
switch ($Action.ToLower()) {
    "deploy" {
        Invoke-Deploy
    }
    "backup" {
        Backup-Data
    }
    "cleanup" {
        Remove-UnusedResources
    }
    "health" {
        Test-Health
    }
    "status" {
        Show-Status
    }
    default {
        Write-Host "Usage: .\deploy.ps1 [-Environment <production|development>] [-Action <deploy|backup|cleanup|health|status>]"
        Write-Host "  deploy    - Full deployment (default)"
        Write-Host "  backup    - Create data backup"
        Write-Host "  cleanup   - Clean up unused Docker resources"
        Write-Host "  health    - Perform health check"
        Write-Host "  status    - Show deployment status"
        Write-Host ""
        Write-Host "Environment options: production (default), development"
        exit 1
    }
}