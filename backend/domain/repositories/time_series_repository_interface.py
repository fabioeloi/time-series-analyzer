from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.time_series import TimeSeries


class TimeSeriesRepositoryInterface(ABC):
    """Abstract repository interface for time series data storage"""
    
    @abstractmethod
    async def save(self, time_series: TimeSeries) -> None:
        """Save a time series to the repository"""
        pass
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[TimeSeries]:
        """Find a time series by ID"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[TimeSeries]:
        """Get all stored time series"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete a time series by ID"""
        pass
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if a time series exists with the given ID"""
        pass