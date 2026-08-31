"""
Input sanitization middleware for WolfAssistants
Protects against XSS and injection attacks
"""
import re
import html
import json
from typing import Any, Dict, List, Union, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse
import logging

# Configure sanitization logger
sanitization_logger = logging.getLogger("sanitization")

class InputSanitizer:
    """Comprehensive input sanitization"""
    
    def __init__(self):
        # Dangerous patterns to detect and block
        self.dangerous_patterns = [
            # Script injection patterns
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'data:application/javascript',
            
            # Event handlers
            r'on\w+\s*=',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
            r'onfocus\s*=',
            r'onblur\s*=',
            
            # HTML injection
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'<form[^>]*>',
            r'<input[^>]*>',
            r'<textarea[^>]*>',
            r'<select[^>]*>',
            r'<option[^>]*>',
            r'<button[^>]*>',
            
            # SQL injection patterns
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+set',
            r'alter\s+table',
            r'create\s+table',
            r'exec\s*\(',
            r'sp_',
            r'xp_',
            
            # Command injection patterns
            r';\s*rm\s+',
            r';\s*del\s+',
            r';\s*cat\s+',
            r';\s*ls\s+',
            r';\s*dir\s+',
            r';\s*type\s+',
            r';\s*echo\s+',
            r';\s*ping\s+',
            r';\s*nslookup\s+',
            r';\s*whoami',
            r';\s*id\s*$',
            r';\s*uname\s*$',
            
            # Path traversal
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'%252e%252e%252f',
            r'%252e%252e%255c',
            
            # LDAP injection (more specific patterns)
            r'\([^)]*\)(?=.*[=<>!&|])',  # Only flag parentheses when followed by LDAP operators
            r'(?<![a-zA-Z0-9])[=<>!](?![a-zA-Z0-9])',  # LDAP operators not in words
            r'(?<![a-zA-Z0-9])&(?![a-zA-Z0-9])',  # & not in words
            r'(?<![a-zA-Z0-9])\|(?![a-zA-Z0-9])',  # | not in words
            r'(?<![a-zA-Z0-9])!(?![a-zA-Z0-9])',  # ! not in words
            
            # NoSQL injection
            r'\$where',
            r'\$ne',
            r'\$gt',
            r'\$lt',
            r'\$regex',
            r'\$exists',
            r'\$in',
            r'\$nin',
            r'\$or',
            r'\$and',
            r'\$not',
            r'\$nor',
            r'\$all',
            r'\$elemMatch',
            r'\$size',
            r'\$type',
            r'\$mod',
            r'\$text',
            r'\$search',
            r'\$language',
            r'\$caseSensitive',
            r'\$diacriticSensitive',
            r'\$meta',
            r'\$slice',
            r'\$sort',
            r'\$natural',
            r'\$comment',
            r'\$explain',
            r'\$hint',
            r'\$maxScan',
            r'\$maxTimeMS',
            r'\$max',
            r'\$min',
            r'\$returnKey',
            r'\$showDiskLoc',
            r'\$snapshot',
            r'\$tailable',
            r'\$oplogReplay',
            r'\$noCursorTimeout',
            r'\$awaitData',
            r'\$exhaust',
            r'\$partial',
            r'\$readPreference',
            r'\$maxTimeMS',
            r'\$maxTime',
            r'\$maxAwaitTimeMS',
            r'\$maxAwaitTime',
            r'\$readConcern',
            r'\$writeConcern',
            r'\$collation',
            r'\$hint',
            r'\$comment',
            r'\$explain',
            r'\$query',
            r'\$orderby',
            r'\$sort',
            r'\$natural',
            r'\$max',
            r'\$min',
            r'\$returnKey',
            r'\$showDiskLoc',
            r'\$snapshot',
            r'\$tailable',
            r'\$oplogReplay',
            r'\$noCursorTimeout',
            r'\$awaitData',
            r'\$exhaust',
            r'\$partial',
            r'\$readPreference',
            r'\$maxTimeMS',
            r'\$maxTime',
            r'\$maxAwaitTimeMS',
            r'\$maxAwaitTime',
            r'\$readConcern',
            r'\$writeConcern',
            r'\$collation'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in self.dangerous_patterns]
        
        # Allowed HTML tags for content (if any)
        self.allowed_html_tags = {
            'b', 'i', 'u', 'em', 'strong', 'p', 'br', 'div', 'span',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
            'blockquote', 'code', 'pre', 'a', 'img'
        }
        
        # Allowed HTML attributes
        self.allowed_attributes = {
            'href', 'title', 'alt', 'src', 'width', 'height', 'class', 'id'
        }
    
    def sanitize_string(self, value: str, allow_html: bool = False) -> str:
        """Sanitize a string value"""
        if not isinstance(value, str):
            return value
        
        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                sanitization_logger.warning(f"Dangerous pattern detected: {pattern.pattern} in input: {value[:100]}...")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid input detected. Please remove potentially dangerous content."
                )
        
        if allow_html:
            # Allow safe HTML
            return self._sanitize_html(value)
        else:
            # Escape HTML entities
            return html.escape(value, quote=True)
    
    def _sanitize_html(self, value: str) -> str:
        """Sanitize HTML content"""
        # Remove dangerous tags and attributes
        # This is a simplified version - in production, use a proper HTML sanitizer like bleach
        import re
        
        # Remove script tags and their content
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove dangerous attributes
        value = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
        
        # Remove dangerous tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'meta', 'style', 'form', 'input', 'textarea', 'select', 'option', 'button']
        for tag in dangerous_tags:
            value = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', value, flags=re.IGNORECASE | re.DOTALL)
            value = re.sub(rf'<{tag}[^>]*/?>', '', value, flags=re.IGNORECASE)
        
        return value
    
    def sanitize_dict(self, data: Dict[str, Any], allow_html_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sanitize a dictionary recursively"""
        if allow_html_fields is None:
            allow_html_fields = []
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                allow_html = key in allow_html_fields
                sanitized[key] = self.sanitize_string(value, allow_html)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, allow_html_fields)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value, allow_html_fields)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def sanitize_list(self, data: List[Any], allow_html_fields: Optional[List[str]] = None) -> List[Any]:
        """Sanitize a list recursively"""
        if allow_html_fields is None:
            allow_html_fields = []
        
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item, allow_html_fields))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item, allow_html_fields))
            else:
                sanitized.append(item)
        
        return sanitized
    
    def sanitize_json(self, json_str: str) -> str:
        """Sanitize JSON string"""
        try:
            data = json.loads(json_str)
            sanitized_data = self.sanitize_dict(data)
            return json.dumps(sanitized_data)
        except json.JSONDecodeError:
            # If it's not valid JSON, treat as string
            return self.sanitize_string(json_str)
    
    def validate_email(self, email: str) -> str:
        """Validate and sanitize email address"""
        if not email or not isinstance(email, str):
            raise HTTPException(status_code=400, detail="Invalid email address")
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Sanitize email
        return self.sanitize_string(email.lower().strip())
    
    def validate_url(self, url: str) -> str:
        """Validate and sanitize URL"""
        if not url or not isinstance(url, str):
            raise HTTPException(status_code=400, detail="Invalid URL")
        
        # Basic URL validation
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Sanitize URL
        return self.sanitize_string(url.strip())

# Global sanitizer instance
input_sanitizer = InputSanitizer()

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Input sanitization middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        # Fields that are allowed to contain HTML
        self.html_allowed_fields = [
            'description', 'content', 'body', 'message', 'notes'
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> StarletteResponse:
        # Get client IP for logging
        client_ip = self._get_client_ip(request)
        
        # Sanitize request data
        try:
            sanitization_result = await self._sanitize_request(request)
            if sanitization_result:
                return sanitization_result
        except HTTPException as e:
            sanitization_logger.warning(f"Input sanitization failed for {client_ip}: {e.detail}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={"error": "Input sanitization failed", "message": str(e.detail)}
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _sanitize_request(self, request: Request):
        """Sanitize incoming request data"""
        # Sanitize query parameters
        if request.query_params:
            sanitized_params = {}
            for key, value in request.query_params.items():
                try:
                    sanitized_key = input_sanitizer.sanitize_string(key)
                    sanitized_value = input_sanitizer.sanitize_string(value)
                    sanitized_params[sanitized_key] = sanitized_value
                except HTTPException:
                    sanitization_logger.warning(f"Suspicious query parameter: {key}={value}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid query parameter", "message": "Suspicious content detected in query parameters"}
                    )
            
            # Replace query params (this is a simplified approach)
            # In a real implementation, you'd need to modify the request object
        
        # Sanitize headers (skip common safe headers)
        safe_headers = {'user-agent', 'accept', 'accept-language', 'accept-encoding', 'connection', 'upgrade-insecure-requests'}
        
        for header_name, header_value in request.headers.items():
            if isinstance(header_value, str) and header_name.lower() not in safe_headers:
                # Check for suspicious header content
                try:
                    input_sanitizer.sanitize_string(header_value)
                except HTTPException:
                    sanitization_logger.warning(f"Suspicious header content: {header_name}={header_value}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid header content", "message": "Suspicious content detected in headers"}
                    )
        
        return None  # No sanitization issues found
    
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

# Utility functions for manual sanitization
def sanitize_input(data: Any, allow_html_fields: Optional[List[str]] = None) -> Any:
    """Sanitize input data"""
    if isinstance(data, str):
        return input_sanitizer.sanitize_string(data)
    elif isinstance(data, dict):
        return input_sanitizer.sanitize_dict(data, allow_html_fields)
    elif isinstance(data, list):
        return input_sanitizer.sanitize_list(data, allow_html_fields)
    else:
        return data

def validate_email_input(email: str) -> str:
    """Validate and sanitize email input"""
    return input_sanitizer.validate_email(email)

def validate_url_input(url: str) -> str:
    """Validate and sanitize URL input"""
    return input_sanitizer.validate_url(url)
