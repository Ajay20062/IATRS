"""
IATRS - Intelligent Applicant Tracking System
Main FastAPI Application Entry Point

Version: 2.0.0
"""
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, engine
from app.routes.analytics_routes import router as analytics_router
from app.routes.application_routes import router as application_router
from app.routes.auth_routes import router as auth_router
from app.routes.interview_routes import router as interview_router
from app.routes.job_routes import router as job_router
from app.routes.notification_routes import router as notification_router
from app.routes.oauth_routes import router as oauth_router
from app.routes.profile_routes import router as profile_router
from app.routes.system_routes import router as system_router
from app.schema_migrations import ensure_schema_compatibility
from app.utils.logging_config import setup_logging, setup_exception_handlers, performance_monitor_middleware
from app.utils.rate_limiter import setup_rate_limiting

# Get settings
settings = get_settings()

# Setup logging
logger = setup_logging(settings.log_level, settings.log_file)


# WebSocket Connection Manager
class ConnectionManager:
    """Manage WebSocket connections for real-time notifications."""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, user_type: str) -> str:
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        connection_key = f"{user_type}:{user_id}"
        
        if connection_key not in self.active_connections:
            self.active_connections[connection_key] = []
        self.active_connections[connection_key].append(websocket)
        
        logger.info(f"WebSocket connected: {connection_key}")
        return connection_key
    
    def disconnect(self, websocket: WebSocket, user_id: int, user_type: str):
        """Remove a WebSocket connection."""
        connection_key = f"{user_type}:{user_id}"
        if connection_key in self.active_connections:
            self.active_connections[connection_key].remove(websocket)
            if not self.active_connections[connection_key]:
                del self.active_connections[connection_key]
        logger.info(f"WebSocket disconnected: {user_type}:{user_id}")
    
    async def send_personal_message(self, message: dict, user_id: int, user_type: str):
        """Send a message to a specific user."""
        connection_key = f"{user_type}:{user_id}"
        if connection_key in self.active_connections:
            for connection in self.active_connections[connection_key]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting WebSocket message: {e}")


# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting IATRS Application v2.0.0")
    
    if settings.auto_create_tables:
        try:
            Base.metadata.create_all(bind=engine)
            ensure_schema_compatibility(engine)
            logger.info("Database tables ensured.")
        except Exception as e:
            logger.exception(f"Failed to auto-create database tables: {e}")
    
    # Setup rate limiting
    if settings.enable_rate_limit:
        limiter = setup_rate_limiting(app, f"{settings.rate_limit_per_minute}/minute", True)
        logger.info("Rate limiting enabled.")
    
    logger.info(f"Application started successfully on {settings.cors_origins}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    manager.active_connections.clear()
    logger.info("Application shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Applicant Tracking System with AI-powered features",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance monitoring middleware
app.middleware("http")(performance_monitor_middleware)

# Include routers
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(job_router)
app.include_router(application_router)
app.include_router(interview_router)
app.include_router(profile_router)
app.include_router(notification_router)
app.include_router(analytics_router)
app.include_router(system_router)

# Setup exception handlers
setup_exception_handlers(app)

# Static files
frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="frontend-css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="frontend-js")

# Uploads directory
uploads_dir = Path(settings.upload_dir)
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/", include_in_schema=False)
def home():
    """Root endpoint - redirect to frontend or show API info."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return RedirectResponse(
            url="/frontend/index.html",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    return {
        "message": "IATRS API is running",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/{page_name}.html", include_in_schema=False)
def frontend_pages(page_name: str):
    """Serve frontend HTML pages."""
    page_file = frontend_dir / f"{page_name}.html"
    if page_file.exists():
        return FileResponse(page_file)
    raise HTTPException(status_code=404, detail="Page not found")


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": "connected",
        "debug": settings.debug,
    }


@app.get("/monitoring/performance", tags=["Monitoring"])
def get_performance_metrics():
    """Get current performance metrics."""
    return performance_monitor.get_metrics()


# WebSocket endpoint for real-time notifications
@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.
    Clients should connect with: ws://host/ws/notifications?user_id={id}&user_type={type}
    """
    await websocket.receive()  # Wait for initial connection data
    
    try:
        data = await websocket.receive_json()
        user_id = data.get("user_id")
        user_type = data.get("user_type")
        
        if not user_id or not user_type:
            await websocket.close(code=4000, reason="Missing user_id or user_type")
            return
        
        connection_key = await manager.connect(websocket, user_id, user_type)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "connection_key": connection_key,
            "message": "Successfully connected to notification service",
        })
        
        # Keep connection alive
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id, user_type)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=4001, reason=str(e))
        except Exception:
            pass


# Helper function to send notifications
async def create_notification(
    db: AsyncGenerator,
    user_id: int,
    user_type: str,
    title: str,
    message: str,
    notification_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
    send_email: bool = True,
):
    """Create a notification and send it via WebSocket."""
    from app import models
    from app.database import SessionLocal
    
    db_session = SessionLocal()
    try:
        notification = models.Notification(
            user_id=user_id,
            user_type=user_type,
            title=title,
            message=message,
            notification_type=notification_type,
            related_type=related_type,
            related_id=related_id,
            send_email=send_email,
        )
        db_session.add(notification)
        db_session.commit()
        
        # Send via WebSocket
        await manager.send_personal_message(
            {
                "type": "notification",
                "notification_id": notification.notification_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "created_at": str(notification.created_at),
            },
            user_id,
            user_type,
        )
        
        return notification
    finally:
        db_session.close()


# Import Session for helper function
from sqlalchemy.orm import Session
