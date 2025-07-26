"""
Utility functions for session-based LLM provider management
"""

from typing import Optional
from fastapi import Request, HTTPException, status

from app.services.llm_provider import LLMProviderFactory, LLMProviderBase
from app.middleware.session_middleware import (
    get_llm_config_from_request,
    require_session,
)
from app.models.session import LLMConfiguration


def get_llm_provider_from_session(request: Request) -> LLMProviderBase:
    """
    Get LLM provider instance from session configuration.

    This function should be used in API endpoints that need LLM functionality.
    It automatically extracts the LLM configuration from the session and creates
    the appropriate provider instance.

    Args:
        request: FastAPI request object (with session middleware applied)

    Returns:
        LLMProviderBase: Configured LLM provider instance

    Raises:
        HTTPException: If session is invalid or LLM config not found
    """
    # Ensure we have a valid session
    session_id = require_session(request)

    # Get LLM configuration from session
    llm_config = get_llm_config_from_request(request)
    if not llm_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration not found in session",
        )

    # Convert to provider configuration format
    provider_config = {
        "api_key": llm_config.api_key,
        "base_url": llm_config.base_url,
        "model": llm_config.model_name,
        "temperature": llm_config.temperature,
        "max_tokens": llm_config.max_tokens,
        "top_p": llm_config.top_p,
        "frequency_penalty": llm_config.frequency_penalty,
        "presence_penalty": llm_config.presence_penalty,
        **llm_config.additional_params,
    }

    # Remove None values
    provider_config = {k: v for k, v in provider_config.items() if v is not None}

    # Create and return provider instance
    try:
        return LLMProviderFactory.create(llm_config.provider.value, provider_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create LLM provider: {str(e)}",
        )


def get_session_id_from_request(request: Request) -> str:
    """
    Get session ID from request (with validation).

    Args:
        request: FastAPI request object

    Returns:
        str: Session ID

    Raises:
        HTTPException: If session is invalid
    """
    return require_session(request)


def get_session_llm_config(request: Request) -> LLMConfiguration:
    """
    Get LLM configuration from session.

    Args:
        request: FastAPI request object

    Returns:
        LLMConfiguration: LLM configuration from session

    Raises:
        HTTPException: If session is invalid or config not found
    """
    # Ensure we have a valid session
    require_session(request)

    # Get LLM configuration from session
    llm_config = get_llm_config_from_request(request)
    if not llm_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration not found in session",
        )

    return llm_config
