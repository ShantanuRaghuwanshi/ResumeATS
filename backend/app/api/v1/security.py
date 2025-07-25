"""
Security management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from security.authentication import require_authentication, require_role, UserRole
from security.monitoring import security_monitor, ThreatLevel, AttackType
from security.audit_logging import audit_logger, AuditEventType, AuditSeverity
from security.rate_limiting import rate_limiter
from fastapi import Depends
from configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/security/alerts")
async def get_security_alerts(
    request: Request,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    threat_level: Optional[str] = Query(None),
    attack_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Get security alerts (Admin only)"""

    try:
        # Parse optional filters
        threat_level_enum = None
        if threat_level:
            try:
                threat_level_enum = ThreatLevel(threat_level.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid threat level. Valid values: {[t.value for t in ThreatLevel]}",
                )

        attack_type_enum = None
        if attack_type:
            try:
                attack_type_enum = AttackType(attack_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid attack type. Valid values: {[a.value for a in AttackType]}",
                )

        # Get alerts
        alerts = security_monitor.get_recent_alerts(
            hours=hours, threat_level=threat_level_enum, attack_type=attack_type_enum
        )

        # Limit results
        alerts = alerts[:limit]

        # Convert to JSON-serializable format
        alert_data = []
        for alert in alerts:
            alert_data.append(
                {
                    "id": alert.id,
                    "timestamp": alert.timestamp.isoformat(),
                    "threat_level": alert.threat_level.value,
                    "attack_type": alert.attack_type.value,
                    "source_ip": alert.source_ip,
                    "user_agent": alert.user_agent,
                    "description": alert.description,
                    "details": alert.details,
                    "affected_resource": alert.affected_resource,
                    "user_id": alert.user_id,
                    "session_id": alert.session_id,
                    "mitigation_applied": alert.mitigation_applied,
                    "false_positive": alert.false_positive,
                }
            )

        return JSONResponse(
            {
                "success": True,
                "alerts": alert_data,
                "total_count": len(alert_data),
                "filters": {
                    "hours": hours,
                    "threat_level": threat_level,
                    "attack_type": attack_type,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security alerts: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve security alerts"
        )


@router.get("/security/summary")
async def get_security_summary(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role)
):
    """Get security monitoring summary (Admin only)"""

    try:
        summary = security_monitor.get_security_summary()

        return JSONResponse(
            {
                "success": True,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get security summary: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve security summary"
        )


@router.post("/security/ip/{ip_address}/block")
async def block_ip_address(
    ip_address: str,
    request: Request,
    reason: str = Body(...),
    current_user: Dict[str, Any] = Depends(require_role)
):
    """Block an IP address (Admin only)"""

    try:
        # Validate IP address format
        import ipaddress

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IP address format")

        # Block the IP
        security_monitor.blocked_ips.add(ip_address)

        # Log the action
        from security.audit_logging import log_user_action

        await log_user_action(
            "ip_blocked",
            request,
            user_id=current_user.get("user_id"),
            resource_type="ip_address",
            resource_id=ip_address,
            details={"reason": reason, "blocked_by": current_user.get("user_id")},
            success=True,
        )

        return JSONResponse(
            {
                "success": True,
                "message": f"IP address {ip_address} has been blocked",
                "reason": reason,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to block IP address: {e}")
        raise HTTPException(status_code=500, detail="Failed to block IP address")


@router.delete("/security/ip/{ip_address}/block")
async def unblock_ip_address(
    ip_address: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Unblock an IP address (Admin only)"""

    try:
        # Validate IP address format
        import ipaddress

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IP address format")

        # Unblock the IP
        security_monitor.unblock_ip(ip_address)

        # Also update rate limiter reputation
        rate_limiter.user_reputation.pop(ip_address, None)
        rate_limiter.suspicious_ips.discard(ip_address)
        rate_limiter.blocked_ips.pop(ip_address, None)

        # Log the action
        from security.audit_logging import log_user_action

        await log_user_action(
            "ip_unblocked",
            request,
            user_id=current_user.get("user_id"),
            resource_type="ip_address",
            resource_id=ip_address,
            details={"unblocked_by": current_user.get("user_id")},
            success=True,
        )

        return JSONResponse(
            {"success": True, "message": f"IP address {ip_address} has been unblocked"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unblock IP address: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP address")


@router.get("/security/blocked-ips")
async def get_blocked_ips(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Get list of blocked IP addresses (Admin only)"""

    try:
        blocked_ips = list(security_monitor.blocked_ips)

        # Get additional info from rate limiter
        ip_info = []
        for ip in blocked_ips:
            reputation = rate_limiter.get_user_reputation(ip)
            ip_info.append(
                {
                    "ip": ip,
                    "reputation_score": reputation["score"],
                    "violations": reputation["violations"],
                    "last_violation": (
                        reputation["last_violation"].isoformat()
                        if reputation["last_violation"]
                        else None
                    ),
                    "total_requests": reputation["total_requests"],
                    "first_seen": reputation["first_seen"].isoformat(),
                }
            )

        return JSONResponse(
            {"success": True, "blocked_ips": ip_info, "total_count": len(ip_info)}
        )

    except Exception as e:
        logger.error(f"Failed to get blocked IPs: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve blocked IP addresses"
        )


@router.post("/security/alert/{alert_id}/mark-false-positive")
async def mark_false_positive(
    alert_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Mark a security alert as false positive (Admin only)"""

    try:
        # Find the alert
        alert = None
        for a in security_monitor.alerts:
            if a.id == alert_id:
                alert = a
                break

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Mark as false positive
        alert.false_positive = True

        # Log the action
        from security.audit_logging import log_user_action

        await log_user_action(
            "alert_marked_false_positive",
            request,
            user_id=current_user.get("user_id"),
            resource_type="security_alert",
            resource_id=alert_id,
            details={"marked_by": current_user.get("user_id")},
            success=True,
        )

        return JSONResponse(
            {"success": True, "message": f"Alert {alert_id} marked as false positive"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark alert as false positive: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")


@router.get("/security/audit-logs")
async def get_audit_logs(
    request: Request,
    event_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Get audit logs (Admin only)"""

    try:
        # Parse event type
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event type. Valid values: {[e.value for e in AuditEventType]}",
                )

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Search audit logs
        events = await audit_logger.search_events(
            event_type=event_type_enum,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        return JSONResponse(
            {
                "success": True,
                "events": events,
                "total_count": len(events),
                "filters": {
                    "event_type": event_type,
                    "user_id": user_id,
                    "hours": hours,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")


@router.get("/security/rate-limits")
async def get_rate_limit_status(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Get rate limiting status and statistics (Admin only)"""

    try:
        # Get client IP for demonstration
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Get rate limiter statistics
        stats = {
            "total_tracked_ips": len(rate_limiter.user_reputation),
            "suspicious_ips": len(rate_limiter.suspicious_ips),
            "blocked_ips": len(rate_limiter.blocked_ips),
            "current_client_ip": client_ip,
            "current_client_reputation": rate_limiter.get_user_reputation(client_ip),
            "is_current_client_blocked": rate_limiter.is_blocked(client_ip),
        }

        # Get top IPs by reputation
        top_ips = []
        for ip, reputation in list(rate_limiter.user_reputation.items())[:20]:
            top_ips.append(
                {
                    "ip": ip,
                    "reputation_score": reputation["score"],
                    "total_requests": reputation["total_requests"],
                    "violations": reputation["violations"],
                    "is_suspicious": ip in rate_limiter.suspicious_ips,
                    "is_blocked": rate_limiter.is_blocked(ip),
                }
            )

        # Sort by reputation score
        top_ips.sort(key=lambda x: x["reputation_score"])

        stats["top_ips_by_reputation"] = top_ips

        return JSONResponse({"success": True, "rate_limit_stats": stats})

    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve rate limit status"
        )


@router.post("/security/cleanup")
async def cleanup_security_data(
    request: Request,
    days: int = Body(7, ge=1, le=30),
    current_user: Dict[str, Any] = Depends(require_role),
):
    """Cleanup old security data (Admin only)"""

    try:
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        # Cleanup old alerts
        original_alert_count = len(security_monitor.alerts)
        security_monitor.alerts = [
            alert for alert in security_monitor.alerts if alert.timestamp > cutoff_time
        ]
        cleaned_alerts = original_alert_count - len(security_monitor.alerts)

        # Cleanup old IP activity
        cleaned_ips = 0
        for ip in list(security_monitor.ip_activity.keys()):
            security_monitor.ip_activity[ip] = [
                timestamp
                for timestamp in security_monitor.ip_activity[ip]
                if timestamp > cutoff_time
            ]
            if not security_monitor.ip_activity[ip]:
                del security_monitor.ip_activity[ip]
                cleaned_ips += 1

        # Log the cleanup action
        from security.audit_logging import log_user_action

        await log_user_action(
            "security_data_cleanup",
            request,
            user_id=current_user.get("user_id"),
            details={
                "days": days,
                "cleaned_alerts": cleaned_alerts,
                "cleaned_ips": cleaned_ips,
                "performed_by": current_user.get("user_id"),
            },
            success=True,
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Security data cleanup completed",
                "cleaned_alerts": cleaned_alerts,
                "cleaned_ips": cleaned_ips,
            }
        )

    except Exception as e:
        logger.error(f"Failed to cleanup security data: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup security data")


# Health check for security services
@router.get("/security/health")
async def security_health_check():
    """Health check for security services"""

    try:
        health_status = {
            "security_monitor": {
                "active": security_monitor.monitoring_active,
                "total_alerts": len(security_monitor.alerts),
                "blocked_ips": len(security_monitor.blocked_ips),
            },
            "audit_logger": {
                "active": audit_logger.writer_task is not None
                and not audit_logger.writer_task.done(),
                "queue_size": audit_logger.log_queue.qsize(),
            },
            "rate_limiter": {
                "tracked_ips": len(rate_limiter.user_reputation),
                "suspicious_ips": len(rate_limiter.suspicious_ips),
                "blocked_ips": len(rate_limiter.blocked_ips),
            },
        }

        return JSONResponse(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": health_status,
            }
        )

    except Exception as e:
        logger.error(f"Security health check failed: {e}")
        return JSONResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
            status_code=500,
        )
