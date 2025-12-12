from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base exception class"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthError(AppException):
    """Authentication error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ValidationError(AppException):
    """Validation error"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class NotFoundError(AppException):
    """Not found error"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class PermissionError(AppException):
    """Permission error"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class RateLimitError(AppException):
    """Rate limit error"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom app exceptions"""
    request_id = str(uuid.uuid4())
    logger.error(f"Request {request_id}: {exc.message}", extra={
        "request_id": request_id,
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "request_id": request_id
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    request_id = str(uuid.uuid4())
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"Validation error {request_id}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "details": errors,
            "request_id": request_id
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    request_id = str(uuid.uuid4())
    logger.error(f"HTTP error {request_id}: {exc.detail}", extra={
        "request_id": request_id,
        "status_code": exc.status_code,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    request_id = str(uuid.uuid4())
    logger.error(f"Unhandled error {request_id}: {str(exc)}", extra={
        "request_id": request_id,
        "path": request.url.path,
        "traceback": traceback.format_exc()
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request_id
        }
    )
