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
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

> **Note**: Replace `YOUR_USERNAME` with your GitHub username/organization and `YOUR_REPO_NAME` with your repository name. If you used the included [`init_repo.sh`](../init_repo.sh) script to set up your repository, these values would have been configured during setup.

### 2. Local Development with Docker

The easiest way to start development is using Docker Compose, which sets up both frontend and backend services:

```bash
docker-compose up
```

This will:
- Start TimescaleDB (PostgreSQL with TimescaleDB extension) on port 5432
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

#### Redis Setup

If you plan to use caching, you'll need a running Redis instance. The easiest way to run Redis locally is via Docker:

```bash
docker run --name time-series-redis -p 6379:6379 -d redis/redis-stack-server:latest
```

To stop and remove the Redis container:

```bash
docker stop time-series-redis
docker rm time-series-redis
```

## Database Setup

The project uses PostgreSQL with the TimescaleDB extension for efficient time-series data storage.

### Environment Variables

Configure the following database environment variables in your `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/time_series_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=time_series_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600
```

### Redis Environment Variables

For caching with Redis, configure the following environment variables in your `.env` file:

```bash
# Redis Configuration
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
REDIS_TTL_SECONDS=300
```

*   `REDIS_ENABLED`: Set to `true` to enable Redis caching.
*   `REDIS_URL`: The connection URL for your Redis instance.
*   `REDIS_TTL_SECONDS`: The default Time-To-Live (TTL) for cached entries in seconds.

### Database Migrations

The project uses Alembic for database schema migrations:

```bash
cd backend

# Run migrations to set up the database schema
python -m alembic upgrade head

# Create a new migration (if needed)
python -m alembic revision --autogenerate -m "Description of changes"

# Downgrade migrations (if needed)
python -m alembic downgrade -1
```

### Manual Database Setup

If you need to set up PostgreSQL with TimescaleDB manually:

1. **Install PostgreSQL**: Follow the official PostgreSQL installation guide for your OS
2. **Install TimescaleDB**: Follow the TimescaleDB installation guide
3. **Create Database**:
   ```sql
   CREATE DATABASE time_series_db;
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```
4. **Run Migrations**: Use Alembic as described above

### Database Schema

The database consists of two main tables:

- `time_series_metadata`: Stores metadata about each time series (ID, columns, timestamps)
- `time_series_data_points`: TimescaleDB hypertable storing the actual time-series data points

The hypertable is optimized for time-series queries and includes automatic compression for data older than 1 day.

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