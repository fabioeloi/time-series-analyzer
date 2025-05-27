from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
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
from infrastructure.repositories.time_series_repository import TimeSeriesRepository
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO, TimeSeriesResponseDTO
from infrastructure.auth.api_key_auth import get_api_key_dependency

app = FastAPI(title="Time Series Analyzer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection - create repository and inject into service
time_series_repository = TimeSeriesRepository()
time_series_service = TimeSeriesService(time_series_repository)

@app.post("/api/upload-csv/", response_model=TimeSeriesResponseDTO)
async def upload_csv(file: UploadFile = File(...),
                     time_column: Optional[str] = None,
                     value_columns: Optional[List[str]] = None,
                     api_key: str = get_api_key_dependency()):
    """
    Upload a CSV file for time series analysis.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    try:
        contents = await file.read()
        # Read the CSV, ensuring empty column names are properly handled
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')), low_memory=False)
        
        # Verify that the specified columns actually exist in the dataframe
        all_columns = df.columns.tolist()
        
        if time_column and time_column not in all_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Time column '{time_column}' not found in data. Available columns: {', '.join(all_columns)}"
            )
        
        if value_columns:
            invalid_columns = [col for col in value_columns if col not in all_columns]
            if invalid_columns:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Column(s) {', '.join(invalid_columns)} not found in data. Available columns: {', '.join(all_columns)}"
                )
        
        # Provide info about available columns if none are specified
        if time_column is None and value_columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            available_cols = {
                "all_columns": all_columns,
                "numeric_columns": numeric_cols,
                "suggested_time_column": all_columns[0] if all_columns else None,
                "suggested_value_columns": numeric_cols
            }
            return JSONResponse(content={
                "message": "No columns specified. Here are the available columns:",
                "columns": available_cols
            })
        
        # Create DTO for service request
        request_dto = TimeSeriesRequestDTO(
            dataframe=df,
            time_column=time_column,
            value_columns=value_columns
        )
        
        # Process the time series data
        result = time_series_service.process_time_series(request_dto)
        return result
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log unexpected errors
        import traceback
        print(f"Error processing CSV: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.get("/api/analyze/{analysis_id}", response_model=TimeSeriesResponseDTO)
async def get_analysis(analysis_id: str, domain: str = "time", api_key: str = get_api_key_dependency()):
    """
    Retrieve time series analysis results.
    Domain can be 'time' or 'frequency'.
    """
    try:
        result = time_series_service.get_analysis_result(analysis_id, domain)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {str(e)}")

@app.get("/api/diagnostic")
async def diagnostic(analysis_id: Optional[str] = None):
    """
    Diagnostic endpoint to help troubleshoot issues with analysis IDs.
    Returns information about available analyses and storage status.
    """
    # Get the repository from the service
    repository = time_series_service.repository
    
    # Check the storage file
    storage_path = repository._storage_path
    storage_file = repository._storage_file
    backup_file = repository._backup_file
    
    storage_info = {
        "storage_path": storage_path,
        "storage_file": storage_file,
        "storage_file_exists": os.path.exists(storage_file),
        "storage_file_size": os.path.getsize(storage_file) if os.path.exists(storage_file) else 0,
        "backup_file": backup_file,
        "backup_file_exists": os.path.exists(backup_file),
        "data_directory_exists": os.path.exists(storage_path)
    }
    
    # Get list of available analysis IDs
    available_ids = repository.list_available_ids()
    
    result = {
        "storage_info": storage_info,
        "available_analyses": available_ids,
        "analysis_count": len(available_ids)
    }
    
    # If specific analysis ID was provided, check if it exists
    if analysis_id:
        analysis = repository.find_by_id(analysis_id)
        if analysis:
            result["analysis_found"] = True
            result["analysis_details"] = {
                "id": analysis.id,
                "time_column": analysis.time_column,
                "value_columns": analysis.value_columns,
                "data_columns": list(analysis.data.columns) if analysis.data is not None else [],
                "data_length": len(analysis.data) if analysis.data is not None else 0
            }
        else:
            result["analysis_found"] = False
            result["error"] = f"Analysis with ID {analysis_id} not found."
    
    return JSONResponse(content=result)

@app.get("/api/export/{analysis_id}")
async def export_analysis(analysis_id: str, format: str = "csv", domain: str = "time", api_key: str = get_api_key_dependency()):
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
async def health_check(api_key: str = get_api_key_dependency()):
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)