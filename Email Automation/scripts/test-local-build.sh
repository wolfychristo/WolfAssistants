#!/bin/bash

# Local Build Test Script for WolfAssistants
# Tests production builds locally before deployment

set -e  # Exit on error

echo "=========================================="
echo "WolfAssistants - Local Build Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Must run from Email Automation directory${NC}"
    exit 1
fi

# Step 1: Check environment variables
echo -e "${YELLOW}Step 1: Checking environment variables...${NC}"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Warning: DATABASE_URL not set. Using .env file if available.${NC}"
fi
if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}Warning: SECRET_KEY not set. Using .env file if available.${NC}"
fi
echo -e "${GREEN}✓ Environment check complete${NC}"
echo ""

# Step 2: Build Frontend
echo -e "${YELLOW}Step 2: Building frontend...${NC}"
cd frontend

# Set API URL for local testing if not already set
export REACT_APP_API_URL=${REACT_APP_API_URL:-"http://localhost:8000/api/v1"}

echo "Using API URL: $REACT_APP_API_URL"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Build
echo "Building frontend..."
npm run build

if [ ! -d "build" ]; then
    echo -e "${RED}Error: Frontend build failed - build directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Frontend build successful${NC}"
cd ..
echo ""

# Step 3: Start Backend (in background)
echo -e "${YELLOW}Step 3: Starting backend server...${NC}"
cd backend

# Set production environment variables if not set
export ENVIRONMENT=${ENVIRONMENT:-"production"}
export CORS_ORIGINS=${CORS_ORIGINS:-"http://localhost:3000"}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Start backend in background
echo "Starting backend server on port 8000..."
python main.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Backend failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
cd ..
echo ""

# Step 4: Health Checks
echo -e "${YELLOW}Step 4: Running health checks...${NC}"

# Wait a bit more for server to be ready
sleep 3

# Test backend health endpoint
echo "Testing backend health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "FAILED")

if [ "$HEALTH_RESPONSE" = "FAILED" ]; then
    echo -e "${RED}Error: Backend health check failed${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo "Health response: $HEALTH_RESPONSE"
echo -e "${GREEN}✓ Backend health check passed${NC}"
echo ""

# Step 5: Test Frontend Build
echo -e "${YELLOW}Step 5: Testing frontend build...${NC}"
cd frontend

# Start a simple HTTP server to serve the build
echo "Starting test server for frontend build..."
npx serve -s build -l 3000 &
FRONTEND_PID=$!

# Wait for frontend server
sleep 3

# Test if frontend is accessible
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")

if [ "$FRONTEND_RESPONSE" != "200" ]; then
    echo -e "${RED}Error: Frontend server not responding (HTTP $FRONTEND_RESPONSE)${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✓ Frontend build test passed${NC}"
cd ..
echo ""

# Step 6: Summary
echo -e "${GREEN}=========================================="
echo "Local Build Test - SUCCESS"
echo "==========================================${NC}"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop servers, run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo -e "${YELLOW}Note: Servers are running in background. Stop them when done testing.${NC}"

