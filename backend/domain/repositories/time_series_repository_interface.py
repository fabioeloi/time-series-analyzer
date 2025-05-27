from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.time_series import TimeSeries


class TimeSeriesRepositoryInterface(ABC):
    """Abstract repository interface for time series data storage"""
    
    @abstractmethod
    def save(self, time_series: TimeSeries) -> None:
        """Save a time series to the repository"""
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[TimeSeries]:
        """Find a time series by ID"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[TimeSeries]:
        """Get all stored time series"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> None:
        """Delete a time series by ID"""
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        """Check if a time series exists with the given ID"""
        pass