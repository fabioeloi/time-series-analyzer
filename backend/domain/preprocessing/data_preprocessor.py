import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union, Any


class DataPreprocessor:
    """
    Domain class responsible for preprocessing time series data
    """
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        """
        Initialize the data preprocessor with optional data
        
        Parameters:
        -----------
        data : pd.DataFrame, optional
            Initial dataframe to process
        """
        self.data = data.copy() if data is not None else None
    
    def set_data(self, data: pd.DataFrame) -> None:
        """
        Set the data to be processed
        
        Parameters:
        -----------
        data : pd.DataFrame
            Dataframe to process
        """
        if data is None or data.empty:
            raise ValueError("Cannot set empty data")
            
        self.data = data.copy()
    
    def handle_missing_values(self, 
                            columns: List[str] = None,
                            method: str = 'ffill', 
                            limit: Optional[int] = None) -> pd.DataFrame:
        """
        Handle missing values in the dataset
        
        Parameters:
        -----------
        columns : List[str], optional
            List of column names to process, if None all columns are processed
        method : str, default 'ffill'
            Method to fill missing values:
            - 'ffill': forward fill
            - 'bfill': backward fill
            - 'mean': fill with mean of column
            - 'median': fill with median of column
            - 'mode': fill with most common value
            - 'constant': fill with value provided in 'value' parameter
        limit : int, optional
            Maximum number of consecutive NaNs to fill
            
        Returns:
        --------
        pd.DataFrame
            Processed dataframe
        """
        if self.data is None:
            raise ValueError("Data not set. Call set_data before processing.")
        
        result = self.data.copy()
        
        # If no columns specified, use all columns
        if columns is None:
            columns = result.columns
        
        for col in columns:
            if col not in result.columns:
                continue
                
            if method == 'ffill':
                result[col] = result[col].fillna(method='ffill', limit=limit)
                
            elif method == 'bfill':
                result[col] = result[col].fillna(method='bfill', limit=limit)
                
            elif method == 'mean':
                if pd.api.types.is_numeric_dtype(result[col]):
                    result[col] = result[col].fillna(result[col].mean())
                    
            elif method == 'median':
                if pd.api.types.is_numeric_dtype(result[col]):
                    result[col] = result[col].fillna(result[col].median())
                    
            elif method == 'mode':
                # Get the first mode if there are multiple modes
                mode_value = result[col].mode().iloc[0] if not result[col].mode().empty else None
                if mode_value is not None:
                    result[col] = result[col].fillna(mode_value)
                    
            elif method == 'constant' and 'value' in locals():
                result[col] = result[col].fillna(value)
                
        return result
    
    def remove_outliers(self, 
                      columns: List[str] = None, 
                      method: str = 'iqr', 
                      threshold: float = 1.5) -> pd.DataFrame:
        """
        Remove or replace outliers in the dataset
        
        Parameters:
        -----------
        columns : List[str], optional
            List of column names to process, if None all numeric columns are used
        method : str, default 'iqr'
            Method to identify outliers:
            - 'iqr': Interquartile Range method
            - 'zscore': Z-score method
            - 'percentile': Remove values outside specified percentile range
        threshold : float, default 1.5
            Threshold for outlier detection:
            - For IQR method: multiple of IQR to define outliers
            - For Z-score method: standard deviations to define outliers
            
        Returns:
        --------
        pd.DataFrame
            DataFrame with outliers removed
        """
        if self.data is None:
            raise ValueError("Data not set. Call set_data before processing.")
            
        result = self.data.copy()
        
        # If no columns specified, use all numeric columns
        if columns is None:
            columns = result.select_dtypes(include=[np.number]).columns.tolist()
        else:
            # Filter out non-numeric columns from the provided list
            columns = [col for col in columns if col in result.columns and 
                      pd.api.types.is_numeric_dtype(result[col])]
        
        if method == 'iqr':
            for col in columns:
                Q1 = result[col].quantile(0.25)
                Q3 = result[col].quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR

                # Keep values within [lower_bound, upper_bound] or NaN; drop true outliers
                mask_in_bounds = (result[col] >= lower_bound) & (result[col] <= upper_bound)
                mask_is_nan = result[col].isna()
                result = result[mask_in_bounds | mask_is_nan]
                
        elif method == 'zscore':
            for col in columns:
                # Calculate z-scores
                mean = result[col].mean()
                std = result[col].std()
                
                if std > 0:  # Avoid division by zero
                    z_scores = abs((result[col] - mean) / std)
                    # Filter out outliers based on z-score threshold
                    result = result[(z_scores <= threshold) | (result[col].isna())]
                
        elif method == 'percentile':
            for col in columns:
                lower_percentile = (1 - threshold) / 2
                upper_percentile = 1 - lower_percentile

                lower_bound = result[col].quantile(lower_percentile)
                upper_bound = result[col].quantile(upper_percentile)

                # Keep values within percentile bounds or NaN
                mask_in_bounds = (result[col] >= lower_bound) & (result[col] <= upper_bound)
                mask_is_nan = result[col].isna()
                result = result[mask_in_bounds | mask_is_nan]
                
        return result
    
    def normalize_data(self, 
                     columns: List[str] = None,
                     method: str = 'minmax') -> pd.DataFrame:
        """
        Normalize data in specified columns
        
        Parameters:
        -----------
        columns : List[str], optional
            List of column names to normalize, if None all numeric columns are used
        method : str, default 'minmax'
            Normalization method:
            - 'minmax': Scale to range [0, 1]
            - 'zscore': Standardize to mean=0, std=1
            - 'robust': Scale based on median and quantiles
            - 'log': Apply natural logarithm transformation
            
        Returns:
        --------
        pd.DataFrame
            Normalized dataframe
        """
        if self.data is None:
            raise ValueError("Data not set. Call set_data before processing.")
            
        result = self.data.copy()
        
        # If no columns specified, use all numeric columns
        if columns is None:
            columns = result.select_dtypes(include=[np.number]).columns.tolist()
        else:
            # Filter out non-numeric columns from the provided list
            columns = [col for col in columns if col in result.columns and 
                      pd.api.types.is_numeric_dtype(result[col])]
        
        for col in columns:
            if method == 'minmax':
                col_min = result[col].min()
                col_max = result[col].max()
                
                if col_max > col_min:  # Avoid division by zero
                    result[col] = (result[col] - col_min) / (col_max - col_min)
                else:
                    # If all values are the same, set to 0 or 0.5
                    result[col] = 0 if col_min == 0 else 0.5
                    
            elif method == 'zscore':
                mean = result[col].mean()
                std = result[col].std()
                
                if std > 0:  # Avoid division by zero
                    result[col] = (result[col] - mean) / std
                    
            elif method == 'robust':
                median = result[col].median()
                q1 = result[col].quantile(0.25)
                q3 = result[col].quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:  # Avoid division by zero
                    result[col] = (result[col] - median) / iqr
                    
            elif method == 'log':
                # Handle zero or negative values by adding a small constant
                if (result[col] <= 0).any():
                    min_val = result[col].min()
                    offset = abs(min_val) + 1 if min_val <= 0 else 0
                    result[col] = np.log(result[col] + offset)
                else:
                    result[col] = np.log(result[col])
                    
        return result
    
    def resample_time_series(self,
                           time_column: str,
                           value_columns: List[str],
                           freq: str = 'D', 
                           agg_func: str = 'mean') -> pd.DataFrame:
        """
        Resample time series data to a specified frequency
        
        Parameters:
        -----------
        time_column : str
            Name of the datetime column
        value_columns : List[str]
            List of column names containing the values to resample
        freq : str, default 'D'
            Frequency string (e.g. 'D' for daily, 'M' for monthly)
        agg_func : str, default 'mean'
            Aggregation function for resampling:
            - 'mean': Average of values
            - 'sum': Sum of values
            - 'median': Median of values
            - 'min': Minimum value
            - 'max': Maximum value
            
        Returns:
        --------
        pd.DataFrame
            Resampled dataframe
        """
        if self.data is None:
            raise ValueError("Data not set. Call set_data before processing.")
            
        # Make a copy to avoid modifying the original data
        df = self.data.copy()
        
        # Ensure the time column is datetime type
        if time_column not in df.columns:
            raise ValueError(f"Time column '{time_column}' not found in data")
            
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_dtype(df[time_column]):
            try:
                df[time_column] = pd.to_datetime(df[time_column])
            except Exception as e:
                raise ValueError(f"Could not convert '{time_column}' to datetime: {str(e)}")
                
        # Check that all value columns exist
        missing_cols = [col for col in value_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Value columns not found in data: {missing_cols}")
            
        # Set the time column as index
        df = df.set_index(time_column)
        
        # Select only the value columns we want to resample
        df = df[value_columns]
        
        # Map string aggregate function to the actual function
        agg_map = {
            'mean': np.mean,
            'sum': np.sum,
            'median': np.median,
            'min': np.min,
            'max': np.max
        }
        
        agg_function = agg_map.get(agg_func.lower(), np.mean)
        
        # Resample the data
        resampled = df.resample(freq).agg(agg_function)
        
        # Reset index to make the time column a regular column again
        resampled = resampled.reset_index()
        
        return resampled