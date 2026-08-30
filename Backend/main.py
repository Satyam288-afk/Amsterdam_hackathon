"""
Sambhaash AI - Main FastAPI Application
Entry point for the backend server
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from config import get_config
from services.database.supabase_client import get_db_client, close_db_client
from services.ngrok_setup import initialize_ngrok
from api.routes import lead_routes, rm_routes, admin_routes, kb_analytics_routes, call_routes, webhook_routes, whatsapp_routes, queue_routes, public_routes, summary_routes, recovery_routes

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== LIFESPAN CONTEXT ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # STARTUP
    logger.info("[APP] Starting Sambhaash AI Backend...")
    
    try:
        # Initialize ngrok tunnel if in development mode
        logger.info("[APP] Setting up ngrok tunnel...")
        await initialize_ngrok()
    except Exception as e:
        logger.error(f"[APP] Ngrok setup error: {e}")
    
    try:
        db = await get_db_client()
        health = await db.health_check()
        if health:
            logger.info("[APP] Database connection successful")
        else:
            logger.warning("[APP] Database health check failed - running in degraded mode")
    except Exception as e:
        logger.warning(f"[APP] Database connection failed - running in degraded mode: {str(e)}")
    
    yield
    
    # SHUTDOWN
    logger.info("[APP] Shutting down Sambhaash AI Backend...")
    try:
        await close_db_client()
        logger.info("[APP] Database connection closed")
    except Exception as e:
        logger.error(f"[APP] Error during shutdown: {str(e)}")


# ==================== APPLICATION SETUP ====================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    config = get_config()
    
    app = FastAPI(
        title="Sambhaash AI Revenue Recovery",
        description="Bounded multilingual recovery workflows for overdue B2B receivables",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # ==================== MIDDLEWARE ====================
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        # The local Vite server may choose a free port during a demo. Keep this
        # limited to loopback origins; deployed origins remain explicit above.
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=config.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.trusted_hosts
    )
    
    # ==================== ROUTES ====================
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Sambhaash AI Backend",
            "version": "1.0.0"
        }
    
    # API Routes
    app.include_router(lead_routes.router)
    app.include_router(rm_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(kb_analytics_routes.router)
    app.include_router(call_routes.router)
    app.include_router(webhook_routes.router)
    app.include_router(whatsapp_routes.router)
    app.include_router(queue_routes.router)
    app.include_router(public_routes.router)
    app.include_router(summary_routes.router)
    app.include_router(recovery_routes.router)
    
    # ==================== ROOT ENDPOINT ====================
    
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API info"""
        return {
            "name": "Sambhaash AI",
            "description": "AI receivables recovery agent for overdue B2B invoices",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "health": "/health",
                "recovery_demo": "/api/recovery/summary",
                "recovery_cases": "/api/recovery/cases"
            }
        }
    
    # ==================== ERROR HANDLERS ====================
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        logger.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected server error occurred"
            }
        )
    
    logger.info("[APP] FastAPI application created successfully")
    return app


# ==================== APPLICATION INSTANCE ====================

app = create_app()


# ==================== MAIN ====================

if __name__ == "__main__":
    config = get_config()
    
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
