#!/bin/bash

# Backend test runner script for CI/CD
set -e

echo "Setting up backend test environment..."

# Ensure we're in the correct directory
cd "$(dirname "$0")/.."

# Install dependencies if not already installed
echo "Installing backend dependencies..."
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# Set PYTHONPATH to include the project root
export PYTHONPATH="${PWD}:$PYTHONPATH"

echo "Running backend tests..."
pytest --cov=backend \
       --cov-report=xml \
       --cov-report=term-missing \
       --junitxml=test-results.xml \
       --tb=short \
       --strict-markers \
       -v

echo "Backend tests completed successfully!"