import pandas as pd
from typing import List, Dict, Any, Optional, Union
from domain.preprocessing import DataPreprocessor


class PreprocessingService:
    """
    Application service for preprocessing time series data
    """
    
    def __init__(self):
        """
        Initialize the preprocessing service
        """
        self.preprocessor = None
    
    def _get_preprocessor(self, data: pd.DataFrame = None) -> DataPreprocessor:
        """
        Get a data preprocessor instance with data set
        
        Parameters:
        -----------
        data : pd.DataFrame, optional
            Data to process
        
        Returns:
        --------
        DataPreprocessor
            A preprocessor instance with data set
        """
        if data is None:
            if self.preprocessor is None:
                raise ValueError("No data provided and no preprocessor initialized")
            return self.preprocessor
            
        return DataPreprocessor(data)
    
    def handle_missing_values(self,
                             data: pd.DataFrame,
                             columns: List[str] = None,
                             method: str = 'ffill',
                             limit: Optional[int] = None) -> pd.DataFrame:
        """
        Handle missing values in the dataset
        
        Parameters:
        -----------
        data : pd.DataFrame
            Data to process
        columns : List[str], optional
            List of column names to process
        method : str, default 'ffill'
            Method to fill missing values: 'ffill', 'bfill', 'mean', 'median', 'mode', 'constant'
        limit : int, optional
            Maximum number of consecutive NaNs to fill
        
        Returns:
        --------
        pd.DataFrame
            Processed dataframe
        """
        preprocessor = self._get_preprocessor(data)
        return preprocessor.handle_missing_values(columns=columns, method=method, limit=limit)
    
    def remove_outliers(self,
                      data: pd.DataFrame,
                      columns: List[str] = None,
                      method: str = 'iqr',
                      threshold: float = 1.5) -> pd.DataFrame:
        """
        Remove outliers from the dataset
        
        Parameters:
        -----------
        data : pd.DataFrame
            Data to process
        columns : List[str], optional
            List of column names to process
        method : str, default 'iqr'
            Method to identify outliers: 'iqr', 'zscore', 'percentile'
        threshold : float, default 1.5
            Threshold for outlier detection
        
        Returns:
        --------
        pd.DataFrame
            Dataframe with outliers removed
        """
        preprocessor = self._get_preprocessor(data)
        return preprocessor.remove_outliers(columns=columns, method=method, threshold=threshold)
    
    def normalize_data(self,
                     data: pd.DataFrame,
                     columns: List[str] = None,
                     method: str = 'minmax') -> pd.DataFrame:
        """
        Normalize data in specified columns
        
        Parameters:
        -----------
        data : pd.DataFrame
            Data to process
        columns : List[str], optional
            List of column names to normalize
        method : str, default 'minmax'
            Normalization method: 'minmax', 'zscore', 'robust', 'log'
        
        Returns:
        --------
        pd.DataFrame
            Normalized dataframe
        """
        preprocessor = self._get_preprocessor(data)
        return preprocessor.normalize_data(columns=columns, method=method)
    
    def resample_time_series(self,
                           data: pd.DataFrame,
                           time_column: str,
                           value_columns: List[str],
                           freq: str = 'D',
                           agg_func: str = 'mean') -> pd.DataFrame:
        """
        Resample time series data to a specified frequency
        
        Parameters:
        -----------
        data : pd.DataFrame
            Data to process
        time_column : str
            Name of the datetime column
        value_columns : List[str]
            List of column names containing values to resample
        freq : str, default 'D'
            Frequency string (e.g. 'D' for daily, 'M' for monthly)
        agg_func : str, default 'mean'
            Aggregation function: 'mean', 'sum', 'median', 'min', 'max'
        
        Returns:
        --------
        pd.DataFrame
            Resampled dataframe
        """
        preprocessor = self._get_preprocessor(data)
        return preprocessor.resample_time_series(
            time_column=time_column,
            value_columns=value_columns,
            freq=freq,
            agg_func=agg_func
        )
    
    def process_time_series_data(self,
                               data: pd.DataFrame,
                               operations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply a sequence of preprocessing operations to time series data
        
        Parameters:
        -----------
        data : pd.DataFrame
            Data to process
        operations : List[Dict[str, Any]]
            List of operations to apply, each with:
            - 'type': Operation type ('missing_values', 'outliers', 'normalize', 'resample')
            - 'params': Parameters for the operation
        
        Returns:
        --------
        pd.DataFrame
            Processed dataframe
        """
        result = data.copy()
        preprocessor = self._get_preprocessor(result)
        
        for op in operations:
            op_type = op.get('type')
            params = op.get('params', {})
            
            if op_type == 'missing_values':
                result = preprocessor.handle_missing_values(**params)
            
            elif op_type == 'outliers':
                result = preprocessor.remove_outliers(**params)
            
            elif op_type == 'normalize':
                result = preprocessor.normalize_data(**params)
            
            elif op_type == 'resample' and 'time_column' in params and 'value_columns' in params:
                result = preprocessor.resample_time_series(**params)
            
            # Update the preprocessor with the latest result
            preprocessor = DataPreprocessor(result)
        
        return result