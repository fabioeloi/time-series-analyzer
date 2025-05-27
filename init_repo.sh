#!/bin/bash
set -e

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REPO_NAME="time-series-analyzer"
DEFAULT_VISIBILITY="private"
DEFAULT_DESCRIPTION="A web-based time series analysis tool with multi-layered visualization capabilities"

# Function to display help
show_help() {
    echo -e "${BLUE}Time Series Analyzer - GitHub Repository Setup${NC}"
    echo "=================================================="
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --user USERNAME        GitHub username or organization"
    echo "  -r, --repo REPO_NAME       Repository name (default: ${DEFAULT_REPO_NAME})"
    echo "  -v, --visibility VISIBILITY Repository visibility: public, private, internal (default: ${DEFAULT_VISIBILITY})"
    echo "  -d, --description DESC     Repository description"
    echo "  -s, --skip-secrets         Skip GitHub Actions secrets setup"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GITHUB_USER                GitHub username or organization"
    echo "  REPO_NAME                  Repository name"
    echo "  REPO_VISIBILITY            Repository visibility"
    echo "  REPO_DESCRIPTION           Repository description"
    echo "  SKIP_SECRETS               Skip secrets setup (set to 'true')"
    echo ""
    echo "Examples:"
    echo "  $0 -u myusername -r my-analyzer"
    echo "  $0 --user myorg --repo analytics-tool --visibility public"
    echo "  GITHUB_USER=myuser REPO_NAME=my-project $0"
}

# Function to prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local result
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " result
        echo "${result:-$default}"
    else
        read -p "$prompt: " result
        echo "$result"
    fi
}

# Function to validate repository visibility
validate_visibility() {
    local visibility="$1"
    case "$visibility" in
        public|private|internal)
            return 0
            ;;
        *)
            echo -e "${RED}Error: Invalid visibility '$visibility'. Must be 'public', 'private', or 'internal'.${NC}" >&2
            return 1
            ;;
    esac
}

# Parse command line arguments
GITHUB_USER="${GITHUB_USER:-}"
REPO_NAME="${REPO_NAME:-$DEFAULT_REPO_NAME}"
REPO_VISIBILITY="${REPO_VISIBILITY:-$DEFAULT_VISIBILITY}"
REPO_DESCRIPTION="${REPO_DESCRIPTION:-$DEFAULT_DESCRIPTION}"
SKIP_SECRETS="${SKIP_SECRETS:-false}"

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user)
            GITHUB_USER="$2"
            shift 2
            ;;
        -r|--repo)
            REPO_NAME="$2"
            shift 2
            ;;
        -v|--visibility)
            REPO_VISIBILITY="$2"
            shift 2
            ;;
        -d|--description)
            REPO_DESCRIPTION="$2"
            shift 2
            ;;
        -s|--skip-secrets)
            SKIP_SECRETS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option '$1'${NC}" >&2
            echo "Use '$0 --help' for usage information."
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Time Series Analyzer - GitHub Repository Setup${NC}"
echo "----------------------------------------------"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}GitHub CLI (gh) is not installed. Please install it first:${NC}"
    echo "  - macOS: brew install gh"
    echo "  - Linux: Follow instructions at https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo "  - Windows: scoop install gh"
    exit 1
fi

# Check if the user is authenticated with gh
echo "Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Please log in to GitHub first using: gh auth login${NC}"
    exit 1
fi
echo -e "${GREEN}✓ GitHub authentication verified${NC}"

# Get GitHub username if not provided
if [ -z "$GITHUB_USER" ]; then
    # Try to get the current authenticated user
    CURRENT_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")
    if [ -n "$CURRENT_USER" ]; then
        GITHUB_USER=$(prompt_with_default "GitHub username/organization" "$CURRENT_USER")
    else
        GITHUB_USER=$(prompt_with_default "GitHub username/organization" "")
    fi
    
    if [ -z "$GITHUB_USER" ]; then
        echo -e "${RED}Error: GitHub username/organization is required${NC}" >&2
        exit 1
    fi
fi

# Get repository name if using default
if [ "$REPO_NAME" = "$DEFAULT_REPO_NAME" ]; then
    # Try to derive from current directory name
    CURRENT_DIR=$(basename "$(pwd)")
    if [ "$CURRENT_DIR" != "." ] && [ "$CURRENT_DIR" != "/" ]; then
        REPO_NAME=$(prompt_with_default "Repository name" "$CURRENT_DIR")
    else
        REPO_NAME=$(prompt_with_default "Repository name" "$DEFAULT_REPO_NAME")
    fi
fi

# Validate and get repository visibility
if ! validate_visibility "$REPO_VISIBILITY"; then
    REPO_VISIBILITY=$(prompt_with_default "Repository visibility (public/private/internal)" "$DEFAULT_VISIBILITY")
    while ! validate_visibility "$REPO_VISIBILITY"; do
        echo -e "${RED}Please enter a valid visibility option.${NC}"
        REPO_VISIBILITY=$(prompt_with_default "Repository visibility (public/private/internal)" "$DEFAULT_VISIBILITY")
    done
fi

# Get repository description
if [ "$REPO_DESCRIPTION" = "$DEFAULT_DESCRIPTION" ]; then
    REPO_DESCRIPTION=$(prompt_with_default "Repository description" "$DEFAULT_DESCRIPTION")
fi

# Confirm repository creation
echo ""
echo -e "${BLUE}Repository Configuration:${NC}"
echo "  GitHub User/Org: $GITHUB_USER"
echo "  Repository Name: $REPO_NAME"
echo "  Visibility: $REPO_VISIBILITY"
echo "  Description: $REPO_DESCRIPTION"
echo ""

read -p "Proceed with repository creation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Repository creation cancelled."
    exit 0
fi

# Create the GitHub repository
echo -e "${GREEN}Creating GitHub repository: $GITHUB_USER/$REPO_NAME${NC}"
REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME"

gh repo create "$GITHUB_USER/$REPO_NAME" \
    "--$REPO_VISIBILITY" \
    --description "$REPO_DESCRIPTION" \
    --homepage "$REPO_URL" \
    --confirm

# Initialize Git repository locally if not already initialized
if [ ! -d ".git" ]; then
    echo -e "${GREEN}Initializing Git repository locally${NC}"
    git init
else
    echo -e "${GREEN}Git repository already initialized${NC}"
fi

# Function to clear the cache directory
clear_cache() {
    local cache_dir="data"
    
    echo "Cleaning up cache and temporary files..."
    
    if [ -d "$cache_dir" ]; then
        rm -rf "$cache_dir"/*
    fi
    
    # Clear the data directory before committing
    if [ -f "backend/data/time_series_storage.pkl" ]; then
        rm "backend/data/time_series_storage.pkl"
    fi
    
    # Clear the __pycache__ directories
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Clear node_modules if present (but preserve in .gitignore)
    # Don't actually remove node_modules, just ensure it's ignored
    if [ -f "frontend/package.json" ] && [ ! -f ".gitignore" ] || ! grep -q "node_modules" .gitignore 2>/dev/null; then
        echo "node_modules/" >> .gitignore
    fi
}

# Clear the cache directory before committing
clear_cache

echo -e "${GREEN}Staging and committing files${NC}"
git add .
git commit -m "Initial commit: $REPO_NAME project setup"

echo -e "${GREEN}Setting up remote and pushing code${NC}"
git branch -M main

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    echo "Remote 'origin' already exists, updating URL..."
    git remote set-url origin "$REPO_URL.git"
else
    git remote add origin "$REPO_URL.git"
fi

git push -u origin main

# GitHub Actions secrets setup
if [ "$SKIP_SECRETS" != "true" ]; then
    echo ""
    echo -e "${GREEN}GitHub Actions Secrets Setup${NC}"
    echo "========================================="
    
    read -p "Do you want to set up GitHub Actions secrets now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "You can set up secrets in two ways:"
        echo ""
        echo "1. Manually via GitHub web interface:"
        echo "   Navigate to: $REPO_URL/settings/secrets/actions"
        echo ""
        echo "2. Using GitHub CLI (if you have the values ready):"
        echo "   gh secret set AWS_ACCESS_KEY_ID"
        echo "   gh secret set AWS_SECRET_ACCESS_KEY"
        echo "   gh secret set AWS_ECR_REGISTRY_URL"
        echo ""
        echo "Required secrets for AWS deployment:"
        echo "  - AWS_ACCESS_KEY_ID: Your AWS access key"
        echo "  - AWS_SECRET_ACCESS_KEY: Your AWS secret access key"
        echo "  - AWS_ECR_REGISTRY_URL: Your ECR registry URL (optional)"
        echo ""
        
        read -p "Set up secrets via CLI now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Setting up AWS secrets..."
            echo "Enter your AWS Access Key ID:"
            gh secret set AWS_ACCESS_KEY_ID
            echo "Enter your AWS Secret Access Key:"
            gh secret set AWS_SECRET_ACCESS_KEY
            echo "Enter your AWS ECR Registry URL (or press Enter to skip):"
            read -r ECR_URL
            if [ -n "$ECR_URL" ]; then
                echo "$ECR_URL" | gh secret set AWS_ECR_REGISTRY_URL
            fi
            echo -e "${GREEN}✓ Secrets configured successfully${NC}"
        fi
    fi
else
    echo -e "${YELLOW}Skipping GitHub Actions secrets setup${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo "========================================="
echo "Repository Details:"
echo "  Name: $GITHUB_USER/$REPO_NAME"
echo "  URL: $REPO_URL"
echo "  Visibility: $REPO_VISIBILITY"
echo ""
echo "Next Steps:"
echo "  1. Visit your repository: $REPO_URL"
echo "  2. Configure GitHub Actions secrets if not done already"
echo "  3. Review and customize the project for your needs"
echo "  4. Start developing!"