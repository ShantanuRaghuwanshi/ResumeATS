"""
Integration service for connecting all components and services
Provides centralized error handling, logging, and service coordination
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import traceback
import json

from services.conversation_manager import ConversationManager
from services.section_optimizer import SectionOptimizer
from services.job_matcher import JobMatcher
from services.feedback_analyzer import FeedbackAnalyzer
from services.version_manager import VersionManager
from services.websocket_manager import (
    websocket_manager,
    send_notification,
    send_error_notification,
)
from services.cache_service import CacheService
from services.performance_monitor import PerformanceMonitor
from services.background_jobs import BackgroundJobService
from security.audit_logging import AuditLogger
from security.security_service import SecurityService
from services.llm_provider import get_llm_provider
from configs.config import get_logger

logger = get_logger(__name__)


class ServiceStatus:
    """Service status tracking"""

    def __init__(self, name: str):
        self.name = name
        self.is_healthy = True
        self.last_check = datetime.utcnow()
        self.error_count = 0
        self.last_error = None

    def mark_healthy(self):
        self.is_healthy = True
        self.last_check = datetime.utcnow()

    def mark_unhealthy(self, error: str):
        self.is_healthy = False
        self.last_check = datetime.utcnow()
        self.error_count += 1
        self.last_error = error


class IntegrationService:
    """
    Central integration service that coordinates all application components
    """

    def __init__(self):
        # Initialize default LLM provider for services that require it
        default_llm_config = {
            "api_key": "",  # Will be set from environment or config
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            # Try to create OpenAI provider as default, fallback to Ollama if that fails
            self.default_llm_provider = get_llm_provider("openai", default_llm_config)
        except Exception:
            # Fallback to Ollama if OpenAI is not available
            try:
                ollama_config = {
                    "model": "llama2",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                self.default_llm_provider = get_llm_provider("ollama", ollama_config)
            except Exception as e:
                logger.error(f"Failed to initialize LLM provider: {e}")
                # Create a minimal mock provider as last resort
                from services.llm_provider import LLMProviderBase
                class MockLLMProvider(LLMProviderBase):
                    def __init__(self, config):
                        super().__init__(config)
                    async def extract_personal_details(self, text):
                        return None
                    async def extract_sections(self, text):
                        return None
                    async def generate_conversation_response(self, message, context, history, profile=None):
                        return None
                self.default_llm_provider = MockLLMProvider({})
        
        # Initialize service instances
        self.conversation_manager = ConversationManager()
        self.section_optimizer = SectionOptimizer()
        self.job_matcher = JobMatcher(self.default_llm_provider)
        self.feedback_analyzer = FeedbackAnalyzer()
        self.version_manager = VersionManager()
        self.cache_service = CacheService()
        self.performance_monitor = PerformanceMonitor()
        self.background_jobs = BackgroundJobService()
        self.audit_logger = AuditLogger()
        self.security_service = SecurityService()

        # Service health tracking
        self.service_status: Dict[str, ServiceStatus] = {
            "conversation_manager": ServiceStatus("conversation_manager"),
            "section_optimizer": ServiceStatus("section_optimizer"),
            "job_matcher": ServiceStatus("job_matcher"),
            "feedback_analyzer": ServiceStatus("feedback_analyzer"),
            "version_manager": ServiceStatus("version_manager"),
            "websocket_manager": ServiceStatus("websocket_manager"),
            "cache_service": ServiceStatus("cache_service"),
            "background_jobs": ServiceStatus("background_jobs"),
        }

        # Circuit breaker states
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}

        # Fallback mechanisms
        self.fallback_enabled = True

    async def initialize(self):
        """Initialize all services and perform health checks"""

        logger.info("Initializing integration service...")

        try:
            # Initialize services in dependency order
            await self._initialize_core_services()
            await self._initialize_ai_services()
            await self._initialize_realtime_services()
            await self._initialize_background_services()

            # Perform initial health checks
            await self.health_check_all_services()

            logger.info("Integration service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize integration service: {e}")
            raise

    async def _initialize_core_services(self):
        """Initialize core services"""

        try:
            # Initialize cache service
            await self.cache_service.initialize()
            self.service_status["cache_service"].mark_healthy()

            # Initialize security service
            await self.security_service.initialize()

            # Initialize audit logging
            await self.audit_logger.initialize()

            # Initialize performance monitoring
            await self.performance_monitor.initialize()

        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            raise

    async def _initialize_ai_services(self):
        """Initialize AI-powered services"""

        try:
            # Initialize conversation manager
            await self.conversation_manager.initialize()
            self.service_status["conversation_manager"].mark_healthy()

            # Initialize section optimizer
            await self.section_optimizer.initialize()
            self.service_status["section_optimizer"].mark_healthy()

            # Initialize job matcher
            await self.job_matcher.initialize()
            self.service_status["job_matcher"].mark_healthy()

            # Initialize feedback analyzer
            await self.feedback_analyzer.initialize()
            self.service_status["feedback_analyzer"].mark_healthy()

            # Initialize version manager
            await self.version_manager.initialize()
            self.service_status["version_manager"].mark_healthy()

        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
            raise

    async def _initialize_realtime_services(self):
        """Initialize real-time services"""

        try:
            # WebSocket manager is already initialized globally
            self.service_status["websocket_manager"].mark_healthy()

        except Exception as e:
            logger.error(f"Failed to initialize real-time services: {e}")
            raise

    async def _initialize_background_services(self):
        """Initialize background services"""

        try:
            # Initialize background job manager
            self.service_status["background_jobs"].mark_healthy()

        except Exception as e:
            logger.error(f"Failed to initialize background services: {e}")
            raise

    async def health_check_all_services(self) -> Dict[str, Any]:
        """Perform health checks on all services"""

        health_results = {}
        overall_healthy = True

        for service_name, status in self.service_status.items():
            try:
                # Perform service-specific health check
                is_healthy = await self._health_check_service(service_name)

                if is_healthy:
                    status.mark_healthy()
                else:
                    status.mark_unhealthy("Health check failed")
                    overall_healthy = False

                health_results[service_name] = {
                    "healthy": is_healthy,
                    "last_check": status.last_check.isoformat(),
                    "error_count": status.error_count,
                    "last_error": status.last_error,
                }

            except Exception as e:
                status.mark_unhealthy(str(e))
                overall_healthy = False
                health_results[service_name] = {
                    "healthy": False,
                    "last_check": status.last_check.isoformat(),
                    "error_count": status.error_count,
                    "last_error": str(e),
                }

        return {
            "overall_healthy": overall_healthy,
            "services": health_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _health_check_service(self, service_name: str) -> bool:
        """Perform health check on a specific service"""

        try:
            if service_name == "conversation_manager":
                return await self.conversation_manager.health_check()
            elif service_name == "section_optimizer":
                return await self.section_optimizer.health_check()
            elif service_name == "job_matcher":
                return await self.job_matcher.health_check()
            elif service_name == "feedback_analyzer":
                return await self.feedback_analyzer.health_check()
            elif service_name == "version_manager":
                return await self.version_manager.health_check()
            elif service_name == "websocket_manager":
                return len(websocket_manager.connections) >= 0  # Basic check
            elif service_name == "cache_service":
                return await self.cache_service.health_check()
            elif service_name == "background_jobs":
                return await self.background_jobs.health_check()
            else:
                return True

        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return False

    async def handle_service_error(
        self,
        service_name: str,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Centralized error handling for all services
        """

        error_id = f"{service_name}_{operation}_{datetime.utcnow().timestamp()}"
        error_details = {
            "error_id": error_id,
            "service": service_name,
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Log error
        logger.error(f"Service error in {service_name}.{operation}: {error}")

        # Update service status
        if service_name in self.service_status:
            self.service_status[service_name].mark_unhealthy(str(error))

        # Audit log the error
        await self.audit_logger.log_error(error_details)

        # Check if circuit breaker should be triggered
        await self._check_circuit_breaker(service_name, error)

        # Attempt fallback if available
        fallback_result = await self._attempt_fallback(service_name, operation, context)

        # Notify relevant users if needed
        if context and context.get("user_id"):
            await send_error_notification(
                context.get("connection_id", ""),
                "service_error",
                f"An error occurred in {service_name}. Please try again.",
                error_id,
            )

        return {
            "success": False,
            "error_id": error_id,
            "error_message": str(error),
            "fallback_used": fallback_result is not None,
            "fallback_result": fallback_result,
        }

    async def _check_circuit_breaker(self, service_name: str, error: Exception):
        """Check and update circuit breaker state"""

        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure": None,
                "next_attempt": None,
            }

        breaker = self.circuit_breakers[service_name]
        breaker["failure_count"] += 1
        breaker["last_failure"] = datetime.utcnow()

        # Open circuit breaker if too many failures
        if breaker["failure_count"] >= 5 and breaker["state"] == "closed":
            breaker["state"] = "open"
            breaker["next_attempt"] = datetime.utcnow().timestamp() + 300  # 5 minutes
            logger.warning(f"Circuit breaker opened for {service_name}")

    async def _attempt_fallback(
        self, service_name: str, operation: str, context: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        """Attempt fallback mechanisms for failed operations"""

        if not self.fallback_enabled:
            return None

        try:
            # Service-specific fallback logic
            if service_name == "conversation_manager":
                return await self._conversation_fallback(operation, context)
            elif service_name == "section_optimizer":
                return await self._optimizer_fallback(operation, context)
            elif service_name == "job_matcher":
                return await self._job_matcher_fallback(operation, context)
            elif service_name == "feedback_analyzer":
                return await self._feedback_fallback(operation, context)

        except Exception as e:
            logger.error(f"Fallback failed for {service_name}.{operation}: {e}")

        return None

    async def _conversation_fallback(
        self, operation: str, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Fallback for conversation manager operations"""

        if operation == "send_message":
            # Return cached response or generic message
            return {
                "message": "I'm experiencing some technical difficulties. Please try again in a moment.",
                "suggestions": [],
                "fallback": True,
            }

        return None

    async def _optimizer_fallback(
        self, operation: str, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Fallback for section optimizer operations"""

        if operation == "optimize_section":
            # Return basic suggestions from cache or templates
            return {
                "suggestions": [
                    {
                        "type": "general",
                        "title": "Service Temporarily Unavailable",
                        "description": "AI optimization is temporarily unavailable. Please try again later.",
                        "fallback": True,
                    }
                ],
                "fallback": True,
            }

        return None

    async def _job_matcher_fallback(
        self, operation: str, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Fallback for job matcher operations"""

        if operation == "analyze_job_description":
            # Return basic analysis
            return {
                "analysis": {"skills": [], "requirements": [], "fallback": True},
                "message": "Job analysis is temporarily unavailable. Basic matching will be used.",
            }

        return None

    async def _feedback_fallback(
        self, operation: str, context: Dict[str, Any]
    ) -> Optional[Any]:
        """Fallback for feedback analyzer operations"""

        if operation == "analyze_change_impact":
            # Return basic feedback
            return {
                "feedback": {
                    "score": 0.5,
                    "message": "Detailed feedback is temporarily unavailable.",
                    "fallback": True,
                }
            }

        return None

    async def execute_with_error_handling(
        self,
        service_name: str,
        operation: str,
        func,
        *args,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a service operation with comprehensive error handling
        """

        start_time = datetime.utcnow()

        try:
            # Check circuit breaker
            if await self._is_circuit_breaker_open(service_name):
                return {
                    "success": False,
                    "error": "Service temporarily unavailable (circuit breaker open)",
                    "fallback_result": await self._attempt_fallback(
                        service_name, operation, context
                    ),
                }

            # Execute operation with performance monitoring
            with self.performance_monitor.track_operation(
                f"{service_name}.{operation}"
            ):
                result = await func(*args, **kwargs)

            # Reset circuit breaker on success
            await self._reset_circuit_breaker(service_name)

            # Log successful operation
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(
                f"Successfully executed {service_name}.{operation} in {execution_time:.2f}s"
            )

            return {"success": True, "result": result, "execution_time": execution_time}

        except Exception as e:
            return await self.handle_service_error(service_name, operation, e, context)

    async def _is_circuit_breaker_open(self, service_name: str) -> bool:
        """Check if circuit breaker is open for a service"""

        if service_name not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[service_name]

        if breaker["state"] == "open":
            if datetime.utcnow().timestamp() > breaker.get("next_attempt", 0):
                breaker["state"] = "half_open"
                return False
            return True

        return False

    async def _reset_circuit_breaker(self, service_name: str):
        """Reset circuit breaker on successful operation"""

        if service_name in self.circuit_breakers:
            breaker = self.circuit_breakers[service_name]
            if breaker["state"] in ["half_open", "open"]:
                breaker["state"] = "closed"
                breaker["failure_count"] = 0
                logger.info(f"Circuit breaker reset for {service_name}")

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""

        health_status = await self.health_check_all_services()
        websocket_stats = websocket_manager.get_connection_stats()
        performance_stats = await self.performance_monitor.get_stats()

        return {
            "system_health": health_status,
            "websocket_connections": websocket_stats,
            "performance_metrics": performance_stats,
            "circuit_breakers": {
                name: {
                    "state": breaker["state"],
                    "failure_count": breaker["failure_count"],
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def shutdown(self):
        """Gracefully shutdown all services"""

        logger.info("Shutting down integration service...")

        try:
            # Shutdown services in reverse dependency order
            await self.background_jobs.shutdown()
            await self.performance_monitor.shutdown()
            await self.cache_service.shutdown()

            logger.info("Integration service shutdown complete")

        except Exception as e:
            logger.error(f"Error during integration service shutdown: {e}")


# Global integration service instance
integration_service = IntegrationService()


# Decorator for automatic error handling
def with_error_handling(service_name: str, operation: str):
    """Decorator to automatically wrap service methods with error handling"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = kwargs.pop("_context", None)
            return await integration_service.execute_with_error_handling(
                service_name, operation, func, *args, context=context, **kwargs
            )

        return wrapper

    return decorator
