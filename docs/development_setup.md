# Development Setup Guide

This guide provides instructions for setting up the Time Series Analyzer project for local development.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Docker and Docker Compose**: Required for containerized development
- **Python 3.9+**: For backend development
- **Node.js 16+**: For frontend development
- **Git**: For version control

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/fabioeloi/time-series-analyzer.git
cd time-series-analyzer
```

### 2. Local Development with Docker

The easiest way to start development is using Docker Compose, which sets up both frontend and backend services:

```bash
docker-compose up
```

This will:
- Start the Python FastAPI backend on http://localhost:8000
- Start the React frontend on http://localhost:3000
- Set up live-reloading for both services

The API documentation will be available at http://localhost:8000/docs

### 3. Manual Development Setup

#### Backend Setup

If you prefer to run the backend directly:

```bash
cd backend
# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
# Run the backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

For frontend development:

```bash
cd frontend
# Install dependencies
npm install
# Start development server
npm start
```

## Project Structure

```
├── backend/                  # Python FastAPI backend
│   ├── domain/               # Domain models (DDD)
│   ├── application/          # Application services
│   ├── infrastructure/       # Infrastructure concerns
│   ├── interfaces/           # API interfaces
│   └── samples/              # Sample data files
├── frontend/                 # React frontend
├── infrastructure/           # Terraform IaC
├── tests/                    # Test directory
└── docs/                     # Documentation
```

## Testing

### Backend Tests

```bash
cd backend
pytest
# Or with coverage
pytest --cov=./ --cov-report=term
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Code Style and Linting

- **Backend**: We follow the PEP 8 style guide for Python code
- **Frontend**: ESLint and Prettier are configured for JavaScript/TypeScript code

## Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

## Deployment

The project uses GitHub Actions for CI/CD. When code is merged to main branch:

1. Tests are automatically run
2. Docker images are built and pushed to AWS ECR
3. Infrastructure is updated using Terraform
4. Application is deployed to AWS ECS

For manual deployments, see the infrastructure README in the `infrastructure/` directory.