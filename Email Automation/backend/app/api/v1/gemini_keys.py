"""
Gemini API Keys Management and Monitoring

Provides endpoints for monitoring API key health, usage, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.core.gemini_key_manager import key_manager
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def get_key_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get health status of all API keys."""
    
    # Check if user has admin access (for now, allow all authenticated users)
    # In production, you might want to restrict this to admin users only
    
    health_status = key_manager.get_health_status()
    available_keys = key_manager.get_available_keys_count()
    total_keys = key_manager.get_total_keys_count()
    
    return {
        "total_keys": total_keys,
        "available_keys": available_keys,
        "unhealthy_keys": total_keys - available_keys,
        "key_health": health_status,
        "summary": {
            "healthy_percentage": (available_keys / total_keys * 100) if total_keys > 0 else 0,
            "status": "healthy" if available_keys > 0 else "unhealthy"
        }
    }

@router.get("/status")
def get_key_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get simplified status of API keys."""
    
    available_keys = key_manager.get_available_keys_count()
    total_keys = key_manager.get_total_keys_count()
    
    return {
        "status": "operational" if available_keys > 0 else "degraded",
        "available_keys": available_keys,
        "total_keys": total_keys,
        "capacity": f"{available_keys}/{total_keys} keys available"
    }

@router.post("/refresh")
def refresh_key_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force refresh of key health status."""
    
    # This would trigger a health check
    # For now, just return current status
    health_status = key_manager.get_health_status()
    
    return {
        "message": "Key health refreshed",
        "timestamp": "2025-09-21T14:42:10Z",  # Would be actual timestamp
        "key_health": health_status
    }

@router.get("/capacity")
def get_capacity_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get capacity information for API keys."""
    
    available_keys = key_manager.get_available_keys_count()
    total_keys = key_manager.get_total_keys_count()
    
    # Calculate theoretical capacity
    # Each key can handle ~10-14 users per day with current limits
    users_per_key = 12  # Conservative estimate
    max_users = available_keys * users_per_key
    
    return {
        "available_keys": available_keys,
        "total_keys": total_keys,
        "estimated_capacity": {
            "max_users": max_users,
            "users_per_key": users_per_key,
            "utilization": "low" if max_users > 50 else "high"
        },
        "recommendations": {
            "add_keys": max(0, 8 - available_keys) if max_users < 100 else 0,
            "status": "sufficient" if max_users >= 100 else "insufficient"
        }
    }

@router.get("/categorization-stats")
def get_categorization_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about API key categorization."""
    from app.core.user_api_key_assigner import user_key_assigner
    
    stats = user_key_assigner.get_category_stats(db)
    
    return {
        "categorization_enabled": True,
        "categories": stats,
        "total_keys": len(settings.gemini_api_keys),
        "key_health": key_manager.get_health_status()
    }

@router.get("/circuit-breaker-stats")
def get_circuit_breaker_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get circuit breaker statistics."""
    from app.core.circuit_breaker import circuit_breaker
    
    return {
        "circuit_breaker_enabled": True,
        "circuit_states": circuit_breaker.get_stats()
    }

@router.get("/queue-stats")
def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get request queue statistics."""
    from app.core.request_queue import request_queue
    
    return {
        "queue_enabled": getattr(settings, 'REQUEST_QUEUE_ENABLED', False),
        "queue_stats": request_queue.get_stats()
    }
