from typing import Dict, Optional, List
import os
import pickle
import logging
import json
from domain.models.time_series import TimeSeries
from domain.repositories.time_series_repository_interface import TimeSeriesRepositoryInterface

class TimeSeriesRepository(TimeSeriesRepositoryInterface):
    """Repository for storing and retrieving time series data"""
    
    def __init__(self):
        self._storage: Dict[str, TimeSeries] = {}
        self._storage_path = os.path.join(os.path.dirname(__file__), "../../data")
        self._storage_file = os.path.join(self._storage_path, "time_series_storage.pkl")
        self._backup_file = os.path.join(self._storage_path, "time_series_storage_backup.json")
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory if it doesn't exist
        os.makedirs(self._storage_path, exist_ok=True)
        
        # Load existing data if available
        self._load_from_disk()
        
    def _save_to_disk(self) -> None:
        """Persist data to disk"""
        try:
            # Primary storage (pickle)
            with open(self._storage_file, 'wb') as f:
                pickle.dump(self._storage, f)
            
            # Backup storage (JSON for inspection/debugging)
            backup_data = {}
            for key, ts in self._storage.items():
                backup_data[key] = {
                    "id": ts.id,
                    "time_column": ts.time_column,
                    "value_columns": ts.value_columns,
                    "num_columns": len(ts.data.columns) if ts.data is not None else 0,
                    "num_rows": len(ts.data) if ts.data is not None else 0
                }
            
            with open(self._backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            self.logger.info(f"Successfully saved {len(self._storage)} time series analyses to disk")
        except Exception as e:
            self.logger.error(f"Error saving time series data to disk: {str(e)}")
    
    def _load_from_disk(self) -> None:
        """Load data from disk if available"""
        if os.path.exists(self._storage_file):
            try:
                with open(self._storage_file, 'rb') as f:
                    self._storage = pickle.load(f)
                self.logger.info(f"Loaded {len(self._storage)} time series analyses from disk")
                
                # Log the available analysis IDs for debugging
                if self._storage:
                    self.logger.info(f"Available analysis IDs: {list(self._storage.keys())}")
            except Exception as e:
                self.logger.error(f"Error loading time series data from disk: {str(e)}")
                self._storage = {}
        else:
            self.logger.info("No time series storage file found. Starting with empty storage.")
            self._storage = {}
        
    async def save(self, time_series: TimeSeries) -> None:
        """Save a time series to the repository"""
        self._storage[time_series.id] = time_series
        self.logger.info(f"Saved time series with ID: {time_series.id}")
        self._save_to_disk()
        
    async def find_by_id(self, id: str) -> Optional[TimeSeries]:
        """Find a time series by ID"""
        result = self._storage.get(id)
        if result:
            self.logger.info(f"Found time series with ID: {id}")
        else:
            self.logger.warning(f"Time series with ID: {id} not found")
        return result
        
    async def find_all(self) -> List[TimeSeries]:
        """Get all stored time series"""
        self.logger.info(f"Returning all {len(self._storage)} time series analyses")
        return list(self._storage.values())
        
    async def delete(self, id: str) -> None:
        """Delete a time series by ID"""
        if id in self._storage:
            del self._storage[id]
            self.logger.info(f"Deleted time series with ID: {id}")
            self._save_to_disk()
        else:
            self.logger.warning(f"Cannot delete: time series with ID: {id} not found")
            
    async def exists(self, id: str) -> bool:
        """Check if a time series exists with the given ID"""
        return id in self._storage
    
    def list_available_ids(self) -> List[str]:
        """List all available analysis IDs"""
        return list(self._storage.keys())