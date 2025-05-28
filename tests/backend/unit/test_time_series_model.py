import sys
import os
import pandas as pd
import numpy as np
import pytest
from pathlib import Path

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from domain.models.time_series import TimeSeries

class TestTimeSeriesModel:
    
    def test_create_time_series(self):
        """Test creating a time series object with specific columns"""
        # Create test data
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='H'),
            'temperature': np.random.rand(10) * 30,
            'humidity': np.random.rand(10) * 100,
            'pressure': np.random.rand(10) * 1000
        })
        
        # Create time series object
        time_series = TimeSeries.create(
            data=data,
            time_column='timestamp',
            value_columns=['temperature', 'humidity', 'pressure']
        )
        
        # Verify the object was created correctly
        assert time_series.time_column == 'timestamp'
        assert set(time_series.value_columns) == set(['temperature', 'humidity', 'pressure'])
        assert isinstance(time_series.id, str)
        assert len(time_series.id) > 0
        
    def test_create_with_defaults(self):
        """Test creating a time series with default column detection"""
        # Create test data
        data = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=5, freq='D'),
            'value1': [1, 2, 3, 4, 5],
            'value2': [5, 4, 3, 2, 1]
        })
        
        # Create time series object with defaults
        time_series = TimeSeries.create(data=data)
        
        # Verify defaults were applied correctly
        assert time_series.time_column == 'date'  # First column
        assert set(time_series.value_columns) == set(['value1', 'value2'])  # All non-time columns
        
    def test_get_time_domain_data(self):
        """Test getting time domain data"""
        # Create test data
        data = pd.DataFrame({
            'time': [1, 2, 3, 4, 5],
            'series1': [10, 20, 30, 40, 50],
            'series2': [5, 15, 25, 35, 45]
        })
        
        # Create time series object
        time_series = TimeSeries.create(
            data=data,
            time_column='time',
            value_columns=['series1', 'series2']
        )
        
        # Get time domain data
        time_domain_data = time_series.get_time_domain_data()
        
        # Verify the data structure and values
        assert 'time' in time_domain_data
        assert 'series' in time_domain_data
        assert set(time_domain_data['series'].keys()) == set(['series1', 'series2'])
        assert time_domain_data['time'] == [1, 2, 3, 4, 5]
        assert time_domain_data['series']['series1'] == [10, 20, 30, 40, 50]
        assert time_domain_data['series']['series2'] == [5, 15, 25, 35, 45]
        
    def test_get_frequency_domain_data(self):
        """Test getting frequency domain data"""
        # Create a simple sine wave for testing FFT
        time = np.linspace(0, 10, 1000)
        # 5 Hz sine wave + 10 Hz sine wave
        signal1 = np.sin(2 * np.pi * 5 * time) + 0.5 * np.sin(2 * np.pi * 10 * time)
        signal2 = np.sin(2 * np.pi * 15 * time)
        
        data = pd.DataFrame({
            'time': time,
            'signal1': signal1,
            'signal2': signal2
        })
        
        # Create time series object
        time_series = TimeSeries.create(
            data=data,
            time_column='time',
            value_columns=['signal1', 'signal2']
        )
        
        # Get frequency domain data
        freq_domain_data = time_series.get_frequency_domain_data()
        
        # Verify the data structure
        assert 'frequencies' in freq_domain_data
        assert 'amplitudes' in freq_domain_data
        assert set(freq_domain_data['frequencies'].keys()) == set(['signal1', 'signal2'])
        assert set(freq_domain_data['amplitudes'].keys()) == set(['signal1', 'signal2'])
        
        # Check that the frequency with highest amplitude for signal1 is around 5Hz
        signal1_freqs = freq_domain_data['frequencies']['signal1']
        signal1_amps = freq_domain_data['amplitudes']['signal1']
        max_amp_idx = np.argmax(signal1_amps)
        # Find the frequency with the highest amplitude (should be close to 5 Hz)
        # Note: This test is approximate due to FFT bin resolution
        assert 4 < signal1_freqs[max_amp_idx] < 6 or 9 < signal1_freqs[max_amp_idx] < 11