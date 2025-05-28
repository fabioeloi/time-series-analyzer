# Infrastructure Outputs

# ECR Repository URLs
output "backend_ecr_url" {
  value       = aws_ecr_repository.backend_repo.repository_url
  description = "Backend ECR repository URL"
}

output "frontend_ecr_url" {
  value       = aws_ecr_repository.frontend_repo.repository_url
  description = "Frontend ECR repository URL"
}

# Load Balancer
output "load_balancer_dns" {
  value       = aws_lb.app_lb.dns_name
  description = "Application Load Balancer DNS name"
}

output "load_balancer_zone_id" {
  value       = aws_lb.app_lb.zone_id
  description = "Application Load Balancer zone ID"
}

# Database
output "database_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "RDS PostgreSQL endpoint"
  sensitive   = true
}

output "database_connection_details" {
  value = {
    endpoint = aws_db_instance.postgres.endpoint
    port     = aws_db_instance.postgres.port
    database = aws_db_instance.postgres.db_name
    username = aws_db_instance.postgres.username
  }
  description = "Database connection details"
  sensitive   = true
}

# Secrets Manager
output "database_credentials_secret_arn" {
  value       = aws_secretsmanager_secret.db_credentials.arn
  description = "ARN of the database credentials secret"
  sensitive   = true
}

output "api_key_secret_arn" {
  value       = aws_secretsmanager_secret.api_key.arn
  description = "ARN of the API key secret"
  sensitive   = true
}

output "database_url_secret_arn" {
  value       = aws_secretsmanager_secret.database_url.arn
  description = "ARN of the database URL secret"
  sensitive   = true
}

# VPC and Networking
output "vpc_id" {
  value       = aws_vpc.time_series_vpc.id
  description = "VPC ID"
}

output "public_subnet_ids" {
  value       = aws_subnet.public_subnets[*].id
  description = "Public subnet IDs"
}

output "private_subnet_ids" {
  value       = aws_subnet.private_subnets[*].id
  description = "Private subnet IDs"
}

# ECS
output "ecs_cluster_name" {
  value       = aws_ecs_cluster.app_cluster.name
  description = "ECS cluster name"
}

output "ecs_service_name" {
  value       = aws_ecs_service.backend_service.name
  description = "ECS service name"
}

# Security Groups
output "alb_security_group_id" {
  value       = aws_security_group.alb_sg.id
  description = "ALB security group ID"
}

output "backend_security_group_id" {
  value       = aws_security_group.backend_sg.id
  description = "Backend security group ID"
}

output "database_security_group_id" {
  value       = aws_security_group.db_sg.id
  description = "Database security group ID"
}

# Frontend S3 Bucket
output "frontend_s3_bucket_name" {
  value       = aws_s3_bucket.frontend_bucket.bucket
  description = "Name of the S3 bucket for frontend static files"
}

# CloudFront Distribution
output "cloudfront_distribution_domain_name" {
  value       = aws_cloudfront_distribution.frontend_distribution.domain_name
  description = "Domain name of the CloudFront distribution for the frontend"
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.frontend_distribution.id
  description = "ID of the CloudFront distribution for the frontend"
}