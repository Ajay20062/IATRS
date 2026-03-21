"""
Comprehensive logging and monitoring utilities.
"""
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import time
import json


def setup_logging(log_level: str = "INFO", log_file: str = "logs/iatrs.log") -> logging.Logger:
    """
    Set up comprehensive logging with file rotation and console output.
    """
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("iatrs")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        log_path.parent / "error.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(error_handler)
    
    return logger


def create_audit_logger(db_session_func) -> logging.Logger:
    """
    Create an audit logger that logs to both file and database.
    """
    audit_logger = logging.getLogger("iatrs.audit")
    audit_logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if not audit_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | AUDIT | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        audit_logger.addHandler(handler)
    
    return audit_logger


async def log_request_middleware(request: Request, call_next):
    """
    Middleware to log all HTTP requests with timing.
    """
    # Start timer
    start_time = time.time()
    
    # Get request details
    method = request.method
    url = str(request.url)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log request
    logging.getLogger("iatrs.requests").info(
        f"{method} {url} from {client_ip} - {user_agent}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logging.getLogger("iatrs.requests").info(
            f"{method} {url} - Status: {response.status_code} - Duration: {duration:.3f}s"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(f"{duration:.3f}s")
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        # Log error
        logging.getLogger("iatrs.errors").error(
            f"{method} {url} - Error after {duration:.3f}s: {str(e)}",
            exc_info=True
        )
        
        raise


def setup_exception_handlers(app: FastAPI):
    """
    Set up global exception handlers for comprehensive error logging.
    """
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Log the exception
        logging.getLogger("iatrs.errors").error(
            f"Unhandled exception on {request.method} {request.url}: {str(exc)}",
            exc_info=True,
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
            }
        )
        
        # Return JSON error response
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": type(exc).__name__,
            }
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        logging.getLogger("iatrs.requests").warning(
            f"404 Not Found: {request.method} {request.url}"
        )
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"}
        )


class PerformanceMonitor:
    """
    Monitor application performance metrics.
    """
    
    def __init__(self):
        self.request_times = []
        self.error_counts = {}
        self.start_time = datetime.now()
    
    def record_request(self, duration: float, endpoint: str, status_code: int):
        """Record a request's performance metrics."""
        self.request_times.append({
            "timestamp": datetime.now(),
            "duration": duration,
            "endpoint": endpoint,
            "status_code": status_code,
        })
        
        # Keep only last 1000 requests
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
        
        # Track errors
        if status_code >= 400:
            self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
    
    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        if not self.request_times:
            return {
                "total_requests": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "error_rate": 0,
                "uptime_hours": 0,
            }
        
        durations = [r["duration"] for r in self.request_times]
        errors = sum(1 for r in self.request_times if r["status_code"] >= 400)
        
        return {
            "total_requests": len(self.request_times),
            "avg_response_time": sum(durations) / len(durations),
            "min_response_time": min(durations),
            "max_response_time": max(durations),
            "error_rate": errors / len(self.request_times) * 100,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "top_errors": dict(sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


async def performance_monitor_middleware(request: Request, call_next):
    """
    Middleware to monitor request performance.
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Record metrics
        performance_monitor.record_request(
            duration=duration,
            endpoint=request.url.path,
            status_code=response.status_code,
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        # Record error
        performance_monitor.record_request(
            duration=duration,
            endpoint=request.url.path,
            status_code=500,
        )
        
        raise


# Note: The performance endpoint is defined in main.py
# @router.get("/monitoring/performance")
async def get_performance_metrics():
    """Get current performance metrics."""
    return performance_monitor.get_metrics()
