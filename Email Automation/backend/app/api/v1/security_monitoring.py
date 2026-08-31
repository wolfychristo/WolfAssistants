"""
Security monitoring endpoints for WolfAssistants
Provides real-time security insights and threat detection
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.core.auth import get_current_user
from app.middleware.security_audit import (
    security_auditor, 
    get_security_report, 
    get_ip_analysis, 
    get_user_analysis,
    log_security_event,
    EventType,
    ThreatLevel
)
from app.middleware.ip_rate_limiting import (
    ip_rate_limiter,
    get_ip_statistics,
    block_ip,
    unblock_ip,
    clear_all_rate_limits
)

# Configure router
router = APIRouter()

# Configure logging
security_logger = logging.getLogger("security_monitoring")

@router.get("/security/dashboard")
async def get_security_dashboard(
    request: Request,
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive security dashboard"""
    try:
        # Get security report
        report = get_security_report(hours)
        
        # Get current threat level
        threat_level = "LOW"
        if report['threat_counts'].get('critical', 0) > 0:
            threat_level = "CRITICAL"
        elif report['threat_counts'].get('high', 0) > 5:
            threat_level = "HIGH"
        elif report['threat_counts'].get('medium', 0) > 10:
            threat_level = "MEDIUM"
        
        # Get blocked IPs
        blocked_ips = [ip for ip, stats in ip_rate_limiter.blocked_ips.items()]
        
        # Get recent security events
        recent_events = list(security_auditor.events)[-20:]  # Last 20 events
        
        dashboard = {
            "overview": {
                "threat_level": threat_level,
                "total_events": report['total_events'],
                "unique_ips": report['unique_ips'],
                "blocked_ips": len(blocked_ips),
                "report_period_hours": hours,
                "generated_at": datetime.now().isoformat()
            },
            "threats": {
                "by_level": report['threat_counts'],
                "by_type": report['event_counts']
            },
            "suspicious_activity": {
                "top_ips": report['suspicious_ips'][:5],
                "top_users": report['suspicious_users'][:5]
            },
            "recent_events": [
                {
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "level": event.threat_level,
                    "ip": event.ip_address,
                    "description": event.description
                }
                for event in recent_events
            ],
            "blocked_ips": blocked_ips
        }
        
        # Log dashboard access
        log_security_event(
            EventType.DATA_ACCESS,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            "/api/v1/security/dashboard",
            "GET",
            "Security dashboard accessed"
        )
        
        return JSONResponse(content=dashboard)
        
    except Exception as e:
        security_logger.error(f"Security dashboard error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate security dashboard"
        )

@router.get("/security/ip/{ip_address}")
async def get_ip_security_analysis(
    ip_address: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed security analysis for specific IP"""
    try:
        analysis = get_ip_analysis(ip_address)
        
        # Log IP analysis access
        log_security_event(
            EventType.DATA_ACCESS,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            f"/api/v1/security/ip/{ip_address}",
            "GET",
            f"IP analysis accessed for {ip_address}"
        )
        
        return JSONResponse(content=analysis)
        
    except Exception as e:
        security_logger.error(f"IP analysis error for {ip_address}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze IP address"
        )

@router.get("/security/user/{user_id}")
async def get_user_security_analysis(
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed security analysis for specific user"""
    try:
        analysis = get_user_analysis(user_id)
        
        # Log user analysis access
        log_security_event(
            EventType.DATA_ACCESS,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            f"/api/v1/security/user/{user_id}",
            "GET",
            f"User analysis accessed for {user_id}"
        )
        
        return JSONResponse(content=analysis)
        
    except Exception as e:
        security_logger.error(f"User analysis error for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze user"
        )

@router.post("/security/block-ip")
async def block_ip_address(
    request: Request,
    ip_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Manually block an IP address"""
    try:
        ip_address = ip_data.get("ip_address")
        duration = ip_data.get("duration", 3600)  # Default 1 hour
        reason = ip_data.get("reason", "Manual block")
        
        if not ip_address:
            raise HTTPException(
                status_code=400,
                detail="IP address is required"
            )
        
        # Block the IP
        block_ip(ip_address, duration, reason)
        
        # Log the block action
        log_security_event(
            EventType.IP_BLOCKED,
            ThreatLevel.HIGH,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            "/api/v1/security/block-ip",
            "POST",
            f"IP {ip_address} manually blocked for {duration} seconds: {reason}",
            {"ip_address": ip_address, "duration": duration, "reason": reason}
        )
        
        return JSONResponse(content={
            "message": f"IP {ip_address} blocked for {duration} seconds",
            "ip_address": ip_address,
            "duration": duration,
            "reason": reason
        })
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error(f"IP block error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to block IP address"
        )

@router.post("/security/unblock-ip")
async def unblock_ip_address(
    request: Request,
    ip_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Manually unblock an IP address"""
    try:
        ip_address = ip_data.get("ip_address")
        
        if not ip_address:
            raise HTTPException(
                status_code=400,
                detail="IP address is required"
            )
        
        # Unblock the IP
        unblock_ip(ip_address)
        
        # Log the unblock action
        log_security_event(
            EventType.IP_UNBLOCKED,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            "/api/v1/security/unblock-ip",
            "POST",
            f"IP {ip_address} manually unblocked",
            {"ip_address": ip_address}
        )
        
        return JSONResponse(content={
            "message": f"IP {ip_address} unblocked",
            "ip_address": ip_address
        })
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error(f"IP unblock error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to unblock IP address"
        )

@router.get("/security/rate-limits")
async def get_rate_limit_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get current rate limiting status"""
    try:
        # Get rate limiter statistics
        stats = {
            "total_ips_tracked": len(ip_rate_limiter.ip_stats),
            "blocked_ips": len(ip_rate_limiter.blocked_ips),
            "active_ips": len(ip_rate_limiter.ip_stats) - len(ip_rate_limiter.blocked_ips),
            "top_ips_by_requests": sorted(
                [(ip, data['request_count']) for ip, data in ip_rate_limiter.ip_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        
        # Log rate limit status access
        log_security_event(
            EventType.DATA_ACCESS,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            "/api/v1/security/rate-limits",
            "GET",
            "Rate limit status accessed"
        )
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        security_logger.error(f"Rate limit status error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get rate limit status"
        )

@router.get("/security/health")
async def get_security_health(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get security system health status"""
    try:
        # Check if security systems are running
        health_status: Dict[str, Any] = {
            "security_headers": "ACTIVE",
            "ip_rate_limiting": "ACTIVE",
            "input_sanitization": "ACTIVE",
            "security_audit": "ACTIVE",
            "threat_detection": "ACTIVE",
            "monitoring": "ACTIVE",
            "timestamp": datetime.now().isoformat()
        }
        
        # Check for any issues
        issues = []
        
        # Check if we have recent events (indicates system is working)
        if len(security_auditor.events) == 0:
            issues.append("No security events recorded")
        
        # Check if rate limiter is working
        if len(ip_rate_limiter.ip_stats) == 0:
            issues.append("No IP statistics recorded")
        
        if issues:
            health_status["issues"] = issues
            health_status["status"] = "DEGRADED"
        else:
            health_status["status"] = "HEALTHY"
        
        return JSONResponse(content=health_status)
        
    except Exception as e:
        security_logger.error(f"Security health check error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "error": "Security health check failed",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/security/alerts")
async def get_security_alerts(
    request: Request,
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get recent security alerts and warnings"""
    try:
        # Get recent high-priority events
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        alerts = []
        for event in security_auditor.events:
            event_time = datetime.fromisoformat(event.timestamp)
            if event_time > cutoff_time and event.threat_level in ['high', 'critical']:
                alerts.append({
                    "timestamp": event.timestamp,
                    "type": event.event_type,
                    "level": event.threat_level,
                    "ip": event.ip_address,
                    "description": event.description,
                    "details": event.details
                })
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Log alerts access
        log_security_event(
            EventType.DATA_ACCESS,
            ThreatLevel.LOW,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "Unknown"),
            current_user.get("email"),
            "/api/v1/security/alerts",
            "GET",
            f"Security alerts accessed for last {hours} hours"
        )
        
        return JSONResponse(content={
            "alerts": alerts,
            "total_alerts": len(alerts),
            "period_hours": hours,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        security_logger.error(f"Security alerts error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get security alerts"
        )

@router.post("/rate-limits/clear")
async def clear_rate_limits(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Clear all rate limiting data (development only)"""
    try:
        # Log the action
        log_security_event(
            event_type=EventType.ADMIN_ACTION,
            threat_level=ThreatLevel.LOW,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "Unknown"),
            user_id=current_user.get("id"),
            endpoint="/api/v1/security/rate-limits/clear",
            method="POST",
            description="Rate limits cleared by admin",
            details={"admin_action": "clear_rate_limits"}
        )
        
        # Clear all rate limits
        clear_all_rate_limits()
        
        return JSONResponse(content={
            "message": "All rate limiting data cleared successfully",
            "timestamp": datetime.now().isoformat(),
            "cleared_by": current_user.get("email")
        })
        
    except Exception as e:
        security_logger.error(f"Clear rate limits error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear rate limits"
        )
