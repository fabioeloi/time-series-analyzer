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
        
        # If time_column is not specified, attempt to use the first column
        if time_column is None:
            time_column = data.columns[0]
            
        # If value_columns are not specified, use all columns except the time column
        if value_columns is None:
            value_columns = [col for col in data.columns if col != time_column]
            
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
            result["series"][col] = self.data[col].tolist()
            
        return result
    
    def get_frequency_domain_data(self) -> Dict[str, Any]:
        """Transform data to frequency domain using FFT"""
        result = {
            "frequencies": {},
            "amplitudes": {}
        }
        
        # Calculate sample spacing from time data
        time_values = pd.to_numeric(self.data[self.time_column])
        sample_spacing = (time_values.iloc[-1] - time_values.iloc[0]) / (len(time_values) - 1)
        
        for col in self.value_columns:
            # Perform FFT
            values = self.data[col].to_numpy()
            # Remove NaN values
            values = values[~np.isnan(values)]
            
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