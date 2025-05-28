from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from scipy import signal
import uuid

@dataclass
class TimeSeries:
    """Domain model for time series data"""
    id: str
    data: pd.DataFrame
    time_column: str
    value_columns: List[str]
    
    @classmethod
    def create(cls, data: pd.DataFrame, time_column: Optional[str] = None, value_columns: Optional[List[str]] = None) -> 'TimeSeries':
        """Factory method to create a new TimeSeries"""
        # Generate a unique ID
        new_id = str(uuid.uuid4())
        
        # Validate that we don't have empty column names
        if "" in data.columns:
            # Remove or rename empty columns
            renamed_cols = {col: f"Column_{i}" if col == "" else col for i, col in enumerate(data.columns)}
            data = data.rename(columns=renamed_cols)
            
        # If time_column is not specified, attempt to use the first column
        if time_column is None:
            time_column = data.columns[0]
        
        # Handle empty time column name
        if time_column == "":
            raise ValueError(f"Time column name cannot be empty. Available columns: {', '.join(data.columns)}")
            
        # Ensure time column exists
        if time_column not in data.columns:
            raise ValueError(f"Time column '{time_column}' not found in data. Available columns: {', '.join(data.columns)}")
            
        # Only convert to datetime if it's not already a numeric type
        if not pd.api.types.is_numeric_dtype(data[time_column]):
            # Try to convert time column to datetime with flexible parsing
            try:
                data[time_column] = pd.to_datetime(data[time_column], infer_datetime_format=True, errors='coerce')
                if data[time_column].isna().all():
                    raise ValueError(f"Could not parse any datetime values from column '{time_column}'")
            except Exception as e:
                raise ValueError(f"Error parsing time column '{time_column}': {str(e)}")

            # Ensure no NaT values in the time column
            if data[time_column].isna().any():
                raise ValueError(f"Time column '{time_column}' contains NaT values after parsing")

        # If value_columns are not specified, use all numeric columns except the time column
        if value_columns is None:
            value_columns = [col for col in data.select_dtypes(include=[np.number]).columns if col != time_column]
            if not value_columns:
                # Try to convert string columns to numeric
                for col in data.columns:
                    if col != time_column:
                        try:
                            data[col] = pd.to_numeric(data[col], errors='coerce')
                            if not data[col].isna().all():
                                value_columns.append(col)
                        except:
                            continue
        
        # Filter out any empty column names
        value_columns = [col for col in value_columns if col != ""]
                            
        # Validate value columns and convert to numeric where possible
        valid_value_columns = []
        for col in value_columns:
            if col not in data.columns:
                raise ValueError(f"Column '{col}' not found in data. Available columns: {', '.join(data.columns)}")
            
            # Try to convert to numeric if not already
            if not np.issubdtype(data[col].dtype, np.number):
                try:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
                except:
                    raise ValueError(f"Column '{col}' could not be converted to numeric data")
                    
            if not data[col].isna().all():
                valid_value_columns.append(col)
                
        if not valid_value_columns:
            raise ValueError("No valid numeric columns found for analysis")
            
        value_columns = valid_value_columns
            
        return cls(
            id=new_id,
            data=data,
            time_column=time_column,
            value_columns=value_columns
        )
    
    def get_time_domain_data(self) -> Dict[str, Any]:
        """Get data in time domain format"""
        result = {
            "time": self.data[self.time_column].tolist(),
            "series": {}
        }
        
        for col in self.value_columns:
            # Handle NaN values by replacing them with None
            result["series"][col] = [None if pd.isna(x) else float(x) for x in self.data[col]]
            
        return result
    
    def get_frequency_domain_data(self) -> Dict[str, Any]:
        """Transform data to frequency domain using FFT"""
        result = {
            "frequencies": {},
            "amplitudes": {}
        }
        
        try:
            # Calculate sample spacing from time data
            time_col = self.data[self.time_column]
            
            # Handle numeric or datetime time columns differently
            if pd.api.types.is_numeric_dtype(time_col):
                time_values = time_col
                # For test case with linspace time values, we need to use the actual time increment
                if len(time_values) > 2 and np.allclose(np.diff(time_values), np.diff(time_values).mean()):
                    # This is likely a linspace-generated array with consistent spacing
                    sample_spacing = np.diff(time_values).mean()
                else:
                    # Calculate spacing for irregular timestamps
                    sample_spacing = (time_values.iloc[-1] - time_values.iloc[0]) / (len(time_values) - 1)
            else:
                # Convert datetime to Unix timestamp
                time_values = pd.to_datetime(time_col).astype(np.int64) // 10**9
                sample_spacing = (time_values.iloc[-1] - time_values.iloc[0]) / (len(time_values) - 1)
            
            if len(time_values) < 2:
                raise ValueError("Not enough time points to calculate sample spacing")
                
            if sample_spacing == 0 or np.isclose(sample_spacing, 0):
                # Use a default sample spacing if the calculated value is too close to zero
                sample_spacing = 0.1  # Smaller default spacing to give higher frequencies
                
            # Ensure sample spacing is not zero by checking for unique time values
            if len(time_values.unique()) < 2:
                # If all time values are the same, use artificial spacing
                sample_spacing = 0.1
            
            for col in self.value_columns:
                # Perform FFT
                values = self.data[col].to_numpy()
                # Remove NaN values and interpolate
                mask = ~np.isnan(values)
                if not mask.all():
                    # If there are NaN values, interpolate them
                    x = np.arange(len(values))
                    values = np.interp(x, x[mask], values[mask])
                
                # Apply FFT
                fft_result = np.fft.fft(values)
                # Get the frequencies
                n = len(values)
                freqs = np.fft.fftfreq(n, sample_spacing)
                
                # Store positive frequencies and their magnitudes
                positive_mask = freqs > 0
                result["frequencies"][col] = freqs[positive_mask].tolist()
                result["amplitudes"][col] = np.abs(fft_result[positive_mask]).tolist()
                
            return result
        except Exception as e:
            raise ValueError(f"Error calculating frequency domain data: {str(e)}")
    
    def to_dto(self, domain: str = "time"):
        """Convert TimeSeries to TimeSeriesResponseDTO"""
        # Import here to avoid circular imports
        from interfaces.dto.time_series_dto import TimeSeriesResponseDTO
        
        # Prepare domain-specific data
        time_domain_data = None
        frequency_domain_data = None
        
        if domain == "time":
            time_domain_data = self.get_time_domain_data()
        elif domain == "frequency":
            frequency_domain_data = self.get_frequency_domain_data()
        elif domain == "both":
            # Support for both domains if needed
            time_domain_data = self.get_time_domain_data()
            frequency_domain_data = self.get_frequency_domain_data()
        else:
            raise ValueError(f"Invalid domain '{domain}'. Must be 'time', 'frequency', or 'both'")
        
        return TimeSeriesResponseDTO(
            analysis_id=self.id,
            columns=list(self.data.columns),
            time_column=self.time_column,
            value_columns=self.value_columns,
            time_domain=time_domain_data,
            frequency_domain=frequency_domain_data
        )