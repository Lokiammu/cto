from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import structlog
from datetime import datetime
import uuid

from backend.config import settings
from backend.database import connect_to_mongo, close_mongo_connection
from backend.middleware.error_handlers import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

# Import routers
from backend.api import auth, products, cart, loyalty, orders, users
from backend.websocket import chat
from backend.realtime.inventory import start_inventory_listener, stop_inventory_listener

# Import background tasks
from backend.tasks.cleanup import run_daily_cleanup
from backend.tasks.inventory_sync import sync_inventory, check_low_stock_alerts

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = logging.getLogger(__name__)


# Background task scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting FastAPI application...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Start inventory change listener
    await start_inventory_listener()
    
    # Start background tasks scheduler
    if settings.enable_background_tasks:
        # Daily cleanup at 2 AM
        scheduler.add_job(run_daily_cleanup, 'cron', hour=2, minute=0)
        
        # Inventory sync every 15 minutes
        scheduler.add_job(sync_inventory, 'interval', minutes=15)
        
        # Low stock alerts every hour
        scheduler.add_job(check_low_stock_alerts, 'interval', hours=1)
        
        scheduler.start()
        logger.info("Background tasks scheduler started")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop background tasks
    if settings.enable_background_tasks and scheduler.running:
        scheduler.shutdown()
        logger.info("Background tasks scheduler stopped")
    
    # Stop inventory listener
    await stop_inventory_listener()
    
    # Close database connection
    await close_mongo_connection()
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()
    
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} - Duration: {duration:.3f}s")
    
    return response


# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api_version
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI Backend API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(loyalty.router)
app.include_router(orders.router)
app.include_router(users.router)
app.include_router(chat.router)


# Initialize Sentry (optional)
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0 if settings.debug else 0.1,
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
