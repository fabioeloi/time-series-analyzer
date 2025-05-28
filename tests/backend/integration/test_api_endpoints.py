import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
import json

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "backend"))

# Import app from main.py
from main import app, get_time_series_service # Import get_time_series_service for override
from application.services.time_series_service import TimeSeriesService
from domain.models.time_series import TimeSeries
from interfaces.dto.time_series_dto import TimeSeriesResponseDTO # TimeSeriesColumnsDTO is not defined here

# Mock the API_KEY environment variable for all tests in this file
@pytest.fixture(autouse=True)
def mock_api_key_env():
    with patch.dict(os.environ, {"API_KEY": "test-api-key-12345"}):
        yield

@pytest.fixture
def client():
    """Fixture for a TestClient instance."""
    return TestClient(app)

@pytest.fixture
def mock_time_series_service():
    """Fixture for mocking the TimeSeriesService."""
    mock_service = MagicMock(spec=TimeSeriesService)
    mock_service.process_time_series = AsyncMock()
    mock_service.get_analysis_result = AsyncMock(return_value=None) # Default to not found
    mock_service.delete_time_series = AsyncMock(return_value=False) # Default to not found
    mock_service.get_all_analysis_ids = AsyncMock(return_value=[]) # Default to empty list
    
    # Mock the repository attribute on the service mock
    mock_service.repository = MagicMock()
    mock_service.repository.find_all = AsyncMock(return_value=[])
    mock_service.repository.find_by_id = AsyncMock(return_value=None)
    return mock_service

@pytest.fixture(autouse=True)
def override_dependencies(mock_time_series_service):
    """Override dependencies with mocks for API tests."""
    app.dependency_overrides[get_time_series_service] = lambda: mock_time_series_service
    yield
    app.dependency_overrides = {} # Clear overrides after test

# Removed mock_columns_dto fixture as TimeSeriesColumnsDTO is not used directly in TimeSeriesResponseDTO

@pytest.mark.asyncio
class TestAPIEndpoints:
    async def test_upload_csv_success(self, client, mock_time_series_service):
        """Test successful CSV upload and processing."""
        csv_content = "timestamp,value1,value2\n2023-01-01,10,20\n2023-01-02,15,25"
        
        # Mock the service response
        mock_response_dto = TimeSeriesResponseDTO(
            analysis_id="mock-analysis-id",
            time_column="timestamp",
            value_columns=["value1", "value2"],
            columns=["timestamp", "value1", "value2"], # Provide as List[str]
            time_domain={"time": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"], "series": {"value1": [10, 15], "value2": [20, 25]}},
            frequency_domain=None,
            # message="Successfully processed" # Message is not part of TimeSeriesResponseDTO
        )
        mock_time_series_service.process_time_series.return_value = mock_response_dto

        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"},
            files={"file": ("test.csv", csv_content, "text/csv")},
            params={"time_column": "timestamp", "value_columns": ["value1", "value2"]} 
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_id"] == "mock-analysis-id"
        assert response_json["time_column"] == "timestamp"
        assert set(response_json["value_columns"]) == set(["value1", "value2"])
        assert set(response_json["columns"]) == set(["timestamp", "value1", "value2"])
        assert "time_domain" in response_json
        mock_time_series_service.process_time_series.assert_called_once()

    async def test_upload_csv_no_file(self, client):
        """Test CSV upload without a file."""
        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"},
            params={"time_column": "timestamp", "value_columns": ["value1", "value2"]}
        )
        assert response.status_code == 422 

    async def test_upload_csv_invalid_format(self, client):
        """Test CSV upload with invalid format (e.g., not CSV)."""
        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"},
            files={"file": ("test.txt", "not a csv", "text/plain")},
            params={"time_column": "timestamp", "value_columns": ["value1", "value2"]}
        )
        assert response.status_code == 400 

    async def test_get_analysis_result_time_domain_success(self, client, mock_time_series_service):
        """Test retrieving time domain analysis results successfully."""
        analysis_id = "test-analysis-id"
        mock_time_domain_data = {
            "time": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
            "series": {"value1": [10, 15], "value2": [20, 25]}
        }
        mock_response_dto = TimeSeriesResponseDTO(
            analysis_id=analysis_id,
            time_column="timestamp",
            value_columns=["value1", "value2"],
            columns=["timestamp", "value1", "value2"], # Provide as List[str]
            time_domain=mock_time_domain_data,
            frequency_domain=None,
            # message="Found" # Message is not part of TimeSeriesResponseDTO
        )
        mock_time_series_service.get_analysis_result.return_value = mock_response_dto

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_id"] == analysis_id
        assert response_json["time_domain"] == mock_time_domain_data
        assert response_json["frequency_domain"] is None
        assert set(response_json["columns"]) == set(["timestamp", "value1", "value2"])
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_get_analysis_result_frequency_domain_success(self, client, mock_time_series_service):
        """Test retrieving frequency domain analysis results successfully."""
        analysis_id = "test-analysis-id"
        mock_frequency_domain_data = {
            "frequencies": {"value1": [1.0, 2.0], "value2": [3.0, 4.0]}, 
            "amplitudes": {"value1": [0.1, 0.2], "value2": [0.3, 0.4]}
        }
        mock_response_dto = TimeSeriesResponseDTO(
            analysis_id=analysis_id,
            time_column="timestamp",
            value_columns=["value1", "value2"],
            columns=["timestamp", "value1", "value2"], # Provide as List[str]
            time_domain=None,
            frequency_domain=mock_frequency_domain_data,
            # message="Found" # Message is not part of TimeSeriesResponseDTO
        )
        mock_time_series_service.get_analysis_result.return_value = mock_response_dto

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=frequency",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_id"] == analysis_id
        assert response_json["time_domain"] is None
        assert response_json["frequency_domain"] == mock_frequency_domain_data
        assert set(response_json["columns"]) == set(["timestamp", "value1", "value2"])
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "frequency")

    async def test_get_analysis_result_not_found(self, client, mock_time_series_service):
        """Test retrieving analysis results for a non-existent ID."""
        analysis_id = "non-existent-id"
        mock_time_series_service.get_analysis_result.return_value = None 

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 404
        assert f"Analysis with ID '{analysis_id}' not found" in response.json()["detail"]
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_get_analysis_result_invalid_domain(self, client, mock_time_series_service):
        """Test retrieving analysis results with an invalid domain parameter."""
        analysis_id = "some-id-for-domain-test"

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=invalid", 
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 422 
        mock_time_series_service.get_analysis_result.assert_not_called()


    async def test_export_csv_success(self, client, mock_time_series_service):
        """Test successful CSV export."""
        analysis_id = "test-export-id"
        mock_response_dto = TimeSeriesResponseDTO(
            analysis_id=analysis_id,
            time_column="timestamp",
            value_columns=["value1", "value2"],
            columns=["timestamp", "value1", "value2"], # Provide as List[str]
            time_domain={
                "time": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"], 
                "series": {"value1": [10, 15], "value2": [20, 25]}
            },
            frequency_domain=None,
            # message="Export data" # Message is not part of TimeSeriesResponseDTO
        )
        mock_time_series_service.get_analysis_result.return_value = mock_response_dto

        response = client.get(
            f"/api/export/{analysis_id}?format=csv&domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert f"time_series_analysis_{analysis_id}_time.csv" in response.headers["content-disposition"]
        
        expected_csv_content = "timestamp,value1,value2\r\n" \
                               "2023-01-01T00:00:00,10,20\r\n" \
                               "2023-01-02T00:00:00,15,25\r\n"
        assert response.text == expected_csv_content
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_export_csv_not_found(self, client, mock_time_series_service):
        """Test CSV export for a non-existent ID."""
        analysis_id = "non-existent-export-id"
        mock_time_series_service.get_analysis_result.return_value = None

        response = client.get(
            f"/api/export/{analysis_id}?format=csv&domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 404
        assert f"Analysis for export with ID '{analysis_id}' not found" in response.json()["detail"]
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_delete_analysis_success(self, client, mock_time_series_service):
        """Test successful deletion of an analysis."""
        analysis_id = "test-delete-id"
        mock_time_series_service.delete_time_series.return_value = True

        response = client.delete(
            f"/api/analyze/{analysis_id}",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200 
        assert response.json() == {"message": "Analysis deleted successfully", "analysis_id": analysis_id}
        mock_time_series_service.delete_time_series.assert_called_once_with(analysis_id)

    async def test_delete_analysis_not_found(self, client, mock_time_series_service):
        """Test deletion of a non-existent analysis."""
        analysis_id = "non-existent-delete-id"
        mock_time_series_service.delete_time_series.return_value = False 

        response = client.delete(
            f"/api/analyze/{analysis_id}",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 404 
        assert "Analysis not found for deletion." in response.json()["detail"]
        mock_time_series_service.delete_time_series.assert_called_once_with(analysis_id)

    async def test_get_all_analysis_ids_success(self, client, mock_time_series_service):
        """Test retrieving all analysis IDs successfully."""
        mock_ids = ["id1", "id2", "id3"]
        mock_time_series_service.get_all_analysis_ids.return_value = mock_ids

        response = client.get(
            "/api/analyses/", 
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.json() == mock_ids 
        mock_time_series_service.get_all_analysis_ids.assert_called_once()

    async def test_get_all_analysis_ids_empty(self, client, mock_time_series_service):
        """Test retrieving all analysis IDs when none exist."""
        mock_time_series_service.get_all_analysis_ids.return_value = []

        response = client.get(
            "/api/analyses/", 
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.json() == [] 
        mock_time_series_service.get_all_analysis_ids.assert_called_once()

    async def test_diagnostic_endpoint_success(self, client, mock_time_series_service):
        """Test the diagnostic endpoint."""
        mock_repo = MagicMock()
        mock_analysis_1 = MagicMock()
        mock_analysis_1.id = "id1"
        mock_analysis_2 = MagicMock()
        mock_analysis_2.id = "id2"
        mock_repo.find_all = AsyncMock(return_value=[mock_analysis_1, mock_analysis_2])
        
        mock_repo.find_by_id = AsyncMock(return_value=None) 
        mock_time_series_service.repository = mock_repo
        
        response = client.get("/api/diagnostic")
        assert response.status_code == 200
        response_json = response.json()
        
        assert "storage_info" in response_json
        assert "available_analyses" in response_json
        assert response_json["available_analyses"] == ["id1", "id2"]
        
        assert response_json["storage_info"]["repository_type"] == "MagicMock"
        assert response_json["storage_info"]["database_backend"] == "File-based" 
        
        mock_repo.find_all.assert_called_once()


    async def test_diagnostic_endpoint_with_id_found(self, client, mock_time_series_service):
        """Test the diagnostic endpoint with a specific ID that is found."""
        analysis_id = "found-id"
        
        mock_analysis_obj = MagicMock(spec=TimeSeries)
        mock_analysis_obj.id = analysis_id
        mock_analysis_obj.time_column = "ts_col"
        mock_analysis_obj.value_columns = ["val_col1"]
        mock_analysis_obj.data = pd.DataFrame({"ts_col": [pd.Timestamp("2023-01-01")], "val_col1": [10]})


        mock_repo = MagicMock()
        mock_repo.find_all = AsyncMock(return_value=[mock_analysis_obj]) 
        mock_repo.find_by_id = AsyncMock(return_value=mock_analysis_obj)
        mock_time_series_service.repository = mock_repo

        response = client.get(f"/api/diagnostic?analysis_id={analysis_id}")
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_found"] is True
        assert response_json["analysis_details"]["id"] == analysis_id
        assert response_json["analysis_details"]["time_column"] == "ts_col"
        assert response_json["analysis_details"]["value_columns"] == ["val_col1"]
        assert response_json["analysis_details"]["data_columns"] == ["ts_col", "val_col1"]
        assert response_json["analysis_details"]["data_length"] == 1
        mock_repo.find_by_id.assert_called_once_with(analysis_id)


    async def test_health_endpoint_success(self, client):
        """Test the health endpoint."""
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}