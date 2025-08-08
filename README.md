# Time Series Analyzer

A web-based time series analysis tool with multi-layered visualization capabilities. This project allows users to upload CSV files with time series data and analyze them in both time and frequency domains with various visualization options.

## Features

- Upload and parse CSV files with time series data
- Visualize multiple data series in the time domain
- Analyze data in the frequency domain using FFT
- Support for various time scales (millisecond to day)
- Stacked or overlaid visualizations
- Responsive web interface

## Architecture

This project follows Domain-Driven Design (DDD) principles and is built using:

### Backend
- Python with FastAPI
- Data processing with Pandas, NumPy, and SciPy
- RESTful API endpoints
- In-memory caching service

### Frontend

Authentication header:
- The frontend sends `X-API-Key` with requests only if `REACT_APP_API_KEY` is set and non-empty in the environment.
- For local dev, create a `.env` in `frontend/` with `REACT_APP_API_KEY=<your_key>` if your backend requires it.
- For tests, the header is omitted when the env var is not set, matching the test expectations.

- React with TypeScript
- D3.js for data visualization
- Responsive design

### DevOps
- Docker and Docker Compose for containerization
- Infrastructure as Code (IaC) using Terraform
- CI/CD with GitHub Actions
- Deployment to AWS (ECR/ECS)

## Project Structure

```
.
├── .github/workflows      # GitHub Actions CI/CD
├── backend                # Python FastAPI backend
│   ├── domain             # Domain models (DDD)
│   ├── application        # Application services
│   ├── infrastructure     # Infrastructure concerns
│   └── interfaces         # API interfaces
├── frontend               # React + TypeScript frontend
├── infrastructure         # Terraform IaC
├── tests                  # Test directory
└── docs                   # Documentation
```

## Current Project Status

🟢 **All Services Operational & CI/CD Stable** - All services are working, and the CI/CD pipeline is stable after recent fixes.

### Service Status
- ✅ **TimescaleDB**: Running on port 5432 with time-series optimizations
- ✅ **Redis**: Running on port 6379 for caching (Note: Currently, an in-memory cache is used by default in the backend service. Redis integration is available but might require configuration.)
- ✅ **Backend**: Running on port 8000 with authentication and in-memory caching enabled
- ✅ **Frontend**: Running on port 3000 with API connectivity

### Recent Fixes
- **CI/CD Pipeline**: Resolved issues with deprecated actions and backend test failures.
- **Cache Module**: Added an in-memory caching service to the backend.
- **Docker Backend Startup**: Resolved missing API_KEY environment variable issue.
- **Environment Configuration**: Added comprehensive `.env` file for all services.
- **Container Dependencies**: Updated Docker Compose with proper service dependencies and health checks.

For detailed information about recent fixes, see:
- [CI/CD Pipeline Fixes Summary](docs/ci_cd_pipeline_final_fixes.md)
- [Docker Startup Fix Summary](docs/docker_startup_fix_summary.md)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for local frontend development)
- Python 3.9+ (for local backend development)
- AWS CLI (for deployment)
- Terraform (for infrastructure provisioning)

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```
   
   > **Note**: Replace `YOUR_USERNAME` with your GitHub username/organization and `YOUR_REPO_NAME` with your repository name. If you're setting up a new instance of this project, you can use the included [`init_repo.sh`](init_repo.sh) script to automate the repository creation and setup process.

2. **Set up environment configuration**:
   ```bash
   # Copy the example environment file and configure it
   cp .env.example .env
   ```
   
   > **Important**: The `.env` file is already configured with development defaults. For production deployment, make sure to update the `API_KEY` and other security-sensitive variables.

3. Start the development environment:
   ```
   docker-compose up
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Testing



Run the full suite (backend + frontend + optional Docker):

```zsh
./run_tests.sh
```

Notes:
- The script creates/uses a backend venv automatically and runs unit + integration tests.
- If the Docker daemon is not running, Docker checks are skipped and do not fail the run.
- Coverage is printed for backend tests.

You can also run tests individually:


Run backend tests:
```
cd backend
pytest
```

Run frontend tests:
```
cd frontend
npm test
```

## Deployment

### AWS Infrastructure Deployment

The project includes complete AWS infrastructure provisioning using Terraform. The infrastructure supports production-ready deployment with proper security, scalability, and monitoring.

#### Quick Start with Deployment Script

For easy deployment, use the provided deployment script:

```bash
cd infrastructure
./deploy.sh
```

This script will:
1. Check prerequisites (Terraform, AWS CLI, Docker)
2. Validate Terraform configuration
3. Create infrastructure resources
4. Build and push container images
5. Deploy the application to ECS

#### Manual Deployment Steps

1. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

2. **Set up Terraform variables:**
   ```bash
   cd infrastructure
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Deploy infrastructure:**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Build and push images:**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(terraform output -raw backend_ecr_url | cut -d'/' -f1)
   
   # Build and push backend
   cd ../backend
   docker build -t time-series-analyzer-backend .
   docker tag time-series-analyzer-backend:latest $(cd ../infrastructure && terraform output -raw backend_ecr_url):latest
   docker push $(cd ../infrastructure && terraform output -raw backend_ecr_url):latest
   ```

#### Infrastructure Components

The Terraform configuration creates:

- **VPC with public/private subnets** - Secure network architecture
- **RDS PostgreSQL** - Managed database with TimescaleDB support
- **ECS Fargate** - Containerized application deployment
- **Application Load Balancer** - High availability and traffic distribution
- **ECR repositories** - Container image storage
- **Secrets Manager** - Secure credential storage
- **CloudWatch** - Logging and monitoring
- **IAM roles** - Least-privilege security

#### Post-Deployment

After deployment, access your application at:
```bash
# Get the application URL
cd infrastructure
echo "http://$(terraform output -raw load_balancer_dns)"
```

API endpoints:
- Health check: `http://<load-balancer-dns>/api/health`
- CSV upload: `http://<load-balancer-dns>/api/upload-csv/`
- API docs: `http://<load-balancer-dns>/docs`

For detailed infrastructure documentation, see [`infrastructure/README.md`](infrastructure/README.md).

### Automated CI/CD Deployment

The project is also configured for automatic deployment via GitHub Actions. When code is pushed to the main branch:

1. Tests are run
2. Docker images are built and pushed to AWS ECR
3. Infrastructure is provisioned/updated with Terraform
4. Application is deployed to AWS ECS

## CSV File Format

The tool accepts CSV files with the following characteristics:
- First row should contain column headers
- One column should represent time (can be specified during upload)
- Remaining columns are treated as data series (can be selected during upload)

Example:
```
timestamp,temperature,humidity,pressure
2023-01-01 00:00:00,22.5,45,1013.25
2023-01-01 01:00:00,21.8,47,1013.10
...
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please follow the standard GitHub flow:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Submit a pull request

Please include tests for any new functionality and ensure all tests pass.