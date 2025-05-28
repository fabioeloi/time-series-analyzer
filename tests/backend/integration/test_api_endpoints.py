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
from main import app
from application.services.time_series_service import TimeSeriesService
from domain.models.time_series import TimeSeries

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
    mock_service.get_analysis_result = AsyncMock()
    mock_service.delete_time_series = AsyncMock()
    mock_service.get_all_analysis_ids = AsyncMock()
    return mock_service

@pytest.fixture(autouse=True)
def override_time_series_service(mock_time_series_service):
    """Override the TimeSeriesService dependency with a mock."""
    app.dependency_overrides[TimeSeriesService] = lambda: mock_time_series_service
    yield
    app.dependency_overrides = {} # Clear overrides after test

@pytest.mark.asyncio
class TestAPIEndpoints:
    async def test_upload_csv_success(self, client, mock_time_series_service):
        """Test successful CSV upload and processing."""
        csv_content = "timestamp,value1,value2\n2023-01-01,10,20\n2023-01-02,15,25"
        
        # Mock the service response
        mock_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'value1': [10, 15],
            'value2': [20, 25]
        })
        mock_time_series = TimeSeries.create(
            data=mock_df,
            time_column='timestamp',
            value_columns=['value1', 'value2']
        )
        mock_time_series_service.process_time_series.return_value = mock_time_series.to_dto("time")

        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"},
            files={"file": ("test.csv", csv_content, "text/csv")}
        )

        assert response.status_code == 200
        response_json = response.json()
        assert "analysis_id" in response_json
        assert response_json["time_column"] == "timestamp"
        assert set(response_json["value_columns"]) == set(["value1", "value2"])
        assert "time_domain" in response_json
        mock_time_series_service.process_time_series.assert_called_once()

    async def test_upload_csv_no_file(self, client):
        """Test CSV upload without a file."""
        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 422 # Unprocessable Entity for missing file

    async def test_upload_csv_invalid_format(self, client):
        """Test CSV upload with invalid format (e.g., not CSV)."""
        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "test-api-key-12345"},
            files={"file": ("test.txt", "not a csv", "text/plain")}
        )
        assert response.status_code == 400 # Bad Request for invalid file type

    async def test_get_analysis_result_time_domain_success(self, client, mock_time_series_service):
        """Test retrieving time domain analysis results successfully."""
        analysis_id = "test-analysis-id"
        mock_time_domain_data = {
            "time": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
            "series": {"value1": [10, 15], "value2": [20, 25]}
        }
        mock_time_series_service.get_analysis_result.return_value = MagicMock(
            analysis_id=analysis_id,
            time_column="timestamp",
            value_columns=["value1", "value2"],
            time_domain=mock_time_domain_data,
            frequency_domain=None
        )

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_id"] == analysis_id
        assert response_json["time_domain"] == mock_time_domain_data
        assert response_json["frequency_domain"] is None
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_get_analysis_result_frequency_domain_success(self, client, mock_time_series_service):
        """Test retrieving frequency domain analysis results successfully."""
        analysis_id = "test-analysis-id"
        mock_frequency_domain_data = {
            "frequencies": {"value1": [1, 2], "value2": [3, 4]},
            "amplitudes": {"value1": [0.1, 0.2], "value2": [0.3, 0.4]}
        }
        mock_time_series_service.get_analysis_result.return_value = MagicMock(
            analysis_id=analysis_id,
            time_column="timestamp",
            value_columns=["value1", "value2"],
            time_domain=None,
            frequency_domain=mock_frequency_domain_data
        )

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=frequency",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["analysis_id"] == analysis_id
        assert response_json["time_domain"] is None
        assert response_json["frequency_domain"] == mock_frequency_domain_data
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "frequency")

    async def test_get_analysis_result_not_found(self, client, mock_time_series_service):
        """Test retrieving analysis results for a non-existent ID."""
        analysis_id = "non-existent-id"
        mock_time_series_service.get_analysis_result.side_effect = ValueError(f"No time series found with ID {analysis_id}")

        response = client.get(
            f"/api/analyze/{analysis_id}?domain=time",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 404
        assert "No time series found" in response.json()["detail"]
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_get_analysis_result_invalid_domain(self, client):
        """Test retrieving analysis results with an invalid domain parameter."""
        response = client.get(
            "/api/analyze/some-id?domain=invalid",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 422 # Unprocessable Entity for invalid enum value

    async def test_export_csv_success(self, client, mock_time_series_service):
        """Test successful CSV export."""
        analysis_id = "test-export-id"
        mock_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'value1': [10, 15],
            'value2': [20, 25]
        })
        mock_time_series = TimeSeries.create(
            data=mock_df,
            time_column='timestamp',
            value_columns=['value1', 'value2']
        )
        mock_time_series_service.get_analysis_result.return_value = mock_time_series.to_dto("time")

        response = client.get(
            f"/api/export/{analysis_id}",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment; filename=time_series_analysis.csv" in response.headers["content-disposition"]
        expected_csv = "timestamp,value1,value2\r\n2023-01-01 00:00:00,10,20\r\n2023-01-02 00:00:00,15,25\r\n"
        assert response.text == expected_csv
        mock_time_series_service.get_analysis_result.assert_called_once_with(analysis_id, "time")

    async def test_export_csv_not_found(self, client, mock_time_series_service):
        """Test CSV export for a non-existent ID."""
        analysis_id = "non-existent-export-id"
        mock_time_series_service.get_analysis_result.side_effect = ValueError(f"No time series found with ID {analysis_id}")

        response = client.get(
            f"/api/export/{analysis_id}",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 404
        assert "No time series found" in response.json()["detail"]
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
        assert response.json() == {"message": f"Time series with ID {analysis_id} deleted successfully."}
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
        assert "Time series with ID non-existent-delete-id not found." in response.json()["detail"]
        mock_time_series_service.delete_time_series.assert_called_once_with(analysis_id)

    async def test_get_all_analysis_ids_success(self, client, mock_time_series_service):
        """Test retrieving all analysis IDs successfully."""
        mock_ids = ["id1", "id2", "id3"]
        mock_time_series_service.get_all_analysis_ids.return_value = mock_ids

        response = client.get(
            "/api/analyses",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.json() == {"analysis_ids": mock_ids}
        mock_time_series_service.get_all_analysis_ids.assert_called_once()

    async def test_get_all_analysis_ids_empty(self, client, mock_time_series_service):
        """Test retrieving all analysis IDs when none exist."""
        mock_time_series_service.get_all_analysis_ids.return_value = []

        response = client.get(
            "/api/analyses",
            headers={"X-API-Key": "test-api-key-12345"}
        )

        assert response.status_code == 200
        assert response.json() == {"analysis_ids": []}
        mock_time_series_service.get_all_analysis_ids.assert_called_once()

    async def test_diagnostic_endpoint_success(self, client, mock_time_series_service):
        """Test the diagnostic endpoint."""
        mock_time_series_service.get_all_analysis_ids.return_value = ["id1", "id2"]
        
        # Mock the cache service's get_cache_info method
        with patch('main.cache_service.get_cache_info', new_callable=AsyncMock) as mock_get_cache_info:
            mock_get_cache_info.return_value = {"cache_size": "10MB", "cached_items": 5}

            response = client.get("/api/diagnostic")
            assert response.status_code == 200
            response_json = response.json()
            assert "storage_info" in response_json
            assert "available_analyses" in response_json
            assert response_json["available_analyses"] == ["id1", "id2"]
            assert response_json["storage_info"] == {"cache_size": "10MB", "cached_items": 5}
            mock_time_series_service.get_all_analysis_ids.assert_called_once()
            mock_get_cache_info.assert_called_once()

    async def test_health_endpoint_success(self, client):
        """Test the health endpoint."""
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}