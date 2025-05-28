# Backend Architecture Review

This document provides a detailed review of the backend architecture for the time-series analyzer project.

## 1. Main Technologies and Frameworks:

The backend is primarily built with **Python**. Key technologies and frameworks include:

*   **Web Framework:** [`FastAPI`](backend/requirements.txt:2) for building RESTful APIs.
*   **ASGI Server:** [`Uvicorn`](backend/requirements.txt:3) to serve the FastAPI application.
*   **Data Manipulation & Scientific Computing:** [`Pandas`](backend/requirements.txt:4), [`NumPy`](backend/requirements.txt:5), and [`SciPy`](backend/requirements.txt:6) for time series data processing and analysis (e.g., FFT).
*   **Database ORM:** [`SQLAlchemy`](backend/requirements.txt:14) for object-relational mapping.
*   **Asynchronous PostgreSQL Driver:** [`Asyncpg`](backend/requirements.txt:15) for asynchronous database interactions.
*   **Database Migration:** [`Alembic`](backend/requirements.txt:16) for managing database schema migrations.
*   **PostgreSQL Adapter:** [`Psycopg2-binary`](backend/requirements.txt:17) for connecting to PostgreSQL/TimescaleDB.
*   **Caching:** [`Redis`](backend/requirements.txt:19) for caching analysis results.
*   **Data Validation:** [`Pydantic`](backend/requirements.txt:11) for data validation and serialization, especially for DTOs.
*   **Environment Variables:** [`python-dotenv`](backend/requirements.txt:18) for managing environment-specific configurations.

## 2. Overall Structure of the Backend:

The backend follows a layered architecture, often resembling a Clean Architecture or Hexagonal Architecture pattern, promoting separation of concerns.

*   **`backend/main.py`**: This is the application's entry point, responsible for setting up the FastAPI application, configuring CORS, defining API endpoints, and managing application lifecycle events (database and Redis initialization/shutdown). It acts as the API layer, handling HTTP requests and delegating to the application services.
*   **`application/`**: Contains the application-specific business logic and orchestrates operations.
    *   [`application/services/time_series_service.py`](backend/application/services/time_series_service.py): Houses the `TimeSeriesService` class, which implements the core business logic for processing, retrieving, updating, and deleting time series data. It interacts with repositories and the domain model.
*   **`domain/`**: This is the core layer, independent of external frameworks or databases. It defines the business entities and abstract contracts for data persistence.
    *   [`domain/models/time_series.py`](backend/domain/models/time_series.py): Defines the `TimeSeries` dataclass, the central domain model encapsulating time series data (using Pandas DataFrames) and methods for time and frequency domain transformations.
    *   [`domain/repositories/time_series_repository_interface.py`](backend/domain/repositories/time_series_repository_interface.py): Defines the `TimeSeriesRepositoryInterface`, an abstract base class that specifies the contract for data storage operations (e.g., `save`, `find_by_id`). This enforces the Repository Pattern.
*   **`infrastructure/`**: Provides concrete implementations for interfaces defined in the domain layer and handles external concerns.
    *   `infrastructure/auth/`: Contains authentication logic.
        *   [`infrastructure/auth/api_key_auth.py`](backend/infrastructure/auth/api_key_auth.py): Implements API key authentication, including the `APIKeyAuth` class and a FastAPI dependency `get_api_key_dependency` for securing endpoints.
    *   `infrastructure/cache/`: Handles caching mechanisms.
        *   `infrastructure/cache/redis_config.py`: Configures Redis connection.
        *   `infrastructure/cache/cache_service.py`: Provides a service for interacting with the Redis cache.
    *   `infrastructure/database/`: Manages database connections and ORM models.
        *   [`infrastructure/database/config.py`](backend/infrastructure/database/config.py): Handles database connection setup, session management (`get_db`), and initialization (`init_db`, `close_db`).
        *   [`infrastructure/database/models.py`](backend/infrastructure/database/models.py): Defines SQLAlchemy ORM models (`TimeSeriesMetadata`, `TimeSeriesDataPoint`) that map to the TimescaleDB schema.
        *   [`infrastructure/database/repositories/time_series_db_repository.py`](backend/infrastructure/database/repositories/time_series_db_repository.py): A concrete implementation of `TimeSeriesRepositoryInterface` that uses SQLAlchemy to persist and retrieve `TimeSeries` objects from the TimescaleDB database.
    *   `infrastructure/repositories/`: Contains other repository implementations.
        *   [`infrastructure/repositories/time_series_repository.py`](backend/infrastructure/repositories/time_series_repository.py): A file-based implementation of `TimeSeriesRepositoryInterface`, used as a fallback or for development/testing.
*   **`interfaces/dto/`**: Defines Data Transfer Objects (DTOs) for data exchange between layers.
    *   [`interfaces/dto/time_series_dto.py`](backend/interfaces/dto/time_series_dto.py): Contains `TimeSeriesRequestDTO` (for incoming data, e.g., CSV uploads) and `TimeSeriesResponseDTO` (for outgoing analysis results), leveraging Pydantic for validation.

## 3. Purpose of Main Components:

*   **Services (`application/services/`)**: The `TimeSeriesService` acts as the coordinator for business operations. It encapsulates the application's use cases, orchestrating interactions between the domain models and repositories. It's responsible for applying business rules and ensuring data consistency.
*   **Models (`domain/models/`)**: The `TimeSeries` model is the heart of the domain. It represents the core business entity and contains the logic related to time series data itself, such as data validation, time-domain data extraction, and frequency-domain transformations.
*   **Repositories (`domain/repositories/`, `infrastructure/database/repositories/`, `infrastructure/repositories/`)**: The `TimeSeriesRepositoryInterface` defines a contract for data persistence, abstracting the underlying storage mechanism. `TimeSeriesDBRepository` provides the concrete implementation for database persistence (TimescaleDB), while `TimeSeriesRepository` offers a file-based alternative. Repositories are responsible for abstracting data access logic from the business logic.
*   **Database Configurations (`infrastructure/database/config.py`)**: Manages the lifecycle of database connections and sessions, ensuring that database resources are properly initialized and released. It also provides a FastAPI dependency for injecting database sessions into endpoints and services.
*   **API Endpoints (`backend/main.py`)**: These are the public interfaces of the backend, exposing functionalities like CSV upload, analysis retrieval, diagnostics, and data export. They handle HTTP requests, perform input validation (using DTOs), and delegate the actual processing to the `TimeSeriesService`.

## 4. Summarize Component Interactions:

The backend operates with a clear flow of control and data:

1.  **Request Reception:** A client sends an HTTP request to a FastAPI endpoint defined in [`backend/main.py`](backend/main.py).
2.  **Authentication & Dependency Injection:** The FastAPI endpoint uses dependencies (e.g., `get_api_key_dependency` for authentication, `get_time_series_service` for the service instance) to prepare the request context.
3.  **Data Transfer Objects (DTOs):** Incoming request data is validated and transformed into `TimeSeriesRequestDTO` (from `interfaces/dto/`) before being passed to the application service. Similarly, results from the service are converted into `TimeSeriesResponseDTO` before being sent back to the client.
4.  **Service Orchestration:** The `TimeSeriesService` (from `application/services/`) receives the DTO and orchestrates the necessary business logic. It decides which repository implementation to use (database or file-based) based on availability or configuration.
5.  **Domain Logic & Data Access:** The `TimeSeriesService` interacts with the `TimeSeries` domain model (from `domain/models/`) to perform data transformations and analysis. It uses a concrete repository implementation (e.g., `TimeSeriesDBRepository` from `infrastructure/database/repositories/`) to persist or retrieve `TimeSeries` objects.
6.  **Infrastructure Details:** The repository implementations handle the low-level details of data storage, interacting with the database configuration (`infrastructure/database/config.py`) and ORM models (`infrastructure/database/models.py`). Caching (via `infrastructure/cache/`) is also managed by the service or repository to optimize data retrieval.
7.  **Response Generation:** After processing, the `TimeSeriesService` returns a `TimeSeriesResponseDTO` to the FastAPI endpoint, which then sends the appropriate HTTP response back to the client.

This layered approach ensures that the core business logic (domain) remains independent of external concerns (infrastructure, interfaces), making the system more maintainable, testable, and flexible to changes in technology.

Here's a Mermaid diagram illustrating the component interactions:

```mermaid
graph TD
    A[Client] -->|HTTP Request| B(FastAPI Endpoints in main.py)
    B -->|Uses DTOs| C(interfaces/dto)
    B -->|Authenticates| D(infrastructure/auth)
    B -->|Injects TimeSeriesService| E(application/services/TimeSeriesService)
    E -->|Uses Repository Interface| F(domain/repositories/TimeSeriesRepositoryInterface)
    F -->|Implemented by (DB)| G(infrastructure/database/repositories/TimeSeriesDBRepository)
    F -->|Implemented by (File)| H(infrastructure/repositories/TimeSeriesRepository - File-based)
    G -->|Interacts with DB Config| I(infrastructure/database/config)
    G -->|Maps to DB Models| J(infrastructure/database/models)
    E -->|Operates on Domain Model| K(domain/models/TimeSeries)
    E -->|Uses for Caching| L(infrastructure/cache)
    K -->|Performs Analysis| M(Pandas/NumPy/SciPy)
    E -->|Returns DTOs| C
    C -->|HTTP Response| B
    B -->|HTTP Response| A