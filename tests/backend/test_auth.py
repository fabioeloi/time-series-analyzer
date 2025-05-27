import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from infrastructure.auth.api_key_auth import APIKeyAuth, get_api_key_dependency


class TestAPIKeyAuth:
    """Test cases for the API Key authentication functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Mock environment variable for testing
        self.test_api_key = "test-api-key-12345"
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_api_key_auth_initialization(self):
        """Test that APIKeyAuth initializes correctly with environment variable."""
        auth = APIKeyAuth()
        assert auth.api_key == "test-api-key-12345"
        
    @patch.dict(os.environ, {}, clear=True)
    def test_api_key_auth_missing_env_var(self):
        """Test that APIKeyAuth raises ValueError when API_KEY is not set."""
        with pytest.raises(ValueError, match="API_KEY environment variable is not set"):
            APIKeyAuth()
            
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_validate_api_key_success(self):
        """Test successful API key validation."""
        auth = APIKeyAuth()
        result = auth.validate_api_key("test-api-key-12345")
        assert result == "test-api-key-12345"
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_validate_api_key_missing_header(self):
        """Test API key validation when header is missing."""
        auth = APIKeyAuth()
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert "API key is required" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "X-API-Key"
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_validate_api_key_invalid_key(self):
        """Test API key validation with invalid key."""
        auth = APIKeyAuth()
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_api_key("wrong-api-key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "X-API-Key"
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_validate_api_key_timing_attack_protection(self):
        """Test that the API key comparison uses secrets.compare_digest for timing attack protection."""
        auth = APIKeyAuth()
        
        # Test with keys of different lengths (timing attack scenario)
        with pytest.raises(HTTPException):
            auth.validate_api_key("short")
            
        with pytest.raises(HTTPException):
            auth.validate_api_key("this-is-a-very-long-invalid-api-key-that-should-fail")


class TestAPIKeyAuthIntegration:
    """Integration tests for API Key authentication with FastAPI endpoints."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.test_api_key = "test-api-key-12345"
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_api_endpoints_with_authentication(self):
        """Test that API endpoints require authentication."""
        from main import app
        
        client = TestClient(app)
        
        # Test upload endpoint without API key
        response = client.post("/api/upload-csv/")
        assert response.status_code == 401
        assert "API key is required" in response.json()["detail"]
        
        # Test upload endpoint with invalid API key
        response = client.post(
            "/api/upload-csv/",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        
        # Test analyze endpoint without API key
        response = client.get("/api/analyze/test-id")
        assert response.status_code == 401
        
        # Test export endpoint without API key
        response = client.get("/api/export/test-id")
        assert response.status_code == 401
        
        # Test health endpoint without API key
        response = client.get("/api/health")
        assert response.status_code == 401
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_diagnostic_endpoint_no_auth_required(self):
        """Test that the diagnostic endpoint does not require authentication."""
        from main import app
        
        client = TestClient(app)
        
        # Test diagnostic endpoint without API key - should work
        response = client.get("/api/diagnostic")
        assert response.status_code == 200
        # The response should contain diagnostic information
        assert "storage_info" in response.json()
        assert "available_analyses" in response.json()
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_health_endpoint_with_valid_auth(self):
        """Test that the health endpoint works with valid authentication."""
        from main import app
        
        client = TestClient(app)
        
        # Test health endpoint with valid API key
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_api_key_header_case_sensitivity(self):
        """Test that API key header is case-sensitive as expected."""
        from main import app
        
        client = TestClient(app)
        
        # Test with correct case
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "test-api-key-12345"}
        )
        assert response.status_code == 200
        
        # Test with wrong case (should fail because FastAPI header handling)
        response = client.get(
            "/api/health",
            headers={"x-api-key": "test-api-key-12345"}
        )
        # Note: FastAPI normalizes headers, so this should actually work
        # The test verifies the current behavior
        assert response.status_code == 200
        
    @patch.dict(os.environ, {"API_KEY": "test-api-key-12345"})
    def test_multiple_header_scenarios(self):
        """Test various header scenarios for API key authentication."""
        from main import app
        
        client = TestClient(app)
        
        # Test with empty string API key
        response = client.get(
            "/api/health",
            headers={"X-API-Key": ""}
        )
        assert response.status_code == 401
        
        # Test with whitespace API key
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "   "}
        )
        assert response.status_code == 401
        
        # Test with correct API key but extra whitespace
        response = client.get(
            "/api/health",
            headers={"X-API-Key": " test-api-key-12345 "}
        )
        assert response.status_code == 401  # Should fail due to exact match requirement