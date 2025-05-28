from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from scipy import signal
from fastapi.responses import JSONResponse, FileResponse # FileResponse might not be needed if we switch to in-memory for CSV
import io
from typing import List, Optional
import csv
import tempfile # May not be needed for CSV export if in-memory
import os # May not be needed for CSV export if in-memory
import logging
from enum import Enum

from domain.models.time_series import TimeSeries
from application.services.time_series_service import TimeSeriesService
from infrastructure.repositories.time_series_repository import TimeSeriesRepository
from infrastructure.database.repositories.time_series_db_repository import TimeSeriesDBRepository
from infrastructure.database.config import get_db, init_db, close_db
from interfaces.dto.time_series_dto import TimeSeriesRequestDTO, TimeSeriesResponseDTO
from infrastructure.auth.api_key_auth import get_api_key_dependency
from infrastructure.cache.redis_config import redis_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Time Series Analyzer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance (will be set during startup)
time_series_service = None

class AnalysisDomain(str, Enum):
    TIME = "time"
    FREQUENCY = "frequency"

class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    global time_series_service
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")

        try:
            logger.info("Initializing Redis connection...")
            await redis_manager.initialize()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Redis: {str(e)}")
            logger.warning("Redis connection not established. Caching will be disabled.")
        
        fallback_repository = TimeSeriesRepository()
        
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        time_series_service = TimeSeriesService(TimeSeriesRepository())
        logger.warning("Using file-based repository as fallback")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    try:
        logger.info("Shutting down Redis connection...")
        try:
            await redis_manager.close()
            logger.info("Redis connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")

        logger.info("Shutting down database connections...")
        await close_db()
        logger.info("Shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


async def get_time_series_service(db_session = Depends(get_db)) -> TimeSeriesService:
    """Dependency to get TimeSeriesService with database repository"""
    try:
        db_repository = TimeSeriesDBRepository(db_session)
        return TimeSeriesService(db_repository)
    except Exception as e:
        logger.warning(f"Database not available, using fallback: {str(e)}")
        return TimeSeriesService(TimeSeriesRepository())

@app.post("/api/upload-csv/", response_model=TimeSeriesResponseDTO)
async def upload_csv(file: UploadFile = File(...),
                     time_column: Optional[str] = Query(None), 
                     value_columns: Optional[List[str]] = Query(None), 
                     api_key: str = get_api_key_dependency(),
                     service: TimeSeriesService = Depends(get_time_series_service)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')), low_memory=False)
        
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
        
        if not time_column and not value_columns and not df.empty:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            available_cols_data = {
                "all_columns": all_columns,
                "numeric_columns": numeric_cols,
                "suggested_time_column": all_columns[0] if all_columns else None,
                "suggested_value_columns": numeric_cols
            }
            return JSONResponse(content={
                "message": "No columns specified. Here are the available columns:",
                "columns": available_cols_data 
            }, status_code=200) 

        if not time_column or not value_columns:
             raise HTTPException(status_code=400, detail="Both time_column and value_columns must be specified for analysis.")

        request_dto = TimeSeriesRequestDTO(
            dataframe=df,
            time_column=time_column,
            value_columns=value_columns
        )
        
        result = await service.process_time_series(request_dto)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Error processing CSV: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.get("/api/analyze/{analysis_id}", response_model=TimeSeriesResponseDTO)
async def get_analysis(analysis_id: str, domain: AnalysisDomain = AnalysisDomain.TIME,
                      api_key: str = get_api_key_dependency(),
                      service: TimeSeriesService = Depends(get_time_series_service)):
    try:
        result = await service.get_analysis_result(analysis_id, domain.value)
        if not result: 
            raise HTTPException(status_code=404, detail=f"Analysis with ID '{analysis_id}' not found.")
        return result
    except HTTPException: 
        raise
    except Exception as e: 
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

@app.delete("/api/analyze/{analysis_id}", status_code=200)
async def delete_analysis(analysis_id: str,
                          api_key: str = get_api_key_dependency(),
                          service: TimeSeriesService = Depends(get_time_series_service)):
    try:
        success = await service.delete_time_series(analysis_id)
        if not success:
            raise HTTPException(status_code=404, detail="Analysis not found for deletion.")
        return {"message": "Analysis deleted successfully", "analysis_id": analysis_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting analysis: {str(e)}")

@app.get("/api/analyses/", response_model=List[str])
async def get_all_analyses_ids(api_key: str = get_api_key_dependency(),
                               service: TimeSeriesService = Depends(get_time_series_service)):
    try:
        ids = await service.get_all_analysis_ids()
        return ids
    except Exception as e:
        logger.error(f"Error retrieving all analysis IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis IDs: {str(e)}")


@app.get("/api/diagnostic")
async def diagnostic(analysis_id: Optional[str] = None,
                    service: TimeSeriesService = Depends(get_time_series_service)):
    try:
        repository = service.repository
        repository_type = type(repository).__name__
        storage_info = {
            "repository_type": repository_type,
            "database_backend": "TimescaleDB" if "DB" in repository_type else "File-based"
        }
        
        if hasattr(repository, '_storage_path'):
            storage_path = repository._storage_path
            storage_file = repository._storage_file
            backup_file = repository._backup_file
            storage_info.update({
                "storage_path": str(storage_path),
                "storage_file": str(storage_file),
                "storage_file_exists": os.path.exists(storage_file),
                "storage_file_size": os.path.getsize(storage_file) if os.path.exists(storage_file) else 0,
                "backup_file": str(backup_file),
                "backup_file_exists": os.path.exists(backup_file),
                "data_directory_exists": os.path.exists(storage_path)
            })
        
        all_analyses_objects = await repository.find_all() 
        available_ids = [ts.id for ts in all_analyses_objects]
        
        result = {
            "storage_info": storage_info,
            "available_analyses": available_ids,
            "analysis_count": len(available_ids)
        }
        
        if analysis_id:
            analysis = await repository.find_by_id(analysis_id)
            if analysis:
                result["analysis_found"] = True
                data_cols = []
                data_len = 0
                if analysis.data is not None:
                    try:
                        data_cols = list(analysis.data.columns)
                        data_len = len(analysis.data)
                    except Exception:
                        pass

                result["analysis_details"] = {
                    "id": str(analysis.id) if analysis.id else None,
                    "time_column": str(analysis.time_column) if analysis.time_column else None,
                    "value_columns": [str(vc) for vc in analysis.value_columns] if analysis.value_columns else [],
                    "data_columns": data_cols,
                    "data_length": data_len
                }
            else:
                result["analysis_found"] = False
                result["error"] = f"Analysis with ID {analysis_id} not found."
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in diagnostic endpoint: {str(e)}")
        return JSONResponse(content={"error": f"Diagnostic failed: {str(e)}"}, status_code=500)

@app.get("/api/export/{analysis_id}")
async def export_analysis(analysis_id: str, 
                         format: ExportFormat = ExportFormat.CSV, 
                         domain: AnalysisDomain = AnalysisDomain.TIME, 
                         api_key: str = get_api_key_dependency(),
                         service: TimeSeriesService = Depends(get_time_series_service)):
    try:
        result_dto = await service.get_analysis_result(analysis_id, domain.value)
        if not result_dto: 
             raise HTTPException(status_code=404, detail=f"Analysis for export with ID '{analysis_id}' not found.")

        if format == ExportFormat.JSON:
            return result_dto
        
        elif format == ExportFormat.CSV:
            output = io.StringIO()
            writer = csv.writer(output)
            
            if domain == AnalysisDomain.TIME and result_dto.time_domain:
                header = [result_dto.time_column] + result_dto.value_columns
                writer.writerow(header)
                time_data = result_dto.time_domain["time"]
                for i in range(len(time_data)):
                    row = [time_data[i]]
                    for col_val in result_dto.value_columns:
                        row.append(result_dto.time_domain["series"][col_val][i])
                    writer.writerow(row)
            
            elif domain == AnalysisDomain.FREQUENCY and result_dto.frequency_domain:
                for col_name in result_dto.value_columns:
                    writer.writerow([f"{col_name}_frequency", f"{col_name}_amplitude"])
                    freqs = result_dto.frequency_domain["frequencies"][col_name] 
                    amps = result_dto.frequency_domain["amplitudes"][col_name]   
                    for i in range(len(freqs)):
                        writer.writerow([freqs[i], amps[i]])
                    writer.writerow([]) # Add an empty row between series for readability
            
            csv_content = output.getvalue()
            output.close()
            
            filename = f"time_series_analysis_{analysis_id}_{domain.value}.csv"
            headers = {
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
            return Response(content=csv_content, media_type="text/csv", headers=headers)
            
    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"Export failed for analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)