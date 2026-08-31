"""
Secure user schemas with masked credentials
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserProfileResponse(BaseModel):
    """Secure user profile response with masked credentials"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    username: Optional[str] = None
    company_name: Optional[str] = None
    team_size: Optional[str] = None
    revenue_size: Optional[str] = None
    social_link: Optional[str] = None
    calendly_link: Optional[str] = None
    heard_about_us: Optional[str] = None
    profile_image_url: Optional[str] = None
    position_title: Optional[str] = None
    
    # SMTP settings (masked)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # Always None in responses
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True
    
    # IMAP settings (masked)
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None  # Always None in responses
    imap_use_ssl: bool = True
    
    # Credential health (visible)
    smtp_last_tested: Optional[datetime] = None
    smtp_test_status: Optional[str] = None
    smtp_failure_count: int = 0
    
    class Config:
        from_attributes = True

class SMTPTestRequest(BaseModel):
    """Request model for testing SMTP credentials"""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool = True

class SMTPTestResponse(BaseModel):
    """Response model for SMTP test results"""
    success: bool
    message: str
    details: Optional[str] = None

class UserUpdateRequest(BaseModel):
    """Request model for updating user profile"""
    full_name: Optional[str] = None
    username: Optional[str] = None
    company_name: Optional[str] = None
    team_size: Optional[str] = None
    revenue_size: Optional[str] = None
    social_link: Optional[str] = None
    calendly_link: Optional[str] = None
    heard_about_us: Optional[str] = None
    profile_image_url: Optional[str] = None
    position_title: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    """Request model for changing password"""
    current_password: str
    new_password: str
    confirm_password: str
