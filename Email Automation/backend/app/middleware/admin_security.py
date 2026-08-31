from fastapi import Request, HTTPException
from typing import List
import ipaddress
import os

# Admin IP whitelist - can be configured via environment variables
ADMIN_ALLOWED_IPS = os.getenv('ADMIN_ALLOWED_IPS', '').split(',') if os.getenv('ADMIN_ALLOWED_IPS') else []
ADMIN_REQUIRE_VPN = os.getenv('ADMIN_REQUIRE_VPN', 'false').lower() == 'true'

def is_ip_allowed(client_ip: str) -> bool:
    """Check if client IP is in the admin whitelist."""
    if not ADMIN_ALLOWED_IPS or not ADMIN_ALLOWED_IPS[0]:
        return True  # No whitelist configured, allow all
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        
        for allowed_ip in ADMIN_ALLOWED_IPS:
            allowed_ip = allowed_ip.strip()
            if not allowed_ip:
                continue
                
            # Handle CIDR notation
            if '/' in allowed_ip:
                if client_ip_obj in ipaddress.ip_network(allowed_ip, strict=False):
                    return True
            else:
                # Handle single IP
                if str(client_ip_obj) == allowed_ip:
                    return True
                    
    except (ipaddress.AddressValueError, ValueError):
        return False
    
    return False

def check_admin_security(request: Request) -> bool:
    """Check admin security requirements."""
    # Get client IP
    client_ip = request.client.host
    
    # Check X-Forwarded-For header (for reverse proxies)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        client_ip = real_ip
    
    # IP whitelist check
    if not is_ip_allowed(client_ip):
        return False
    
    # Additional security checks can be added here
    # e.g., VPN detection, time-based access, etc.
    
    return True

def require_admin_security(request: Request):
    """Middleware to require admin security checks."""
    if not check_admin_security(request):
        raise HTTPException(
            status_code=403,
            detail="Access denied. Your IP address is not authorized for admin access."
        )
