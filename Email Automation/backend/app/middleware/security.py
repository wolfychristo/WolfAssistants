"""
Security middleware for WolfAssistants
Implements comprehensive security headers and protection
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse
import time
import hashlib
import hmac
from typing import Callable
import logging

# Configure security logging
security_logger = logging.getLogger("security")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Comprehensive security headers middleware"""
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key.encode()
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        # Start timing
        start_time = time.time()
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Log request
        security_logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add comprehensive security headers
        self._add_security_headers(response, request)
        
        # Add security monitoring headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = self._generate_request_id(request)
        
        # Log response
        security_logger.info(f"Response: {response.status_code} for {request.method} {request.url.path} from {client_ip} in {process_time:.3f}s")
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address"""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _generate_request_id(self, request: Request) -> str:
        """Generate unique request ID for tracking"""
        data = f"{request.url.path}{time.time()}{request.headers.get('user-agent', '')}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add comprehensive security headers"""
        
        # Content Security Policy - Strict CSP
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.gemini.google.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            "upgrade-insecure-requests; "
            "block-all-mixed-content"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HTTP Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options - Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection - XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - Control browser features
        permissions_policy = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "interest-cohort=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "bluetooth=(), "
            "clipboard-read=(), "
            "clipboard-write=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "fullscreen=(), "
            "gamepad=(), "
            "hid=(), "
            "idle-detection=(), "
            "local-fonts=(), "
            "midi=(), "
            "otp-credentials=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "serial=(), "
            "speaker-selection=(), "
            "storage-access=(), "
            "sync-xhr=(), "
            "unload=(), "
            "usb=(), "
            "web-share=(), "
            "xr-spatial-tracking=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # Cross-Origin Embedder Policy
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # Cross-Origin Opener Policy
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Cross-Origin Resource Policy
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Cache Control for sensitive endpoints
        if request.url.path.startswith("/api/v1/auth") or request.url.path.startswith("/api/v1/otp"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Server header - Hide server information
        response.headers["Server"] = "WolfAssistants/1.0"
        
        # Remove potentially dangerous headers
        headers_to_remove = [
            "X-Powered-By",
            "X-AspNet-Version",
            "X-AspNetMvc-Version"
        ]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """Security audit and monitoring middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.suspicious_patterns = [
            b"<script",
            b"javascript:",
            b"onload=",
            b"onerror=",
            b"onclick=",
            b"eval(",
            b"document.cookie",
            b"document.location",
            b"window.location",
            b"../",
            b"..\\",
            b"union select",
            b"drop table",
            b"delete from",
            b"insert into",
            b"update set",
            b"exec(",
            b"system(",
            b"cmd.exe",
            b"/bin/sh",
            b"<iframe",
            b"<object",
            b"<embed",
            b"<link",
            b"<meta",
            b"<style",
            b"<form",
            b"<input",
            b"<textarea",
            b"<select",
            b"<option",
            b"<button"
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        # Check for suspicious patterns in request
        await self._audit_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Audit response
        await self._audit_response(request, response)
        
        return response
    
    async def _audit_request(self, request: Request):
        """Audit incoming request for security threats"""
        client_ip = self._get_client_ip(request)
        
        # Check URL for suspicious patterns
        url_lower = str(request.url).lower()
        for pattern in self.suspicious_patterns:
            if pattern.decode() in url_lower:
                security_logger.warning(f"SUSPICIOUS URL PATTERN: {pattern.decode()} in {url_lower} from {client_ip}")
        
        # Check headers for suspicious content
        for header_name, header_value in request.headers.items():
            if isinstance(header_value, str):
                header_lower = header_value.lower()
                for pattern in self.suspicious_patterns:
                    if pattern.decode() in header_lower:
                        security_logger.warning(f"SUSPICIOUS HEADER: {header_name}={header_value} from {client_ip}")
        
        # Check query parameters
        for param_name, param_value in request.query_params.items():
            if isinstance(param_value, str):
                param_lower = param_value.lower()
                for pattern in self.suspicious_patterns:
                    if pattern.decode() in param_lower:
                        security_logger.warning(f"SUSPICIOUS QUERY PARAM: {param_name}={param_value} from {client_ip}")
    
    async def _audit_response(self, request: Request, response: StarletteResponse):
        """Audit response for security issues"""
        client_ip = self._get_client_ip(request)
        
        # Log high-risk responses
        if response.status_code >= 400:
            security_logger.warning(f"ERROR RESPONSE: {response.status_code} for {request.method} {request.url.path} from {client_ip}")
        
        # Check for sensitive data leakage
        if hasattr(response, 'body') and response.body:
            body_str = str(response.body).lower()
            sensitive_patterns = [
                "password",
                "secret",
                "key",
                "token",
                "error:",
                "exception:",
                "traceback:",
                "stack trace"
            ]
            for pattern in sensitive_patterns:
                if pattern in body_str:
                    security_logger.warning(f"POTENTIAL DATA LEAKAGE: {pattern} in response to {request.method} {request.url.path} from {client_ip}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
