"""
Consolidated async FastAPI application for RunPrayers API.
Enhanced with proper dependency injection, async operations, and comprehensive error handling.
"""
from fastapi import FastAPI, HTTPException
import logging
import asyncio
from contextlib import asynccontextmanager
from .routers import prayers
from .core.prayer_service import get_prayer_service
from .core.supabase_client import cleanup_supabase
from .settings import validate_config, DATA_MODE

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Add file handler for production
        # logging.FileHandler("app.log")
    ]
)
log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async application lifespan management."""
    log.info("Starting RunPrayers API v2.0...")
    
    # Startup
    try:
        # Validate configuration
        if not validate_config():
            log.warning("Configuration validation failed - some features may not work")
        
        # Initialize prayer service (this will set up storage strategy)
        prayer_service = await get_prayer_service()
        log.info("Prayer service initialized with %s storage", 
                type(prayer_service.storage).__name__)
        
        # Test service health
        status = await prayer_service.get_service_status()
        if status.get("storage_healthy"):
            log.info("Service health check passed")
        else:
            log.warning("Service health check failed: %s", status.get("error"))
        
        log.info("RunPrayers API startup complete")
        
        yield
        
    except Exception as e:
        log.error("Failed to start application: %s", e, exc_info=True)
        raise
    
    # Shutdown
    log.info("Shutting down RunPrayers API...")
    try:
        # Cleanup database connections
        await cleanup_supabase()
        
        log.info("RunPrayers API shutdown complete")
    except Exception as e:
        log.error("Error during shutdown: %s", e, exc_info=True)

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="RunPrayers API",
    description="Prayer management system with email distribution - Enhanced with async operations and SOLID architecture",
    version="2.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(prayers.router)

# Legacy endpoints for backward compatibility
@app.post("/add_prayer")
async def add_prayer_legacy(payload):
    """Legacy endpoint redirect to new API."""
    return await prayers.add_prayer_endpoint(payload)

@app.get("/ping")
async def ping():
    """Simple health check endpoint."""
    return {"status": "alive", "version": "2.0.0"}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RunPrayers API",
        "version": "2.0.0",
        "description": "Prayer management system with email distribution",
        "data_mode": DATA_MODE,
        "features": [
            "Async operations",
            "Connection pooling", 
            "SOLID architecture",
            "Comprehensive error handling",
            "Health monitoring"
        ],
        "documentation": "/docs",
        "health": "/api/health"
    }
