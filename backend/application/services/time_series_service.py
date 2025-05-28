from typing import Dict, List, Optional
import pandas as pd
import logging

from domain.models.time_series import TimeSeries
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO, TimeSeriesResponseDTO
from domain.repositories.time_series_repository_interface import TimeSeriesRepositoryInterface
from infrastructure.cache.cache_service import cache_service

logger = logging.getLogger(__name__)

class TimeSeriesService:
    """Application service for time series operations"""
    
    def __init__(self, repository: TimeSeriesRepositoryInterface):
        self.repository = repository
        
    async def process_time_series(self, request: TimeSeriesRequestDTO) -> TimeSeriesResponseDTO:
        """Process time series data from uploaded CSV"""
        # Create domain model
        time_series = TimeSeries.create(
            data=request.dataframe,
            time_column=request.time_column,
            value_columns=request.value_columns
        )
        
        # Store the time series
        await self.repository.save(time_series)
        
        # Get time domain data
        time_domain_data = time_series.get_time_domain_data()
        
        # Cache the TimeSeries object data for future retrieval
        try:
            timeseries_cache_data = {
                'id': time_series.id,
                'data': time_series.data.to_dict('records'),
                'time_column': time_series.time_column,
                'value_columns': time_series.value_columns,
                'columns': list(time_series.data.columns)
            }
            await cache_service.cache_timeseries_object(time_series.id, timeseries_cache_data)
            
            # Cache time domain data
            await cache_service.cache_time_domain_data(time_series.id, time_domain_data)
            
            logger.info(f"Cached TimeSeries {time_series.id} and time domain data")
        except Exception as e:
            logger.warning(f"Failed to cache TimeSeries {time_series.id}: {e}")
        
        # Create response DTO
        response = TimeSeriesResponseDTO(
            analysis_id=time_series.id,
            columns=list(time_series.data.columns),
            time_column=time_series.time_column,
            value_columns=time_series.value_columns,
            time_domain=time_domain_data,
            frequency_domain=None  # Not calculated by default
        )
        
        return response
    
    async def get_analysis_result(self, analysis_id: str, domain: str = "time") -> TimeSeriesResponseDTO:
        """Retrieve analysis results by ID with caching"""
        # Try to get cached TimeSeries data first
        cached_timeseries = await cache_service.get_timeseries_object(analysis_id)
        time_series = None
        
        if cached_timeseries:
            # Reconstruct TimeSeries from cache
            try:
                data_df = pd.DataFrame(cached_timeseries['data'])
                time_series = TimeSeries(
                    id=cached_timeseries['id'],
                    data=data_df,
                    time_column=cached_timeseries['time_column'],
                    value_columns=cached_timeseries['value_columns']
                )
                logger.debug(f"TimeSeries {analysis_id} loaded from cache")
            except Exception as e:
                logger.warning(f"Failed to reconstruct TimeSeries from cache: {e}")
                cached_timeseries = None
        
        # If not in cache, get from repository
        if not cached_timeseries:
            time_series = await self.repository.find_by_id(analysis_id)
            if not time_series:
                raise ValueError(f"No time series found with ID {analysis_id}")
            
            # Cache the TimeSeries for future use
            try:
                timeseries_cache_data = {
                    'id': time_series.id,
                    'data': time_series.data.to_dict('records'),
                    'time_column': time_series.time_column,
                    'value_columns': time_series.value_columns,
                    'columns': list(time_series.data.columns)
                }
                await cache_service.cache_timeseries_object(time_series.id, timeseries_cache_data)
                logger.debug(f"TimeSeries {analysis_id} cached from database")
            except Exception as e:
                logger.warning(f"Failed to cache TimeSeries {analysis_id}: {e}")
        
        # Get time domain data (try cache first)
        time_domain_data = await cache_service.get_time_domain_data(analysis_id)
        if not time_domain_data:
            time_domain_data = time_series.get_time_domain_data()
            # Cache the computed time domain data
            try:
                await cache_service.cache_time_domain_data(analysis_id, time_domain_data)
                logger.debug(f"Time domain data for {analysis_id} computed and cached")
            except Exception as e:
                logger.warning(f"Failed to cache time domain data for {analysis_id}: {e}")
        else:
            logger.debug(f"Time domain data for {analysis_id} loaded from cache")
        
        # Get frequency domain data if requested (try cache first)
        frequency_domain_data = None
        if domain == "frequency":
            frequency_domain_data = await cache_service.get_frequency_domain_data(analysis_id)
            if not frequency_domain_data:
                frequency_domain_data = time_series.get_frequency_domain_data()
                # Cache the computed frequency domain data
                try:
                    await cache_service.cache_frequency_domain_data(analysis_id, frequency_domain_data)
                    logger.debug(f"Frequency domain data for {analysis_id} computed and cached")
                except Exception as e:
                    logger.warning(f"Failed to cache frequency domain data for {analysis_id}: {e}")
            else:
                logger.debug(f"Frequency domain data for {analysis_id} loaded from cache")
        
        # Create response DTO
        response = TimeSeriesResponseDTO(
            analysis_id=time_series.id,
            columns=list(time_series.data.columns),
            time_column=time_series.time_column,
            value_columns=time_series.value_columns,
            time_domain=time_domain_data,
            frequency_domain=frequency_domain_data
        )
        
        return response
    
    async def delete_time_series(self, analysis_id: str) -> bool:
        """Delete a time series and invalidate its cache"""
        # Delete from repository
        deleted = await self.repository.delete(analysis_id)
        
        if deleted:
            # Invalidate all cache entries for this TimeSeries
            try:
                invalidated_count = await cache_service.invalidate_timeseries(analysis_id)
                logger.info(f"Deleted TimeSeries {analysis_id} and invalidated {invalidated_count} cache entries")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for deleted TimeSeries {analysis_id}: {e}")
        
        return deleted
    
    async def update_time_series(self, time_series: TimeSeries) -> TimeSeries:
        """Update a time series and invalidate its cache"""
        # Update in repository
        updated_time_series = await self.repository.save(time_series)
        
        # Invalidate cache entries for this TimeSeries
        try:
            invalidated_count = await cache_service.invalidate_timeseries(time_series.id)
            logger.info(f"Updated TimeSeries {time_series.id} and invalidated {invalidated_count} cache entries")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for updated TimeSeries {time_series.id}: {e}")
        
        return updated_time_series
    
    async def invalidate_cache(self, analysis_id: str) -> int:
        """Manually invalidate cache for a specific TimeSeries"""
        try:
            invalidated_count = await cache_service.invalidate_timeseries(analysis_id)
            logger.info(f"Manually invalidated {invalidated_count} cache entries for TimeSeries {analysis_id}")
            return invalidated_count
        except Exception as e:
            logger.error(f"Failed to invalidate cache for TimeSeries {analysis_id}: {e}")
            return 0