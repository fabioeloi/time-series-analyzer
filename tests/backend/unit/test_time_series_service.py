import sys
import os
import pandas as pd
import numpy as np
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from application.services.time_series_service import TimeSeriesService
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO
from domain.models.time_series import TimeSeries
from domain.repositories.time_series_repository_interface import TimeSeriesRepositoryInterface

class TestTimeSeriesService:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up test fixtures for each test method using a pytest fixture"""
        # Create a mock repository that implements the interface
        mock_repository = MagicMock(spec=TimeSeriesRepositoryInterface)
        # Make all repository methods async
        mock_repository.save = AsyncMock()
        mock_repository.find_by_id = AsyncMock()
        mock_repository.find_all = AsyncMock()
        mock_repository.delete = AsyncMock()
        mock_repository.exists = AsyncMock()

        # Patch cache_service for all tests in this class
        with patch('application.services.time_series_service.cache_service') as mock_cache_service:
            # Make all cache_service methods async mocks
            mock_cache_service.cache_timeseries_object = AsyncMock()
            mock_cache_service.get_timeseries_object = AsyncMock()
            mock_cache_service.cache_time_domain_data = AsyncMock()
            mock_cache_service.get_time_domain_data = AsyncMock()
            mock_cache_service.cache_frequency_domain_data = AsyncMock()
            mock_cache_service.get_frequency_domain_data = AsyncMock()
            mock_cache_service.invalidate_timeseries = AsyncMock()

            self.mock_repository = mock_repository
            self.mock_cache_service = mock_cache_service
            self.service = TimeSeriesService(self.mock_repository)
            yield

    @pytest.mark.asyncio
    async def test_process_time_series(self, setup_mocks):
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
        response = await self.service.process_time_series(request)
        
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
        
        # Verify cache service calls
        self.mock_cache_service.cache_timeseries_object.assert_called_once()
        self.mock_cache_service.cache_time_domain_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_analysis_result_cache_hit(self, setup_mocks):
        """Test retrieving analysis results when data is in cache"""
        analysis_id = "cached-test-id"
        
        # Prepare cached data
        cached_data = {
            'id': analysis_id,
            'data': pd.DataFrame({
                'timestamp': [1, 2, 3],
                'temp': [20, 21, 22],
                'pressure': [1000, 1001, 1002]
            }).to_dict('records'),
            'time_column': 'timestamp',
            'value_columns': ['temp', 'pressure'],
            'columns': ['timestamp', 'temp', 'pressure']
        }
        cached_time_domain = {
            'time': [1, 2, 3],
            'series': {
                'temp': [20, 21, 22],
                'pressure': [1000, 1001, 1002]
            }
        }
        
        # Mock cache service to return cached data
        self.mock_cache_service.get_timeseries_object.return_value = cached_data
        self.mock_cache_service.get_time_domain_data.return_value = cached_time_domain
        self.mock_cache_service.get_frequency_domain_data.return_value = None # Not cached for this test

        # Call the service method
        response = await self.service.get_analysis_result(analysis_id, "time")

        # Verify cache hit behavior
        self.mock_cache_service.get_timeseries_object.assert_called_once_with(analysis_id)
        self.mock_cache_service.get_time_domain_data.assert_called_once_with(analysis_id)
        self.mock_repository.find_by_id.assert_not_called() # Should not hit DB
        self.mock_cache_service.cache_timeseries_object.assert_not_called() # Should not cache again
        self.mock_cache_service.cache_time_domain_data.assert_not_called() # Should not cache again

        # Verify response content
        assert response.analysis_id == analysis_id
        assert response.time_domain == cached_time_domain
        assert response.frequency_domain is None

    @pytest.mark.asyncio
    async def test_get_analysis_result_cache_miss(self, setup_mocks):
        """Test retrieving analysis results when data is not in cache (cache miss)"""
        analysis_id = "miss-test-id"
        
        # Mock cache service to return None (cache miss)
        self.mock_cache_service.get_timeseries_object.return_value = None
        self.mock_cache_service.get_time_domain_data.return_value = None
        self.mock_cache_service.get_frequency_domain_data.return_value = None

        # Create a mock time series for repository
        mock_ts = MagicMock(spec=TimeSeries)
        mock_ts.id = analysis_id
        mock_ts.time_column = 'timestamp'
        mock_ts.value_columns = ['temp', 'pressure']
        mock_ts.data = pd.DataFrame({
            'timestamp': [1, 2, 3],
            'temp': [20, 21, 22],
            'pressure': [1000, 1001, 1002]
        })
        mock_ts.get_time_domain_data.return_value = {
            'time': [1, 2, 3],
            'series': {
                'temp': [20, 21, 22],
                'pressure': [1000, 1001, 1002]
            }
        }
        self.mock_repository.find_by_id.return_value = mock_ts

        # Call the service method
        response = await self.service.get_analysis_result(analysis_id, "time")

        # Verify cache miss behavior
        self.mock_cache_service.get_timeseries_object.assert_called_once_with(analysis_id)
        self.mock_repository.find_by_id.assert_called_once_with(analysis_id) # Should hit DB
        self.mock_cache_service.cache_timeseries_object.assert_called_once() # Should cache after retrieval
        self.mock_cache_service.cache_time_domain_data.assert_called_once() # Should cache time domain data

        # Verify response content
        assert response.analysis_id == analysis_id
        assert response.time_domain is not None
        assert response.frequency_domain is None

    @pytest.mark.asyncio
    async def test_get_analysis_result_frequency_domain_cache_hit(self, setup_mocks):
        """Test retrieving frequency domain analysis results when data is in cache"""
        analysis_id = "cached-freq-id"
        
        # Prepare cached data
        cached_data = {
            'id': analysis_id,
            'data': pd.DataFrame({
                'timestamp': np.linspace(0, 1, 10),
                'signal': np.sin(2 * np.pi * 5 * np.linspace(0, 1, 10))
            }).to_dict('records'),
            'time_column': 'timestamp',
            'value_columns': ['signal'],
            'columns': ['timestamp', 'signal']
        }
        cached_time_domain = {
            'time': list(np.linspace(0, 1, 10)),
            'series': {
                'signal': list(np.sin(2 * np.pi * 5 * np.linspace(0, 1, 10)))
            }
        }
        cached_frequency_domain = {
            'frequencies': {
                'signal': [1, 2, 3, 4, 5]
            },
            'amplitudes': {
                'signal': [0.1, 0.2, 0.3, 0.4, 0.5]
            }
        }
        
        # Mock cache service to return cached data
        self.mock_cache_service.get_timeseries_object.return_value = cached_data
        self.mock_cache_service.get_time_domain_data.return_value = cached_time_domain
        self.mock_cache_service.get_frequency_domain_data.return_value = cached_frequency_domain

        # Call the service method
        response = await self.service.get_analysis_result(analysis_id, "frequency")

        # Verify cache hit behavior
        self.mock_cache_service.get_timeseries_object.assert_called_once_with(analysis_id)
        self.mock_cache_service.get_time_domain_data.assert_called_once_with(analysis_id)
        self.mock_cache_service.get_frequency_domain_data.assert_called_once_with(analysis_id)
        self.mock_repository.find_by_id.assert_not_called() # Should not hit DB
        self.mock_cache_service.cache_timeseries_object.assert_not_called() # Should not cache again
        self.mock_cache_service.cache_time_domain_data.assert_not_called() # Should not cache again
        self.mock_cache_service.cache_frequency_domain_data.assert_not_called() # Should not cache again

        # Verify response content
        assert response.analysis_id == analysis_id
        assert response.time_domain == cached_time_domain
        assert response.frequency_domain == cached_frequency_domain

    @pytest.mark.asyncio
    async def test_get_analysis_result_frequency_domain_cache_miss(self, setup_mocks):
        """Test retrieving frequency domain analysis results when not in cache"""
        analysis_id = "miss-freq-id"
        
        # Mock cache service to return None (cache miss)
        self.mock_cache_service.get_timeseries_object.return_value = None
        self.mock_cache_service.get_time_domain_data.return_value = None
        self.mock_cache_service.get_frequency_domain_data.return_value = None

        # Create a mock time series for repository
        mock_ts = MagicMock(spec=TimeSeries)
        mock_ts.id = analysis_id
        mock_ts.time_column = 'timestamp'
        mock_ts.value_columns = ['signal']
        mock_ts.data = pd.DataFrame({
            'timestamp': np.linspace(0, 1, 10),
            'signal': np.sin(2 * np.pi * 5 * np.linspace(0, 1, 10))
        })
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
        self.mock_repository.find_by_id.return_value = mock_ts

        # Call the service method
        response = await self.service.get_analysis_result(analysis_id, "frequency")

        # Verify cache miss behavior
        self.mock_cache_service.get_timeseries_object.assert_called_once_with(analysis_id)
        self.mock_repository.find_by_id.assert_called_once_with(analysis_id) # Should hit DB
        self.mock_cache_service.cache_timeseries_object.assert_called_once() # Should cache after retrieval
        self.mock_cache_service.cache_time_domain_data.assert_called_once() # Should cache time domain data
        self.mock_cache_service.cache_frequency_domain_data.assert_called_once() # Should cache frequency domain data

        # Verify response content
        assert response.analysis_id == analysis_id
        assert response.time_domain is not None
        assert response.frequency_domain is not None

    @pytest.mark.asyncio
    async def test_delete_time_series_invalidates_cache(self, setup_mocks):
        """Test that deleting a time series invalidates its cache entries"""
        analysis_id = "delete-test-id"
        
        # Mock repository to return True for deletion
        self.mock_repository.delete.return_value = True
        
        # Mock cache service to return a count of invalidated entries
        self.mock_cache_service.invalidate_timeseries.return_value = 3 # Simulate 3 entries invalidated

        # Call the service method
        deleted = await self.service.delete_time_series(analysis_id)

        # Verify repository delete was called
        self.mock_repository.delete.assert_called_once_with(analysis_id)
        
        # Verify cache invalidation was called
        self.mock_cache_service.invalidate_timeseries.assert_called_once_with(analysis_id)
        
        assert deleted is True

    @pytest.mark.asyncio
    async def test_update_time_series_invalidates_cache(self, setup_mocks):
        """Test that updating a time series invalidates its cache entries"""
        analysis_id = "update-test-id"
        
        # Create a mock time series for update
        mock_ts = MagicMock(spec=TimeSeries)
        mock_ts.id = analysis_id
        mock_ts.time_column = 'timestamp'
        mock_ts.value_columns = ['value']
        mock_ts.data = pd.DataFrame({'timestamp': [1], 'value': [10]})

        # Mock repository to return the updated time series
        self.mock_repository.save.return_value = mock_ts
        
        # Mock cache service to return a count of invalidated entries
        self.mock_cache_service.invalidate_timeseries.return_value = 2 # Simulate 2 entries invalidated

        # Call the service method
        updated_ts = await self.service.update_time_series(mock_ts)

        # Verify repository save was called
        self.mock_repository.save.assert_called_once_with(mock_ts)
        
        # Verify cache invalidation was called
        self.mock_cache_service.invalidate_timeseries.assert_called_once_with(analysis_id)
        
        assert updated_ts == mock_ts

    @pytest.mark.asyncio
    async def test_get_analysis_result_not_found(self, setup_mocks):
        """Test handling of a non-existent analysis ID"""
        # Mock the cache service to return None for time series object
        self.mock_cache_service.get_timeseries_object.return_value = None
        
        # Mock the repository to return None, simulating a non-existent ID
        self.mock_repository.find_by_id.return_value = None
        
        # Check that the service raises an exception for a non-existent ID
        with pytest.raises(ValueError, match="No time series found with ID non-existent-id"):
            await self.service.get_analysis_result("non-existent-id", "time")