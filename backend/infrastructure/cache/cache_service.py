import asyncio
from typing import Dict, Any, Optional, Tuple

class InMemoryCacheService:
    """
    A simple asynchronous in-memory cache service.
    """
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def _get_key(self, prefix: str, analysis_id: str) -> str:
        return f"{prefix}:{analysis_id}"

    async def cache_timeseries_object(self, analysis_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            key = await self._get_key("timeseries_object", analysis_id)
            self._cache[key] = data

    async def get_timeseries_object(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            key = await self._get_key("timeseries_object", analysis_id)
            return self._cache.get(key)

    async def cache_time_domain_data(self, analysis_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            key = await self._get_key("time_domain", analysis_id)
            self._cache[key] = data

    async def get_time_domain_data(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            key = await self._get_key("time_domain", analysis_id)
            return self._cache.get(key)

    async def cache_frequency_domain_data(self, analysis_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            key = await self._get_key("frequency_domain", analysis_id)
            self._cache[key] = data

    async def get_frequency_domain_data(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            key = await self._get_key("frequency_domain", analysis_id)
            return self._cache.get(key)

    async def invalidate_timeseries(self, analysis_id: str) -> int:
        """
        Invalidates all cache entries related to a specific analysis_id.
        Returns the number of invalidated entries.
        """
        invalidated_count = 0
        async with self._lock:
            prefixes_to_check = ["timeseries_object", "time_domain", "frequency_domain"]
            keys_to_delete = []
            for prefix in prefixes_to_check:
                key = await self._get_key(prefix, analysis_id)
                if key in self._cache:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if key in self._cache: # Check again in case of concurrent modification (though lock should prevent)
                    del self._cache[key]
                    invalidated_count += 1
        return invalidated_count

    async def clear_all_cache(self) -> int:
        """Clears the entire cache."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

# Instantiate the service for easy import
cache_service = InMemoryCacheService()