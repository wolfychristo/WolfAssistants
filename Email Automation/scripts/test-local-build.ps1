# Local Build Test Script for WolfAssistants (PowerShell)
# Tests production builds locally before deployment

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "WolfAssistants - Local Build Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check environment variables
Write-Host "Step 1: Checking environment variables..." -ForegroundColor Yellow
if (-not $env:DATABASE_URL) {
    Write-Host "Warning: DATABASE_URL not set. Using .env file if available." -ForegroundColor Red
}
if (-not $env:SECRET_KEY) {
    Write-Host "Warning: SECRET_KEY not set. Using .env file if available." -ForegroundColor Red
}
Write-Host "✓ Environment check complete" -ForegroundColor Green
Write-Host ""

# Step 2: Build Frontend
Write-Host "Step 2: Building frontend..." -ForegroundColor Yellow
Set-Location frontend

# Set API URL for local testing if not already set
if (-not $env:REACT_APP_API_URL) {
    $env:REACT_APP_API_URL = "http://localhost:8000/api/v1"
}

Write-Host "Using API URL: $env:REACT_APP_API_URL"

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

# Build
Write-Host "Building frontend..."
npm run build

if (-not (Test-Path "build")) {
    Write-Host "Error: Frontend build failed - build directory not found" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Frontend build successful" -ForegroundColor Green
Set-Location ..
Write-Host ""

# Step 3: Start Backend (in background)
Write-Host "Step 3: Starting backend server..." -ForegroundColor Yellow
Set-Location backend

# Set production environment variables if not set
if (-not $env:ENVIRONMENT) {
    $env:ENVIRONMENT = "production"
}
if (-not $env:CORS_ORIGINS) {
    $env:CORS_ORIGINS = "http://localhost:3000"
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

# Install dependencies if needed
if (-not (Test-Path "venv\.installed")) {
    Write-Host "Installing backend dependencies..."
    pip install -r requirements.txt
    New-Item -ItemType File -Path "venv\.installed" -Force | Out-Null
}

# Start backend in background
Write-Host "Starting backend server on port 8000..."
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    & "venv\Scripts\python.exe" main.py
}

# Wait for backend to start
Write-Host "Waiting for backend to start..."
Start-Sleep -Seconds 5

# Check if backend is running
if ($backendJob.State -eq "Failed") {
    Write-Host "Error: Backend failed to start" -ForegroundColor Red
    Stop-Job $backendJob
    Remove-Job $backendJob
    exit 1
}

Write-Host "✓ Backend server started (Job ID: $($backendJob.Id))" -ForegroundColor Green
Set-Location ..
Write-Host ""

# Step 4: Health Checks
Write-Host "Step 4: Running health checks..." -ForegroundColor Yellow

# Wait a bit more for server to be ready
Start-Sleep -Seconds 3

# Test backend health endpoint
Write-Host "Testing backend health endpoint..."
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Health response: $($healthResponse.Content)"
    Write-Host "✓ Backend health check passed" -ForegroundColor Green
} catch {
    Write-Host "Error: Backend health check failed: $_" -ForegroundColor Red
    Stop-Job $backendJob
    Remove-Job $backendJob
    exit 1
}
Write-Host ""

# Step 5: Test Frontend Build
Write-Host "Step 5: Testing frontend build..." -ForegroundColor Yellow
Set-Location frontend

# Start a simple HTTP server to serve the build
Write-Host "Starting test server for frontend build..."
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    npx serve -s build -l 3000
}

# Wait for frontend server
Start-Sleep -Seconds 3

# Test if frontend is accessible
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✓ Frontend build test passed" -ForegroundColor Green
    } else {
        throw "Frontend returned status code $($frontendResponse.StatusCode)"
    }
} catch {
    Write-Host "Error: Frontend server not responding: $_" -ForegroundColor Red
    Stop-Job $backendJob, $frontendJob
    Remove-Job $backendJob, $frontendJob
    exit 1
}
Set-Location ..
Write-Host ""

# Step 6: Summary
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Local Build Test - SUCCESS" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host ""
Write-Host "Backend Job ID: $($backendJob.Id)"
Write-Host "Frontend Job ID: $($frontendJob.Id)"
Write-Host ""
Write-Host "To stop servers, run:"
Write-Host "  Stop-Job $($backendJob.Id), $($frontendJob.Id)"
Write-Host "  Remove-Job $($backendJob.Id), $($frontendJob.Id)"
Write-Host ""
Write-Host "Note: Servers are running in background. Stop them when done testing." -ForegroundColor Yellow

