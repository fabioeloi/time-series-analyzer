import sys
import os
import pandas as pd
import numpy as np
import pytest
from pathlib import Path

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from domain.preprocessing.data_preprocessor import DataPreprocessor
from domain.models.time_series import TimeSeries
import unittest


class TestDataPreprocessor(unittest.TestCase):
    
    def setUp(self):
        # Setup test data
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        data = {
            'date': dates,
            'value': [10, 20, None, 40, 50, None, None, 80, 90, 1000],  # Added outlier 1000
            'category': ['A', 'B', None, 'A', 'B', None, 'C', 'A', 'B', 'C']
        }
        self.test_df = pd.DataFrame(data)
        self.preprocessor = DataPreprocessor(self.test_df)
        
    def test_handle_missing_values_ffill(self):
        result = self.preprocessor.handle_missing_values(method='ffill')
        # Check that numeric values were forward filled
        self.assertEqual(result['value'].iloc[2], 20)
        self.assertEqual(result['value'].iloc[5], 50)
        self.assertEqual(result['value'].iloc[6], 50)
        
        # Check that categorical values were also filled
        self.assertEqual(result['category'].iloc[2], 'B')
        
    def test_handle_missing_values_mean(self):
        result = self.preprocessor.handle_missing_values(columns=['value'], method='mean')
        # The mean of [10, 20, 40, 50, 80, 90, 1000] is approximately 184.29
        mean_value = self.test_df['value'].mean()
        self.assertAlmostEqual(result['value'].iloc[2], mean_value, places=1)
        
        # Check that only specified columns were processed
        self.assertIsNone(result['category'].iloc[2])
        
    def test_remove_outliers_iqr(self):
        result = self.preprocessor.remove_outliers(method='iqr', threshold=1.5)
        # We expect the outlier value 1000 to be removed
        self.assertEqual(len(result), 9)
        self.assertNotIn(1000, result['value'].values)
        
    def test_normalize_data_minmax(self):
        result = self.preprocessor.normalize_data(columns=['value'], method='minmax')
        # After min-max normalization, values should be between 0 and 1
        non_null_values = result['value'].dropna()
        self.assertTrue((non_null_values >= 0).all())
        self.assertTrue((non_null_values <= 1).all())
        
        # Check min value is 0 and max value is 1
        self.assertEqual(result['value'].min(), 0)
        self.assertEqual(result['value'].max(), 1)
        
    def test_normalize_data_zscore(self):
        result = self.preprocessor.normalize_data(columns=['value'], method='zscore')
        # After z-score normalization, mean should be near 0 and std dev near 1
        mean_value = result['value'].mean()
        std_value = result['value'].std()
        
        # Allow for some floating point imprecision
        self.assertAlmostEqual(mean_value, 0, places=1)
        self.assertAlmostEqual(std_value, 1, places=1)
        
    def test_resample_time_series(self):
        # First create a sample with hourly data
        dates = pd.date_range(start='2023-01-01', periods=48, freq='H')
        data = {
            'timestamp': dates,
            'temperature': np.sin(np.linspace(0, 4*np.pi, 48)) * 10 + 20,  # Sinusoidal data
            'humidity': np.random.randint(30, 70, size=48)
        }
        hourly_df = pd.DataFrame(data)
        
        # Test resampling from hourly to 6-hourly
        preprocessor = DataPreprocessor(hourly_df)
        result = preprocessor.resample_time_series(
            time_column='timestamp',
            value_columns=['temperature', 'humidity'],
            freq='6H',
            agg_func='mean'
        )
        
        # Check result shape (expect 48/6 = 8 rows)
        self.assertEqual(len(result), 8)
        self.assertIn('timestamp', result.columns)
        self.assertIn('temperature', result.columns)
        self.assertIn('humidity', result.columns)


if __name__ == '__main__':
    unittest.main()