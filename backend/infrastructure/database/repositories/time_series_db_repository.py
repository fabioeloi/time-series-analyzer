"""Database-backed repository implementation for TimeSeries"""
import json
import logging
from typing import List, Optional
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.models.time_series import TimeSeries
from domain.repositories.time_series_repository_interface import TimeSeriesRepositoryInterface
from ..models import TimeSeriesMetadata, TimeSeriesDataPoint


class TimeSeriesDBRepository(TimeSeriesRepositoryInterface):
    """Database-backed repository for storing and retrieving time series data"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    async def save(self, time_series: TimeSeries) -> None:
        """Save a time series to the database"""
        try:
            # Check if metadata already exists
            stmt = select(TimeSeriesMetadata).where(TimeSeriesMetadata.id == time_series.id)
            result = await self.db_session.execute(stmt)
            existing_metadata = result.scalar_one_or_none()
            
            if existing_metadata:
                # Update existing metadata
                existing_metadata.time_column = time_series.time_column
                existing_metadata.value_columns = json.dumps(time_series.value_columns)
                
                # Delete existing data points
                delete_stmt = delete(TimeSeriesDataPoint).where(
                    TimeSeriesDataPoint.time_series_id == time_series.id
                )
                await self.db_session.execute(delete_stmt)
                
                metadata = existing_metadata
            else:
                # Create new metadata
                metadata = TimeSeriesMetadata(
                    id=time_series.id,
                    time_column=time_series.time_column,
                    value_columns=json.dumps(time_series.value_columns)
                )
                self.db_session.add(metadata)
            
            # Convert and save data points
            await self._save_data_points(time_series)
            await self.db_session.flush()
            
            self.logger.info(f"Saved time series with ID: {time_series.id}")
            
        except Exception as e:
            self.logger.error(f"Error saving time series {time_series.id}: {str(e)}")
            raise
    
    async def _save_data_points(self, time_series: TimeSeries) -> None:
        """Save time series data points to the database"""
        data_points = []
        
        # Convert pandas DataFrame to database records
        for index, row in time_series.data.iterrows():
            timestamp = row[time_series.time_column]
            
            # Convert timestamp to datetime if it's not already
            if pd.api.types.is_numeric_dtype(pd.Series([timestamp])):
                # If it's numeric, treat it as Unix timestamp or index
                if timestamp > 1e9:  # Likely Unix timestamp
                    timestamp = pd.to_datetime(timestamp, unit='s')
                else:  # Likely an index, use current time with offset
                    base_time = pd.Timestamp.now()
                    timestamp = base_time + pd.Timedelta(seconds=float(timestamp))
            else:
                timestamp = pd.to_datetime(timestamp)
            
            # Create data points for each value column
            for column in time_series.value_columns:
                value = row[column]
                # Handle NaN values
                if pd.isna(value):
                    value = None
                else:
                    value = float(value)
                
                data_point = TimeSeriesDataPoint(
                    time_series_id=time_series.id,
                    timestamp=timestamp,
                    column_name=column,
                    value=value
                )
                data_points.append(data_point)
        
        # Bulk insert data points
        self.db_session.add_all(data_points)
    
    async def find_by_id(self, id: str) -> Optional[TimeSeries]:
        """Find a time series by ID"""
        try:
            # Get metadata with data points
            stmt = select(TimeSeriesMetadata).options(
                selectinload(TimeSeriesMetadata.data_points)
            ).where(TimeSeriesMetadata.id == id)
            
            result = await self.db_session.execute(stmt)
            metadata = result.scalar_one_or_none()
            
            if not metadata:
                self.logger.warning(f"Time series with ID: {id} not found")
                return None
            
            # Convert database records back to TimeSeries
            time_series = await self._convert_to_time_series(metadata)
            self.logger.info(f"Found time series with ID: {id}")
            return time_series
            
        except Exception as e:
            self.logger.error(f"Error finding time series {id}: {str(e)}")
            raise
    
    async def find_all(self) -> List[TimeSeries]:
        """Get all stored time series"""
        try:
            # Get all metadata with data points
            stmt = select(TimeSeriesMetadata).options(
                selectinload(TimeSeriesMetadata.data_points)
            )
            
            result = await self.db_session.execute(stmt)
            all_metadata = result.scalars().all()
            
            time_series_list = []
            for metadata in all_metadata:
                time_series = await self._convert_to_time_series(metadata)
                time_series_list.append(time_series)
            
            self.logger.info(f"Returning all {len(time_series_list)} time series analyses")
            return time_series_list
            
        except Exception as e:
            self.logger.error(f"Error finding all time series: {str(e)}")
            raise
    
    async def delete(self, id: str) -> None:
        """Delete a time series by ID"""
        try:
            # Check if exists
            if not await self.exists(id):
                self.logger.warning(f"Cannot delete: time series with ID: {id} not found")
                return
            
            # Delete metadata (cascades to data points)
            stmt = delete(TimeSeriesMetadata).where(TimeSeriesMetadata.id == id)
            await self.db_session.execute(stmt)
            
            self.logger.info(f"Deleted time series with ID: {id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting time series {id}: {str(e)}")
            raise
    
    async def exists(self, id: str) -> bool:
        """Check if a time series exists with the given ID"""
        try:
            stmt = select(TimeSeriesMetadata.id).where(TimeSeriesMetadata.id == id)
            result = await self.db_session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            self.logger.error(f"Error checking existence of time series {id}: {str(e)}")
            raise
    
    async def _convert_to_time_series(self, metadata: TimeSeriesMetadata) -> TimeSeries:
        """Convert database records to TimeSeries domain model"""
        # Parse value columns
        value_columns = json.loads(metadata.value_columns)
        
        # Group data points by timestamp
        data_dict = {}
        
        for data_point in metadata.data_points:
            timestamp = data_point.timestamp
            if timestamp not in data_dict:
                data_dict[timestamp] = {metadata.time_column: timestamp}
            
            data_dict[timestamp][data_point.column_name] = data_point.value
        
        # Convert to DataFrame
        if data_dict:
            # Sort by timestamp
            sorted_timestamps = sorted(data_dict.keys())
            rows = [data_dict[ts] for ts in sorted_timestamps]
            df = pd.DataFrame(rows)
            
            # Ensure all value columns exist (fill with NaN if missing)
            for col in value_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Reorder columns
            columns_order = [metadata.time_column] + value_columns
            df = df[columns_order]
        else:
            # Empty DataFrame with correct structure
            columns = [metadata.time_column] + value_columns
            df = pd.DataFrame(columns=columns)
        
        return TimeSeries(
            id=metadata.id,
            data=df,
            time_column=metadata.time_column,
            value_columns=value_columns
        )