#!/bin/bash
set -e

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Time Series Analyzer - GitHub Repository Setup${NC}"
echo "----------------------------------------------"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. Please install it first:"
    echo "  - macOS: brew install gh"
    echo "  - Linux: Follow instructions at https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo "  - Windows: scoop install gh"
    exit 1
fi

# Check if the user is authenticated with gh
if ! gh auth status &> /dev/null; then
    echo "Please log in to GitHub first using: gh auth login"
    exit 1
fi

echo -e "${GREEN}Creating GitHub repository: time-series-analyzer${NC}"
gh repo create fabioeloi/time-series-analyzer \
    --public \
    --description "A web-based time series analysis tool with multi-layered visualization capabilities" \
    --homepage "https://github.com/fabioeloi/time-series-analyzer" \
    --confirm

echo -e "${GREEN}Initializing Git repository locally${NC}"
git init

# Function to clear the cache directory
clear_cache() {
    cache_dir="data"

    if [ -d "$cache_dir" ]; then
        rm -rf "$cache_dir"/*
    fi

    # Clear the data directory before committing
    if [ -f "backend/data/time_series_storage.pkl" ]; then
        rm "backend/data/time_series_storage.pkl"
    fi

    # Clear the __pycache__ directories
    find . -type d -name "__pycache__" -exec rm -r {} +
}

# Clear the cache directory before committing
clear_cache

git add .
git commit -m "Initial commit: Time Series Analyzer project"

echo -e "${GREEN}Setting up remote and pushing code${NC}"
git branch -M main
git remote add origin https://github.com/fabioeloi/time-series-analyzer.git
git push -u origin main

echo -e "${GREEN}Setting up repository secrets for GitHub Actions${NC}"
echo "You will need to manually add these secrets in the GitHub repository settings:"
echo "  - AWS_ACCESS_KEY_ID"
echo "  - AWS_SECRET_ACCESS_KEY"
echo "Navigate to https://github.com/fabioeloi/time-series-analyzer/settings/secrets/actions to add them"

echo -e "${YELLOW}Setup complete!${NC}"
echo "Your time series analyzer repository has been created and initialized."
echo "Visit https://github.com/fabioeloi/time-series-analyzer to view it."