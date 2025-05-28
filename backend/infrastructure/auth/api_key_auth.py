"""API Key Authentication module for securing API endpoints."""

import os
import secrets
from typing import Optional
from fastapi import HTTPException, Header, Depends, status


class APIKeyAuth:
    """API Key authentication handler."""
    
    def __init__(self):
        """Initialize the API key authentication with the configured key."""
        api_key_env = os.getenv("API_KEY")
        
        if api_key_env is None:
            raise ValueError("API_KEY environment variable is not set")
        
        self.api_key = api_key_env
    
    def validate_api_key(self, x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
        """
        Validate the API key from the X-API-Key header.
        
        Args:
            x_api_key: The API key from the X-API-Key header
            
        Returns:
            str: The validated API key
            
        Raises:
            HTTPException: If the API key is missing or invalid
        """
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required. Please provide a valid X-API-Key header.",
                headers={"WWW-Authenticate": "X-API-Key"},
            )
        
        # Use secrets.compare_digest to prevent timing attacks
        if not secrets.compare_digest(x_api_key, self.api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key. Please provide a valid X-API-Key header.",
                headers={"WWW-Authenticate": "X-API-Key"},
            )
        
        return x_api_key


# Global instance - using lazy initialization
_api_key_auth_instance: Optional[APIKeyAuth] = None


def get_api_key_auth() -> APIKeyAuth:
    """
    Get the global API key authentication instance using lazy initialization.
    
    Returns:
        APIKeyAuth: The global API key authentication instance
    """
    global _api_key_auth_instance
    if _api_key_auth_instance is None:
        _api_key_auth_instance = APIKeyAuth()
    return _api_key_auth_instance


def reset_api_key_auth():
    """
    Reset the global API key authentication instance.
    This is primarily used for testing purposes.
    """
    global _api_key_auth_instance
    _api_key_auth_instance = None


def get_api_key_dependency():
    """
    FastAPI dependency for API key authentication.
    
    Returns:
        Callable: The API key validation dependency
    """
    return Depends(get_api_key_auth().validate_api_key)