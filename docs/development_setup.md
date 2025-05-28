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

### 2. Environment Configuration

Before starting the application, you need to set up the environment configuration:

```bash
# Copy the example environment file
cp .env.example .env
```

The `.env` file contains all necessary environment variables with development defaults. Key variables include:

- `API_KEY`: Required for backend authentication (default: `dev-api-key-12345-change-in-production`)
- `DATABASE_URL`: PostgreSQL connection string for TimescaleDB
- `REDIS_URL`: Redis connection string for caching
- Environment-specific settings for development/production

> **Important**: The provided `.env` file is already configured with development defaults that work with Docker Compose. Only modify these values if you need different settings or are deploying to production.

### 3. Local Development with Docker

The easiest way to start development is using Docker Compose, which sets up all services:

```bash
docker-compose up
```

This will:
- Start TimescaleDB (PostgreSQL with TimescaleDB extension) on port 5432
- Start Redis for caching on port 6379
- Start the Python FastAPI backend on http://localhost:8000
- Start the React frontend on http://localhost:3000
- Set up live-reloading for both services

The API documentation will be available at http://localhost:8000/docs

#### Service Dependencies
The services start in the correct order with health checks:
1. **TimescaleDB** starts first and waits for PostgreSQL to be ready
2. **Redis** starts and waits for Redis server to be ready
3. **Backend** starts after database and Redis are healthy
4. **Frontend** starts after backend is healthy

### 4. Manual Development Setup

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

### Environment Variables Configuration

The `.env` file contains all necessary environment variables with development defaults. Here are the key sections:

#### Authentication Configuration
```bash
# Required for backend API authentication
API_KEY=dev-api-key-12345-change-in-production
```

#### Database Configuration
```bash
# PostgreSQL with TimescaleDB Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@timescaledb:5432/time_series_db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600
```

> **Note**: When using Docker Compose, the host should be `timescaledb` (the Docker service name), not `localhost`.

#### Cache Configuration
```bash
# Redis Configuration
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
REDIS_TTL_SECONDS=3600
```

> **Note**: When using Docker Compose, the host should be `redis` (the Docker service name), not `localhost`.

#### Application Environment
```bash
# Environment settings
ENVIRONMENT=development
NODE_ENV=development
REACT_APP_API_URL=http://localhost:8000
```

### Environment Variable Validation

The backend application validates required environment variables during startup:

- **API_KEY**: Required for authentication system initialization
- **DATABASE_URL**: Required for database connectivity
- **REDIS_URL**: Required when Redis caching is enabled

Missing required variables will cause the application to fail during startup with clear error messages.

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
## Troubleshooting

### Common Docker Issues

#### Backend Container Fails to Start
**Symptoms**: Backend container exits immediately or shows authentication errors

**Solution**: 
1. Ensure the `.env` file exists and contains the required `API_KEY` variable:
   ```bash
   # Check if .env file exists
   ls -la .env
   
   # If missing, copy from example
   cp .env.example .env
   ```

2. Verify the API_KEY is set in `.env`:
   ```bash
   grep API_KEY .env
   ```

3. Restart the containers:
   ```bash
   docker-compose down
   docker-compose up
   ```

#### Database Connection Issues
**Symptoms**: Backend shows database connection errors

**Solutions**:
1. Check if TimescaleDB container is running:
   ```bash
   docker-compose ps timescaledb
   ```

2. Verify database environment variables in `.env`:
   ```bash
   grep DATABASE_URL .env
   ```

3. Ensure the database URL uses the correct Docker service name (`timescaledb`, not `localhost`):
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:password@timescaledb:5432/time_series_db
   ```

#### Redis Connection Issues
**Symptoms**: Caching errors or Redis connection failures

**Solutions**:
1. Check if Redis container is running:
   ```bash
   docker-compose ps redis
   ```

2. Verify Redis configuration in `.env`:
   ```bash
   grep REDIS .env
   ```

3. Ensure Redis URL uses the correct Docker service name (`redis`, not `localhost`):
   ```bash
   REDIS_URL=redis://redis:6379/0
   ```

#### Port Conflicts
**Symptoms**: "Port already in use" errors during startup

**Solutions**:
1. Check what's using the ports:
   ```bash
   # Check port 3000 (frontend)
   lsof -i :3000
   
   # Check port 8000 (backend)
   lsof -i :8000
   
   # Check port 5432 (database)
   lsof -i :5432
   ```

2. Stop conflicting processes or change ports in `docker-compose.yml`

#### Container Build Issues
**Symptoms**: Docker build failures or image not found errors

**Solutions**:
1. Clean Docker cache and rebuild:
   ```bash
   docker-compose down --volumes
   docker system prune -f
   docker-compose build --no-cache
   docker-compose up
   ```

2. Check available disk space:
   ```bash
   df -h
   ```

### Environment Configuration Issues

#### Missing Environment Variables
**Symptoms**: Application startup failures with environment variable errors

**Solutions**:
1. Compare your `.env` with `.env.example`:
   ```bash
   diff .env .env.example
   ```

2. Ensure all required variables are set:
   ```bash
   # Check for required variables
   grep -E "API_KEY|DATABASE_URL|REDIS_URL" .env
   ```

#### Incorrect Service Hostnames
**Symptoms**: Connection timeouts when services try to communicate

**Solutions**:
1. When running with Docker Compose, use Docker service names as hostnames:
   - Database: `timescaledb` (not `localhost`)
   - Redis: `redis` (not `localhost`)
   - Backend: `backend` (not `localhost`)

2. When running services locally (without Docker), use `localhost`

### Performance Issues

#### Slow Container Startup
**Solutions**:
1. Increase Docker memory allocation (Docker Desktop settings)
2. Use Docker BuildKit for faster builds:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

#### Database Performance
**Solutions**:
1. Check database logs:
   ```bash
   docker-compose logs timescaledb
   ```

2. Monitor database connections:
   ```bash
   docker-compose exec timescaledb psql -U postgres -d time_series_db -c "SELECT * FROM pg_stat_activity;"
   ```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: Use `docker-compose logs [service-name]` to view detailed logs
2. **Restart services**: Sometimes a simple restart resolves transient issues
3. **Clean state**: Use `docker-compose down --volumes` to reset all data
4. **Review documentation**: Check the [Docker Startup Fix Summary](docker_startup_fix_summary.md) for recent fixes

### Useful Commands

```bash
# View all container logs
docker-compose logs

# View specific service logs
docker-compose logs backend

# Check container status
docker-compose ps

# Restart a specific service
docker-compose restart backend

# Full cleanup and restart
docker-compose down --volumes
docker-compose up --build

# Execute commands in running containers
docker-compose exec backend bash
docker-compose exec timescaledb psql -U postgres -d time_series_db
```