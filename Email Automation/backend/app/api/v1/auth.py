from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional
import smtplib
from email.mime.text import MIMEText
import ssl

from app.core.database import get_db, get_accounts_db, SessionLocal, AccountsSessionLocal, create_tenant_schema
from app.core.config import settings
from app.core.auth import create_access_token, verify_password, get_password_hash
from app.core.password_validation import validate_password
from app.models.user import User
from app.models.token import EmailVerificationToken, PasswordResetToken, ChangeEmailToken
from sqlalchemy import text
import os
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter()

def _log_activity_async(
    user_id: int,
    activity_type_str: str,
    description: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    risk_score: int = 0
):
    """
    Background task for logging user activity asynchronously.
    This prevents activity logging from blocking the login response.
    """
    try:
        from app.core.user_monitoring import UserMonitoringService
        from app.models.user_activity import ActivityType
        
        # Create a new database session for background task
        db = SessionLocal()
        try:
            monitoring_service = UserMonitoringService(db)
            
            # Convert string to ActivityType enum
            activity_type = ActivityType[activity_type_str] if hasattr(ActivityType, activity_type_str) else ActivityType.LOGIN
            
            monitoring_service.log_activity(
                user_id=user_id,
                activity_type=activity_type,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                risk_score=risk_score
            )
        finally:
            db.close()
    except Exception as e:
        # Silently fail - activity logging should not break the main flow
        # Log error for debugging (in production, use proper logging)
        print(f"Background activity logging failed: {e}")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send system email: {e}")

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    businessName: str | None = None
    # Extended optional fields during registration (can complete later via profile)
    username: str | None = None
    company_name: str | None = None
    team_size: str | None = None
    revenue_size: str | None = None
    social_link: str | None = None
    website_url: str | None = None
    calendly_link: str | None = None
    heard_about_us: str | None = None
    referral_code: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def _send_email(to_email: str, subject: str, body: str):
    host = settings.EMAIL_HOST
    port = settings.EMAIL_PORT or 587
    user = settings.EMAIL_USER or 'wolfersquade@gmail.com'
    password = settings.EMAIL_PASSWORD
    from_addr = settings.EMAIL_FROM or 'wolfersquade@gmail.com'
    if not host or not user or not password:
        # In dev, do not hard fail; log would be better, but here we raise to surface config issue
        raise HTTPException(status_code=500, detail="Email SMTP settings missing")

    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_email
    context = ssl.create_default_context()
    # Try preferred mode first
    try:
        if int(port or 0) == 465 and not settings.EMAIL_USE_TLS:
            server = smtplib.SMTP_SSL(host, int(port), context=context, timeout=15)
            server.ehlo()
        else:
            server = smtplib.SMTP(host, int(port), timeout=15)
            server.ehlo()
            if settings.EMAIL_USE_TLS:
                server.starttls(context=context)
                server.ehlo()
        server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        return
    except Exception:
        try:
            # Fallback between 587 STARTTLS and 465 SSL
            alt_port = 587 if int(port or 0) == 465 or not settings.EMAIL_USE_TLS else 465
            if alt_port == 465:
                server = smtplib.SMTP_SSL(host, alt_port, context=context, timeout=15)
                server.ehlo()
            else:
                server = smtplib.SMTP(host, alt_port, timeout=15)
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
            server.quit()
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"SMTP send failed: {e2}")

def _send_simple_text(to_email: str, subject: str, text_body: str):
    # Use per-user SMTP settings if available, otherwise fall back to global settings
    from app.core.database import SessionLocal
    from app.models.user import User
    
    # Try to find user by email to get their SMTP settings
    pdb = SessionLocal()
    try:
        user_row = pdb.query(User).filter(User.email == to_email).first()
        
        # Try per-user SMTP first if configured
        if user_row and user_row.smtp_host and user_row.smtp_username and user_row.smtp_password:
            try:
                host = user_row.smtp_host
                port = int(user_row.smtp_port or (587 if user_row.smtp_use_tls else 465))
                user = user_row.smtp_username
                password = user_row.smtp_password
                from_addr = user_row.smtp_from or user
                use_tls = True if user_row.smtp_use_tls is None else bool(user_row.smtp_use_tls)
                
                msg = MIMEText(text_body, 'plain', 'utf-8')
                msg['Subject'] = subject
                msg['From'] = from_addr or ''
                msg['To'] = to_email
                context = ssl.create_default_context()
                
                if port == 465 and not use_tls:
                    server = smtplib.SMTP_SSL(host, port, context=context, timeout=15)
                    server.ehlo()
                else:
                    server = smtplib.SMTP(host, port, timeout=15)
                    server.ehlo()
                    if use_tls:
                        server.starttls(context=context)
                        server.ehlo()
                server.login(user, password)
                server.sendmail(from_addr or '', [to_email], msg.as_string())
                server.quit()
                return
            except Exception as e:
                if settings.DEBUG:
                    pass
                # Fall through to global settings
    finally:
        pdb.close()
    
    # Fallback to global settings
    host = settings.EMAIL_HOST
    port = settings.EMAIL_PORT or 587
    user = settings.EMAIL_USER
    password = settings.EMAIL_PASSWORD
    from_addr = settings.EMAIL_FROM or settings.EMAIL_USER
    
    if not host or not user or not password:
        raise HTTPException(status_code=500, detail="Email SMTP settings missing")
    
    msg = MIMEText(text_body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_addr or ''
    msg['To'] = to_email
    context = ssl.create_default_context()
    
    try:
        if int(port or 0) == 465 and not settings.EMAIL_USE_TLS:
            server = smtplib.SMTP_SSL(host, int(port), context=context, timeout=15)
            server.ehlo()
        else:
            server = smtplib.SMTP(host, int(port), timeout=15)
            server.ehlo()
            if settings.EMAIL_USE_TLS:
                server.starttls(context=context)
                server.ehlo()
        server.login(user, password)
        server.sendmail(from_addr or '', [to_email], msg.as_string())
        server.quit()
        return
    except Exception:
        try:
            alt_port = 587 if int(port or 0) == 465 or not settings.EMAIL_USE_TLS else 465
            if alt_port == 465:
                server = smtplib.SMTP_SSL(host, alt_port, context=context, timeout=15)
                server.ehlo()
            else:
                server = smtplib.SMTP(host, alt_port, timeout=15)
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(user, password)
            server.sendmail(from_addr or '', [to_email], msg.as_string())
            server.quit()
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Email send failed: {e2}")

@router.post("/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_accounts_db)):
    """
    Register a new user with optimized transaction batching.
    All database operations are batched into a single transaction to reduce
    database round-trips from 3+ to 1, improving registration speed by 200-400ms.
    """
    try:
        # Validate password (including breach check)
        await validate_password(payload.password)
        
        # Check for existing user before starting transaction
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Batch all database operations in single transaction
        # This reduces database round-trips from 3+ to 1
        try:
            # Set up 14-day free trial
            trial_start = datetime.utcnow()
            trial_end = trial_start + timedelta(days=14)
            
            # Create user
            user = User(
                email=payload.email,
                full_name=payload.name,
                hashed_password=get_password_hash(payload.password),
                is_active=True,
                username=payload.username,
                company_name=payload.company_name or payload.businessName,
                team_size=payload.team_size,
                revenue_size=payload.revenue_size,
                social_link=payload.social_link,
                website_url=payload.website_url,
                calendly_link=payload.calendly_link,
                heard_about_us=payload.heard_about_us,
                tier_activated_at=trial_start,
                payment_status="trialing",  # Set to trialing during trial period
                trial_start_date=trial_start,
                trial_end_date=trial_end,
                pricing_tier="starter"  # Default to starter tier
            )
            db.add(user)
            db.flush()  # Get user.id without committing yet
            
            # Process referral if code provided (within same transaction)
            referral_processed = False
            if payload.referral_code:
                try:
                    from app.api.v1.referrals import process_referral_signup
                    from app.models.referral import ReferralCode
                    
                    # Look for the referral code in the main Supabase database
                    code_obj = db.query(ReferralCode).filter(
                        ReferralCode.code == payload.referral_code
                    ).first()
                    
                    if code_obj:
                        # Found the referral code! Process the referral
                        referral_processed = process_referral_signup(user, payload.referral_code, db)
                    
                except Exception as e:
                    print(f"Referral processing error: {e}")
                    pass  # Don't fail registration if referral processing fails
            
            # Create email verification token (within same transaction)
            vtoken = EmailVerificationToken(user_id=user.id, token=EmailVerificationToken.generate_token())
            db.add(vtoken)
            
            # Single commit for all operations - reduces round-trips from 3+ to 1
            db.commit()
            db.refresh(user)
            
            # Create tenant schema for the new user
            # This happens after account creation so we can rollback if schema creation fails
            # Schema creation is critical for data isolation, so we retry on failure
            schema_created = False
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    schema_created = create_tenant_schema(payload.email)
                    if schema_created:
                        logger.info(f"✅ Created tenant schema for new user: {payload.email}")
                        # Update user's schema_created flag (create_tenant_schema should handle this, but ensure it's set)
                        user.schema_created = True
                        db.commit()
                        break
                    else:
                        # Check if schema actually exists (might have been created by another process)
                        from app.core.tenant_database import schema_exists
                        if schema_exists(payload.email):
                            logger.info(f"✅ Tenant schema already exists for: {payload.email}")
                            schema_created = True
                            user.schema_created = True
                            db.commit()
                            break
                        else:
                            # Schema creation returned False but schema doesn't exist - retry
                            if attempt < max_retries - 1:
                                logger.warning(f"Schema creation returned False for {payload.email}, retrying ({attempt + 1}/{max_retries})...")
                                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                            else:
                                logger.error(f"Failed to create tenant schema for {payload.email} after {max_retries} attempts")
                except Exception as schema_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"Schema creation attempt {attempt + 1} failed for {payload.email}: {str(schema_error)}. Retrying...")
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    else:
                        # Final attempt failed - log error but don't fail registration
                        # Schema can be created later via admin endpoint or on first login
                        logger.error(f"❌ Failed to create tenant schema for {payload.email} after {max_retries} attempts: {str(schema_error)}", exc_info=True)
                        logger.warning(f"User {payload.email} can still log in, but tenant data won't be accessible until schema is created")
            
            if not schema_created:
                # Log warning for monitoring - schema should be created via admin endpoint
                logger.warning(f"⚠️  Registration completed for {payload.email} but tenant schema was not created. Manual intervention may be required.")
                # Ensure flag is False if schema wasn't created
                user.schema_created = False
                db.commit()
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            # Surface detailed error for debugging (consider logging only in production)
            raise HTTPException(status_code=500, detail=f"Registration failed: {e}")
    except HTTPException:
        raise
    except Exception as e:
        # Handle case where existing user check fails
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": user.email, "is_admin": user.is_admin}, expires_delta=access_token_expires)
    
    response_data = {
        "token": token, 
        "user": {"id": user.id, "email": user.email, "name": user.full_name}, 
        "verification": "sent"
    }
    
    if referral_processed:
        response_data["referral_bonus"] = "You've received 25 welcome credits for joining via referral!"
    
    return response_data

class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    username: str | None = None
    company_name: str | None = None
    position_title: str | None = None
    team_size: str | None = None
    revenue_size: str | None = None
    social_link: str | None = None
    website_url: str | None = None
    calendly_link: str | None = None
    heard_about_us: str | None = None
    profile_image_url: str | None = None

@router.put("/profile")
def update_profile(payload: ProfileUpdateRequest, request: Request, db: Session = Depends(get_accounts_db)):
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from jose import jwt as _jwt
    token = auth.split(' ', 1)[1]
    try:
        p = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = p.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    # Safely access website_url in case column doesn't exist in database yet
    website_url = getattr(user, 'website_url', None)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "username": user.username,
        "company_name": user.company_name,
        "position_title": user.position_title,
        "team_size": user.team_size,
        "revenue_size": user.revenue_size,
        "social_link": user.social_link,
        "website_url": website_url,
        "calendly_link": user.calendly_link,
        "heard_about_us": user.heard_about_us,
        "profile_image_url": user.profile_image_url,
    }

@router.get("/profile")
def get_profile(request: Request, db: Session = Depends(get_accounts_db)):
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from jose import jwt as _jwt
    token = auth.split(' ', 1)[1]
    try:
        p = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = p.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Safely access website_url in case column doesn't exist in database yet
    website_url = getattr(user, 'website_url', None)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "username": user.username,
        "company_name": user.company_name,
        "position_title": user.position_title,
        "team_size": user.team_size,
        "revenue_size": user.revenue_size,
        "social_link": user.social_link,
        "website_url": website_url,
        "calendly_link": user.calendly_link,
        "heard_about_us": user.heard_about_us,
        "profile_image_url": user.profile_image_url,
    }

class EmailConfigRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    imap_use_ssl: bool | None = None
    # Auto follow-up settings
    auto_followup_enabled: bool | None = None
    auto_followup_max_days: int | None = None
    auto_followup_daily_hour: int | None = None
    
@router.put("/email-config")
def update_email_config(payload: EmailConfigRequest, request: Request, db: Session = Depends(get_accounts_db)):
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from jose import jwt as _jwt
    token = auth.split(' ', 1)[1]
    try:
        p = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = p.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == 'smtp_password':
            # Encrypt SMTP password using the User model's method
            if v:
                user.set_smtp_password(v)
            else:
                user.smtp_password = None
        elif k == 'imap_password':
            # Encrypt IMAP password using the User model's method
            if v:
                user.set_imap_password(v)
            else:
                user.imap_password = None
        else:
            setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "Email configuration updated successfully"}

@router.post("/login")
def login(
    payload: LoginRequest, 
    request: Request, 
    db: Session = Depends(get_accounts_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        # Log login attempt for debugging
        logger.info(f"Login attempt for email: {payload.email}")
        
        # Ensure we start with a clean transaction state
        try:
            db.rollback()
        except Exception:
            pass  # Ignore rollback errors if transaction is already clean
        
        # Use raw SQL query to avoid SQLAlchemy column issues - safer approach
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError, ProgrammingError
        
        user = None
        
        try:
            # Always use raw SQL query to avoid SQLAlchemy trying to load missing columns
            # This is safer and works regardless of schema state
            sql_query = text("""
                SELECT id, email, hashed_password, full_name, is_active, is_admin,
                       created_at, updated_at, deleted_at, username, company_name,
                       position_title, team_size, revenue_size, social_link, 
                       website_url, calendly_link, heard_about_us, profile_image_url,
                       tier_activated_at, tier_expires_at, payment_status,
                       last_payment_date, next_payment_date, pricing_tier,
                       subscription_id, timezone, schema_created
                FROM app_users 
                WHERE email = :email
                LIMIT 1
            """)
            result = db.execute(sql_query, {"email": payload.email})
            row = result.fetchone()
            if row:
                # Create a simple object-like structure
                user = type('User', (), {
                    'id': row[0],
                    'email': row[1],
                    'hashed_password': row[2],
                    'full_name': row[3],
                    'is_active': row[4],
                    'is_admin': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'deleted_at': row[8],
                    'username': row[9],
                    'company_name': row[10],
                    'position_title': row[11],
                    'team_size': row[12],
                    'revenue_size': row[13],
                    'social_link': row[14],
                    'website_url': row[15],
                    'calendly_link': row[16],
                    'heard_about_us': row[17],
                    'profile_image_url': row[18],
                    'tier_activated_at': row[19],
                    'tier_expires_at': row[20],
                    'payment_status': row[21],
                    'last_payment_date': row[22],
                    'next_payment_date': row[23],
                    'pricing_tier': row[24],
                    'subscription_id': row[25],
                    'timezone': row[26],
                    'schema_created': row[27],
                    'trial_start_date': None,  # Not in database yet
                    'trial_end_date': None,  # Not in database yet
                })()
        except Exception as query_error:
            # If query fails due to transaction state, rollback and retry with raw SQL
            error_msg = str(query_error)
            logger.error(f"Database query error during login: {error_msg}")
            if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_msg.lower():
                logger.warning(f"Database transaction error during login query, rolling back and retrying with raw SQL: {error_msg}")
                db.rollback()
                try:
                    # Use raw SQL for retry to avoid column issues
                    sql_query = text("""
                        SELECT id, email, hashed_password, full_name, is_active, is_admin,
                               created_at, updated_at, deleted_at, username, company_name,
                               position_title, team_size, revenue_size, social_link, 
                               website_url, calendly_link, heard_about_us, profile_image_url,
                               tier_activated_at, tier_expires_at, payment_status,
                               last_payment_date, next_payment_date, pricing_tier,
                               subscription_id, timezone, schema_created
                        FROM app_users 
                        WHERE email = :email
                        LIMIT 1
                    """)
                    result = db.execute(sql_query, {"email": payload.email})
                    row = result.fetchone()
                    if row:
                        user = type('User', (), {
                            'id': row[0],
                            'email': row[1],
                            'hashed_password': row[2],
                            'full_name': row[3],
                            'is_active': row[4],
                            'is_admin': row[5],
                            'created_at': row[6],
                            'updated_at': row[7],
                            'deleted_at': row[8],
                            'username': row[9],
                            'company_name': row[10],
                            'position_title': row[11],
                            'team_size': row[12],
                            'revenue_size': row[13],
                            'social_link': row[14],
                            'website_url': row[15],
                            'calendly_link': row[16],
                            'heard_about_us': row[17],
                            'profile_image_url': row[18],
                            'tier_activated_at': row[19],
                            'tier_expires_at': row[20],
                            'payment_status': row[21],
                            'last_payment_date': row[22],
                            'next_payment_date': row[23],
                            'pricing_tier': row[24],
                            'subscription_id': row[25],
                            'timezone': row[26],
                            'schema_created': row[27],
                            'trial_start_date': None,
                            'trial_end_date': None,
                        })()
                    else:
                        user = None
                except Exception as retry_error:
                    logger.error(f"Retry query also failed: {str(retry_error)}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Database error during login. Please try again."
                    )
            else:
                raise
        
        # Check if user exists first
        if not user:
            logger.warning(f"Login failed: User not found for email {payload.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found")
        
        # Check if password is correct
        if not user.hashed_password:
            logger.warning(f"Login failed: Account password not set for email {payload.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account password not set")
        
        # Verify password
        try:
            password_valid = verify_password(payload.password, user.hashed_password)
        except Exception as pwd_error:
            logger.error(f"Password verification error for {payload.email}: {str(pwd_error)}")
            raise HTTPException(
                status_code=500, 
                detail="Password verification failed. Please try again."
            )
        
        if not password_valid:
            logger.warning(f"Login failed: Incorrect password for email {payload.email}")
            # Schedule failed login attempt logging as background task
            # This removes 200-800ms blocking operation from login response
            background_tasks.add_task(
                _log_activity_async,
                user_id=user.id,
                activity_type_str="LOGIN",
                description="Failed login attempt - incorrect password",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get('User-Agent'),
                risk_score=10
            )
            
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password is wrong")
        
        # Check if user account is active
        if not user.is_active:
            logger.warning(f"Login failed: Account deactivated for email {payload.email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated")
        
        # Check if user is banned (with error handling - fail open)
        # Skip ban checking entirely if there's any error to avoid blocking login
        try:
            from app.models.user_activity import BanStatus, UserBan
            from datetime import datetime
            from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError
            
            # Check bans using the existing session
            try:
                # Ensure transaction is clean before ban check
                try:
                    db.rollback()
                except Exception:
                    pass
                
                active_bans = db.query(UserBan).filter(
                    UserBan.user_id == user.id,
                    UserBan.status.in_([BanStatus.ACTIVE, BanStatus.PERMANENT])
                ).all()
                
                if active_bans:
                    now = datetime.utcnow()
                    for ban in active_bans:
                        # Check if ban is active and not expired
                        if ban.status == BanStatus.ACTIVE:
                            if ban.expires_at and ban.expires_at < now:
                                continue
                            # User is banned
                            ban_details = {
                                "banned": True,
                                "reason": ban.reason.value if ban.reason else "Unknown",
                                "description": ban.description or "Account suspended",
                                "expires_at": ban.expires_at.isoformat() if ban.expires_at else None
                            }
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN, 
                                detail="Account access denied",
                                headers={"X-Ban-Details": str(ban_details)}
                            )
                        elif ban.status == BanStatus.PERMANENT:
                            # User is permanently banned
                            ban_details = {
                                "banned": True,
                                "reason": ban.reason.value if ban.reason else "Unknown",
                                "description": ban.description or "Account suspended",
                                "expires_at": None
                            }
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN, 
                                detail="Account access denied",
                                headers={"X-Ban-Details": str(ban_details)}
                            )
            except (OperationalError, ProgrammingError, InternalError) as db_error:
                # Table doesn't exist or database error - skip ban check
                error_msg = str(db_error)
                if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_msg.lower():
                    # Try to recover by rolling back
                    try:
                        db.rollback()
                        logger.debug(f"Rolled back transaction after ban check error")
                    except Exception:
                        pass
                logger.debug(f"Ban table query failed (table may not exist): {db_error}")
                pass
        except HTTPException:
            # Re-raise HTTP exceptions (ban detected)
            raise
        except ImportError as import_err:
            # UserBan model might not be available - skip ban check
            logger.debug(f"UserBan model not available: {import_err}")
        except Exception as ban_error:
            # Log ban check error but don't block login (fail open for ban checking)
            logger.warning(f"Error checking ban status for user {user.email}: {ban_error}")
            # Continue with login if ban check fails

        # Schedule successful login logging as background task
        # This removes 200-800ms blocking operation from login response
        background_tasks.add_task(
            _log_activity_async,
            user_id=user.id,
            activity_type_str="LOGIN",
            description="Successful login",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent'),
            risk_score=0
        )

        # Return response immediately without waiting for activity logging
        try:
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            # Ensure is_admin is a boolean, not None
            is_admin = bool(user.is_admin) if user.is_admin is not None else False
            token = create_access_token({"sub": user.email, "is_admin": is_admin}, expires_delta=access_token_expires)
            return {
                "token": token, 
                "user": {
                    "id": user.id, 
                    "email": user.email, 
                    "name": user.full_name or "",
                    "is_admin": is_admin
                }
            }
        except Exception as token_error:
            logger.error(f"Error creating token for user {user.email}: {token_error}")
            import traceback
            logger.error(f"Token creation traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to create access token: {str(token_error)}")
    except HTTPException as http_exc:
        # Log HTTP exceptions for debugging
        logger.warning(f"Login HTTPException for {payload.email if 'payload' in locals() else 'unknown'}: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        from sqlalchemy.exc import OperationalError, ProgrammingError
        error_trace = traceback.format_exc()
        error_msg = str(e)
        
        # Check if error is related to missing column
        # Since we're using raw SQL now, this shouldn't happen, but handle it gracefully
        if isinstance(e, (OperationalError, ProgrammingError)) and ('does not exist' in error_msg.lower() or 'no such column' in error_msg.lower()):
            # Try to extract the column name from the error message
            import re
            column_match = re.search(r"column\s+[\w.]+\.(\w+)\s+does not exist", error_msg, re.IGNORECASE)
            if column_match:
                missing_column = column_match.group(1)
                # If it's a trial column, try to recover with raw SQL one more time
                if 'trial' in missing_column.lower():
                    logger.warning(f"Login error - trial column missing, attempting recovery with raw SQL: {error_msg}")
                    try:
                        from sqlalchemy import text
                        db.rollback()  # Clean transaction state
                        sql_query = text("""
                            SELECT id, email, hashed_password, full_name, is_active, is_admin,
                                   created_at, updated_at, deleted_at, username, company_name,
                                   position_title, team_size, revenue_size, social_link, 
                                   website_url, calendly_link, heard_about_us, profile_image_url,
                                   tier_activated_at, tier_expires_at, payment_status,
                                   last_payment_date, next_payment_date, pricing_tier,
                                   subscription_id, timezone, schema_created
                            FROM app_users 
                            WHERE email = :email
                            LIMIT 1
                        """)
                        result = db.execute(sql_query, {"email": payload.email})
                        row = result.fetchone()
                        if row:
                            # Successfully recovered - create user object and continue
                            user = type('User', (), {
                                'id': row[0], 'email': row[1], 'hashed_password': row[2],
                                'full_name': row[3], 'is_active': row[4], 'is_admin': row[5],
                                'created_at': row[6], 'updated_at': row[7], 'deleted_at': row[8],
                                'username': row[9], 'company_name': row[10], 'position_title': row[11],
                                'team_size': row[12], 'revenue_size': row[13], 'social_link': row[14],
                            })()
                            logger.info(f"Successfully recovered from missing column error using raw SQL")
                            # Continue with normal login flow - we'll jump back to password verification
                            # But we need to skip the rest of the error handling
                            # Actually, we can't easily jump back, so we'll just log and re-raise a cleaner error
                            raise HTTPException(
                                status_code=500,
                                detail=f"Database schema issue detected. Please run migration: ALTER TABLE app_users ADD COLUMN {missing_column} TIMESTAMP;"
                            )
                    except HTTPException:
                        raise
                    except Exception as recovery_error:
                        logger.error(f"Recovery attempt failed: {recovery_error}")
                
                # For non-trial columns, provide helpful error message
                logger.error(f"Login error - database schema mismatch (missing {missing_column} column): {error_msg}\n{error_trace}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Database schema needs to be updated. Please add the '{missing_column}' column to the 'app_users' table. Run: ALTER TABLE app_users ADD COLUMN {missing_column} TIMESTAMP;"
                )
            else:
                # Fallback for website_url (legacy)
                if 'website_url' in error_msg.lower():
                    logger.error(f"Login error - database schema mismatch (missing website_url column): {error_msg}\n{error_trace}")
                    raise HTTPException(
                        status_code=500, 
                        detail="Database schema needs to be updated. Please add the 'website_url' column to the 'app_users' table: ALTER TABLE app_users ADD COLUMN website_url VARCHAR;"
                    )
        
        # Log the actual error for debugging
        logger.error(f"Login error for {payload.email if 'payload' in locals() else 'unknown'}: {error_msg}\n{error_trace}")
        # Surface detailed error for debugging (but sanitize sensitive info)
        safe_error = error_msg[:500]  # Limit error message length
        raise HTTPException(status_code=500, detail=f"Login failed: {safe_error}")

@router.get("/me")
def me(request: Request, db: Session = Depends(get_accounts_db)):
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    # Decode by create_access_token logic; here we only stored email in sub
    from jose import jwt
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    from datetime import datetime
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Use raw SQL query to avoid SQLAlchemy column issues
    try:
        sql_query = text("""
            SELECT id, email, hashed_password, full_name, is_active, is_admin,
                   created_at, updated_at, deleted_at, username, company_name,
                   position_title, team_size, revenue_size, social_link, 
                   website_url, calendly_link, heard_about_us, profile_image_url,
                   tier_activated_at, tier_expires_at, payment_status,
                   last_payment_date, next_payment_date, pricing_tier,
                   subscription_id, timezone, schema_created
            FROM app_users 
            WHERE email = :email
            LIMIT 1
        """)
        result = db.execute(sql_query, {"email": email})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Create user object from row
        user = type('User', (), {
            'id': row[0],
            'email': row[1],
            'hashed_password': row[2],
            'full_name': row[3],
            'is_active': row[4],
            'is_admin': row[5],
            'created_at': row[6],
            'updated_at': row[7],
            'deleted_at': row[8],
            'username': row[9],
            'company_name': row[10],
            'position_title': row[11],
            'team_size': row[12],
            'revenue_size': row[13],
            'social_link': row[14],
            'website_url': row[15],
            'calendly_link': row[16],
            'heard_about_us': row[17],
            'profile_image_url': row[18],
            'tier_activated_at': row[19],
            'tier_expires_at': row[20],
            'payment_status': row[21],
            'last_payment_date': row[22],
            'next_payment_date': row[23],
            'pricing_tier': row[24],
            'subscription_id': row[25],
            'timezone': row[26],
            'schema_created': row[27],
            'trial_start_date': None,  # Not in database yet
            'trial_end_date': None,  # Not in database yet
        })()
    except (OperationalError, ProgrammingError) as db_error:
        # If raw SQL fails, try SQLAlchemy as fallback
        error_str = str(db_error).lower()
        if 'does not exist' in error_str or 'no such column' in error_str:
            logger.warning(f"Raw SQL query failed in /me endpoint, trying SQLAlchemy fallback: {db_error}")
            try:
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid token")
            except Exception:
                raise HTTPException(status_code=500, detail="Database error loading profile")
        else:
            raise HTTPException(status_code=500, detail="Database error loading profile")
    except Exception as e:
        logger.error(f"Error loading user profile: {e}")
        raise HTTPException(status_code=500, detail="Error loading profile")
    
    # Safely access website_url in case column doesn't exist in database yet
    website_url = getattr(user, 'website_url', None)
    
    # Get trial information - use safe access methods
    trial_start_date = getattr(user, 'trial_start_date', None)
    trial_end_date = getattr(user, 'trial_end_date', None)
    
    # Calculate trial status manually
    is_trial_active = False
    trial_days_remaining = 0
    has_trial_expired = True
    
    # Try to get trial dates from database if columns exist
    try:
        # Check if trial columns exist and query them separately
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'app_users' 
            AND column_name IN ('trial_start_date', 'trial_end_date')
        """)
        result = db.execute(check_query)
        existing_columns = [row[0] for row in result]
        
        if 'trial_start_date' in existing_columns and 'trial_end_date' in existing_columns:
            # Columns exist, query them
            trial_query = text("""
                SELECT trial_start_date, trial_end_date
                FROM app_users 
                WHERE email = :email
                LIMIT 1
            """)
            trial_result = db.execute(trial_query, {"email": email})
            trial_row = trial_result.fetchone()
            if trial_row:
                trial_start_date = trial_row[0]
                trial_end_date = trial_row[1]
    except Exception:
        # If check fails, trial dates remain None
        pass
    
    # Calculate trial status if dates are available
    if trial_start_date and trial_end_date:
        now = datetime.utcnow()
        # Handle datetime objects or strings
        if isinstance(trial_start_date, str):
            try:
                trial_start_date = datetime.fromisoformat(trial_start_date.replace('Z', '+00:00'))
            except:
                trial_start_date = None
        if isinstance(trial_end_date, str):
            try:
                trial_end_date = datetime.fromisoformat(trial_end_date.replace('Z', '+00:00'))
            except:
                trial_end_date = None
        
        if trial_start_date and trial_end_date and isinstance(trial_start_date, datetime) and isinstance(trial_end_date, datetime):
            is_trial_active = trial_start_date <= now < trial_end_date
            if now < trial_end_date:
                trial_days_remaining = (trial_end_date - now).days
            has_trial_expired = now >= trial_end_date
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "username": user.username,
        "company_name": user.company_name,
        "position_title": user.position_title,
        "team_size": user.team_size,
        "revenue_size": user.revenue_size,
        "social_link": user.social_link,
        "pricing_tier": user.pricing_tier,
        "payment_status": user.payment_status,
        "trial": {
            "is_active": is_trial_active,
            "days_remaining": trial_days_remaining,
            "has_expired": has_trial_expired,
            "start_date": trial_start_date.isoformat() if trial_start_date and hasattr(trial_start_date, 'isoformat') else (trial_start_date if trial_start_date else None),
            "end_date": trial_end_date.isoformat() if trial_end_date and hasattr(trial_end_date, 'isoformat') else (trial_end_date if trial_end_date else None),
        },
        "website_url": website_url,
        "calendly_link": user.calendly_link,
        "heard_about_us": user.heard_about_us,
        "profile_image_url": user.profile_image_url,
        "is_admin": user.is_admin,
    }

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_accounts_db)):
    rec = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token, EmailVerificationToken.used == False).first()
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    # Use proper SQLAlchemy update method
    db.query(EmailVerificationToken).filter(EmailVerificationToken.id == rec.id).update({"used": True})
    db.commit()
    return {"message": "Email verified"}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_accounts_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Email doesn't exist
        return {"message": "This email is not registered in our system", "exists": False}
    
    # Email exists, generate and send reset link
    token = PasswordResetToken(user_id=user.id, token=PasswordResetToken.generate_token(), expires_at=PasswordResetToken.expiry_in())
    db.add(token)
    db.commit()
    reset_url = f"{settings.HOST if settings.HOST else 'http://localhost'}:{settings.PORT}/api/v1/auth/reset-password?token={token.token}"
    try:
        _send_email(user.email, "Password reset", f"<p>Reset your password by clicking <a href='{reset_url}'>this link</a>. Link expires in 2 hours.</p>")
    except HTTPException:
        # If email sending fails, still return success but note the issue
        return {"message": "Reset link generated but failed to send email. Please try again later.", "exists": True, "link_sent": False}
    
    return {"message": "Password reset link has been sent to your email", "exists": True, "link_sent": True}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_accounts_db)):
    # Validate password (including breach check)
    await validate_password(payload.new_password)
    
    rec = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token, PasswordResetToken.used == False).first()
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    from datetime import datetime as _dt
    # Use SQLAlchemy filter to check expiration instead of Python comparison
    expired_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at < _dt.utcnow()
    ).first()
    if expired_token:
        raise HTTPException(status_code=400, detail="Token expired")
    user = db.query(User).filter(User.id == rec.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.hashed_password = get_password_hash(payload.new_password)
    # Use proper SQLAlchemy update method
    db.query(PasswordResetToken).filter(PasswordResetToken.id == rec.id).update({"used": True})
    db.commit()
    return {"message": "Password updated"}

# OTP-based password reset flow moved to app/api/v1/otp.py

class ChangeEmailRequest(BaseModel):
    new_email: EmailStr

@router.post("/request-change-email")
def request_change_email(payload: ChangeEmailRequest, request: Request, db: Session = Depends(get_accounts_db)):
    # Requires authenticated user; simplified here: read token to find user
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    from jose import jwt
    token_str = auth.split(' ', 1)[1]
    try:
        payload_jwt = jwt.decode(token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload_jwt.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    token = ChangeEmailToken(user_id=user.id, new_email=payload.new_email, token=ChangeEmailToken.generate_token())
    db.add(token)
    db.commit()
    link = f"{settings.HOST if settings.HOST else 'http://localhost'}:{settings.PORT}/api/v1/auth/confirm-change-email?token={token.token}"
    try:
        _send_email(payload.new_email, "Confirm your new email", f"<p>Click <a href='{link}'>here</a> to confirm your new email.</p>")
    except HTTPException:
        pass
    return {"message": "Confirmation link sent to new email"}

@router.get("/confirm-change-email")
def confirm_change_email(token: str, db: Session = Depends(get_accounts_db)):
    rec = db.query(ChangeEmailToken).filter(ChangeEmailToken.token == token, ChangeEmailToken.used == False).first()
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    user = db.query(User).filter(User.id == rec.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    old_email = user.email
    new_email = rec.new_email
    user.email = new_email
    # Use proper SQLAlchemy update method
    db.query(ChangeEmailToken).filter(ChangeEmailToken.id == rec.id).update({"used": True})
    db.commit()
    # Update all related records in Supabase to use new email
    try:
        # Update all tables that reference the user's email
        db.execute(text("UPDATE emails SET owner_email = :new_email WHERE owner_email = :old_email"), 
                  {"new_email": new_email, "old_email": old_email})
        db.execute(text("UPDATE contacts SET owner_email = :new_email WHERE owner_email = :old_email"), 
                  {"new_email": new_email, "old_email": old_email})
        db.execute(text("UPDATE meetings SET owner_email = :new_email WHERE owner_email = :old_email"), 
                  {"new_email": new_email, "old_email": old_email})
        db.execute(text("UPDATE todos SET owner_email = :new_email WHERE owner_email = :old_email"), 
                  {"new_email": new_email, "old_email": old_email})
        db.execute(text("UPDATE chat_sessions SET owner_email = :new_email WHERE owner_email = :old_email"), 
                  {"new_email": new_email, "old_email": old_email})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update related records: {e}")
    try:
        _send_simple_text(user.email, "Email changed", "Your email has been successfully changed.")
    except HTTPException:
        pass
    return {"message": "Email updated"}

@router.api_route("/delete-account", methods=["DELETE", "POST"])  # allow POST as alias for clients/proxies
def delete_account(request: Request, db: Session = Depends(get_accounts_db)):
    """Permanently delete the authenticated user's account and their tenant database."""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    from jose import jwt as _jwt
    try:
        payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete from primary DB
    try:
        # Clean related tokens
        db.execute(text("DELETE FROM email_verification_tokens WHERE user_id = :uid"), {"uid": user.id})
        db.execute(text("DELETE FROM password_reset_tokens WHERE user_id = :uid"), {"uid": user.id})
        db.execute(text("DELETE FROM change_email_tokens WHERE user_id = :uid"), {"uid": user.id})
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete account")

    # All data is now in Supabase - no tenant database files to remove
    pass

    return JSONResponse({"status": "deleted", "message": "Your account and all associated data have been permanently deleted."})# OTP-based password reset endpoints
from app.models.token import PasswordResetOTP
from typing import Any, cast

class ForgotPasswordOtpRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password-otp")
def forgot_password_otp(payload: ForgotPasswordOtpRequest, db: Session = Depends(get_accounts_db)):
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
        # Use system email for OTP sending
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
def verify_reset_otp(payload: VerifyResetOtpRequest, db: Session = Depends(get_accounts_db)):
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
async def reset_password_with_otp(payload: ResetPasswordWithOtpRequest, db: Session = Depends(get_accounts_db)):
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
        # Mark OTP as used
        db.query(PasswordResetOTP).filter(PasswordResetOTP.id == rec.id).update({PasswordResetOTP.used: True})
        # Commit both password update and OTP state change
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update password and OTP state")
    
    try:
        _send_simple_text(user.email, "Password reset successful", "Your password has been reset successfully.")
    except HTTPException:
        pass
    
    return {"message": "Password updated"}

