"""
Rate limiting configuration using SlowAPI.
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def setup_rate_limiting(app: FastAPI, rate_limit: str = "60/minute", enabled: bool = True):
    """
    Set up rate limiting for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        rate_limit: Rate limit string (e.g., "60/minute", "1000/hour")
        enabled: Whether to enable rate limiting
    """
    if not enabled:
        return None
    
    # Create limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return limiter


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "error": "Too many requests",
            "message": f"Please slow down. You've exceeded the rate limit.",
            "retry_after": str(exc.detail),
        }
    )


# Rate limit presets
RATE_LIMITS = {
    "auth": "10/minute",  # Strict limit for auth endpoints
    "api": "60/minute",   # Standard API limit
    "upload": "20/minute", # File upload limit
    "search": "30/minute", # Search endpoint limit
    "public": "100/minute", # Public endpoints
}


def apply_rate_limits(app: FastAPI, limiter: Limiter):
    """
    Apply rate limits to specific routes.
    Note: This should be called after all routers are included.
    """
    from slowapi.middleware import SlowAPIMiddleware
    
    # Add middleware
    app.add_middleware(SlowAPIMiddleware)
    
    # You can apply limits to specific routes in the route decorators
    # Example: @limiter.limit(RATE_LIMITS["auth"])
    
    return limiter
