from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd

class TimeSeriesRequestDTO(BaseModel):
    """Data transfer object for time series requests"""
    dataframe: Any  # pandas DataFrame (not directly serializable by Pydantic)
    time_column: Optional[str] = None
    value_columns: Optional[List[str]] = None
    
    class Config:
        arbitrary_types_allowed = True

class TimeSeriesResponseDTO(BaseModel):
    """Data transfer object for time series responses"""
    analysis_id: str
    columns: List[str]
    time_column: str
    value_columns: List[str]
    time_domain: Optional[Dict[str, Any]] = None
    frequency_domain: Optional[Dict[str, Any]] = None