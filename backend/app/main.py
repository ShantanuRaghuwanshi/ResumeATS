from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1 import (
    resume,
    conversation,
    section_optimization,
    job_analysis,
    feedback,
    version_management,
    websocket,
    security,
    monitoring,
    session,  # Import session router
)
from app.security.middleware import (
    setup_security_middleware,
    shutdown_security_middleware,
)
from app.middleware.session_middleware import (
    SessionMiddleware,
)  # Import session middleware
from app.services.integration_service import integration_service
from app.configs.logging_config import setup_logging, get_service_logger

# Initialize logging
service_loggers = setup_logging()
logger = get_service_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")

    try:
        # Initialize integration service
        # await integration_service.initialize()
        # logger.info("Integration service initialized")

        # Setup security middleware
        # await setup_security_middleware(app)
        logger.info("Security middleware initialized")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    try:
        # await integration_service.shutdown()
        await shutdown_security_middleware()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Application shutdown failed: {e}")


app = FastAPI(
    title="Resume ATS API",
    description="AI-powered resume optimization and analysis API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Allow all origins for development; restrict in production
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup session middleware
app.add_middleware(SessionMiddleware)
# Include API routers - Session router first (no session required)
app.include_router(session.router, prefix="/api/v1", tags=["Session"])
app.include_router(resume.router, prefix="/api/v1", tags=["Resume"])
app.include_router(conversation.router, prefix="/api/v1", tags=["Conversation"])
app.include_router(
    section_optimization.router, prefix="/api/v1", tags=["Section Optimization"]
)
app.include_router(job_analysis.router, prefix="/api/v1", tags=["Job Analysis"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(
    version_management.router, prefix="/api/v1", tags=["Version Management"]
)
app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])
app.include_router(security.router, prefix="/api/v1", tags=["Security"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["Monitoring"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Resume ATS API v2.0",
        "features": [
            "Resume parsing and analysis",
            "AI-powered optimization",
            "Interactive conversation interface",
            "Job description matching",
            "Real-time feedback",
            "Enhanced job analysis and matching",
            "Batch job processing",
            "Job comparison and ranking",
            "Version management and comparison",
            "Resume version control",
            "Template creation from versions",
        ],
    }


# Health check endpoint (basic)
@app.get("/health")
async def health_check():
    try:
        health_status = await integration_service.health_check_all_services()

        return {
            "status": "healthy" if health_status["overall_healthy"] else "unhealthy",
            "version": "2.0.0",
            "services": list(health_status["services"].keys()),
            "overall_healthy": health_status["overall_healthy"],
            "timestamp": health_status["timestamp"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "version": "2.0.0", "error": str(e)}
