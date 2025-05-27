import sys
import os
import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from application.services.time_series_service import TimeSeriesService
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO
from domain.models.time_series import TimeSeries
from domain.repositories.time_series_repository_interface import TimeSeriesRepositoryInterface

class TestTimeSeriesService:
    
    def setup_method(self):
        """Set up test fixtures for each test method"""
        # Create a mock repository that implements the interface
        self.mock_repository = MagicMock(spec=TimeSeriesRepositoryInterface)
        self.service = TimeSeriesService(self.mock_repository)
        
    def test_process_time_series(self):
        """Test processing a time series from uploaded data"""
        # Create test data
        test_df = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=5, freq='D'),
            'value1': [1, 2, 3, 4, 5],
            'value2': [5, 4, 3, 2, 1]
        })
        
        # Create request DTO
        request = TimeSeriesRequestDTO(
            dataframe=test_df,
            time_column='date',
            value_columns=['value1', 'value2']
        )
        
        # Process the time series
        response = self.service.process_time_series(request)
        
        # Verify the service saved the time series in the repository
        self.mock_repository.save.assert_called_once()
        
        # Verify the response structure
        assert response.time_column == 'date'
        assert set(response.value_columns) == set(['value1', 'value2'])
        assert response.analysis_id is not None
        assert response.time_domain is not None
        assert 'time' in response.time_domain
        assert 'series' in response.time_domain
        assert set(response.time_domain['series'].keys()) == set(['value1', 'value2'])
        
    def test_get_analysis_result_time_domain(self):
        """Test retrieving time domain analysis results"""
        # Create a mock time series
        mock_ts = MagicMock(spec=TimeSeries)
        mock_ts.id = "test-id"
        mock_ts.time_column = 'timestamp'
        mock_ts.value_columns = ['temp', 'pressure']
        mock_ts.data = pd.DataFrame({
            'timestamp': [1, 2, 3],
            'temp': [20, 21, 22],
            'pressure': [1000, 1001, 1002]
        })
        
        # Mock the time domain data
        mock_ts.get_time_domain_data.return_value = {
            'time': [1, 2, 3],
            'series': {
                'temp': [20, 21, 22],
                'pressure': [1000, 1001, 1002]
            }
        }
        
        # Mock the repository to return our mock time series
        self.mock_repository.find_by_id.return_value = mock_ts
        
        # Get analysis result in time domain
        response = self.service.get_analysis_result("test-id", "time")
        
        # Verify the repository was called correctly
        self.mock_repository.find_by_id.assert_called_once_with("test-id")
        
        # Verify the response contains time domain data but not frequency domain data
        assert response.time_domain is not None
        assert response.frequency_domain is None
        assert response.time_domain['time'] == [1, 2, 3]
        assert response.time_domain['series']['temp'] == [20, 21, 22]
        
    def test_get_analysis_result_frequency_domain(self):
        """Test retrieving frequency domain analysis results"""
        # Create a mock time series
        mock_ts = MagicMock(spec=TimeSeries)
        mock_ts.id = "test-id"
        mock_ts.time_column = 'timestamp'
        mock_ts.value_columns = ['signal']
        mock_ts.data = pd.DataFrame({
            'timestamp': np.linspace(0, 1, 10),
            'signal': np.sin(2 * np.pi * 5 * np.linspace(0, 1, 10))
        })
        
        # Mock the time domain and frequency domain data
        mock_ts.get_time_domain_data.return_value = {
            'time': list(np.linspace(0, 1, 10)),
            'series': {
                'signal': list(np.sin(2 * np.pi * 5 * np.linspace(0, 1, 10)))
            }
        }
        
        mock_ts.get_frequency_domain_data.return_value = {
            'frequencies': {
                'signal': [1, 2, 3, 4, 5]
            },
            'amplitudes': {
                'signal': [0.1, 0.2, 0.3, 0.4, 0.5]
            }
        }
        
        # Mock the repository to return our mock time series
        self.mock_repository.find_by_id.return_value = mock_ts
        
        # Get analysis result in frequency domain
        response = self.service.get_analysis_result("test-id", "frequency")
        
        # Verify the repository was called correctly
        self.mock_repository.find_by_id.assert_called_once_with("test-id")
        
        # Verify the response contains both time domain and frequency domain data
        assert response.time_domain is not None
        assert response.frequency_domain is not None
        assert 'frequencies' in response.frequency_domain
        assert 'amplitudes' in response.frequency_domain
        assert response.frequency_domain['frequencies']['signal'] == [1, 2, 3, 4, 5]
        
    def test_get_analysis_result_not_found(self):
        """Test handling of a non-existent analysis ID"""
        # Mock the repository to return None, simulating a non-existent ID
        self.mock_repository.find_by_id.return_value = None
        
        # Check that the service raises an exception for a non-existent ID
        with pytest.raises(ValueError, match="No time series found with ID non-existent-id"):
            self.service.get_analysis_result("non-existent-id", "time")