# Time Series Analyzer - AWS Infrastructure

This directory contains Terraform configuration files for deploying the Time Series Analyzer application to AWS. The infrastructure is designed to be production-ready with proper security, scalability, and monitoring.

## Architecture Overview

The infrastructure includes:

- **VPC with Public and Private Subnets**: Secure network isolation
- **Application Load Balancer (ALB)**: Public-facing load balancer for high availability
- **ECS Fargate**: Containerized backend service deployment
- **RDS PostgreSQL**: Managed database with TimescaleDB compatibility
- **ECR**: Container registry for application images
- **Secrets Manager**: Secure storage for sensitive configuration
- **CloudWatch**: Logging and monitoring
- **IAM Roles**: Least-privilege access control

## Infrastructure Components

### Networking
- **VPC**: 10.0.0.0/16 CIDR block
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24 (for ALB)
- **Private Subnets**: 10.0.10.0/24, 10.0.20.0/24 (for ECS tasks and RDS)
- **NAT Gateways**: For private subnet internet access
- **Security Groups**: Restrictive security policies

### Database
- **RDS PostgreSQL 15.4**: Managed database service
- **Multi-AZ**: High availability setup
- **Encrypted Storage**: Data encryption at rest
- **Automated Backups**: 7-day retention period
- **Enhanced Monitoring**: Performance insights enabled

### Application Deployment
- **ECS Fargate**: Serverless container platform
- **Application Load Balancer**: HTTP/HTTPS traffic distribution
- **Auto Scaling**: Built-in with ECS service
- **Health Checks**: Application health monitoring

### Security
- **Private Subnets**: Database and application isolation
- **Security Groups**: Network-level access control
- **Secrets Manager**: Encrypted credential storage
- **IAM Roles**: Service-specific permissions

## Prerequisites

1. **AWS CLI**: Configured with appropriate credentials
2. **Terraform**: Version >= 1.0.0
3. **Docker**: For building and pushing container images
4. **Valid AWS Account**: With appropriate permissions

### Required AWS Permissions

Your AWS user/role needs permissions for:
- VPC, EC2, and networking resources
- RDS database creation and management
- ECS cluster and service management
- ECR repository management
- IAM role creation and policy attachment
- Secrets Manager secret creation
- CloudWatch log group creation
- Application Load Balancer management

## Deployment Instructions

### 1. Configure Variables

Copy the example variables and customize them:

```bash
# Create terraform.tfvars file
cat > terraform.tfvars << EOF
# Required variables
db_password = "your-secure-database-password"
api_key = "your-api-key-for-the-application"

# Optional customizations
aws_region = "us-west-2"
environment = "dev"
db_instance_class = "db.t3.micro"
backend_desired_count = 1

# SSL configuration (optional)
enable_ssl = false
ssl_certificate_arn = ""
EOF
```

### 2. Initialize Terraform

```bash
cd infrastructure
terraform init
```

### 3. Plan the Deployment

```bash
terraform plan
```

Review the planned changes carefully. The initial deployment will create approximately 30+ AWS resources.

### 4. Apply the Configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm the deployment.

### 5. Build and Push Container Images

After the infrastructure is deployed, build and push your application images:

```bash
# Get ECR login token
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(terraform output -raw backend_ecr_url | cut -d'/' -f1)

# Build backend image
cd ../backend
docker build -t time-series-analyzer-backend .

# Tag and push backend image
docker tag time-series-analyzer-backend:latest $(terraform output -raw backend_ecr_url):latest
docker push $(terraform output -raw backend_ecr_url):latest

# Build frontend image (if needed)
cd ../frontend
docker build -t time-series-analyzer-frontend .

# Tag and push frontend image
docker tag time-series-analyzer-frontend:latest $(terraform output -raw frontend_ecr_url):latest
docker push $(terraform output -raw frontend_ecr_url):latest
```

### 6. Update ECS Service

After pushing new images, update the ECS service to deploy them:

```bash
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment \
  --region us-west-2
```

## Environment Variables and Secrets

The application uses the following environment variables, managed through AWS Secrets Manager:

### Database Configuration
- `DATABASE_URL`: Complete PostgreSQL connection string
- `DATABASE_POOL_SIZE`: Connection pool size (default: 5)
- `DATABASE_MAX_OVERFLOW`: Maximum overflow connections (default: 10)
- `DATABASE_POOL_RECYCLE`: Connection recycle time in seconds (default: 3600)

### Application Configuration
- `API_KEY`: API key for securing endpoints
- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

### Secrets Manager Secrets
- `time-series-analyzer-db-credentials`: Database username and password
- `time-series-analyzer-api-key`: Application API key
- `time-series-analyzer-database-url`: Complete database connection URL

## Accessing the Application

After deployment, the application will be available at:

```bash
# Get the load balancer DNS name
terraform output load_balancer_dns
```

The API will be accessible at:
- `http://<load-balancer-dns>/api/health` - Health check endpoint
- `http://<load-balancer-dns>/api/upload-csv/` - CSV upload endpoint

## Monitoring and Logs

### CloudWatch Logs
Application logs are automatically sent to CloudWatch:
- Log Group: `/ecs/time-series-analyzer`
- Retention: 7 days (configurable)

### Database Monitoring
- Enhanced monitoring enabled
- Performance Insights available in RDS console

### Application Health
- ALB health checks monitor `/api/health` endpoint
- ECS service maintains desired task count

## TimescaleDB Setup

The RDS PostgreSQL instance is configured to support TimescaleDB. To enable TimescaleDB:

1. Connect to the database using the credentials from Secrets Manager
2. Run the TimescaleDB extension installation:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

The application's Alembic migrations will handle creating the necessary tables and hypertables.

## Scaling

### Horizontal Scaling
Adjust the number of ECS tasks:

```bash
# Update desired count in terraform.tfvars
backend_desired_count = 3

# Apply the change
terraform apply
```

### Vertical Scaling
Adjust CPU and memory allocation:

```bash
# Update in terraform.tfvars
backend_cpu = 512
backend_memory = 1024

# Apply the change
terraform apply
```

### Database Scaling
Upgrade the RDS instance:

```bash
# Update in terraform.tfvars
db_instance_class = "db.t3.small"

# Apply the change
terraform apply
```

## Cost Optimization

### Development Environment
- Use `db.t3.micro` for RDS (free tier eligible)
- Set `backend_desired_count = 1`
- Consider using spot instances for non-critical workloads

### Production Environment
- Use Multi-AZ RDS deployment
- Enable automated backups with longer retention
- Consider using reserved instances for predictable workloads

## Troubleshooting

### Common Issues

1. **ECS Tasks Not Starting**
   - Check CloudWatch logs for container errors
   - Verify ECR image exists and is accessible
   - Check IAM permissions for task execution role

2. **Database Connection Issues**
   - Verify security group allows connections from ECS tasks
   - Check database credentials in Secrets Manager
   - Ensure database is in the correct subnets

3. **Load Balancer Health Check Failures**
   - Verify application is listening on the correct port
   - Check that `/api/health` endpoint is responding
   - Review target group health check settings

### Debugging Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster $(terraform output -raw ecs_cluster_name) --services $(terraform output -raw ecs_service_name)

# View recent ECS events
aws ecs describe-services --cluster $(terraform output -raw ecs_cluster_name) --services $(terraform output -raw ecs_service_name) --query 'services[0].events'

# Check CloudWatch logs
aws logs describe-log-streams --log-group-name "/ecs/time-series-analyzer"

# View recent application logs
aws logs get-log-events --log-group-name "/ecs/time-series-analyzer" --log-stream-name <stream-name>
```

## Cleanup

To destroy all infrastructure:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources, including the database and any data it contains.

## Security Considerations

1. **Database Security**
   - Database is isolated in private subnets
   - Security groups restrict access to ECS tasks only
   - Encryption at rest and in transit enabled

2. **Application Security**
   - API key authentication required
   - Secrets stored in AWS Secrets Manager
   - ECS tasks run with minimal IAM permissions

3. **Network Security**
   - Private subnets for application and database tiers
   - Security groups implement least-privilege access
   - NACLs provide additional network-level security

## Contributing

When making changes to the infrastructure:

1. Test changes in a development environment first
2. Use `terraform plan` to review changes before applying
3. Update this documentation for any significant changes
4. Consider backward compatibility for existing deployments

## Support

For infrastructure-related issues:
1. Check the Troubleshooting section above
2. Review CloudWatch logs and metrics
3. Consult AWS documentation for service-specific issues
4. Consider opening a support ticket for complex issues