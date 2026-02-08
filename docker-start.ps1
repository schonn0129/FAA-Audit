# FAA Audit Application - Windows Docker Startup Script
# This script makes it easy to manage the Docker containers on Windows

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("up", "down", "logs", "build", "rebuild", "status")]
    [string]$action = "up"
)

$composeFile = "docker-compose.windows.yml"
$backendUrl = "http://localhost:5000/api/health"
$frontendUrl = "http://localhost:8888"

function Test-DockerInstalled {
    try {
        docker --version | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-Service {
    param(
        [string]$url,
        [string]$serviceName
    )
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "✓ $serviceName is running" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ $serviceName is not responding" -ForegroundColor Red
        return $false
    }
}

function Show-Status {
    Write-Host "`n=== FAA Audit Application Status ===" -ForegroundColor Cyan
    Write-Host "Backend:  $backendUrl" -ForegroundColor Gray
    Write-Host "Frontend: $frontendUrl" -ForegroundColor Gray
    Write-Host ""
    
    Test-Service -url $backendUrl -serviceName "Backend API"
    Test-Service -url $frontendUrl -serviceName "Frontend UI"
    
    Write-Host ""
    Write-Host "Docker containers:" -ForegroundColor Cyan
    docker ps --filter "name=faa-audit" --format "table {{.Names}}\t{{.Status}}"
    Write-Host ""
}

# Main execution
if (-not (Test-DockerInstalled)) {
    Write-Host "ERROR: Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "FAA Audit Application - Docker Management" -ForegroundColor Cyan
Write-Host "Command: $action" -ForegroundColor Gray
Write-Host ""

switch ($action) {
    "up" {
        Write-Host "Starting containers..." -ForegroundColor Cyan
        docker-compose -f $composeFile up -d
        Write-Host "Waiting for services to start..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        Show-Status
        Write-Host ""
        Write-Host "Access the application at:" -ForegroundColor Green
        Write-Host "  Frontend: http://localhost:8888" -ForegroundColor Yellow
        Write-Host "  Backend:  http://localhost:5000/api/health" -ForegroundColor Yellow
    }
    
    "down" {
        Write-Host "Stopping containers..." -ForegroundColor Cyan
        docker-compose -f $composeFile down
        Write-Host "Containers stopped." -ForegroundColor Green
    }
    
    "logs" {
        Write-Host "Displaying logs (press Ctrl+C to exit)..." -ForegroundColor Cyan
        docker-compose -f $composeFile logs -f
    }
    
    "build" {
        Write-Host "Building containers..." -ForegroundColor Cyan
        docker-compose -f $composeFile build
        Write-Host "Build complete." -ForegroundColor Green
    }
    
    "rebuild" {
        Write-Host "Rebuilding containers (no cache)..." -ForegroundColor Cyan
        docker-compose -f $composeFile build --no-cache
        docker-compose -f $composeFile down
        docker-compose -f $composeFile up -d
        Start-Sleep -Seconds 5
        Show-Status
        Write-Host ""
        Write-Host "Access the application at:" -ForegroundColor Green
        Write-Host "  Frontend: http://localhost:8888" -ForegroundColor Yellow
        Write-Host "  Backend:  http://localhost:5000/api/health" -ForegroundColor Yellow
    }
    
    "status" {
        Show-Status
    }
    
    default {
        Write-Host "Unknown command: $action" -ForegroundColor Red
        Write-Host "Usage: .\docker-start.ps1 [up|down|logs|build|rebuild|status]" -ForegroundColor Yellow
    }
}
