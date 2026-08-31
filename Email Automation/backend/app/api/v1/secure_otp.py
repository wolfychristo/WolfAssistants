"""
Secure OTP-based password reset system with comprehensive security measures
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
import ssl
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import get_password_hash, verify_password
from app.core.password_validation import validate_password
from app.core.encryption import smtp_encryption
from app.core.audit import audit
from app.core.rate_limiting import (
    check_otp_generation_rate_limit,
    check_otp_verification_rate_limit,
    check_password_reset_rate_limit
)
from app.models.user import User
from app.models.token import PasswordResetOTP

router = APIRouter()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str

def _test_smtp_connection(host: str, port: int, username: str, password: str, use_tls: bool) -> bool:
    """Test SMTP connection without sending email"""
    try:
        context = ssl.create_default_context()
        if port == 465 and not use_tls:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if use_tls:
                server.starttls(context=context)
        
        server.login(username, password)
        server.quit()
        return True
    except Exception:
        return False

def _send_system_email(to_email: str, subject: str, text_body: str) -> bool:
    """Send email using system email configuration for OTPs and notifications"""
    msg = MIMEText(text_body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = settings.SYSTEM_EMAIL_FROM
    msg['To'] = to_email
    
    # Use system email configuration
    host = settings.SYSTEM_EMAIL_HOST
    port = int(settings.SYSTEM_EMAIL_PORT or (587 if settings.SYSTEM_EMAIL_USE_TLS else 465))
    username = settings.SYSTEM_EMAIL_USER or ''
    password = settings.SYSTEM_EMAIL_PASSWORD or ''
    
    if not host or not username or not password:
        raise HTTPException(
            status_code=500,
            detail="System email configuration missing. Please configure SYSTEM_EMAIL_HOST, SYSTEM_EMAIL_USER, and SYSTEM_EMAIL_PASSWORD"
        )
    
    try:
        context = ssl.create_default_context()
        if port == 465 and not settings.SYSTEM_EMAIL_USE_TLS:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if settings.SYSTEM_EMAIL_USE_TLS:
                server.starttls(context=context)
        
        server.login(username, password)
        server.sendmail(settings.SYSTEM_EMAIL_FROM, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send system email: {e}"
        )

def _send_secure_email(user_row: User | None, to_email: str, subject: str, text_body: str) -> bool:
    """Send email using user's SMTP settings with fallback to global settings"""
    msg = MIMEText(text_body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = (user_row.smtp_from if user_row and user_row.smtp_from else (settings.EMAIL_FROM or settings.EMAIL_USER or ''))
    msg['To'] = to_email
    
    # Try per-user SMTP first if configured and valid
    if user_row and user_row.smtp_host and user_row.smtp_username and user_row.smtp_password:
        try:
            use_tls = True if user_row.smtp_use_tls is None else bool(user_row.smtp_use_tls)
            port = int(user_row.smtp_port or (587 if use_tls else 465))
            
            # Decrypt password for SMTP use
            decrypted_password = user_row.get_smtp_password()
            if not decrypted_password:
                raise ValueError("Failed to decrypt SMTP password")
            
            # Test connection first
            if not _test_smtp_connection(user_row.smtp_host, port, user_row.smtp_username, decrypted_password, use_tls):
                raise ValueError("SMTP connection test failed")
            
            # Send email
            context = ssl.create_default_context()
            if port == 465 and not use_tls:
                server = smtplib.SMTP_SSL(user_row.smtp_host, port, context=context, timeout=15)
            else:
                server = smtplib.SMTP(user_row.smtp_host, port, timeout=15)
                if use_tls:
                    server.starttls(context=context)
            
            server.login(user_row.smtp_username, decrypted_password)
            server.sendmail(msg['From'], [to_email], msg.as_string())
            server.quit()
            
            # Clear password from memory
            decrypted_password = None
            
            return True
        except Exception as e:
            # Log the error but don't expose it
            audit.log_smtp_test_attempt(user_row.id, False, "SMTP send failed")
            # Fall through to global SMTP
    
    # Fallback to global settings
    host = settings.EMAIL_HOST
    port = int(settings.EMAIL_PORT or (587 if settings.EMAIL_USE_TLS else 465))
    username = settings.EMAIL_USER or ''
    password = settings.EMAIL_PASSWORD or ''
    from_addr = (settings.EMAIL_FROM or settings.EMAIL_USER or '')
    
    if not host or not username or not password:
        raise HTTPException(
            status_code=500,
            detail="Email service not configured. Please contact support."
        )
    
    try:
        context = ssl.create_default_context()
        if port == 465 and not settings.EMAIL_USE_TLS:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if settings.EMAIL_USE_TLS:
                server.starttls(context=context)
        
        server.login(username, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Please try again later."
        )

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Request password reset OTP"""
    # Check rate limiting
    check_otp_generation_rate_limit(http_request, request.email)
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if user exists or not
        audit.log_otp_generation(request.email, False)
        return {
            "message": "If an account with this email exists, you will receive a password reset code."
        }
    
    # Generate structured OTP: 2 numbers, 2 uppercase, 2 lowercase
    from app.core.otp_utils import generate_structured_otp
    otp_code = generate_structured_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store OTP in database
    existing_otp = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id
    ).first()
    
    if existing_otp:
        # Use SQLAlchemy update method for Column assignments
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == existing_otp.id).update({
            "otp_code": otp_code,
            "expires_at": expires_at,
            "used": False,
            "attempts": 0
        })
    else:
        new_otp = PasswordResetOTP(
            email=request.email,
            otp_code=otp_code,
            expires_at=expires_at
        )
        db.add(new_otp)
    
    db.commit()
    
    # Send OTP email
    try:
        subject = "🔐 Password Reset OTP - WolfAssistants"
        body = f"""
Hello {user.full_name or 'User'},

You have requested to reset your password for WolfAssistants.

Your OTP (One-Time Password) is: {otp_code}

This OTP will expire in 10 minutes.

If you didn't request this password reset, please ignore this email.

Best regards,
WolfAssistants Team

---
This is an automated message. Please do not reply to this email.
        """
        
        success = _send_system_email(request.email, subject, body)
        
        if success:
            audit.log_otp_generation(request.email, True)
            return {
                "message": "Password reset code sent to your email address."
            }
        else:
            audit.log_otp_generation(request.email, False)
            raise HTTPException(
                status_code=500,
                detail="Failed to send email. Please try again later."
            )
    
    except Exception as e:
        audit.log_otp_generation(request.email, False)
        raise HTTPException(
            status_code=500,
            detail="Failed to send email. Please try again later."
        )

@router.post("/verify-otp")
async def verify_otp(
    request: VerifyOTPRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Verify OTP code"""
    # Check rate limiting
    check_otp_verification_rate_limit(http_request, request.email)
    
    # Get user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found."
        )
    
    # Find OTP record
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id
    ).first()
    
    if not otp_record:
        audit.log_otp_verification(request.email, False, 0)
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP code."
        )
    
    # Check if OTP is expired
    if otp_record.expires_at is not None and datetime.utcnow() > otp_record.expires_at:  # type: ignore
        attempts = getattr(otp_record, 'attempts', 0) or 0
        audit.log_otp_verification(request.email, False, attempts)
        raise HTTPException(
            status_code=400,
            detail="OTP code has expired. Please request a new one."
        )
    
    # Check if OTP is already used
    if otp_record.used is not None and otp_record.used:  # type: ignore
        attempts = getattr(otp_record, 'attempts', 0) or 0
        audit.log_otp_verification(request.email, False, attempts)
        raise HTTPException(
            status_code=400,
            detail="OTP code has already been used. Please request a new one."
        )
    
    # Check attempts limit
    attempts = getattr(otp_record, 'attempts', 0) or 0
    if attempts >= 3:
        audit.log_otp_verification(request.email, False, attempts)
        raise HTTPException(
            status_code=400,
            detail="Too many failed attempts. Please request a new OTP code."
        )
    
    # Validate OTP format first
    from app.core.otp_utils import validate_structured_otp
    if not validate_structured_otp(request.otp):
        audit.log_otp_verification(request.email, False, attempts)
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP format. Please enter the 6-character code with 2 numbers, 2 uppercase, and 2 lowercase letters."
        )
    
    # Verify OTP
    if otp_record.otp_code != request.otp:  # type: ignore
        # Use SQLAlchemy update method for Column assignments
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == otp_record.id).update({
            "attempts": attempts + 1
        })
        db.commit()
        
        audit.log_otp_verification(request.email, False, attempts + 1)
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP code. Please try again."
        )
    
    # OTP is valid
    audit.log_otp_verification(request.email, True, attempts)
    return {
        "message": "OTP verified successfully. You can now reset your password."
    }

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Reset password with OTP verification"""
    # Check rate limiting
    check_password_reset_rate_limit(http_request, request.email)
    
    # Validate password confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match."
        )
    
    # Validate password (including breach check) - replaces old length check
    await validate_password(request.new_password)
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found."
        )
    
    # Find and verify OTP
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id
    ).first()
    
    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP code."
        )
    
    # Check if OTP is expired
    if otp_record.expires_at is not None and datetime.utcnow() > otp_record.expires_at:  # type: ignore
        raise HTTPException(
            status_code=400,
            detail="OTP code has expired. Please request a new one."
        )
    
    # Check if OTP is already used
    if otp_record.used is not None and otp_record.used:  # type: ignore
        raise HTTPException(
            status_code=400,
            detail="OTP code has already been used. Please request a new one."
        )
    
    # Validate OTP format first
    from app.core.otp_utils import validate_structured_otp
    if not validate_structured_otp(request.otp):
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP format. Please enter the 6-character code with 2 numbers, 2 uppercase, and 2 lowercase letters."
        )
    
    # Verify OTP
    if otp_record.otp_code != request.otp:  # type: ignore
        # Use SQLAlchemy update method for Column assignments
        attempts = getattr(otp_record, 'attempts', 0) or 0
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == otp_record.id).update({
            "attempts": attempts + 1
        })
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP code. Please try again."
        )
    
    # Check if new password is different from current
    if verify_password(request.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password."
        )
    
    try:
        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        
        # Mark OTP as used
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == otp_record.id).update({
            "used": True
        })
        
        db.commit()
        
        audit.log_password_change(user.id, True)
        
        return {
            "message": "Password reset successfully. You can now login with your new password."
        }
    
    except Exception as e:
        db.rollback()
        audit.log_password_change(user.id, False)
        raise HTTPException(
            status_code=500,
            detail="Failed to reset password. Please try again later."
        )

