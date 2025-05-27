"""API Key Authentication module for securing API endpoints."""

import os
import secrets
from typing import Optional
from fastapi import HTTPException, Header, Depends, status


class APIKeyAuth:
    """API Key authentication handler."""
    
    def __init__(self):
        """Initialize the API key authentication with the configured key."""
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY environment variable is not set")
    
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


# Global instance
api_key_auth = APIKeyAuth()


def get_api_key_dependency():
    """
    FastAPI dependency for API key authentication.
    
    Returns:
        Callable: The API key validation dependency
    """
    return Depends(api_key_auth.validate_api_key)