# Caching Strategy

This document outlines the caching strategy implemented in the time-series analyzer backend, focusing on Redis as the caching backend.

## 1. Chosen Caching Backend and Library

*   **Backend:** Redis
*   **Python Library:** `redis-py` with async support (`aioredis` for `asyncio` compatibility).

Redis is chosen for its high performance, in-memory data store capabilities, and support for various data structures, making it suitable for fast data retrieval.

## 2. Cacheable Operations

The following operations are identified as cacheable due to their frequent access patterns and potential for performance improvement:

*   `find_by_id(id: str)`: Retrieves a single time series record by its ID.
*   `get_time_domain_data(id: str)`: Fetches time-domain data for a specific time series ID.
*   `get_frequency_domain_data(id: str)`: Fetches frequency-domain data for a specific time series ID.

## 3. Cache Key Design

A clear and consistent cache key design is crucial for efficient caching and invalidation. The following patterns are used:

*   **For `find_by_id`:**
    *   Key: `timeseries:{id}`
    *   Example: `timeseries:123e4567-e89b-12d3-a456-426614174000`
    *   Stores the full time series object.

*   **For `get_time_domain_data`:**
    *   Key: `timeseries:{id}:time_domain`
    *   Example: `timeseries:123e4567-e89b-12d3-a456-426614174000:time_domain`
    *   Stores the time-domain data associated with the time series.

*   **For `get_frequency_domain_data`:**
    *   Key: `timeseries:{id}:frequency_domain`
    *   Example: `timeseries:123e4567-e89b-12d3-a456-426614174000:frequency_domain`
    *   Stores the frequency-domain data associated with the time series.

This design ensures that different representations or subsets of a time series are cached independently, allowing for granular invalidation.

## 4. Cache Invalidation Strategy

To maintain data consistency, the cache employs a combination of explicit invalidation and Time-To-Live (TTL):

*   **Explicit Invalidation:**
    *   **On Update:** When a time series record is updated, all associated cache keys (`timeseries:{id}`, `timeseries:{id}:time_domain`, `timeseries:{id}:frequency_domain`) are explicitly invalidated (deleted) from Redis. This ensures that subsequent reads fetch the most current data from the database.
    *   **On Delete:** When a time series record is deleted, its corresponding cache entries are also explicitly removed.

*   **Time-To-Live (TTL):**
    *   All cached entries are configured with a configurable TTL (Time-To-Live). This ensures that even if explicit invalidation fails or is missed, the cached data will eventually expire and be refreshed from the database. The TTL is managed via the `REDIS_TTL_SECONDS` environment variable.

## 5. Serialization Format

*   **Format:** JSON
*   **Reasoning:** JSON is used for serializing Python objects before storing them in Redis. This provides a human-readable and interoperable format, making it easy to inspect cached data and ensuring compatibility across different services or languages if needed.