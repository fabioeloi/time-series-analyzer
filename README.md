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

### Frontend
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

2. Start the development environment:
   ```
   docker-compose up
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Testing

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

The project is configured for automatic deployment via GitHub Actions. When code is pushed to the main branch:

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