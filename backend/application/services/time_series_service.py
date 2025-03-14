from typing import Dict, List, Optional
import pandas as pd

from domain.models.time_series import TimeSeries
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO, TimeSeriesResponseDTO
from infrastructure.repositories.time_series_repository import TimeSeriesRepository

class TimeSeriesService:
    """Application service for time series operations"""
    
    def __init__(self):
        self.repository = TimeSeriesRepository()
        
    def process_time_series(self, request: TimeSeriesRequestDTO) -> TimeSeriesResponseDTO:
        """Process time series data from uploaded CSV"""
        # Create domain model
        time_series = TimeSeries.create(
            data=request.dataframe,
            time_column=request.time_column,
            value_columns=request.value_columns
        )
        
        # Store the time series
        self.repository.save(time_series)
        
        # Get time domain data
        time_domain_data = time_series.get_time_domain_data()
        
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
    
    def get_analysis_result(self, analysis_id: str, domain: str = "time") -> TimeSeriesResponseDTO:
        """Retrieve analysis results by ID"""
        # Get the time series from repository
        time_series = self.repository.find_by_id(analysis_id)
        
        if not time_series:
            raise ValueError(f"No time series found with ID {analysis_id}")
        
        # Get time domain data
        time_domain_data = time_series.get_time_domain_data()
        
        # Get frequency domain data if requested
        frequency_domain_data = None
        if domain == "frequency":
            frequency_domain_data = time_series.get_frequency_domain_data()
        
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