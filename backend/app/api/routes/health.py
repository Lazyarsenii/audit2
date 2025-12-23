"""
Health check and system status endpoints.
"""
from fastapi import APIRouter

from app.core.dependencies import get_system_status, get_available_features

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return service health status."""
    return {"status": "ok", "service": "repo-auditor"}


@router.get("/system/status")
async def system_status():
    """
    Get full system status including available tools and features.

    Returns:
        - dependencies: status of all external tools
        - features: what functionality is available
        - recommendations: how to install missing tools

    Пользователи могут проверить этот endpoint чтобы увидеть
    какие функции доступны в их окружении.
    """
    return get_system_status()


@router.get("/system/features")
async def available_features():
    """
    Get list of available features.

    Quick endpoint to check what analysis features are available.
    """
    return {
        "features": get_available_features(),
    }
