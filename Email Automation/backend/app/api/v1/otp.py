from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
import ssl

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import get_password_hash
from app.core.password_validation import validate_password
from app.models.user import User
from app.models.token import PasswordResetOTP
from typing import Any, cast

router = APIRouter()

def _try_send(host: str, port: int, username: str, password: str, from_addr: str, to_email: str, msg: MIMEText, use_tls: bool) -> None:
    context = ssl.create_default_context()
    if int(port or 0) == 465 and not use_tls:
        server = smtplib.SMTP_SSL(host, int(port), context=context, timeout=15)
        server.ehlo()
    else:
        server = smtplib.SMTP(host, int(port), timeout=15)
        server.ehlo()
        if use_tls:
            server.starttls(context=context)
            server.ehlo()
    server.login(username, password)
    server.sendmail(from_addr, [to_email], msg.as_string())
    server.quit()

def _send_system_email(to_email: str, subject: str, text_body: str):
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
        raise HTTPException(status_code=500, detail="System email configuration missing. Please configure SYSTEM_EMAIL_HOST, SYSTEM_EMAIL_USER, and SYSTEM_EMAIL_PASSWORD")
    
    try:
        _try_send(host, port, username, password, settings.SYSTEM_EMAIL_FROM, to_email, msg, settings.SYSTEM_EMAIL_USE_TLS)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send system email: {e}")

def _send_simple_text_prefer_user(user_row: User | None, to_email: str, subject: str, text_body: str):
    msg = MIMEText(text_body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = (user_row.smtp_from if user_row and user_row.smtp_from else (settings.EMAIL_FROM or settings.EMAIL_USER or ''))
    msg['To'] = to_email
    
    # Try per-user SMTP first if configured
    last_error: Exception | None = None
    if user_row and user_row.smtp_host and user_row.smtp_username and user_row.smtp_password:
        try:
            use_tls = True if user_row.smtp_use_tls is None else bool(user_row.smtp_use_tls)
            port = int(user_row.smtp_port or (587 if use_tls else 465))
            # Decrypt password for SMTP use
            decrypted_password = user_row.get_smtp_password()
            if not decrypted_password:
                raise ValueError("Failed to decrypt SMTP password")
            _try_send(user_row.smtp_host, port, user_row.smtp_username, decrypted_password, msg['From'], to_email, msg, use_tls)
            return
        except Exception as e:
            last_error = e
            if settings.DEBUG:
                pass
    
    # Fallback to global settings
    host = settings.EMAIL_HOST
    port = int(settings.EMAIL_PORT or (587 if settings.EMAIL_USE_TLS else 465))
    username = settings.EMAIL_USER or ''
    password = settings.EMAIL_PASSWORD or ''
    from_addr = (settings.EMAIL_FROM or settings.EMAIL_USER or '')
    
    if not host or not username or not password:
        error_msg = "Global SMTP settings missing. Please configure EMAIL_HOST, EMAIL_USER, and EMAIL_PASSWORD in your .env file"
        if settings.DEBUG:
            error_msg += f" or set up per-user SMTP settings. Per-user error: {last_error}"
        raise HTTPException(status_code=500, detail=error_msg)
    
    try:
        _try_send(host, port, username, password, from_addr, to_email, msg, settings.EMAIL_USE_TLS)
    except Exception as e2:
        error_msg = f"Global SMTP failed: {e2}"
        if last_error:
            error_msg += f" (Per-user SMTP also failed: {last_error})"
        if settings.DEBUG:
            raise HTTPException(status_code=500, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail="Email send failed. Please check your SMTP settings.")

class ForgotPasswordOtpRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password-otp")
def forgot_password_otp(payload: ForgotPasswordOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    # Check if email exists in database
    if not user:
        return {"message": "This email is not registered in our system", "exists": False}
    
    # Email exists, generate and send OTP
    code = PasswordResetOTP.generate_otp(length=6)
    otp = PasswordResetOTP(
        user_id=user.id,
        otp_code=code,
        expires_at=PasswordResetOTP.expiry_in(minutes=10),
    )
    db.add(otp)
    db.commit()
    
    try:
        _send_system_email(
            user.email,
            "🔐 Password Reset OTP - WolfAssistants",
            f"""Hello {user.full_name or 'User'},

You have requested to reset your password for WolfAssistants.

Your OTP (One-Time Password) is: {code}

This OTP will expire in 10 minutes.

If you didn't request this password reset, please ignore this email.

Best regards,
WolfAssistants Team

---
This is an automated message. Please do not reply to this email.
""",
        )
    except HTTPException:
        # If email sending fails, still return success but note the issue
        return {"message": "OTP generated but failed to send email. Please try again later.", "exists": True, "otp_sent": False}
    
    return {"message": "OTP has been sent to the email ID", "exists": True, "otp_sent": True}

class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str

@router.post("/verify-reset-otp")
def verify_reset_otp(payload: VerifyResetOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Email doesn't exist
        raise HTTPException(status_code=400, detail="This email is not registered in our system")
    
    rec = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.otp_code == payload.otp,
            PasswordResetOTP.used == False,  # SQLAlchemy expression
        )
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )
    from datetime import datetime as _dt
    if rec is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    exp = cast(Any, rec.expires_at)
    if exp is None or exp < _dt.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    # Track attempts for basic rate limiting without static typing issues
    try:
        current_attempts = getattr(rec, "attempts", 0) or 0
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == rec.id).update({PasswordResetOTP.attempts: current_attempts + 1})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "OTP verified"}

class ResetPasswordWithOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str

@router.post("/reset-password-otp")
async def reset_password_with_otp(payload: ResetPasswordWithOtpRequest, db: Session = Depends(get_db)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password (including breach check)
    await validate_password(payload.new_password)
    
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Email doesn't exist
        raise HTTPException(status_code=400, detail="This email is not registered in our system")
    
    rec = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.otp_code == payload.otp,
            PasswordResetOTP.used == False,  # SQLAlchemy expression
        )
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )
    from datetime import datetime as _dt
    if rec is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    exp2 = cast(Any, rec.expires_at)
    if exp2 is None or exp2 < _dt.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    user.hashed_password = get_password_hash(payload.new_password)
    try:
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == rec.id).update({PasswordResetOTP.used: True})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update OTP state")
    try:
        _send_system_email(
            user.email, 
            "✅ Password Reset Successful - WolfAssistants", 
            f"""Hello {user.full_name or 'User'},

Your password has been successfully reset for your WolfAssistants account.

If you did not make this change, please contact support immediately.

Best regards,
WolfAssistants Team

---
This is an automated message. Please do not reply to this email.
"""
        )
    except HTTPException:
        pass
    return {"message": "Password updated"}

@router.get("/ping")
def ping():
    return {"ok": True}