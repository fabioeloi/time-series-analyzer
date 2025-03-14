from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from scipy import signal
from fastapi.responses import JSONResponse, FileResponse
import io
from typing import List, Optional
import csv
import tempfile
import os

from domain.models.time_series import TimeSeries
from application.services.time_series_service import TimeSeriesService
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO, TimeSeriesResponseDTO

app = FastAPI(title="Time Series Analyzer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

time_series_service = TimeSeriesService()

@app.post("/api/upload-csv/", response_model=TimeSeriesResponseDTO)
async def upload_csv(file: UploadFile = File(...), 
                     time_column: Optional[str] = None,
                     value_columns: Optional[List[str]] = None):
    """
    Upload a CSV file for time series analysis.
    """
    if file.filename.endswith('.csv'):
        try:
            contents = await file.read()
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            
            # Create DTO for service request
            request_dto = TimeSeriesRequestDTO(
                dataframe=df,
                time_column=time_column,
                value_columns=value_columns
            )
            
            # Process the time series data
            result = time_series_service.process_time_series(request_dto)
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

@app.get("/api/analyze/{analysis_id}", response_model=TimeSeriesResponseDTO)
async def get_analysis(analysis_id: str, domain: str = "time"):
    """
    Retrieve time series analysis results.
    Domain can be 'time' or 'frequency'.
    """
    try:
        result = time_series_service.get_analysis_result(analysis_id, domain)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {str(e)}")

@app.get("/api/export/{analysis_id}")
async def export_analysis(analysis_id: str, format: str = "csv", domain: str = "time"):
    """
    Export time series analysis data in various formats.
    Format can be 'csv' or 'json'.
    Domain can be 'time' or 'frequency'.
    """
    try:
        # Get the analysis result
        result = time_series_service.get_analysis_result(analysis_id, domain)
        
        if format.lower() == "json":
            # Return the data as JSON
            return result
        
        elif format.lower() == "csv":
            # Create a temporary file for the CSV
            fd, path = tempfile.mkstemp(suffix='.csv')
            try:
                with os.fdopen(fd, 'w', newline='') as tmp:
                    # Create CSV writer
                    writer = csv.writer(tmp)
                    
                    # Determine which data to export based on domain
                    if domain == "time" and result.time_domain:
                        # Write header
                        header = [result.time_column] + result.value_columns
                        writer.writerow(header)
                        
                        # Write rows
                        time_data = result.time_domain["time"]
                        for i in range(len(time_data)):
                            row = [time_data[i]]
                            for col in result.value_columns:
                                row.append(result.time_domain["series"][col][i])
                            writer.writerow(row)
                    
                    elif domain == "frequency" and result.frequency_domain:
                        # For each column, write frequency and amplitude
                        for col in result.value_columns:
                            writer.writerow([f"{col}_frequency", f"{col}_amplitude"])
                            freqs = result.frequency_domain["frequencies"][col]
                            amps = result.frequency_domain["amplitudes"][col]
                            for i in range(len(freqs)):
                                writer.writerow([freqs[i], amps[i]])
                            writer.writerow([])  # Empty row between columns
                
                # Return the CSV file
                return FileResponse(
                    path=path,
                    filename=f"time_series_analysis_{analysis_id}_{domain}.csv",
                    media_type="text/csv"
                )
            
            except Exception as e:
                # Clean up temp file in case of error
                os.unlink(path)
                raise e
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Export failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)