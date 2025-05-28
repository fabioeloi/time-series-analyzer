#!/bin/bash

# Time Series Analyzer Infrastructure Deployment Script
# This script helps deploy the AWS infrastructure using Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install Terraform >= 1.0.0"
        exit 1
    fi
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install and configure AWS CLI"
        exit 1
    fi
    
    if ! command_exists docker; then
        print_warning "Docker is not installed. You'll need Docker to build and push container images"
    fi
    
    # Check if AWS credentials are configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials are not configured. Run 'aws configure' first"
        exit 1
    fi
    
    print_status "Prerequisites check completed"
}

# Function to validate terraform configuration
validate_terraform() {
    print_status "Validating Terraform configuration..."
    
    if ! terraform validate; then
        print_error "Terraform configuration is invalid"
        exit 1
    fi
    
    print_status "Terraform configuration is valid"
}

# Function to check if terraform.tfvars exists
check_terraform_vars() {
    if [ ! -f "terraform.tfvars" ]; then
        print_warning "terraform.tfvars file not found"
        print_status "Creating terraform.tfvars from example..."
        
        if [ -f "terraform.tfvars.example" ]; then
            cp terraform.tfvars.example terraform.tfvars
            print_warning "Please edit terraform.tfvars and set the required values:"
            print_warning "- db_password: Set a secure database password"
            print_warning "- api_key: Set a secure API key"
            print_warning "Review other settings as needed"
            read -p "Press Enter after editing terraform.tfvars to continue..."
        else
            print_error "terraform.tfvars.example not found"
            exit 1
        fi
    fi
}

# Function to initialize terraform
init_terraform() {
    print_status "Initializing Terraform..."
    terraform init
}

# Function to plan terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    print_warning "Review the plan above carefully"
    read -p "Do you want to continue with the deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
}

# Function to apply terraform configuration
apply_terraform() {
    print_status "Applying Terraform configuration..."
    terraform apply tfplan
    
    if [ $? -eq 0 ]; then
        print_status "Infrastructure deployment completed successfully!"
        
        # Display important outputs
        print_status "Important outputs:"
        echo "Backend ECR URL: $(terraform output -raw backend_ecr_url)"
        echo "Frontend ECR URL: $(terraform output -raw frontend_ecr_url)"
        echo "Load Balancer DNS: $(terraform output -raw load_balancer_dns)"
        echo "ECS Cluster: $(terraform output -raw ecs_cluster_name)"
        echo "ECS Service: $(terraform output -raw ecs_service_name)"
    else
        print_error "Infrastructure deployment failed"
        exit 1
    fi
}

# Function to build and push container images
build_and_push_images() {
    print_status "Building and pushing container images..."
    
    # Get ECR URLs
    BACKEND_ECR_URL=$(terraform output -raw backend_ecr_url)
    FRONTEND_ECR_URL=$(terraform output -raw frontend_ecr_url)
    AWS_REGION=$(terraform output -raw aws_region || echo "us-west-2")
    
    # Get ECR login token
    print_status "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(echo $BACKEND_ECR_URL | cut -d'/' -f1)
    
    # Build and push backend image
    if [ -d "../backend" ]; then
        print_status "Building backend image..."
        cd ../backend
        docker build -t time-series-analyzer-backend .
        
        print_status "Pushing backend image to ECR..."
        docker tag time-series-analyzer-backend:latest $BACKEND_ECR_URL:latest
        docker push $BACKEND_ECR_URL:latest
        
        cd ../infrastructure
    else
        print_warning "Backend directory not found, skipping backend image build"
    fi
    
    # Build and push frontend image
    if [ -d "../frontend" ]; then
        print_status "Building frontend image..."
        cd ../frontend
        docker build -t time-series-analyzer-frontend .
        
        print_status "Pushing frontend image to ECR..."
        docker tag time-series-analyzer-frontend:latest $FRONTEND_ECR_URL:latest
        docker push $FRONTEND_ECR_URL:latest
        
        cd ../infrastructure
    else
        print_warning "Frontend directory not found, skipping frontend image build"
    fi
}

# Function to deploy frontend to S3 and invalidate CloudFront
deploy_frontend_to_s3() {
    print_status "Deploying frontend to S3 and invalidating CloudFront..."

    if [ -d "../frontend" ]; then
        print_status "Building frontend application..."
        cd ../frontend
        # Assuming 'npm install' and 'npm run build' are standard for frontend projects
        # You might need to adjust this based on the actual frontend build process (e.g., yarn, webpack)
        if [ -f "package.json" ]; then
            npm install
            npm run build
        else
            print_error "package.json not found in frontend directory. Cannot build frontend."
            exit 1
        fi
        cd ../infrastructure

        FRONTEND_BUCKET_NAME=$(terraform output -raw frontend_s3_bucket_name)
        CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)

        print_status "Syncing frontend build directory to S3 bucket: s3://${FRONTEND_BUCKET_NAME}"
        aws s3 sync ../frontend/build/ s3://${FRONTEND_BUCKET_NAME} --delete

        print_status "Invalidating CloudFront distribution: ${CLOUDFRONT_DISTRIBUTION_ID}"
        aws cloudfront create-invalidation --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} --paths "/*"

        print_status "Frontend deployment to S3 and CloudFront initiated."
    else
        print_warning "Frontend directory not found, skipping frontend S3/CloudFront deployment."
    fi
}

# Function to update ECS service
update_ecs_service() {
    print_status "Updating ECS service to deploy new images..."
    
    CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    SERVICE_NAME=$(terraform output -raw ecs_service_name)
    AWS_REGION=$(terraform output -raw aws_region || echo "us-west-2")
    
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION
    
    print_status "ECS service update initiated"
}

# Function to show post-deployment information
show_post_deployment_info() {
    print_status "Post-deployment information:"
    echo
    echo "Application URL: http://$(terraform output -raw load_balancer_dns)"
    echo "Health Check: http://$(terraform output -raw load_balancer_dns)/api/health"
    echo
    echo "To view logs:"
    echo "aws logs describe-log-streams --log-group-name '/ecs/time-series-analyzer'"
    echo
    echo "To check ECS service status:"
    echo "aws ecs describe-services --cluster $(terraform output -raw ecs_cluster_name) --services $(terraform output -raw ecs_service_name)"
    echo
    echo "Database connection details are stored in AWS Secrets Manager."
    echo "Secret ARNs:"
    echo "- Database credentials: $(terraform output -raw database_credentials_secret_arn)"
    echo "- API key: $(terraform output -raw api_key_secret_arn)"
    echo "- Database URL: $(terraform output -raw database_url_secret_arn)"
}

# Main deployment function
deploy() {
    print_status "Starting Time Series Analyzer infrastructure deployment..."
    
    check_prerequisites
    check_terraform_vars
    init_terraform
    validate_terraform
    plan_terraform
    apply_terraform
    
    # Ask if user wants to build and push images
    read -p "Do you want to build and push container images now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command_exists docker; then
            build_and_push_images
            update_ecs_service
            deploy_frontend_to_s3
        else
            print_error "Docker is required to build and push images"
        fi
    else
        print_warning "Skipping image build. You'll need to build and push images manually later."
    fi
    
    show_post_deployment_info
    print_status "Deployment process completed!"
}

# Function to destroy infrastructure
destroy() {
    print_warning "This will destroy ALL infrastructure resources"
    print_warning "This action cannot be undone and will delete the database and all data"
    echo
    read -p "Are you sure you want to destroy the infrastructure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Type 'destroy' to confirm: " confirm
        if [ "$confirm" = "destroy" ]; then
            print_status "Destroying infrastructure..."
            terraform destroy
        else
            print_status "Destruction cancelled"
        fi
    else
        print_status "Destruction cancelled"
    fi
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    destroy)
        destroy
        ;;
    plan)
        check_prerequisites
        check_terraform_vars
        init_terraform
        validate_terraform
        terraform plan
        ;;
    validate)
        check_prerequisites
        init_terraform
        validate_terraform
        ;;
    *)
        echo "Usage: $0 {deploy|destroy|plan|validate}"
        echo
        echo "Commands:"
        echo "  deploy    - Deploy the infrastructure (default)"
        echo "  destroy   - Destroy the infrastructure"
        echo "  plan      - Show the deployment plan"
        echo "  validate  - Validate the Terraform configuration"
        exit 1
        ;;
esac