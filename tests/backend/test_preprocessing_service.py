import sys
import os
import pandas as pd
import numpy as np
import pytest
from unittest import TestCase
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from application.services.preprocessing_service import PreprocessingService
from domain.models.time_series import TimeSeries


class TestPreprocessingService(TestCase):
    
    def setUp(self):
        # Setup test data
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        data = {
            'date': dates,
            'value': [10, 20, None, 40, 50, None, None, 80, 90, 1000],  # Added outlier 1000
            'category': ['A', 'B', None, 'A', 'B', None, 'C', 'A', 'B', 'C']
        }
        self.test_df = pd.DataFrame(data)
        self.service = PreprocessingService()
    
    def test_handle_missing_values(self):
        result = self.service.handle_missing_values(
            data=self.test_df,
            columns=['value'],
            method='ffill'
        )
        
        # Check that values were correctly filled
        self.assertEqual(result['value'].iloc[2], 20)
        self.assertEqual(result['value'].iloc[5], 50)
        self.assertEqual(result['value'].iloc[6], 50)
        
        # Check that other columns were not affected
        self.assertIsNone(result['category'].iloc[2])
    
    def test_remove_outliers(self):
        result = self.service.remove_outliers(
            data=self.test_df,
            method='iqr',
            threshold=1.5
        )
        
        # Verify outlier was removed
        self.assertEqual(len(result), 9)
        self.assertNotIn(1000, result['value'].values)
    
    def test_normalize_data(self):
        result = self.service.normalize_data(
            data=self.test_df,
            columns=['value'],
            method='minmax'
        )
        
        # Verify normalization
        non_null_values = result['value'].dropna()
        self.assertTrue((non_null_values >= 0).all() and (non_null_values <= 1).all())
    
    def test_resample_time_series(self):
        # Create hourly data
        dates = pd.date_range(start='2023-01-01', periods=24, freq='H')
        data = {
            'timestamp': dates,
            'temperature': np.sin(np.linspace(0, 2*np.pi, 24)) * 10 + 20
        }
        hourly_df = pd.DataFrame(data)
        
        # Test resampling to 6-hour intervals
        result = self.service.resample_time_series(
            data=hourly_df,
            time_column='timestamp',
            value_columns=['temperature'],
            freq='6H',
            agg_func='mean'
        )
        
        # Should have 4 rows (24 hours / 6 hours)
        self.assertEqual(len(result), 4)
    
    def test_process_time_series_data(self):
        # Test multiple operations in sequence
        operations = [
            {
                'type': 'missing_values',
                'params': {'columns': ['value'], 'method': 'ffill'}
            },
            {
                'type': 'outliers',
                'params': {'columns': ['value'], 'method': 'iqr', 'threshold': 1.5}
            },
            {
                'type': 'normalize',
                'params': {'columns': ['value'], 'method': 'minmax'}
            }
        ]
        
        result = self.service.process_time_series_data(
            data=self.test_df, 
            operations=operations
        )
        
        # Verify the sequence of operations worked correctly
        # 1. Missing values should be filled
        # 2. Outlier (1000) should be removed
        # 3. Values should be normalized
        self.assertEqual(len(result), 9)  # Outlier removed
        self.assertTrue(result['value'].notna().all())  # No missing values
        
        # Check normalization (values between 0 and 1)
        self.assertTrue((result['value'] >= 0).all() and (result['value'] <= 1).all())

