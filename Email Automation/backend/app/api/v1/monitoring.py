"""
Monitoring API endpoints for WolfAssistants
Provides real-time monitoring and management for 100+ users
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.core.auth import get_current_user
from app.monitoring.user_monitoring import user_monitor, UserStatus
from app.monitoring.health_checker import health_checker, HealthStatus

router = APIRouter()

@router.get("/dashboard")
async def get_monitoring_dashboard(current_user: dict = Depends(get_current_user)):
    """Get comprehensive monitoring dashboard"""
    try:
        # Get system status
        system_status = user_monitor.get_system_status()
        
        # Get health status
        health_status = health_checker.get_health_status()
        
        # Combine into dashboard
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "system": system_status,
            "health": health_status,
            "alerts": _generate_alerts(system_status, health_status)
        }
        
        return JSONResponse(content=dashboard)
        
    except Exception as e:
        logging.error(f"Monitoring dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring data")

@router.get("/users")
async def get_user_monitoring(current_user: dict = Depends(get_current_user)):
    """Get detailed user monitoring information"""
    try:
        active_sessions = user_monitor.active_sessions
        
        users_data = []
        for user_id, session in active_sessions.items():
            users_data.append({
                "user_id": user_id,
                "email": session.email,
                "status": session.status,
                "last_activity": session.last_activity.isoformat(),
                "request_count": session.request_count,
                "features_used": list(session.features_used),
                "ip_address": session.ip_address,
                "session_duration": (datetime.now() - session.session_start).total_seconds()
            })
        
        return JSONResponse(content={
            "active_users": len(active_sessions),
            "users": users_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"User monitoring error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user data")

@router.get("/features")
async def get_feature_monitoring(current_user: dict = Depends(get_current_user)):
    """Get feature health and usage monitoring"""
    try:
        feature_health = user_monitor.feature_health
        
        features_data = []
        for name, health in feature_health.items():
            features_data.append({
                "name": name,
                "status": health.status,
                "user_count": health.user_count,
                "max_capacity": health.max_capacity,
                "utilization_percent": round((health.user_count / health.max_capacity) * 100, 2),
                "response_time": health.response_time,
                "error_rate": health.error_rate,
                "last_check": health.last_check.isoformat()
            })
        
        return JSONResponse(content={
            "features": features_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Feature monitoring error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature data")

@router.get("/health")
async def get_health_status(current_user: dict = Depends(get_current_user)):
    """Get detailed health status of all services"""
    try:
        health_data = health_checker.get_health_status()
        return JSONResponse(content=health_data)
        
    except Exception as e:
        logging.error(f"Health status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health data")

@router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """Get current system alerts and warnings"""
    try:
        system_status = user_monitor.get_system_status()
        health_status = health_checker.get_health_status()
        
        alerts = _generate_alerts(system_status, health_status)
        
        return JSONResponse(content={
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Alerts error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")

@router.post("/users/{user_id}/block")
async def block_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Block a specific user"""
    try:
        user_monitor.block_user(user_id, "Manually blocked by admin")
        
        return JSONResponse(content={
            "message": f"User {user_id} has been blocked",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Block user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to block user")

@router.post("/users/{user_id}/unblock")
async def unblock_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Unblock a specific user"""
    try:
        user_monitor.unblock_user(user_id)
        
        return JSONResponse(content={
            "message": f"User {user_id} has been unblocked",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Unblock user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock user")

@router.get("/performance")
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    """Get performance metrics and statistics"""
    try:
        system_metrics = user_monitor.system_metrics
        feature_health = user_monitor.feature_health
        
        # Calculate performance metrics
        total_users = len(user_monitor.active_sessions)
        avg_response_time = sum(health.response_time for health in feature_health.values()) / len(feature_health)
        total_errors = sum(health.error_rate for health in feature_health.values())
        
        performance_data = {
            "total_active_users": total_users,
            "average_response_time": round(avg_response_time, 3),
            "total_error_rate": round(total_errors, 3),
            "system_metrics": system_metrics,
            "feature_utilization": {
                name: round((health.user_count / health.max_capacity) * 100, 2)
                for name, health in feature_health.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=performance_data)
        
    except Exception as e:
        logging.error(f"Performance metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance data")

def _generate_alerts(system_status: Dict, health_status: Dict) -> List[Dict]:
    """Generate alerts based on system and health status"""
    alerts = []
    
    # Check system metrics
    if system_status.get("system_metrics", {}).get("cpu_usage", 0) > 80:
        alerts.append({
            "level": "warning",
            "message": "High CPU usage detected",
            "timestamp": datetime.now().isoformat()
        })
    
    if system_status.get("system_metrics", {}).get("memory_usage", 0) > 85:
        alerts.append({
            "level": "critical",
            "message": "High memory usage detected",
            "timestamp": datetime.now().isoformat()
        })
    
    # Check feature health
    for feature_name, feature_data in system_status.get("feature_health", {}).items():
        if feature_data.get("status") == "degraded":
            alerts.append({
                "level": "warning",
                "message": f"Feature {feature_name} is degraded",
                "timestamp": datetime.now().isoformat()
            })
        elif feature_data.get("status") == "down":
            alerts.append({
                "level": "critical",
                "message": f"Feature {feature_name} is down",
                "timestamp": datetime.now().isoformat()
            })
    
    # Check health checks
    for check_name, check_data in health_status.get("checks", {}).items():
        if check_data.get("status") == "down":
            alerts.append({
                "level": "critical",
                "message": f"Service {check_name} is down: {check_data.get('error_message', 'Unknown error')}",
                "timestamp": datetime.now().isoformat()
            })
        elif check_data.get("status") == "degraded":
            alerts.append({
                "level": "warning",
                "message": f"Service {check_name} is degraded",
                "timestamp": datetime.now().isoformat()
            })
    
    return alerts
