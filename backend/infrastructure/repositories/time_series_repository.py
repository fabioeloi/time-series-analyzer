from typing import Dict, Optional, List
from domain.models.time_series import TimeSeries

class TimeSeriesRepository:
    """Repository for storing and retrieving time series data"""
    
    def __init__(self):
        # In-memory storage for development
        # In production, this would be replaced with a database
        self._storage: Dict[str, TimeSeries] = {}
        
    def save(self, time_series: TimeSeries) -> None:
        """Save a time series to the repository"""
        self._storage[time_series.id] = time_series
        
    def find_by_id(self, id: str) -> Optional[TimeSeries]:
        """Find a time series by ID"""
        return self._storage.get(id)
        
    def get_all(self) -> List[TimeSeries]:
        """Get all stored time series"""
        return list(self._storage.values())
        
    def delete(self, id: str) -> None:
        """Delete a time series by ID"""
        if id in self._storage:
            del self._storage[id]