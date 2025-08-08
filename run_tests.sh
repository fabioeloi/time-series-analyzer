#!/bin/bash

# Color output definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  Time Series Analyzer - Test Runner    ${NC}"
echo -e "${BLUE}=========================================${NC}"

# Track overall test status
BACKEND_STATUS=0
FRONTEND_STATUS=0
DOCKER_STATUS=0

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
}

# Test backend
print_header "RUNNING BACKEND TESTS"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov

echo "Running pytest with coverage..."
PYTHONPATH=. pytest ../tests/backend/unit ../tests/backend/integration --cov=./ --cov-report=term -o "env:API_KEY=dummy_api_key_for_tests"
BACKEND_STATUS=$?

if [ $BACKEND_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Backend tests passed${NC}"
else
    echo -e "${RED}✗ Backend tests failed${NC}"
fi

deactivate
cd ..

# Test frontend
print_header "RUNNING FRONTEND TESTS"
cd frontend
if [ -f "package.json" ]; then
    echo "Installing frontend dependencies..."
    npm install
    
    echo "Running frontend tests..."
    CI=true npm test
    FRONTEND_STATUS=$?
    
    if [ $FRONTEND_STATUS -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend tests passed${NC}"
    else
        echo -e "${RED}✗ Frontend tests failed${NC}"
    fi
else
    echo -e "${RED}✗ package.json not found - skipping frontend tests${NC}"
    FRONTEND_STATUS=1
fi
cd ..

# Test Docker build
print_header "TESTING DOCKER BUILD"
# Skip Docker tests if daemon is not running
if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon not running, skipping Docker tests..."
    DOCKER_STATUS=1
else
    echo "Building Docker images..."
    docker compose build
    DOCKER_STATUS=$?

    if [ $DOCKER_STATUS -eq 0 ]; then
        echo -e "${GREEN}✓ Docker build successful${NC}"
        echo "Starting containers briefly to ensure they run..."
        docker compose up -d
        echo "Waiting for services to start..."
        sleep 10
        BACKEND_RUNNING=$(docker compose ps -q backend | wc -l)
        FRONTEND_RUNNING=$(docker compose ps -q frontend | wc -l)
        if [ $BACKEND_RUNNING -gt 0 ] && [ $FRONTEND_RUNNING -gt 0 ]; then
            echo -e "${GREEN}✓ All containers started successfully${NC}"
        else
            echo -e "${RED}✗ Container startup issues detected${NC}"
            DOCKER_STATUS=1
        fi
        echo "Stopping test containers..."
        docker compose down
    else
        echo -e "${RED}✗ Docker build failed${NC}"
    fi
fi
# Print summary
print_header "TEST SUMMARY"
if [ $BACKEND_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Backend: PASS${NC}"
else
    echo -e "${RED}✗ Backend: FAIL${NC}"
fi

if [ $FRONTEND_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend: PASS${NC}"
else
    echo -e "${RED}✗ Frontend: FAIL${NC}"
fi

if [ $DOCKER_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Docker: PASS${NC}"
else
    echo -e "${RED}✗ Docker: FAIL${NC}"
fi

# Final status
FINAL_STATUS=$(( $BACKEND_STATUS + $FRONTEND_STATUS + $DOCKER_STATUS ))
if [ $FINAL_STATUS -eq 0 ]; then
    echo -e "\n${GREEN}=========================================${NC}"
    echo -e "${GREEN}  All tests passed successfully!         ${NC}"
    echo -e "${GREEN}=========================================${NC}"
    exit 0
else
    echo -e "\n${RED}=========================================${NC}"
    echo -e "${RED}  Some tests failed. See above for details.${NC}"
    echo -e "${RED}=========================================${NC}"
    exit 1
fi