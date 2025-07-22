"""
Monitoring and health check API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

from services.integration_service import integration_service
from services.websocket_manager import websocket_manager
from services.performance_monitor import PerformanceMonitor
from security.authentication import get_current_user
from security.decorators import require_admin
from configs.logging_config import get_service_logger

logger = get_service_logger("monitoring_api")
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""

    try:
        health_status = await integration_service.health_check_all_services()

        status_code = 200 if health_status["overall_healthy"] else 503

        return {
            "status": "healthy" if health_status["overall_healthy"] else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "services": health_status["services"],
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system metrics"""

    try:
        system_status = await integration_service.get_system_status()

        return {
            "status": (
                "healthy"
                if system_status["system_health"]["overall_healthy"]
                else "unhealthy"
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "system_status": system_status,
        }

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Detailed health check failed")


@router.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""

    try:
        performance_monitor = PerformanceMonitor()
        metrics = await performance_monitor.get_comprehensive_metrics()

        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""

    try:
        stats = websocket_manager.get_connection_stats()

        return {
            "success": True,
            "websocket_stats": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve WebSocket stats"
        )


@router.get("/services/status")
async def get_services_status():
    """Get status of all services"""

    try:
        health_status = await integration_service.health_check_all_services()

        return {
            "success": True,
            "services": health_status["services"],
            "overall_healthy": health_status["overall_healthy"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve services status"
        )


@router.post("/services/{service_name}/restart")
@require_admin
async def restart_service(
    service_name: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Restart a specific service (admin only)"""

    try:
        # Add restart task to background
        background_tasks.add_task(_restart_service, service_name)

        logger.info(
            f"Service restart initiated for {service_name}",
            user_id=current_user.get("id"),
        )

        return {
            "success": True,
            "message": f"Restart initiated for service: {service_name}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to restart service {service_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to restart service: {service_name}"
        )


async def _restart_service(service_name: str):
    """Background task to restart a service"""

    try:
        # Service-specific restart logic
        if service_name == "websocket_manager":
            await websocket_manager.cleanup_inactive_connections()
        elif service_name == "cache_service":
            await integration_service.cache_service.clear_cache()
            await integration_service.cache_service.initialize()
        elif service_name == "background_jobs":
            await integration_service.background_jobs.restart()
        else:
            logger.warning(f"No restart procedure defined for service: {service_name}")

        logger.info(f"Service {service_name} restarted successfully")

    except Exception as e:
        logger.error(f"Failed to restart service {service_name}: {e}")


@router.get("/circuit-breakers")
@require_admin
async def get_circuit_breakers(current_user=Depends(get_current_user)):
    """Get circuit breaker status (admin only)"""

    try:
        system_status = await integration_service.get_system_status()

        return {
            "success": True,
            "circuit_breakers": system_status["circuit_breakers"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get circuit breakers: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve circuit breakers"
        )


@router.post("/circuit-breakers/{service_name}/reset")
@require_admin
async def reset_circuit_breaker(
    service_name: str, current_user=Depends(get_current_user)
):
    """Reset circuit breaker for a service (admin only)"""

    try:
        await integration_service._reset_circuit_breaker(service_name)

        logger.info(
            f"Circuit breaker reset for {service_name}", user_id=current_user.get("id")
        )

        return {
            "success": True,
            "message": f"Circuit breaker reset for service: {service_name}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to reset circuit breaker for {service_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reset circuit breaker: {service_name}"
        )


@router.get("/logs/recent")
@require_admin
async def get_recent_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
    current_user=Depends(get_current_user),
):
    """Get recent log entries (admin only)"""

    try:
        # This would integrate with log aggregation system
        # For now, return placeholder
        logs = {
            "logs": [],
            "total": 0,
            "filters": {"service": service, "level": level, "limit": limit},
            "message": "Log aggregation not implemented yet",
        }

        return {
            "success": True,
            "data": logs,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get recent logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/performance/summary")
async def get_performance_summary():
    """Get performance summary for the last 24 hours"""

    try:
        performance_monitor = PerformanceMonitor()
        summary = await performance_monitor.get_performance_summary()

        return {
            "success": True,
            "performance_summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance summary"
        )


@router.post("/maintenance/mode")
@require_admin
async def toggle_maintenance_mode(
    enabled: bool, message: Optional[str] = None, current_user=Depends(get_current_user)
):
    """Toggle maintenance mode (admin only)"""

    try:
        # This would integrate with maintenance mode system
        # For now, just log the action

        action = "enabled" if enabled else "disabled"
        logger.info(
            f"Maintenance mode {action}",
            user_id=current_user.get("id"),
            maintenance_message=message,
        )

        return {
            "success": True,
            "maintenance_mode": enabled,
            "message": message or f"Maintenance mode {action}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to toggle maintenance mode: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle maintenance mode")


@router.get("/system/info")
async def get_system_info():
    """Get basic system information"""

    try:
        import platform
        import psutil
        import sys

        system_info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "python": {"version": sys.version, "executable": sys.executable},
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": {
                    "total": psutil.disk_usage("/").total,
                    "free": psutil.disk_usage("/").free,
                },
            },
        }

        return {
            "success": True,
            "system_info": system_info,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system info")


@router.post("/cleanup/inactive-connections")
@require_admin
async def cleanup_inactive_connections(current_user=Depends(get_current_user)):
    """Cleanup inactive WebSocket connections (admin only)"""

    try:
        await websocket_manager.cleanup_inactive_connections()

        logger.info(
            "Inactive connections cleanup completed", user_id=current_user.get("id")
        )

        return {
            "success": True,
            "message": "Inactive connections cleaned up",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cleanup inactive connections: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to cleanup inactive connections"
        )


@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""

    try:
        # Check if critical services are ready
        critical_services = [
            "conversation_manager",
            "section_optimizer",
            "job_matcher",
            "feedback_analyzer",
            "version_manager",
        ]

        health_status = await integration_service.health_check_all_services()

        for service in critical_services:
            if not health_status["services"].get(service, {}).get("healthy", False):
                raise HTTPException(
                    status_code=503, detail=f"Service {service} not ready"
                )

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Readiness check failed")


@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""

    try:
        # Basic liveness check - just ensure the service is responding
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Liveness check failed")
