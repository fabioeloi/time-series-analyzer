#!/bin/bash

# Frontend test runner script for CI/CD
set -e

echo "Setting up frontend test environment..."

# Ensure we're in the correct directory
cd "$(dirname "$0")/../frontend"

# Install dependencies
echo "Installing frontend dependencies..."
npm ci --quiet

# Set CI environment variable
export CI=true

echo "Running frontend tests..."
npm test -- --coverage \
             --watchAll=false \
             --testPathIgnorePatterns=/node_modules/ \
             --maxWorkers=2 \
             --verbose

echo "Frontend tests completed successfully!"