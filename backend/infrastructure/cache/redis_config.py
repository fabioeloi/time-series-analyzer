"""Redis configuration and connection management"""
import os
import redis.asyncio as aioredis
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration class"""
    
    def __init__(self):
        self.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.ttl_seconds = int(os.getenv("REDIS_TTL_SECONDS", "3600"))
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))


class RedisManager:
    """Redis connection manager with connection pooling"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
    
    async def initialize(self) -> None:
        """Initialize Redis connection pool"""
        if not self.config.enabled:
            logger.info("Redis is disabled, skipping initialization")
            return
            
        try:
            # Create connection pool
            if self.config.url:
                self._pool = aioredis.ConnectionPool.from_url(
                    self.config.url,
                    max_connections=self.config.max_connections,
                    retry_on_timeout=True,
                    decode_responses=True
                )
            else:
                self._pool = aioredis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    retry_on_timeout=True,
                    decode_responses=True
                )
            
            # Create Redis client
            self._redis = aioredis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._redis.ping()
            logger.info(f"Redis connection established successfully at {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._redis = None
            self._pool = None
            raise
    
    async def close(self) -> None:
        """Close Redis connections"""
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        
        logger.info("Redis connections closed")
    
    @property
    def redis(self) -> Optional[aioredis.Redis]:
        """Get Redis client instance"""
        return self._redis
    
    @property
    def is_enabled(self) -> bool:
        """Check if Redis is enabled and connected"""
        return self.config.enabled and self._redis is not None


# Global Redis manager instance
redis_config = RedisConfig()
redis_manager = RedisManager(redis_config)


async def get_redis() -> Optional[aioredis.Redis]:
    """Get Redis client instance"""
    return redis_manager.redis


async def is_redis_available() -> bool:
    """Check if Redis is available"""
    return redis_manager.is_enabled