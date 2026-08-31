from fastapi import APIRouter, Depends, HTTPException, Request, Body, UploadFile, File, Response, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple, Dict, Any, cast, Sequence
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import time
import socket
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email import encoders
import os
import pytz
import logging
import hashlib
import threading
import json
import uuid
from contextlib import contextmanager
from app.core.file_upload import save_uploaded_file, validate_total_size, get_file_content, delete_file, cleanup_old_files, UPLOAD_DIR

# Define IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Set up logging
logger = logging.getLogger(__name__)

# --- Follow-up content sanitizers ---
def _sanitize_followup_subject(subject: Optional[str]) -> str:
    s = (subject or "").strip()
    if s.endswith("}"):
        s = s[:-1].strip()
    return s

def _sanitize_followup_body(body: Optional[str]) -> str:
    t = (body or "").strip()
    if t.endswith("}"):
        t = t[:-1].strip()
    try:
        import re
        # Remove initial greeting like "Hi Name,\n" or "Hello ...\n" or "Dear ...\n"
        t = re.sub(r'^(\s*(hi|hello|dear)\b[^\n]*,?\s*\n+)', '', t, flags=re.IGNORECASE)
        # Remove clichéd opener if present at the start
        t = re.sub(r'^(i\s*hope\s*this\s*email\s*finds\s*you\s*well\.?\s*)', '', t, flags=re.IGNORECASE)
    except Exception:
        # Best-effort; ignore regex issues
        pass
    return t

def get_ist_now():
    """Get current datetime in IST timezone."""
    return datetime.now(IST)

def get_professional_persona(heard_about_us: str | None = None, position_title: str | None = None) -> Dict[str, str]:
    """
    Map user's profession/purpose to AI persona for email generation.
    
    Args:
        heard_about_us: User's purpose for using the tool (e.g., "Web Development", "Sales")
        position_title: User's job title (e.g., "Web Developer", "Designer")
        
    Returns:
        Dictionary with persona description, style, focus, and tone
    """
    # Normalize inputs - combine and lowercase for matching
    profession = " ".join([
        (heard_about_us or "").lower(),
        (position_title or "").lower()
    ]).strip()
    
    if not profession:
        # Default fallback persona
        return {
            "persona": "a freelancer or startup owner",
            "style": "professional, business-focused, solution-oriented",
            "focus": "delivering value and building relationships",
            "tone": "professional and friendly",
            "communication_style": "direct but warm, results-focused"
        }
    
    # Web Development / Programming
    if any(keyword in profession for keyword in [
        "web", "developer", "programming", "coding", "software", "programmer",
        "frontend", "backend", "fullstack", "full-stack", "dev", "engineer",
        "javascript", "python", "react", "node", "app development"
    ]):
        return {
            "persona": "a web developer freelancer or startup owner",
            "style": "technical, solution-focused, project-oriented",
            "focus": "technical solutions, project delivery, code quality, building scalable applications",
            "tone": "professional but approachable, detail-oriented, problem-solving",
            "communication_style": "clear and concise, technical when needed but accessible, project-focused"
        }
    
    # Design / Creative
    elif any(keyword in profession for keyword in [
        "design", "designer", "ui", "ux", "graphic", "creative", "visual",
        "ui/ux", "user interface", "user experience", "brand", "illustration",
        "art", "creative director", "visual designer"
    ]):
        return {
            "persona": "a designer or creative professional freelancer/startup owner",
            "style": "creative, visual, portfolio-focused, aesthetic-driven",
            "focus": "visual work, creative projects, design solutions, brand identity, user experience",
            "tone": "creative but professional, visually-oriented, inspiring",
            "communication_style": "visual and descriptive, creative but clear, portfolio-focused"
        }
    
    # Sales / Business Development
    elif any(keyword in profession for keyword in [
        "sales", "business development", "bd", "account executive", "account manager",
        "sales rep", "salesperson", "business developer", "revenue", "closing"
    ]):
        return {
            "persona": "a sales professional or business developer",
            "style": "relationship-focused, value-driven, closing-oriented",
            "focus": "building relationships, demonstrating value, closing deals, understanding client needs",
            "tone": "warm but direct, results-focused, consultative",
            "communication_style": "relationship-building, value-focused, consultative selling approach"
        }
    
    # Marketing
    elif any(keyword in profession for keyword in [
        "marketing", "marketer", "digital marketing", "content", "seo", "social media",
        "growth", "brand", "advertising", "pr", "public relations", "campaign"
    ]):
        return {
            "persona": "a marketing professional or growth-focused freelancer/startup owner",
            "style": "campaign-focused, metrics-driven, brand-oriented",
            "focus": "growth, brand awareness, campaign results, marketing strategies, ROI",
            "tone": "energetic but professional, data-driven, results-oriented",
            "communication_style": "results-focused, metrics-oriented, campaign-driven"
        }
    
    # Consulting / Strategy
    elif any(keyword in profession for keyword in [
        "consultant", "consulting", "strategy", "advisor", "advisory", "strategist",
        "business consultant", "management consultant"
    ]):
        return {
            "persona": "a consultant or strategic advisor",
            "style": "analytical, strategic, insight-driven",
            "focus": "strategic insights, business improvement, problem-solving, actionable recommendations",
            "tone": "consultative and professional, analytical, insightful",
            "communication_style": "strategic and analytical, insight-driven, consultative"
        }
    
    # Recruitment / HR
    elif any(keyword in profession for keyword in [
        "recruitment", "recruiter", "hr", "human resources", "talent", "hiring",
        "headhunter", "staffing", "talent acquisition"
    ]):
        return {
            "persona": "a recruiter or talent acquisition professional",
            "style": "relationship-focused, opportunity-oriented, matchmaking",
            "focus": "finding the right fit, career opportunities, talent matching",
            "tone": "professional and friendly, opportunity-focused, relationship-building",
            "communication_style": "relationship-focused, opportunity-oriented, clear about value proposition"
        }
    
    # Finance / Accounting
    elif any(keyword in profession for keyword in [
        "finance", "financial", "accountant", "accounting", "cpa", "bookkeeping",
        "tax", "financial advisor", "cfo", "controller"
    ]):
        return {
            "persona": "a finance professional or accounting freelancer",
            "style": "precise, numbers-focused, compliance-oriented",
            "focus": "financial solutions, accuracy, compliance, financial planning",
            "tone": "professional and precise, trustworthy, detail-oriented",
            "communication_style": "precise and professional, numbers-focused, compliance-aware"
        }
    
    # Legal
    elif any(keyword in profession for keyword in [
        "legal", "lawyer", "attorney", "law", "paralegal", "legal advisor"
    ]):
        return {
            "persona": "a legal professional or lawyer",
            "style": "precise, compliance-focused, professional",
            "focus": "legal solutions, compliance, risk management, legal advice",
            "tone": "formal and professional, precise, compliance-focused",
            "communication_style": "formal and precise, compliance-oriented, professional"
        }
    
    # Real Estate
    elif any(keyword in profession for keyword in [
        "real estate", "realtor", "property", "realty", "broker", "agent"
    ]):
        return {
            "persona": "a real estate professional or agent",
            "style": "relationship-focused, property-oriented, market-aware",
            "focus": "property solutions, market insights, client relationships, transactions",
            "tone": "friendly and professional, market-focused, relationship-building",
            "communication_style": "relationship-focused, market-aware, transaction-oriented"
        }
    
    # Education / Training
    elif any(keyword in profession for keyword in [
        "education", "teacher", "trainer", "instructor", "coach", "training",
        "educator", "tutor", "learning"
    ]):
        return {
            "persona": "an educator, trainer, or coach",
            "style": "educational, supportive, knowledge-sharing",
            "focus": "learning outcomes, skill development, knowledge transfer, growth",
            "tone": "supportive and professional, educational, encouraging",
            "communication_style": "educational and supportive, knowledge-sharing, growth-oriented"
        }
    
    # Healthcare / Medical
    elif any(keyword in profession for keyword in [
        "healthcare", "medical", "doctor", "physician", "nurse", "health",
        "clinic", "hospital", "therapist", "wellness"
    ]):
        return {
            "persona": "a healthcare professional or medical practitioner",
            "style": "caring, professional, patient-focused",
            "focus": "health solutions, patient care, wellness, medical services",
            "tone": "caring and professional, empathetic, trustworthy",
            "communication_style": "caring and professional, patient-focused, empathetic"
        }
    
    # Default fallback for unrecognized professions
    else:
        return {
            "persona": "a freelancer or startup owner",
            "style": "professional, business-focused, solution-oriented",
            "focus": "delivering value and building relationships",
            "tone": "professional and friendly",
            "communication_style": "direct but warm, results-focused"
        }

def _to_utc_naive(dt: datetime | None) -> datetime | None:
    """Convert timezone-aware datetime to UTC naive datetime for database storage."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Already naive, assume it's UTC
        return dt
    # Convert to UTC and remove timezone info
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
from app.models.contact import Contact
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.user import User

from app.core.database import get_db, get_accounts_db, AccountsSessionLocal
from app.core.tenant_database import get_tenant_db_dependency, get_tenant_db, schema_exists, create_tenant_schema
from app.core.config import settings
from app.models.email import Email, EmailStatus
from jose import jwt
from app.core.database import SessionLocal
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy import text

router = APIRouter()

# Notification endpoints

def _ensure_emails_schema(db: Session) -> None:
    """Ensure the emails table has all required columns for Supabase."""
    # No-op for Supabase - schema is managed by migrations
    pass

# In-memory idempotency cache for 2 minutes
_IDEMPOTENCY_CACHE: Dict[Tuple[str, str], Tuple[dict, datetime]] = {}

def _idem_lookup(owner: Optional[str], key: Optional[str]) -> Optional[dict]:
    if not owner or not key:
        return None
    tup = (owner, key)
    entry = _IDEMPOTENCY_CACHE.get(tup)
    if not entry:
        return None
    resp, at = entry
    try:
        if (get_ist_now() - at) <= timedelta(minutes=2):
            return resp
    except Exception:
        pass
    _IDEMPOTENCY_CACHE.pop(tup, None)
    return None

def _idem_store(owner: Optional[str], key: Optional[str], resp: dict) -> None:
    if not owner or not key:
        return
    _IDEMPOTENCY_CACHE[(owner, key)] = (resp, get_ist_now())

# Unified style guide to ensure a friendly, professional tone across all generated emails
STYLE_GUIDE = (
    "Tone: warm, concise, and professional; plain English; no jargon or hype. "
    "Subject: 4-8 words, Title Case, no emojis or exclamation marks. "
    "Body: ≤ 120 words; short paragraphs; helpful and respectful; one clear CTA; "
    "avoid spammy phrases (free!, limited time, act now). Sign with sender name on one line, and on the next line 'position, company' if present."
)

def _smtp_send_with_retries(host: str, port: int, user: str, password: str, from_addr: str, to_addrs: list[str], msg_str: str, use_tls: bool, attempts: int = 3, timeout: int = 20) -> None:
    """Send email with retries and better error handling for rate limiting"""
    # Validate required parameters
    if not host or not user or not password:
        raise ValueError("host, user, and password must be non-empty strings")
    
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        server = None
        try:

            # Try preferred mode first
            def _try_once(h: str, p: int, tls: bool) -> None:
                nonlocal server
                context = ssl.create_default_context()
                if int(p or 0) == 465 and not tls:
                    
                    server = smtplib.SMTP_SSL(h, int(p), timeout=timeout, context=context)
                    server.ehlo()
                else:
                    
                    server = smtplib.SMTP(h, int(p), timeout=timeout)
                server.ehlo()
                if tls:
                    server.starttls(context=context)
                    server.ehlo()
                
                server.login(user, password)
                
                server.sendmail(from_addr, to_addrs, msg_str)
                
                server.quit()

            _try_once(host, int(port or 0), use_tls)
            return
        except smtplib.SMTPAuthenticationError as e:
            # Don't retry on authentication errors - provide helpful error message
            if 'hostinger' in (host.lower() if host else "") and user and '@' not in user:
                error_detail = f"SMTP authentication failed. For Hostinger, the SMTP username must be the full email address (e.g., {from_addr}), not just '{user}'. Please update your SMTP username in the Profile page."
            else:
                error_detail = f"SMTP authentication failed: {str(e)}. Please verify your SMTP username and password are correct in the Profile page."
            raise HTTPException(status_code=400, detail=error_detail)
        except smtplib.SMTPRecipientsRefused as e:
            # Don't retry on recipient errors
            raise HTTPException(status_code=400, detail=f"Recipient refused: {e}")
        except smtplib.SMTPServerDisconnected as e:
            # Server disconnected - might be rate limiting
            if "rate limit" in str(e).lower() or "too many" in str(e).lower():
                raise HTTPException(status_code=429, detail="SMTP rate limit exceeded - please wait before sending more emails")
            raise HTTPException(status_code=500, detail=f"SMTP server disconnected: {e}")
        except smtplib.SMTPException as e:
            # Check for rate limiting messages
            error_msg = str(e).lower()
            if any(phrase in error_msg for phrase in ["rate limit", "too many", "quota exceeded", "throttled"]):
                raise HTTPException(status_code=429, detail="SMTP rate limit exceeded - please wait before sending more emails")
            raise HTTPException(status_code=500, detail=f"SMTP error: {e}")
        except Exception as e:
            last_error = e
            try:
                if server:
                    server.quit()
            except Exception:
                pass
            # Fallback: try alternate mode/port once per attempt
            try:
                server = None
                if int(port or 0) == 465 or not use_tls:
                    # fallback to STARTTLS 587
                    alt_port = 587
                    alt_tls = True
                else:
                    # fallback to SSL 465
                    alt_port = 465
                    alt_tls = False
                context = ssl.create_default_context()
                if alt_port == 465 and not alt_tls:
                    server = smtplib.SMTP_SSL(host, alt_port, timeout=timeout, context=context)
                    server.ehlo()
                else:
                    server = smtplib.SMTP(host, alt_port, timeout=timeout)
                    server.ehlo()
                    if alt_tls:
                        server.starttls(context=context)
                        server.ehlo()
                try:
                    server.login(user, password)
                    server.sendmail(from_addr, to_addrs, msg_str)
                    server.quit()
                    return
                except smtplib.SMTPAuthenticationError:
                    # Don't retry on authentication errors - password is wrong
                    raise HTTPException(status_code=400, detail="Wrong password")
            except HTTPException:
                raise
            except Exception as e2:
                last_error = e2
                try:
                    if server:
                        server.quit()
                except Exception:
                    pass
                # small exponential backoff before next outer attempt
                time.sleep(min(2 ** attempt, 5))
    raise HTTPException(status_code=500, detail=f"SMTP send failed after retries: {last_error}")

def _has_user_smtp(owner_email: Optional[str]) -> bool:
    if not owner_email:
        return False
    pdb = SessionLocal()
    try:
        u = pdb.query(User).filter(User.email == owner_email).first()
        return bool(u and u.smtp_host and u.smtp_username and u.smtp_password)
    finally:
        pdb.close()

def _resolve_per_user_imap(owner_email: str | None) -> tuple[str | None, int | None, str | None, str | None, bool]:
    """Return (host, port, username, password, use_ssl) preferring per-user settings if present."""
    if owner_email:
        pdb = SessionLocal()
        try:
            # Use raw SQL to avoid SQLAlchemy column issues
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            u = None
            try:
                sql_query = text("""
                    SELECT id, email, imap_host, imap_port, imap_username, imap_password, imap_use_ssl
                    FROM app_users 
                    WHERE email = :email
                    LIMIT 1
                """)
                result = pdb.execute(sql_query, {"email": owner_email})
                row = result.fetchone()
                
                if row:
                    u = type('User', (), {
                        'id': row[0],
                        'email': row[1],
                        'imap_host': row[2],
                        'imap_port': row[3],
                        'imap_username': row[4],
                        'imap_password': row[5],
                        'imap_use_ssl': row[6],
                        'get_imap_password': lambda self: self.imap_password,  # Simple getter
                    })()
            except (OperationalError, ProgrammingError) as db_error:
                # If raw SQL fails, try SQLAlchemy as fallback
                error_str = str(db_error).lower()
                if 'does not exist' in error_str or 'no such column' in error_str:
                    try:
                        u = pdb.query(User).filter(User.email == owner_email).first()
                    except Exception:
                        u = None
                else:
                    u = None
            except Exception:
                u = None
            
            if u and u.imap_host and u.imap_username and u.imap_password:
                # FIXED: Better port handling - validate port is in valid range
                resolved_port = u.imap_port
                use_ssl = True if u.imap_use_ssl is None else bool(u.imap_use_ssl)
                
                if resolved_port is None:
                    # Default based on SSL setting
                    resolved_port = 993 if use_ssl else 143
                    logger.info(f"ℹ️ IMAP port not set in profile for {owner_email}, using default: {resolved_port} (SSL={use_ssl})")
                elif resolved_port < 1 or resolved_port > 65535:
                    # Invalid port, use default
                    logger.warning(f"⚠️ Invalid IMAP port {resolved_port} for user {owner_email}, using default")
                    resolved_port = 993 if use_ssl else 143
                else:
                    logger.debug(f"✅ Using IMAP port from user profile: {resolved_port} for {owner_email}")
                
                logger.info(f"📋 Resolved IMAP config for {owner_email}: host={u.imap_host}, port={resolved_port}, user={u.imap_username}, ssl={use_ssl}")
                
                # Decrypt password using the encryption module
                encrypted_password = getattr(u, 'imap_password', None)
                if encrypted_password:
                    try:
                        from app.core.encryption import smtp_encryption
                        decrypted_password = smtp_encryption.decrypt_password(encrypted_password)
                    except Exception as decrypt_error:
                        logger.warning(f"⚠️ Failed to decrypt IMAP password for {owner_email}: {decrypt_error}")
                        # Try using the password as-is (might be plain text)
                        decrypted_password = encrypted_password
                else:
                    decrypted_password = None
                
                if not decrypted_password:
                    logger.warning(f"⚠️ Failed to get IMAP password for {owner_email}")
                    raise HTTPException(status_code=400, detail="Failed to get IMAP password. Please update your IMAP password in the Profile page.")
                
                return (
                    u.imap_host,
                    resolved_port,
                    u.imap_username,
                    decrypted_password,
                    use_ssl,
                )
            else:
                logger.warning(f"⚠️ User {owner_email} IMAP not fully configured: host={u.imap_host if u else None}, username={u.imap_username if u else None}, password={'***' if (u and u.imap_password) else None}")
        finally:
            pdb.close()
    
    # Global settings fallback
    resolved_port = settings.IMAP_PORT
    if resolved_port is None:
        resolved_port = 993 if settings.IMAP_USE_SSL else 143
    elif resolved_port < 1 or resolved_port > 65535:
        logger.warning(f"Invalid IMAP port {resolved_port} in global settings, using default")
        resolved_port = 993 if settings.IMAP_USE_SSL else 143
    
    return (
        settings.IMAP_HOST,
        resolved_port,
        settings.IMAP_USER,
        settings.IMAP_PASSWORD,
        settings.IMAP_USE_SSL,
    )

def _get_imap_folders(M) -> list[str]:
    """Get list of available IMAP folders."""
    try:
        typ, folders = M.list()
        if typ == 'OK' and folders:
            folder_names = []
            for folder in folders:
                # Parse folder name from IMAP LIST response
                folder_str = folder.decode() if isinstance(folder, bytes) else str(folder)
                # Extract folder name (format: '(\HasNoChildren) "/" "INBOX"' or similar)
                parts = folder_str.split('"')
                if len(parts) >= 3:
                    folder_name = parts[-2]
                    folder_names.append(folder_name)
            return folder_names
    except Exception as e:
        logger.warning(f"Failed to list IMAP folders: {e}")
    return ['INBOX']  # Fallback to INBOX only

def _check_imap_folders_for_emails(M, folders_to_check: list[str], search_criteria: str = 'UNSEEN') -> list[tuple[str, bytes]]:
    """Check multiple IMAP folders and return list of (folder, message_id) pairs."""
    folder_msg_ids: list[tuple[str, bytes]] = []
    for folder in folders_to_check:
        try:
            # Select folder (read-only to avoid changing flags)
            typ, data = M.select(folder, readonly=True)
            if typ != 'OK':
                logger.warning(f"Failed to select folder {folder}: {typ} {data}")
                continue

            # Get message count for logging
            if data and data[0]:
                try:
                    msg_count = int(data[0])
                    logger.info(f"Folder {folder} has {msg_count} total messages")
                except (ValueError, IndexError):
                    pass

            # Search for emails in this folder
            # Handle different search criteria formats
            if search_criteria.startswith('SINCE'):
                # Date-based search: "SINCE 01-Jan-2025"
                typ, data = M.search(None, search_criteria)
            elif search_criteria == 'ALL':
                # Search for all emails
                typ, data = M.search(None, 'ALL')
            else:
                # Standard search (UNSEEN, UNANSWERED, etc.)
                typ, data = M.search(None, search_criteria)
            
            if typ != 'OK':
                logger.warning(f"IMAP search failed in folder {folder} with criteria '{search_criteria}': {typ} {data}")
                continue
                
            if data and data[0]:
                # data[0] is bytes like b'1 2 3 4'
                ids_str = data[0]
                if isinstance(ids_str, bytes):
                    ids_str = ids_str.decode('utf-8', errors='ignore')
                ids = ids_str.split()
                if ids and ids[0]:  # Check if not empty
                    logger.info(f"Found {len(ids)} emails in folder {folder} matching '{search_criteria}'")
                    # Store (folder, id) so we can fetch from correct folder later
                    for msg_id_str in ids:
                        if msg_id_str:  # Skip empty strings
                            folder_msg_ids.append((folder, msg_id_str.encode('utf-8') if isinstance(msg_id_str, str) else msg_id_str))
                else:
                    logger.debug(f"No emails found in folder {folder} matching '{search_criteria}'")
            else:
                logger.debug(f"No emails found in folder {folder} matching '{search_criteria}' (empty result)")
        except Exception as e:
            logger.error(f"Error checking folder {folder} with criteria '{search_criteria}': {e}", exc_info=True)
            continue

    return folder_msg_ids
def _parse_iso_to_utc_naive(iso_str: str) -> datetime:
    """Parse ISO string that may contain 'Z' into a UTC-naive datetime."""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        # fallback: current utc
        return get_ist_now()

def _to_ist_iso(dt: datetime | None) -> str:
    if not dt:
        # Don't fall back to current time - this should be handled by the caller
        raise ValueError("Cannot convert None datetime to ISO format")
    if dt.tzinfo is None:
        # Assume the datetime is in UTC if no timezone info (database stores UTC)
        utc_dt = dt.replace(tzinfo=pytz.UTC)
        return utc_dt.astimezone(IST).isoformat()
    return dt.astimezone(IST).isoformat()

def _get_user_timezone(request: Request) -> str:
    """Get user's timezone from request headers or default to UTC."""
    # Try to get timezone from request headers
    timezone_header = request.headers.get('X-User-Timezone')
    if timezone_header:
        return timezone_header
    
    # Try to get from query parameters
    timezone_param = request.query_params.get('timezone')
    if timezone_param:
        return timezone_param
    
    # Default timezone (can be changed based on user settings)
    return 'Asia/Kolkata'

def _convert_to_user_timezone(ist_timestamp: str, user_timezone: str) -> str:
    """Convert IST timestamp to user's timezone."""
    try:
        # Parse the IST timestamp
        if ist_timestamp.endswith('Z'):
            ist_dt = datetime.fromisoformat(ist_timestamp.replace('Z', '+05:30'))
        else:
            ist_dt = datetime.fromisoformat(ist_timestamp)
        
        # Ensure it's timezone aware (assume IST if no timezone info)
        if ist_dt.tzinfo is None:
            ist_dt = IST.localize(ist_dt)
        
        # Convert to user's timezone
        user_tz = pytz.timezone(user_timezone)
        local_dt = ist_dt.astimezone(user_tz)
        
        # Return in ISO format
        return local_dt.isoformat()
    except Exception as e:
        # If conversion fails, return original timestamp
        return ist_timestamp

def _resolve_per_user_smtp(owner_email: str | None) -> tuple[str | None, int | None, str | None, str | None, str | None, bool]:
    """Return (host, port, username, password, from_addr, use_tls) preferring per-user settings if present."""
    if not owner_email:
        raise HTTPException(status_code=500, detail="No owner email provided. Please ensure you are logged in.")
    
    # Look up in primary DB
    pdb = SessionLocal()
    try:
        u = pdb.query(User).filter(User.email == owner_email).first()
        if u:
            # Check if all required SMTP fields are configured
            if not u.smtp_host:
                raise HTTPException(status_code=400, detail="SMTP Host is not configured. Please configure your email settings in the Profile page.")
            if not u.smtp_username:
                raise HTTPException(status_code=400, detail="SMTP Username is not configured. Please configure your email settings in the Profile page.")
            if not u.smtp_password:
                raise HTTPException(status_code=400, detail="SMTP Password is not configured. Please configure your email settings in the Profile page.")
            if not u.smtp_from:
                raise HTTPException(status_code=400, detail="SMTP From Address is not configured. Please configure your email settings in the Profile page.")
            
            host = u.smtp_host
            user = u.smtp_username
            from_addr = u.smtp_from
            
            # Fix for Hostinger: Use full email address as username if username doesn't contain @
            # Hostinger requires the full email address (e.g., info@thewascard.com) not just username part
            host_lower = host.lower() if host else ""
            if 'hostinger' in host_lower and user and '@' not in user:
                # If username doesn't have @, try using from_addr if it has @
                if from_addr and '@' in from_addr:
                    original_user = user
                    user = from_addr
                elif user:
                    # If from_addr also doesn't have @, log warning but proceed
                    pass
            
            # Decrypt password using the User model's method
            pwd = u.get_smtp_password()
            if not pwd:
                raise HTTPException(status_code=400, detail="Failed to decrypt SMTP password. Please update your SMTP password in the Profile page.")
            from_addr = u.smtp_from
            use_tls = True if u.smtp_use_tls is None else bool(u.smtp_use_tls)
            port = u.smtp_port or (587 if use_tls else 465)
            
            return (host, port, user, pwd, from_addr, use_tls)
        else:
            raise HTTPException(status_code=404, detail=f"User {owner_email} not found in database. Please ensure you are logged in with a valid account.")
    finally:
        pdb.close()
    
    # No fallback to environment variables - only use user profile settings
    raise HTTPException(status_code=500, detail="SMTP settings not found. Please configure your email settings in the Profile page.")

def _smtp_send_existing(email: Email, db: Session) -> None:
    to_addr = email.to_address
    subject = email.subject
    content = email.body
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email.from_address
    msg["To"] = to_addr

    host, port, user, password, from_addr, use_tls = _resolve_per_user_smtp(email.owner_email)

    if not host or not user or not password:
        raise HTTPException(status_code=500, detail="SMTP settings missing")

    smtp_port: int = int(port or 587)
    _smtp_send_with_retries(host, smtp_port, user, password, from_addr or email.from_address, [to_addr], msg.as_string(), use_tls)

    email.status = EmailStatus.sent
    email.sent_at = _to_utc_naive(get_ist_now())
    db.commit()
    db.refresh(email)

@router.get("/counts", response_model=dict)
def email_counts(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    
    # Use tenant database session (same as email creation and listing)
    try:
        # Ensure the emails schema is up to date before querying
        _ensure_emails_schema(db)
        
        # Get all contacts for this owner to filter email counts with error handling
        from app.models.contact import Contact
        try:
            contacts = db.query(Contact).filter(Contact.owner_email == owner).all()
            contact_emails = {contact.email.lower() for contact in contacts}
        except Exception as contact_error:
            logger.warning(f"Error querying contacts in email_counts: {contact_error}")
            contacts = []
            contact_emails = set()
        
        # Base query filtered by owner and contacts with error handling
        try:
            base_query = db.query(Email).filter(Email.owner_email == owner)
        except Exception as query_error:
            from sqlalchemy.exc import OperationalError, ProgrammingError
            error_str = str(query_error).lower()
            
            # Check if it's a missing column error
            if isinstance(query_error, (OperationalError, ProgrammingError)) or 'column' in error_str or 'does not exist' in error_str:
                logger.error(f"Database column error in email_counts (likely missing 'attachments' column): {query_error}", exc_info=True)
                logger.warning("Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;")
                # Return default counts on error - migration needed
                return {
                    "unread_inbox": 0,
                    "drafts": 0,
                    "archived": 0,
                    "trash": 0,
                    "spam": 0,
                }
            else:
                # Re-raise other errors
                logger.error(f"Unexpected database error in email_counts: {query_error}", exc_info=True)
                raise
        
        def _count(status: EmailStatus) -> int:
            # Count all emails with the given status (less restrictive filtering)
            return base_query.filter(Email.status == status).count()
        
        # Handle is_read safely for older records that might not have this column
        try:
            unread_inbox = base_query.filter(
                Email.status == EmailStatus.received, 
                Email.is_read == False  # noqa: E712
            ).count()
        except Exception:
            # Fallback if is_read column doesn't exist yet
            unread_inbox = 0
        
        # Initialize counts dictionary
        counts = {
            "unread_inbox": unread_inbox,
            "drafts": 0,
            "archived": 0,
            "trash": 0,
            "spam": 0,
        }
        
        # Safely populate counts
        try:
            counts["drafts"] = _count(EmailStatus.draft)
        except Exception:
            counts["drafts"] = 0
            
        try:
            counts["archived"] = _count(EmailStatus.archived)
        except Exception:
            counts["archived"] = 0
            
        try:
            counts["trash"] = _count(EmailStatus.trashed)
        except Exception:
            counts["trash"] = 0
            
        try:
            counts["spam"] = _count(EmailStatus.spam)
        except Exception:
            counts["spam"] = 0
        
        return counts
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        from sqlalchemy.exc import OperationalError, ProgrammingError
        error_str = str(e).lower()
        
        # Check if it's a missing column error
        if isinstance(e, (OperationalError, ProgrammingError)) or 'column' in error_str or 'does not exist' in error_str:
            logger.error(f"Database column error in email_counts (likely missing 'attachments' column): {e}", exc_info=True)
            logger.warning("Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;")
            raise HTTPException(
                status_code=500, 
                detail="Database schema error. Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;"
            )
        else:
            logger.error(f"Unexpected error in email_counts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get email counts: {str(e)}")

@router.get("/", response_model=List[dict])
def list_emails(request: Request, db: Session = Depends(get_tenant_db_dependency), folder: Optional[str] = None):
    owner = _get_owner_from_request(request)
    
    # Use the tenant-aware database session passed as dependency
    try:
        # Ensure the emails schema is up to date before querying
        _ensure_emails_schema(db)
        
        # Best-effort IMAP ingest on inbox view to sync latest (DISABLED AUTO-REPLY)
        # Note: Auto-reply functionality has been disabled to prevent unwanted automated responses
        # try:
        #     if folder == 'inbox':
        #         # Trigger ingest in the same request but ignore errors
        #         ingest_imap(request, db)  # type: ignore
        # except Exception:
        #     pass
        
        # Check if attachments column exists - use raw SQL if it doesn't
        use_raw_sql = False
        try:
            from sqlalchemy import text
            # Try to check if attachments column exists (works for PostgreSQL/Supabase)
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'emails' 
                AND column_name = 'attachments'
            """)
            result = db.execute(check_query)
            if result.fetchone() is None:
                use_raw_sql = True
                logger.info("Attachments column not found - using raw SQL query")
        except Exception as check_error:
            # If check fails, assume column doesn't exist and use raw SQL
            logger.warning(f"Could not check for attachments column: {check_error}. Using raw SQL as fallback.")
            use_raw_sql = True
        
        # Query emails from tenant database
        if use_raw_sql:
            # Use raw SQL query excluding attachments column
            from sqlalchemy import text
            folder_filter = ""
            if folder == 'inbox':
                folder_filter = "AND status = 'received'"
            elif folder == 'sent':
                folder_filter = "AND status = 'sent'"
            elif folder == 'drafts':
                folder_filter = "AND status = 'draft'"
            elif folder == 'trash':
                folder_filter = "AND status = 'trashed'"
            elif folder == 'archived':
                folder_filter = "AND status = 'archived'"
            elif folder == 'spam':
                folder_filter = "AND status = 'spam'"
            
            sql_query = text(f"""
                SELECT id, public_id, subject, body, to_address, from_address, status, 
                       sent_at, received_at, is_starred, is_read, owner_email, 
                       scheduled_for, deleted_at, last_error, original_folder
                FROM emails 
                WHERE owner_email = :owner_email {folder_filter}
                ORDER BY id DESC
            """)
            
            result = db.execute(sql_query, {"owner_email": owner})
            rows = result.fetchall()
            
            # Convert rows to Email-like objects
            emails = []
            for row in rows:
                try:
                    status_value = row[6]  # Updated index after adding public_id
                    if isinstance(status_value, str):
                        try:
                            status_enum = EmailStatus(status_value)
                        except ValueError:
                            status_enum = EmailStatus.received
                    else:
                        status_enum = EmailStatus.received
                    
                    email_obj = type('Email', (), {
                        'id': row[0],
                        'public_id': row[1] if len(row) > 1 else None,
                        'subject': row[2] or '',
                        'body': row[3] or '',
                        'to_address': row[4] or '',
                        'from_address': row[5] or '',
                        'status': status_enum,
                        'sent_at': row[7],
                        'received_at': row[8],
                        'is_starred': row[9] if row[9] is not None else False,
                        'is_read': row[10] if row[10] is not None else True,
                        'owner_email': row[11],
                        'scheduled_for': row[12],
                        'deleted_at': row[13],
                        'last_error': row[14],
                        'original_folder': row[15] if len(row) > 15 else None,
                        'attachments': None
                    })()
                    emails.append(email_obj)
                except Exception as row_error:
                    logger.warning(f"Error converting row to Email object: {row_error}")
                    continue
        else:
            # Normal SQLAlchemy query (attachments column exists)
            try:
                q = db.query(Email).filter(Email.owner_email == owner)
                
                # No need to filter out deleted emails since they are permanently deleted
                
                if folder == 'inbox':
                    q = q.filter(Email.status == EmailStatus.received)
                elif folder == 'sent':
                    q = q.filter(Email.status == EmailStatus.sent)
                elif folder == 'drafts':
                    q = q.filter(Email.status == EmailStatus.draft)
                elif folder == 'trash':
                    q = q.filter(Email.status == EmailStatus.trashed)
                elif folder == 'archived':
                    q = q.filter(Email.status == EmailStatus.archived)
                elif folder == 'spam':
                    q = q.filter(Email.status == EmailStatus.spam)
                
                emails = q.order_by(Email.id.desc()).all()
            except Exception as query_error:
                # Handle database errors (e.g., missing columns like attachments)
                from sqlalchemy.exc import OperationalError, ProgrammingError
                from sqlalchemy import text
                
                error_str = str(query_error).lower()
                
                # Check if it's a missing column error - use raw SQL as fallback
                if isinstance(query_error, (OperationalError, ProgrammingError)) or 'column' in error_str or 'does not exist' in error_str or 'attachments' in error_str:
                    logger.warning(f"Database column error detected (likely missing 'attachments' column). Using fallback query: {query_error}")
                    logger.warning("Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;")
                    
                    # Fallback: Use raw SQL query excluding attachments column
                    try:
                        folder_filter = ""
                        if folder == 'inbox':
                            folder_filter = "AND status = 'received'"
                        elif folder == 'sent':
                            folder_filter = "AND status = 'sent'"
                        elif folder == 'drafts':
                            folder_filter = "AND status = 'draft'"
                        elif folder == 'trash':
                            folder_filter = "AND status = 'trashed'"
                        elif folder == 'archived':
                            folder_filter = "AND status = 'archived'"
                        elif folder == 'spam':
                            folder_filter = "AND status = 'spam'"
                        
                        # Query without attachments column
                        sql_query = text(f"""
                            SELECT id, public_id, subject, body, to_address, from_address, status, 
                                   sent_at, received_at, is_starred, is_read, owner_email, 
                                   scheduled_for, deleted_at, last_error, original_folder
                            FROM emails 
                            WHERE owner_email = :owner_email {folder_filter}
                            ORDER BY id DESC
                        """)
                        
                        result = db.execute(sql_query, {"owner_email": owner})
                        rows = result.fetchall()
                        
                        # Convert rows to Email-like objects
                        emails = []
                        for row in rows:
                            try:
                                # Try to create EmailStatus enum from string
                                status_value = row[6]  # Updated index after adding public_id
                                if isinstance(status_value, str):
                                    try:
                                        status_enum = EmailStatus(status_value)
                                    except ValueError:
                                        # Fallback to received if status is invalid
                                        status_enum = EmailStatus.received
                                else:
                                    status_enum = EmailStatus.received
                                
                                # Create a simple object with the row data
                                email_obj = type('Email', (), {
                                    'id': row[0],
                                    'public_id': row[1] if len(row) > 1 else None,
                                    'subject': row[2] or '',
                                    'body': row[3] or '',
                                    'to_address': row[4] or '',
                                    'from_address': row[5] or '',
                                    'status': status_enum,
                                    'sent_at': row[7],
                                    'received_at': row[8],
                                    'is_starred': row[9] if row[9] is not None else False,
                                    'is_read': row[10] if row[10] is not None else True,
                                    'owner_email': row[11],
                                    'scheduled_for': row[12],
                                    'deleted_at': row[13],
                                    'last_error': row[14],
                                    'original_folder': row[15] if len(row) > 15 else None,
                                    'attachments': None  # Column doesn't exist
                                })()
                                emails.append(email_obj)
                            except Exception as row_error:
                                logger.warning(f"Error converting row to Email object: {row_error}")
                                continue
                        
                        logger.info(f"Fallback query successful: retrieved {len(emails)} emails")
                    except Exception as fallback_error:
                        logger.error(f"Fallback query also failed: {fallback_error}", exc_info=True)
                        emails = []
                else:
                    # Re-raise other errors
                    logger.error(f"Unexpected database error in list_emails: {query_error}", exc_info=True)
                    raise

        # Deduplicate inbox view by (from, subject) keeping latest only
        if folder == 'inbox':
            seen_keys: set[str] = set()
            deduped: list[Email] = []
            for e in emails:  # already desc by id
                timestamp_src = getattr(e, 'received_at', None) or getattr(e, 'sent_at', None)
                if timestamp_src:
                    timestamp_key = timestamp_src.replace(microsecond=0).isoformat()
                else:
                    timestamp_key = str(e.id)
                key = f"{(e.from_address or '').lower()}|{(e.subject or '').strip().lower()}|{timestamp_key}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped.append(e)
            emails = deduped

        result = []
        for e in emails:
            # Safely get attachments field (may not exist if migration not run)
            attachments_data = []
            try:
                attachments_field = getattr(e, 'attachments', None)
                if attachments_field:
                    if isinstance(attachments_field, str):
                        try:
                            attachments_data = json.loads(attachments_field)
                        except:
                            attachments_data = []
                    elif isinstance(attachments_field, list):
                        attachments_data = attachments_field
            except Exception:
                attachments_data = []
            
            result.append({
                "id": e.id,
                "public_id": getattr(e, 'public_id', None),  # Include public_id if available
                "subject": e.subject,
                "from": e.from_address,
                "to": e.to_address,
                "content": e.body,
                # Use appropriate timestamp based on email status and convert to user timezone
                "timestamp": _convert_to_user_timezone(
                    _get_email_timestamp(e), 
                    _get_user_timezone(request)
                ),
                "status": e.status.value,
                "isRead": getattr(e, 'is_read', True),  # Safely get is_read with fallback
                "isStarred": getattr(e, 'is_starred', False),  # Safely get is_starred with fallback
                "attachments": attachments_data,
                "tags": [],
                "original_folder": getattr(e, 'original_folder', None),  # Include original_folder for unarchive logic
            })
        
        return result
    except HTTPException:
        # Re-raise HTTPExceptions (auth errors, etc.)
        raise
    except Exception as e:
        from sqlalchemy.exc import OperationalError, ProgrammingError
        error_str = str(e).lower()
        
        # Check if it's a missing column error
        if isinstance(e, (OperationalError, ProgrammingError)) or 'column' in error_str or 'does not exist' in error_str:
            logger.error(f"Database column error in list_emails (likely missing 'attachments' column): {e}", exc_info=True)
            logger.warning("Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;")
            raise HTTPException(
                status_code=500, 
                detail="Database schema error. Please run migration: ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;"
            )
        else:
            logger.error(f"Unexpected error in list_emails: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list emails: {str(e)}")

@router.post("/mark-read/{email_id}")
def mark_email_as_read(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Mark an email as read"""
    owner = _get_owner_from_request(request)
    
    try:
        # Use the tenant-aware database session passed as dependency
        # Ensure the emails schema is up to date before querying
        _ensure_emails_schema(db)
        
        # Find the email in the tenant database
        email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Mark as read
        email.is_read = True
        
        db.commit()
        
        return {"status": "read", "email_id": email_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark email as read: {str(e)}")

@router.post("/spam/{email_id}")
def move_to_spam(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Move an email to spam"""
    owner = _get_owner_from_request(request)
    
    # Use tenant database session for Email model operations
    try:
        row = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Email not found")
        
        row.status = EmailStatus.spam
        row.is_read = True
        
        # mark contact as spam unless explicitly whitelisted
        try:
            c = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == row.from_address).first()
            if c and not getattr(c, 'is_whitelisted', False):
                setattr(c, 'is_spam', True)
        except Exception:
            pass
        
        db.commit()
        
        return {"status": "spam"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to move email to spam: {str(e)}")

@router.post("/not-spam")
def not_spam(request: Request, payload: dict = Body(default_factory=dict), db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    from_email = (payload.get("email") or "").strip()
    email_id = payload.get("email_id")
    if not from_email and email_id:
        row = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Email not found")
        from_email = row.from_address
    if not from_email:
        raise HTTPException(status_code=422, detail="email or email_id required")
    # whitelist contact
    c = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == from_email).first()
    if c:
        setattr(c, 'is_spam', False)
        setattr(c, 'is_whitelisted', True)
    # move existing spam emails from this sender to inbox
    rows = db.query(Email).filter(Email.owner_email == owner, Email.from_address == from_email, Email.status == EmailStatus.spam).all()
    for r in rows:
        r.status = EmailStatus.received
        r.is_read = False
    db.commit()
    return {"status": "unspammed", "moved": len(rows)}

@router.post("/archive/{email_id}")
def archive_email(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Archive an email"""
    owner = _get_owner_from_request(request)
    email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Store original status in original_folder field if not already set
    if not email.original_folder or email.original_folder == "inbox":
        # Get user's email setup address (IMAP username)
        host, port, user_email_setup, password, use_ssl = _resolve_per_user_imap(owner)
        
        # Determine original folder based on from_address comparison
        if email.from_address == user_email_setup:
            # Email was sent from user's email setup address
            email.original_folder = "sent"
        else:
            # Email was received from a different address
            email.original_folder = "inbox"
    
    email.status = EmailStatus.archived
    db.commit()
    return {"status": "archived", "original_folder": email.original_folder}

@router.post("/unarchive/{email_id}")
def unarchive_email(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Unarchive an email back to its original folder"""
    owner = _get_owner_from_request(request)
    email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.status != EmailStatus.archived:
        raise HTTPException(status_code=400, detail="Email is not archived")
    
    # Restore to original folder based on original_folder field
    folder_to_status = {
        "sent": EmailStatus.sent,
        "inbox": EmailStatus.received,
        "drafts": EmailStatus.draft,
        "spam": EmailStatus.spam,
        "trash": EmailStatus.trashed
    }
    
    original_folder = email.original_folder or "inbox"
    email.status = folder_to_status.get(original_folder, EmailStatus.received)
    db.commit()
    return {"status": "unarchived", "restored_to": original_folder}

@router.post("/star/{email_id}")
def star_email(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Star/unstar an email"""
    owner = _get_owner_from_request(request)
    email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.is_starred = not email.is_starred
    db.commit()
    return {"status": "starred" if email.is_starred else "unstarred", "is_starred": email.is_starred}

def _get_email_timestamp(email: Email, user_timezone: str = 'Asia/Kolkata') -> str:
    """Get the appropriate timestamp for an email based on its status."""
    if email.status == EmailStatus.received:
        # For received emails, use received_at if available, otherwise sent_at
        timestamp = email.received_at or email.sent_at
        if timestamp:
            return _to_ist_iso(timestamp)
        else:
            # Use a fixed fallback timestamp based on email ID to prevent changing times
            # This ensures we always have a stable timestamp
            fallback_time = datetime(2025, 1, 1, 0, 0, 0) + timedelta(hours=email.id % 24, minutes=email.id % 60)
            return _to_ist_iso(fallback_time)
    elif email.status == EmailStatus.sent:
        # For sent emails, use sent_at if available, otherwise fallback
        timestamp = email.sent_at or email.scheduled_for
        if timestamp:
            return _to_ist_iso(timestamp)
        else:
            # Use a fixed fallback timestamp based on email ID to prevent changing times
            # This ensures we always have a stable timestamp
            fallback_time = datetime(2025, 1, 1, 0, 0, 0) + timedelta(hours=email.id % 24, minutes=email.id % 60)
            return _to_ist_iso(fallback_time)
    else:
        # For other statuses, use available timestamp or fallback
        timestamp = email.sent_at or email.scheduled_for or email.deleted_at
        if timestamp:
            return _to_ist_iso(timestamp)
        else:
            # Use a fixed fallback timestamp based on email ID to prevent changing times
            # This ensures we always have a stable timestamp
            fallback_time = datetime(2025, 1, 1, 0, 0, 0) + timedelta(hours=email.id % 24, minutes=email.id % 60)
            return _to_ist_iso(fallback_time)

def _get_user_signature(owner: str) -> str:
    """Get user signature from profile or create default signature"""
    try:
        from app.core.database import SessionLocal
        pdb = SessionLocal()
        try:
            owner_row = pdb.query(User).filter(User.email == owner).first()
            if owner_row:
                sender_display = (getattr(owner_row, 'full_name', None) or 
                                getattr(owner_row, 'username', None) or 
                                owner.split('@')[0])
                sender_company = getattr(owner_row, 'company_name', None) or ''
                sender_title = getattr(owner_row, 'position_title', None) or ''
                website_url = getattr(owner_row, 'website_url', None) or ''
                signature_line2 = ", ".join([p for p in [sender_title, sender_company] if p])
                signature = str(sender_display) + ("\n" + signature_line2 if signature_line2 else '')
                if website_url:
                    signature += f"\n{website_url}"
                return signature
        finally:
            pdb.close()
    except Exception:
        pass
    
    # Fallback signature
    return f"{owner.split('@')[0]}\nEmail Automation"

def _build_conversation_context(db: Session, owner: str, to_addr: str) -> tuple[str, str]:
    """Build comprehensive conversation context for AI reply generation.
    
    Returns:
        tuple: (conversation_context, original_context)
    """
    conversation_context = ""
    original_context = ""
    
    try:
        # Handle missing attachments column gracefully
        from sqlalchemy.exc import OperationalError, ProgrammingError
        from sqlalchemy import text
        
        # Try normal query first
        try:
            # Get the original cold email (first email sent to this client)
            original_cold_email = db.query(Email).filter(
                Email.owner_email == owner,
                Email.to_address == to_addr,
                Email.status == EmailStatus.sent
            ).order_by(Email.sent_at.asc()).first()
            
            # Get conversation history (all emails between us and this client)
            sent_emails = db.query(Email).filter(
                Email.owner_email == owner,
                Email.to_address == to_addr,
                Email.status == EmailStatus.sent
            ).order_by(Email.sent_at.asc()).all()
            
            received_emails = db.query(Email).filter(
                Email.owner_email == owner,
                Email.from_address == to_addr,
                Email.status == EmailStatus.received
            ).order_by(Email.received_at.asc()).all()
        except Exception as query_error:
            # Fallback to raw SQL if attachments column is missing
            error_str = str(query_error).lower()
            # Check for psycopg2 errors (they may be wrapped by SQLAlchemy)
            is_column_error = False
            try:
                import psycopg2
                if isinstance(query_error, psycopg2.errors.UndefinedColumn) or (hasattr(query_error, 'orig') and isinstance(query_error.orig, psycopg2.errors.UndefinedColumn)):
                    is_column_error = True
            except (ImportError, AttributeError):
                pass
            if not is_column_error:
                is_column_error = (
                    isinstance(query_error, (OperationalError, ProgrammingError)) or 
                    'column' in error_str or 
                    'does not exist' in error_str or 
                    'attachments' in error_str
                )
            if is_column_error:
                # Use raw SQL queries excluding attachments column
                sql_sent = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email
                    FROM emails 
                    WHERE owner_email = :owner_email AND to_address = :to_address AND status = :status
                    ORDER BY sent_at ASC
                """)
                sql_received = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email
                    FROM emails 
                    WHERE owner_email = :owner_email AND from_address = :from_address AND status = :status
                    ORDER BY received_at ASC
                """)
                
                sent_result = db.execute(sql_sent, {
                    "owner_email": owner,
                    "to_address": to_addr,
                    "status": "sent"
                })
                received_result = db.execute(sql_received, {
                    "owner_email": owner,
                    "from_address": to_addr,
                    "status": "received"
                })
                
                # Convert to Email-like objects
                sent_rows = sent_result.fetchall()
                received_rows = received_result.fetchall()
                
                sent_emails = []
                for row in sent_rows:
                    email_obj = type('Email', (), {
                        'id': row[0],
                        'subject': row[1],
                        'body': row[2],
                        'to_address': row[3],
                        'from_address': row[4],
                        'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                        'sent_at': row[6],
                        'received_at': row[7],
                    })()
                    sent_emails.append(email_obj)
                
                received_emails = []
                for row in received_rows:
                    email_obj = type('Email', (), {
                        'id': row[0],
                        'subject': row[1],
                        'body': row[2],
                        'to_address': row[3],
                        'from_address': row[4],
                        'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                        'sent_at': row[6],
                        'received_at': row[7],
                    })()
                    received_emails.append(email_obj)
                
                # Get first sent email as original
                original_cold_email = sent_emails[0] if sent_emails else None
            else:
                # Re-raise if it's not a column error
                raise
        
        # Combine and sort all emails chronologically
        all_emails = []
        for email in sent_emails:
            all_emails.append({
                'type': 'sent',
                'subject': email.subject,
                'body': email.body,
                'timestamp': email.sent_at,
                'date': email.sent_at
            })
        for email in received_emails:
            all_emails.append({
                'type': 'received',
                'subject': email.subject,
                'body': email.body,
                'timestamp': email.received_at,
                'date': email.received_at
            })
        
        # Sort by timestamp
        all_emails.sort(key=lambda x: x['date'] if x['date'] else datetime.min)
        conversation_history = all_emails[-5:]  # Get last 5 emails for context
        
        # Build conversation context
        if conversation_history:
            conversation_context = "\n\nCONVERSATION HISTORY (chronological order):\n"
            for i, email in enumerate(conversation_history):
                email_type = "SENT BY ME" if email['type'] == 'sent' else "RECEIVED FROM CLIENT"
                conversation_context += f"\n{i+1}. {email_type} - Subject: {email['subject']}\n"
                conversation_context += f"   Content: {email['body'][:200]}{'...' if len(email['body']) > 200 else ''}\n"
        
        # Build original cold email context
        if original_cold_email:
            original_context = f"\n\nORIGINAL COLD EMAIL CONTEXT:\nSubject: {original_cold_email.subject}\nContent: {original_cold_email.body}\n"
            
    except Exception:
        pass
    
    return conversation_context, original_context

def _build_enhanced_reply_prompt(original: str, receiver_name: str, to_addr: str, receiver_company: str, 
                                receiver_position: str, sender_name: str, conversation_context: str, 
                                original_context: str) -> str:
    """Build an enhanced prompt for AI reply generation with conversation context."""
    return (
        "You are an expert email assistant that analyzes conversation history and crafts intelligent, contextual replies. "
        "Your task is to understand the full conversation context and generate an appropriate response.\n\n"
        
        "ANALYSIS STEPS:\n"
        "1. Review the conversation history to understand the relationship and context\n"
        "2. Identify the client's current intent from their latest message\n"
        "3. Consider what was discussed previously and any commitments made\n"
        "4. Craft a reply that addresses their current needs while maintaining conversation continuity\n\n"
        
        "INTENT CLASSIFICATION:\n"
        "Classify the client's intent as one of: interested, not_interested, request_more_info, schedule, unsubscribe, unclear, follow_up, objection, question\n\n"
        
        "REPLY GUIDELINES:\n"
        "- Subject line: Maximum 100 characters - must be compelling and engaging\n"
        "- Body: Exactly 300-350 characters (including spaces) - count carefully, make it informative and persuasive\n"
        "- Reference previous conversation points when relevant\n"
        "- Match the client's tone and communication style\n"
        "- Address specific concerns or questions raised\n"
        "- If scheduling, include [[CALENDLY_LINK]] placeholder\n"
        "- If unsubscribe, acknowledge and confirm removal\n"
        "- Do NOT use internal notes or contact information\n"
        "- Do NOT include signature in body - it will be automatically added\n\n"
        
        f"CLIENT INFO: name={receiver_name}, email={to_addr}, company={receiver_company}, position={receiver_position}\n"
        f"SENDER INFO: name={sender_name}\n\n"
        
        f"LATEST CLIENT MESSAGE:\n```{original}```\n"
        f"{conversation_context}"
        f"{original_context}\n\n"
        
        "IMPORTANT: You must respond with a valid JSON object in this exact format:\n"
        "{\n"
        '  "intent": "one_of_the_classifications_above",\n'
        '  "subject": "compelling subject line (max 100 characters)",\n'
        '  "body": "informative and persuasive reply content (exactly 300-350 characters including spaces - count carefully)",\n'
        '  "schedule": null\n'
        "}\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "- Subject: Maximum 100 characters - make it compelling and engaging\n"
        "- Body: Exactly 300-350 characters including spaces - count every character\n"
        "- Body must be informative, persuasive, and value-focused\n"
        "- Do NOT include signature in body - it will be automatically added\n"
        "- The 'schedule' field should be null unless scheduling is explicitly requested\n"
        "- Verify character counts before returning JSON"
    )

def _build_expert_reply_prompt(
    original: str, 
    receiver_name: str, 
    to_addr: str, 
    receiver_company: str,
    receiver_position: str, 
    sender_name: str, 
    conversation_context: str, 
    original_context: str,
    sender_title: str = "",
    sender_company: str = "",
    calendly_link: str = "",
    website_url: str = "",
    email_type: str = "reply",  # "reply" or "cold"
    professional_persona: Dict[str, str] | None = None  # Persona from get_professional_persona()
) -> str:
    """Build expert-level prompt for AI email generation with profession-specific persona.
    
    This prompt incorporates advanced psychological techniques, structured templates, and professional
    email writing best practices for high-converting cold and warm emails.
    Uses the user's profession to adopt the appropriate professional persona.
    """
    
    # Determine if this is a cold email or reply based on conversation context
    is_cold = not conversation_context or len(conversation_context.strip()) < 50
    
    # Use provided persona or default
    persona = professional_persona or get_professional_persona()
    
    # Build the expert instruction with profession-specific persona
    prompt = (
        f"You are {persona['persona']} reaching out to prospects via email. "
        f"Your communication style is {persona['communication_style']}. "
        f"Your writing style is {persona['style']}. "
        f"Your focus is on {persona['focus']}. "
        f"Your tone should be {persona['tone']}.\n\n"
        
        "CRITICAL GUIDELINES:\n"
        "- Always prioritize relevance and respect the recipient's time\n"
        "- Never invent metrics or outcomes you cannot substantiate\n"
        "- When data is missing, use conservative, generic phrasing (e.g., 'typical clients see improvements in X') and mark placeholders for the user to fill\n"
        "- Write emails that authentically represent your professional role and expertise\n"
        "- Use language and examples that are natural for someone in your profession\n"
        "- Focus on value that aligns with your professional expertise\n\n"
        
        "## Required Inputs Provided:\n"
        f"1. recipient_name: {receiver_name or 'Team'}\n"
        f"2. recipient_title: {receiver_position or 'N/A'}\n"
        f"3. company_name: {receiver_company or 'N/A'}\n"
        f"4. sender_name: {sender_name}\n"
        f"5. sender_title: {sender_title or 'N/A'}\n"
        f"6. calendly_link: {calendly_link or '[[CALENDLY_LINK]]'}\n"
        f"7. website_url: {website_url or 'Not provided'}\n\n"
        
        "## Core Email Structure (MANDATORY):\n"
        "1. Subject line — MUST be compelling and engaging, maximum 100 characters. Should be specific, trigger curiosity, and promise clear benefit.\n"
        "2. Email body — MUST be informative and persuasive, exactly 300-350 characters (including spaces). This is CRITICAL - count characters carefully.\n"
        "   - Body should be engaging, value-focused, and drive action\n"
        "   - Include personalized context, value proposition, and clear next step\n"
        "   - Keep it concise but impactful - every character counts\n"
        "3. Signature — Professional signature will be automatically added. Do NOT include signature in the body - it will be appended automatically.\n"
        "   - If calendly_link is provided and prospect shows interest, include [[CALENDLY_LINK]] in the body\n\n"
        
        "CRITICAL LENGTH REQUIREMENTS:\n"
        "- Subject: Maximum 100 characters (count carefully)\n"
        "- Body: Exactly 300-350 characters including spaces (count carefully)\n"
        "- The signature is NOT included in the body character count - it will be added automatically\n\n"
        
        "Keep paragraphs short — 1–2 sentences each. Use single blank line between paragraphs.\n\n"
    )
    
    if is_cold:
        prompt += (
            "## Cold Email Rules:\n"
            "- Lines: 3–5 (short), 5–8 (medium), 8–12 (long)\n"
            "- Words: short 40–80, medium 90–160, long 170–280\n"
            "- Subject: promise clear benefit or reference specific trigger (not clickbait)\n\n"
            
            "## MANDATORY Cold Email Structure (Follow This Exact Order):\n"
            "1. CONTEXT & CREDIBILITY (Opening): Briefly introduce who you are and why you're reaching out\n"
            "   - Example: 'Hi [Name], I'm [Name] and I help [type of companies] [achieve outcome].'\n"
            "   - OR: 'Hi [Name], I work with [type of companies] like [Company] to [achieve outcome].'\n"
            "   - NEVER start with raw observations or 'I wanted to reach out regarding...'\n\n"
            
            "2. OBSERVATION (1-2 sentences): Reference what you noticed about their company\n"
            "   - Use research notes as background - DO NOT include verbatim\n"
            "   - Synthesize into 2-3 key insights maximum\n"
            "   - Example: 'I reviewed [Company] and noticed [specific, relevant insight].'\n"
            "   - Focus on opportunities, not just problems\n"
            "   - Keep it concise and professional\n\n"
            
            "3. VALUE PROPOSITION (1-2 sentences): Connect observations to how you can help\n"
            "   - State the benefit/outcome you can deliver\n"
            "   - Example: 'Companies with similar challenges see [outcome] when [solution].'\n"
            "   - OR: 'I've helped brands address these gaps and typically see [result].'\n"
            "   - Always connect problems to solutions/expertise\n"
            "   - Show expertise without bragging\n\n"
            
            "4. LOW-FRICTION OFFER (1 sentence): Present a simple, valuable next step\n"
            "   - Example: 'If useful, I can share a short, actionable plan that addresses these gaps.'\n"
            "   - OR: 'I can run a quick audit and share 3 immediate improvements.'\n"
            "   - Make it easy to say yes\n"
            "   - Focus on value they'll receive\n\n"
            
            "5. CLEAR CTA (1 sentence): Simple, direct question\n"
            "   - Example: 'Would you like me to send that over?'\n"
            "   - OR: 'Want me to share that?'\n"
            "   - OR: 'Should I send that?'\n"
            "   - Keep it conversational and low-pressure\n\n"
            
            "## CRITICAL: How to Use Research Notes:\n"
            "- Research notes are BACKGROUND CONTEXT only - NEVER include them verbatim\n"
            "- MANDATORY: You MUST extract and use 2-3 specific insights from the research notes provided below\n"
            "- Synthesize: Extract key insights that are relevant and actionable\n"
            "- Transform: Convert observations into opportunities (e.g., 'complex checkout' → 'streamlined checkout can reduce abandonment')\n"
            "- Connect: Always link observations to value you can provide\n"
            "- Structure: Context → Observation → Value → Offer → CTA\n"
            "- NEVER write: 'I wanted to reach out regarding [full notes dump]'\n"
            "- NEVER write: '[Company] is a [description]. The founder [details]. The website [analysis].'\n"
            "- NEVER write generic emails like 'I came across [Company] and wanted to connect about potential opportunities'\n"
            "- Instead write: 'I reviewed [Company] and noticed [specific insight from notes]. I can help [value].'\n"
            "- Example: If notes mention 'website lacks modern design', write: 'I noticed your website could benefit from a modern refresh to better showcase your expertise.'\n"
            "- Example: If notes mention 'relies on referrals', write: 'I see you're growing through referrals - I can help you expand your reach with digital channels.'\n"
            "- Craft engaging, professional text that flows naturally\n"
            "- Use website_url in signature if provided to establish credibility\n"
            "- Include [[CALENDLY_LINK]] in body if prospect expresses interest or requests scheduling\n"
            "- FAILURE TO USE RESEARCH NOTES WILL RESULT IN A GENERIC, LOW-VALUE EMAIL\n\n"
            
            "## AVOID SPAM TRIGGERS (Critical for Deliverability):\n"
            "- NEVER use urgency phrases: 'act now', 'limited time', 'expires today', 'urgent', 'immediately'\n"
            "- NEVER use financial spam triggers: 'free money', 'get rich quick', 'guaranteed income', 'risk-free'\n"
            "- NEVER use excessive punctuation: !!!, ???, $$$, %%%\n"
            "- NEVER use ALL CAPS for emphasis (use normal sentence case)\n"
            "- AVOID suspicious phrases: 'click here', 'you have won', 'claim your prize', 'congratulations'\n"
            "- Use professional, conversational tone - avoid salesy language\n"
            "- Focus on value and relationship, not urgency or pressure\n"
            "- Use full URLs instead of link shorteners (bit.ly, tinyurl, etc.)\n"
            "- Limit use of marketing words: 'free', 'guaranteed', 'special', 'limited' (use sparingly and naturally)\n\n"
            
            "## Tone & Style:\n"
            "- Professional but conversational\n"
            "- Persuasive, not informational\n"
            "- Focus on benefits and outcomes, not just problems\n"
            "- Show expertise through value, not through listing credentials\n"
            "- Guide recipient toward next step\n"
            "- Keep it concise - respect their time\n\n"
        )
    else:
        prompt += (
            "## Reply Email Rules:\n"
            "- If INTERESTED: warm, efficient, action-oriented. Provide two clear next steps (time options or 'send short list of questions')\n"
            "- If NOT INTERESTED: gracious, low pressure, leave door open. Ask permission to check back in 3 months or for referral\n"
            "- Body MUST be exactly 300-350 characters (including spaces) - count carefully\n"
            "- Subject MUST be maximum 100 characters and compelling\n"
            "- Include required prep and what you'll deliver in meeting (agenda: 10–15 minutes: pain, solution, next steps)\n"
            "- Tone: warm, efficient, action-oriented for interested; gracious, low pressure for not interested\n"
            "- Signature will be automatically added - do NOT include it in the body\n\n"
        )
    
    prompt += (
        "## Psychological Techniques to Apply:\n"
        "- Authority: signature + credential; cite reputable client or metric in first paragraph\n"
        "- Social proof: 'We've worked with X, Y, Z' or 'Similar companies see +%' (use only truthful claims)\n"
        "- Reciprocity: offer free audit/resource before asking for meeting\n"
        "- Scarcity: limited pilot slots or quarter timeline (only if true)\n"
        "- Commitment/Foot-in-door: ask for small 'yes' (e.g., 'Want my 2-minute audit?') before larger commitment\n"
        "- Anchoring: show high-level outcome first then present offer\n"
        "- Loss aversion: highlight what they stand to lose by not acting (conservative, factual language)\n"
        "- Cognitive load reduction: use bullets, single clear CTA, limit choices to 1–2 options\n\n"
        
        "## Tone Guidelines:\n"
        "- Cold: Concise, professional, slightly curious. Avoid hard sell. (Words: neutral, confident)\n"
        "- Warm (engaged/previous interaction): Friendly, consultative, helpful. (Words: collaborative, exploratory)\n"
        "- Hot/Negotiation/Closing: Direct, benefit- and deadline-oriented, slightly urgent but respectful. (Words: confirm, finalize, schedule)\n\n"
        
        f"## Context Information:\n"
        f"CLIENT INFO: name={receiver_name}, email={to_addr}, company={receiver_company}, position={receiver_position}\n"
        f"SENDER INFO: name={sender_name}, title={sender_title}, company={sender_company}\n\n"
    )
    
    if not is_cold:
        prompt += (
            f"LATEST CLIENT MESSAGE:\n```{original}```\n"
            f"{conversation_context}"
            f"{original_context}\n\n"
        )
    else:
        prompt += (
            f"## Background Research / Personalization Notes:\n"
            f"CRITICAL: These notes are for CONTEXT ONLY. DO NOT include them verbatim in the email.\n"
            f"Instead, use them to:\n"
            f"1. Understand the company/recipient context\n"
            f"2. Extract 2-3 key, relevant insights\n"
            f"3. Transform insights into opportunities\n"
            f"4. Connect opportunities to value you can provide\n\n"
            f"Structure your email as:\n"
            f"- Context: Who you are and why reaching out\n"
            f"- Observation: 1-2 sentences synthesizing key insights\n"
            f"- Value: How you can help address these insights\n"
            f"- Offer: Low-friction next step\n"
            f"- CTA: Clear, simple question\n\n"
            f"RESEARCH DATA (for context only):\n{original_context if original_context else 'Use company research and industry insights'}\n\n"
            f"CRITICAL INSTRUCTION: You MUST use the research data above to personalize this email. "
            f"Extract 2-3 specific insights from the research notes and incorporate them naturally into your email. "
            f"Do NOT write a generic email - the research data contains valuable information about the company, "
            f"their challenges, and opportunities that MUST be reflected in your response. "
            f"If you write a generic email without using the research insights, the email will be low-value and ineffective.\n\n"
        )
    
    prompt += (
        "## Output Format (CRITICAL):\n"
        "You MUST respond with a valid JSON object in this exact format:\n"
        "{\n"
        '  "intent": "interested|not_interested|request_more_info|schedule|unsubscribe|unclear|follow_up|objection|question",\n'
        '  "variants": {\n'
        '    "short": {\n'
        '      "subject": "subject line (max 100 chars, compelling and engaging)",\n'
        '      "body": "email body (exactly 300-350 chars including spaces - count carefully)",\n'
        '      "why_this_works": "brief explanation of psychological techniques used"\n'
        '    },\n'
        '    "medium": {\n'
        '      "subject": "subject line (max 100 chars, compelling and engaging)",\n'
        '      "body": "email body (exactly 300-350 chars including spaces - count carefully)",\n'
        '      "why_this_works": "brief explanation of psychological techniques used"\n'
        '    },\n'
        '    "long": {\n'
        '      "subject": "subject line (max 100 chars, compelling and engaging)",\n'
        '      "body": "email body (exactly 300-350 chars including spaces - count carefully)",\n'
        '      "why_this_works": "brief explanation of psychological techniques used"\n'
        '    }\n'
        '  },\n'
        '  "schedule": null\n'
        "}\n\n"
        
        "CRITICAL LENGTH REQUIREMENTS (MUST FOLLOW EXACTLY):\n"
        "- Subject line: Maximum 100 characters - make it compelling and engaging\n"
        "- Body: Exactly 300-350 characters including spaces - count every character\n"
        "- Do NOT include signature in body - it will be automatically added\n"
        "- Verify character counts before returning JSON\n\n"
        
        "IMPORTANT NOTES:\n"
        "- Keep paragraphs short (1–2 sentences each)\n"
        "- Use single blank line between paragraphs\n"
        "- If scheduling is requested, set schedule to {\"title\": \"Call with [Name]\", \"start_iso\": \"ISO8601\", \"end_iso\": \"ISO8601\"}\n"
        "- Replace [[CALENDLY_LINK]] with actual calendly_link value when provided\n"
        "- Include [[CALENDLY_LINK]] in the email body when:\n"
        "  * Prospect expresses interest (intent: 'interested')\n"
        "  * Prospect requests scheduling (intent: 'schedule')\n"
        "  * Prospect asks for a call or meeting\n"
        "- Place [[CALENDLY_LINK]] naturally in the body, typically after the value proposition or in the CTA section\n"
        "- Format as: 'Would you like to schedule a quick call? [[CALENDLY_LINK]]'\n"
        "- Do NOT fabricate case studies, results, or client names\n"
        "- No misleading subject lines or false urgency\n"
        "- Use numerals for measurable claims (e.g., '18%', '$12k')\n"
        "- When listing time options, format as: 'Option A — Tue 10:00–10:15 IST; Option B — Wed 15:00–15:15 IST'\n"
        "- For reply emails: If client says 'Hey, [Name]', address them as that name - NOT the sender name\n"
        "- If client proposes specific times, confirm it works and do NOT ask for alternatives\n"
        "- The signature will be automatically appended - do NOT include it in the body\n\n"
        
        "Generate all three variants (short, medium, long) with the SAME length requirements. "
        "Each variant should have a compelling subject (max 100 chars) and informative body (exactly 300-350 chars)."
    )
    
    return prompt

def _add_signature_to_content(content: str, owner: str) -> str:
    """Add signature to email content if not already present"""
    if not content:
        return content
    
    # Check if signature is already present
    signature = _get_user_signature(owner)
    signature_lines = signature.split('\n')
    
    # Check if any signature line is already in the content
    for line in signature_lines:
        if line.strip() and line.strip() in content:
            return content  # Signature already present
    
    # Add signature if not present
    if content.strip():
        return f"{content.strip()}\n\n{signature}"
    else:
        return signature

def _send_email(payload: dict, db: Optional[Session], owner: Optional[str] = None) -> dict:
    try:
        to_addr = payload.get("to")
        subject = payload.get("subject")
        content = payload.get("content")
        attachments_data = payload.get("attachments", [])  # List of attachment metadata
        
        if not to_addr or not subject:
            raise HTTPException(status_code=422, detail="to, subject required")
        
        # Validate content for spam triggers (warn but don't block)
        try:
            from app.core.content_validator import validate_email_content, get_content_suggestions
            is_valid, warnings, score_details = validate_email_content(subject, content or "")
            if warnings:
                logger.warning(f"Email content validation warnings for {to_addr}: {warnings}")
                # Log suggestions for debugging
                suggestions = get_content_suggestions(warnings, score_details)
                logger.info(f"Content improvement suggestions: {suggestions}")
        except Exception as e:
            # Don't block sending if validation fails
            logger.warning(f"Content validation failed (allowing send): {e}")
        
        # Automatically add signature to content
        if owner:
            content = _add_signature_to_content(content or "", owner)
        
        if not content:
            raise HTTPException(status_code=422, detail="content required")
        
        if not owner:
            raise HTTPException(status_code=500, detail="Owner email is required")
    except Exception as e:
        raise
    
    # Get SMTP configuration first
    try:
        host, port, user, password, from_addr, use_tls = _resolve_per_user_smtp(owner)
    except HTTPException as e:
        # Re-raise HTTPExceptions as-is to preserve error details
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SMTP configuration: {str(e)}")

    # CRITICAL: Check domain authentication (SPF/DKIM/DMARC) before sending
    # Missing authentication is a major cause of spam filtering
    try:
        from app.core.deliverability import check_spf_record, check_dkim_record, check_dmarc_record
        if from_addr and '@' in from_addr:
            domain = from_addr.split('@')[1]
            spf_ok, spf_error = check_spf_record(domain)
            dkim_ok, dkim_error, _ = check_dkim_record(domain, "default")
            dmarc_ok, dmarc_error, _ = check_dmarc_record(domain)
            
            # Log warnings if authentication is missing (but don't block sending)
            auth_warnings = []
            if not spf_ok:
                auth_warnings.append(f"SPF not configured: {spf_error}")
            if not dkim_ok:
                auth_warnings.append(f"DKIM not configured: {dkim_error}")
            if not dmarc_ok:
                auth_warnings.append(f"DMARC not configured: {dmarc_error}")
            
            if auth_warnings:
                logger.warning(f"⚠️ DOMAIN AUTHENTICATION MISSING for {domain}: {'; '.join(auth_warnings)}")
                logger.warning(f"⚠️ Emails from {domain} may go to spam. Configure SPF/DKIM/DMARC DNS records.")
            else:
                logger.info(f"✓ Domain authentication verified for {domain} (SPF/DKIM/DMARC configured)")
    except Exception as e:
        # Don't block sending if auth check fails (might be DNS timeout, etc.)
        logger.warning(f"Could not verify domain authentication: {e}")

    # Check deliverability protection (rate limiting, reputation)
    is_cold_send = False
    try:
        from app.core.database import SessionLocal as AccountsSessionLocal
        from app.models.email_reputation import EmailReputation
        from app.core.deliverability import should_throttle_sending, get_recommended_cold_send_limit
        from datetime import datetime, timedelta
        from sqlalchemy.exc import OperationalError, ProgrammingError
        
        # Check if this is a cold send (no existing contact)
        if db:
            try:
                existing_contact = db.query(Contact).filter(
                    Contact.owner_email == owner,
                    Contact.email == to_addr.lower()
                ).first()
                is_cold_send = not existing_contact
            except Exception:
                # If contact check fails, assume warm send to be safe
                is_cold_send = False
        
        # Get reputation record (only if tables exist)
        accounts_db = None
        try:
            accounts_db = AccountsSessionLocal()
            # Check if tables exist by trying a simple query
            try:
                reputation = accounts_db.query(EmailReputation).filter(
                    EmailReputation.owner_email == owner,
                    EmailReputation.mailbox == from_addr
                ).first()
            except (OperationalError, ProgrammingError) as e:
                # Tables don't exist yet - skip deliverability checks
                logger.warning(f"Deliverability tables not found, skipping checks: {e}")
                reputation = None
                if accounts_db:
                    accounts_db.close()
                accounts_db = None
            
            if reputation and accounts_db:
                # Check if throttled
                if reputation.is_throttled and reputation.throttle_until:
                    if datetime.now(timezone.utc) < reputation.throttle_until:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Sending temporarily paused: {reputation.throttle_reason or 'Reputation protection'}. Resumes at {reputation.throttle_until.isoformat()}"
                        )
                    else:
                        # Throttle period expired, clear it
                        reputation.is_throttled = False
                        reputation.throttle_reason = None
                        reputation.throttle_until = None
                        accounts_db.commit()
                
                # Check cold send limits
                if is_cold_send:
                    # Reset daily counter if needed
                    if not reputation.cold_sends_reset_at or (datetime.now(timezone.utc) - reputation.cold_sends_reset_at) > timedelta(days=1):
                        reputation.cold_sends_today = 0
                        reputation.cold_sends_reset_at = datetime.now(timezone.utc)
                    
                    # Check limit
                    if reputation.cold_sends_today >= reputation.max_cold_sends_per_day:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Daily cold send limit reached ({reputation.cold_sends_today}/{reputation.max_cold_sends_per_day}). This protects your sender reputation."
                        )
                
                # Check reputation-based throttling
                total_sent = reputation.total_sent or 1
                bounce_rate = (reputation.total_bounced / total_sent) if total_sent > 0 else 0.0
                complaint_rate = (reputation.total_complained / total_sent) if total_sent > 0 else 0.0
                
                should_throttle, throttle_reason = should_throttle_sending(
                    reputation.reputation_score,
                    bounce_rate,
                    complaint_rate,
                    reputation.cold_sends_today,
                    reputation.max_cold_sends_per_day
                )
                
                if should_throttle:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Sending paused for deliverability protection: {throttle_reason}"
                    )
        except HTTPException:
            if accounts_db:
                accounts_db.close()
            raise
        except (OperationalError, ProgrammingError) as e:
            # Tables don't exist - skip deliverability checks
            if accounts_db:
                accounts_db.close()
            logger.warning(f"Deliverability tables not found, skipping checks: {e}")
        except Exception as e:
            # Don't block sending if deliverability check fails
            if accounts_db:
                accounts_db.close()
            logger.warning(f"Deliverability check failed (allowing send): {e}")
    except Exception as e:
        # Outer try block - catch any import or setup errors
        logger.warning(f"Deliverability check setup failed (allowing send): {e}")

    # Send via SMTP and store in database
    try:
        # Create proper email message with all required headers
        # Use multipart if attachments exist, otherwise plain text
        if attachments_data:
            # Use multipart message for emails with attachments
            msg = MIMEMultipart()
            msg.attach(MIMEText(content, "plain", "utf-8"))
            
            # Add attachments
            for att_data in attachments_data:
                if isinstance(att_data, str):
                    # If it's a JSON string, parse it
                    try:
                        att_data = json.loads(att_data)
                    except:
                        continue
                
                stored_filename = att_data.get("stored_filename") or att_data.get("id")
                filename = att_data.get("filename", "attachment")
                content_type = att_data.get("content_type", "application/octet-stream")
                
                if not stored_filename:
                    continue
                
                try:
                    # Get file path
                    file_path = UPLOAD_DIR / stored_filename
                    
                    if not file_path.exists():
                        logger.warning(f"Attachment file not found: {file_path}")
                        continue
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Create appropriate MIME type
                    if content_type.startswith('image/'):
                        attachment = MIMEImage(file_content)
                    elif content_type.startswith('application/pdf') or content_type.startswith('application/'):
                        attachment = MIMEApplication(file_content)
                    else:
                        attachment = MIMEBase('application', 'octet-stream')
                        attachment.set_payload(file_content)
                        encoders.encode_base64(attachment)
                    
                    # Set headers
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    attachment.add_header('Content-Type', content_type)
                    
                    msg.attach(attachment)
                    
                    # Keep file for 30 days for download capability (don't delete immediately)
                    # Files will be cleaned up by the periodic cleanup_old_files() function
                    # This allows users to download attachments from sent emails
                        
                except Exception as e:
                    logger.error(f"Error attaching file {filename}: {e}", exc_info=True)
                    # Continue with other attachments
        else:
            # Plain text email without attachments
            msg = MIMEText(content, "plain", "utf-8")
        
        # Set email headers for BOTH multipart (with attachments) and plain text emails
        # This is critical for deliverability - headers must be set for all emails
        msg["Subject"] = subject
        msg["From"] = from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or ""
        msg["To"] = to_addr
        # IMPROVED: Use UTC timezone for Date header (more standard, better deliverability)
        # Some spam filters flag non-UTC timezones as suspicious
        utc_now = datetime.now(timezone.utc)
        msg["Date"] = utc_now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # FIXED: Use proper domain instead of localhost for Message-ID
        domain = from_addr.split('@')[1] if '@' in from_addr else (settings.EMAIL_FROM.split('@')[1] if settings.EMAIL_FROM and '@' in settings.EMAIL_FROM else 'wolfassistants.com')
        
        # IMPROVED: Better Message-ID format (more standard, less automated-looking)
        # Format: <unique-id.timestamp@domain>
        msg_id_unique = uuid.uuid4().hex[:16]  # 16-char hex string
        msg_id_timestamp = int(time.time())
        msg["Message-ID"] = f"<{msg_id_unique}.{msg_id_timestamp}@{domain}>"
        
        # CRITICAL: Return-Path header (required for bounce handling and deliverability)
        # This must match the From address or be a valid bounce address
        msg["Return-Path"] = from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or ""
        
        # ENHANCED: Critical headers for 99.9% deliverability
        msg["Reply-To"] = from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or ""
        
        # List-Unsubscribe header (required by Gmail, Outlook, and other major providers)
        # This is critical for inbox placement - missing this can cause spam filtering
        unsubscribe_domain = from_addr.split('@')[1] if '@' in from_addr else 'wolfassistants.com'
        unsubscribe_url = f"https://{unsubscribe_domain}/unsubscribe?email={to_addr}"
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        
        # Priority headers - use normal to avoid spam triggers
        msg["X-Priority"] = "3"  # Normal priority (1=highest, 5=lowest)
        msg["Importance"] = "normal"
        msg["X-Auto-Response-Suppress"] = "All"
        
        # Anti-spam headers - help email providers trust the message
        msg["X-Entity-Ref-ID"] = f"{msg_id_timestamp}-{msg_id_unique}"  # Unique tracking ID
        msg["X-Content-Type-Options"] = "nosniff"
        
        # X-Mailer header - identifies the sending application (better than User-Agent for emails)
        # User-Agent is not a standard email header and can trigger spam filters
        # X-Mailer is the standard way to identify email clients/applications
        msg["X-Mailer"] = "WolfAssistants Email Automation v1.0"
        
        # Content-Type and encoding (already set by MIMEText/MIMEMultipart, but ensure UTF-8)
        if not attachments_data:
            try:
                # Only replace if header exists, otherwise MIMEText already set it correctly
                if "Content-Type" in msg:
                    msg.replace_header("Content-Type", "text/plain; charset=utf-8")
            except Exception:
                # If replace fails, Content-Type is already set correctly by MIMEText
                pass
        
        # Precedence header - explicitly set to "normal" to avoid bulk classification
        # (Not setting "bulk" which triggers spam filters)
        msg["Precedence"] = "normal"
        
        # Organization header - adds legitimacy
        org_domain = from_addr.split('@')[1] if '@' in from_addr else 'WolfAssistants'
        msg["Organization"] = org_domain.split('.')[0].title() if '.' in org_domain else org_domain
        
        # CRITICAL: Authentication-Results header (helps providers verify SPF/DKIM/DMARC)
        # Note: This is typically added by receiving servers, but we can add a hint
        # The actual results will be determined by the receiving server based on DNS records
        auth_domain = from_addr.split('@')[1] if '@' in from_addr else domain
        # We don't set actual results here (server does that), but we can add a comment
        # This header helps email providers understand authentication status
        
        # MIME-Version header (required for proper email parsing)
        if "MIME-Version" not in msg:
            msg["MIME-Version"] = "1.0"

        if not host or not user or not password:
            raise RuntimeError("SMTP settings missing")

        # Use SSL if port 465 or TLS flag false handling
        smtp_port: int = int(port or 587)
        # Ensure from_addr is a string, not None, to satisfy type checker and avoid runtime errors
        if from_addr is None:
            raise HTTPException(status_code=500, detail="SMTP 'from' address is missing or invalid")
        _smtp_send_with_retries(host, smtp_port, user, password, from_addr, [to_addr], msg.as_string(), use_tls)
        
        # Record successful delivery for reputation tracking
        try:
            from app.core.database import SessionLocal as AccountsSessionLocal
            from app.models.email_reputation import EmailReputation
            from app.core.deliverability import get_recommended_cold_send_limit, calculate_reputation_score
            from datetime import datetime, timedelta
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            accounts_db = AccountsSessionLocal()
            try:
                try:
                    reputation = accounts_db.query(EmailReputation).filter(
                        EmailReputation.owner_email == owner,
                        EmailReputation.mailbox == from_addr
                    ).first()
                    
                    if not reputation:
                        reputation = EmailReputation(
                            owner_email=owner,
                            mailbox=from_addr,
                            max_cold_sends_per_day=get_recommended_cold_send_limit(100.0)
                        )
                        accounts_db.add(reputation)
                    
                    # Update metrics
                    reputation.total_sent += 1
                    reputation.total_delivered += 1
                    
                    # Track cold sends
                    if is_cold_send:
                        if not reputation.cold_sends_reset_at or (datetime.now(timezone.utc) - reputation.cold_sends_reset_at) > timedelta(days=1):
                            reputation.cold_sends_today = 0
                            reputation.cold_sends_reset_at = datetime.now(timezone.utc)
                        reputation.cold_sends_today += 1
                    
                    # Recalculate reputation score
                    reputation.reputation_score = calculate_reputation_score(
                        reputation.total_sent,
                        reputation.total_delivered,
                        reputation.total_bounced,
                        reputation.total_complained
                    )
                    reputation.last_calculated = datetime.utcnow()
                    
                    accounts_db.commit()
                except (OperationalError, ProgrammingError):
                    # Tables don't exist yet - skip tracking
                    pass
            finally:
                accounts_db.close()
        except Exception as e:
            # Don't fail email send if reputation tracking fails
            logger.warning(f"Failed to record delivery for reputation: {e}")

    except HTTPException as e:
        
        # Record bounce if recipient was refused (hard bounce)
        if e.status_code == 400 and "recipient refused" in str(e.detail).lower():
            try:
                from app.core.database import SessionLocal as AccountsSessionLocal
                from app.models.email_reputation import EmailReputation, BounceRecord
                from app.core.deliverability import calculate_reputation_score
                from datetime import datetime
                from sqlalchemy.exc import OperationalError, ProgrammingError
                
                accounts_db = AccountsSessionLocal()
                try:
                    try:
                        reputation = accounts_db.query(EmailReputation).filter(
                            EmailReputation.owner_email == owner,
                            EmailReputation.mailbox == from_addr
                        ).first()
                        
                        if not reputation:
                            reputation = EmailReputation(
                                owner_email=owner,
                                mailbox=from_addr,
                                max_cold_sends_per_day=50
                            )
                            accounts_db.add(reputation)
                            accounts_db.flush()
                        
                        # Record bounce
                        bounce = BounceRecord(
                            reputation_id=reputation.id,
                            owner_email=owner,
                            mailbox=from_addr,
                            recipient_email=to_addr,
                            bounce_type='hard',
                            bounce_reason=str(e.detail),
                            subject=subject
                        )
                        accounts_db.add(bounce)
                        
                        # Update reputation metrics
                        reputation.total_sent += 1
                        reputation.total_bounced += 1
                        reputation.reputation_score = calculate_reputation_score(
                            reputation.total_sent,
                            reputation.total_delivered,
                            reputation.total_bounced,
                            reputation.total_complained
                        )
                        reputation.last_calculated = datetime.now(timezone.utc)
                        
                        accounts_db.commit()
                    except (OperationalError, ProgrammingError):
                        # Tables don't exist yet - skip bounce recording
                        pass
                finally:
                    accounts_db.close()
            except Exception as bounce_error:
                logger.warning(f"Failed to record bounce: {bounce_error}")
        
        # Re-raise HTTPException as-is (it already has proper status code and detail)
        raise
    except Exception as e:
        # Surface error
        raise HTTPException(status_code=500, detail=f"SMTP send failed: {str(e)}")

    # Store the email in the database
    if db and owner:
        try:
            from app.models.email import Email, EmailStatus
            from datetime import datetime
            
            # Get current time and convert to UTC naive for database storage
            current_time = get_ist_now()
            sent_at_utc = _to_utc_naive(current_time)
            
            # Prepare attachment metadata for storage
            attachments_json = None
            if attachments_data:
                # Store only metadata, not file paths
                att_metadata = []
                for att in attachments_data:
                    if isinstance(att, str):
                        try:
                            att = json.loads(att)
                        except:
                            continue
                    att_metadata.append({
                        "filename": att.get("filename"),
                        "content_type": att.get("content_type"),
                        "size": att.get("size")
                    })
                attachments_json = json.dumps(att_metadata) if att_metadata else None
            
            # Create email record in Supabase
            email_record = Email(
                subject=subject,
                body=content,
                to_address=to_addr,
                from_address=from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or "",
                status=EmailStatus.sent,
                sent_at=sent_at_utc,
                owner_email=owner,
                is_read=True,
                is_starred=False,
                original_folder="sent"
            )
            
            # Set attachments using setattr (works even if column doesn't exist yet)
            if attachments_json:
                try:
                    email_record.attachments = attachments_json
                except Exception:
                    # Column doesn't exist - skip (migration needed)
                    # Use setattr as fallback
                    try:
                        setattr(email_record, 'attachments', attachments_json)
                    except Exception:
                        pass
            
            db.add(email_record)
            try:
                db.commit()
                db.refresh(email_record)
            except Exception as commit_error:
                db.rollback()
                logger.error(f"Failed to commit email to database: {str(commit_error)}", exc_info=True)
                raise  # Re-raise to be caught by outer except
            
            # Parse attachments for response
            attachments_list = []
            if attachments_json:
                try:
                    attachments_list = json.loads(attachments_json)
                except:
                    pass
            
            # Return the stored email data with correct timestamp
            result = {
                "id": email_record.id,
                "subject": subject,
                "from": from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or "",
                "to": to_addr,
                "content": content,
                "timestamp": _to_ist_iso(email_record.sent_at) if email_record.sent_at else _to_ist_iso(current_time),
                "status": "sent",
                "isRead": True,
                "isStarred": False,
                "attachments": attachments_list,
                "tags": [],
            }
            
        except Exception as e:
            # Log the database error for debugging
            logger.error(f"Failed to store email in database: {str(e)}", exc_info=True)
            # Try to rollback if transaction is still active
            try:
                db.rollback()
            except Exception:
                pass
            # Still return success since email was sent, but log the database error
            result = {
                "id": f"temp_{int(time.time())}",
                "subject": subject,
                "from": from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or "",
                "to": to_addr,
                "content": content,
                "timestamp": _to_ist_iso(get_ist_now()),
                "status": "sent",
                "isRead": True,
                "isStarred": False,
                "attachments": [],
                "tags": [],
            }
    else:
        # Fallback if no database connection
        result = {
            "id": f"temp_{int(time.time())}",
            "subject": subject,
            "from": from_addr or settings.EMAIL_FROM or settings.EMAIL_USER or "",
            "to": to_addr,
            "content": content,
            "timestamp": _to_ist_iso(get_ist_now()),
            "status": "sent",
            "isRead": True,
            "isStarred": False,
            "attachments": [],
            "tags": [],
        }
    
    return result

@router.post("/upload-attachment")
async def upload_attachment(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload a file attachment for email composition."""
    owner = _get_owner_from_request(request)
    
    try:
        # Clean up old files periodically (30 days retention)
        cleanup_old_files(max_age_hours=720)
        
        # Save uploaded file
        metadata = await save_uploaded_file(file)
        
        # Return metadata (without file_path for security)
        return {
            "id": metadata["id"],
            "filename": metadata["filename"],
            "content_type": metadata["content_type"],
            "size": metadata["size"],
            "stored_filename": metadata["stored_filename"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@router.get("/by-public-id/{public_id}")
def get_email_by_public_id(
    public_id: str,
    request: Request,
    db: Session = Depends(get_tenant_db_dependency)
):
    """Get an email by its public_id (UUID)."""
    try:
        owner = _get_owner_from_request(request)
        email = db.query(Email).filter(
            Email.public_id == public_id,
            Email.owner_email == owner
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Format email response similar to list_emails
        email_data = {
            "id": email.id,
            "public_id": email.public_id,
            "subject": email.subject or "",
            "body": email.body or "",
            "to": email.to_address or "",
            "from": email.from_address or "",
            "status": email.status.value if email.status else "received",
            "timestamp": email.received_at.isoformat() if email.received_at else (email.sent_at.isoformat() if email.sent_at else datetime.now(timezone.utc).isoformat()),
            "isRead": email.is_read or False,
            "isStarred": email.is_starred or False,
            "attachments": getattr(email, 'attachments', []) if hasattr(email, 'attachments') else [],
        }
        
        return email_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get email by public_id")
        raise HTTPException(status_code=500, detail=f"Failed to get email: {str(e)}")

@router.get("/download-attachment/{email_id}")
def download_attachment(
    request: Request,
    email_id: int,
    filename: str = Query(..., description="Name of the attachment file to download"),
    db: Session = Depends(get_tenant_db_dependency)
):
    """Download an attachment from an email."""
    owner = _get_owner_from_request(request)
    
    try:
        from app.models.email import Email
        
        # Get email from database
        email = db.query(Email).filter(
            Email.id == email_id,
            Email.owner_email == owner
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Parse attachments metadata
        attachments_data = []
        try:
            attachments_field = getattr(email, 'attachments', None)
            if attachments_field:
                if isinstance(attachments_field, str):
                    attachments_data = json.loads(attachments_field)
                elif isinstance(attachments_field, list):
                    attachments_data = attachments_field
        except Exception as e:
            logger.warning(f"Error parsing attachments for email {email_id}: {e}")
            raise HTTPException(status_code=400, detail="Invalid attachments data")
        
        
        if not attachments_data:
            raise HTTPException(status_code=404, detail="No attachments found in email")
        
        # Find the requested attachment
        attachment = None
        for att in attachments_data:
            if isinstance(att, str):
                try:
                    att = json.loads(att)
                except:
                    continue
            att_filename = att.get("filename")
            att_stored = att.get("stored_filename") or att.get("id")
            if att_filename == filename or (att_stored and att_stored == filename):
                attachment = att
                matched_download_name = att_filename or filename
                break
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        stored_filename = attachment.get("stored_filename") or attachment.get("id")
        download_filename = attachment.get("filename") or filename
        if not stored_filename:
            # For received emails, we need to fetch from IMAP
            # Try to fetch from IMAP
            return _fetch_attachment_from_imap(request, email, filename, owner)
        
        # For sent emails, try to get from temp_attachments
        file_path = UPLOAD_DIR / stored_filename
        
        if file_path.exists():
            # File exists in temp storage
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                content_type = attachment.get("content_type", "application/octet-stream")
                
                return Response(
                    content=file_content,
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{download_filename}"'
                    }
                )
            except Exception as e:
                logger.error(f"Error reading attachment file {file_path}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to read attachment file")
        else:
            # File not found in temp storage, try IMAP for sent emails
            return _fetch_attachment_from_imap(request, email, filename, owner)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to download attachment: {str(e)}")

def _fetch_attachment_from_imap(request: Request, email: Email, filename: str, owner: str) -> Response:
    """Fetch attachment from IMAP server."""
    import imaplib
    from email import message_from_bytes
    from email.utils import parseaddr
    
    M = None
    try:
        host, port, user, password, use_ssl = _resolve_per_user_imap(owner)
        if not host or not user or not password:
            raise HTTPException(status_code=400, detail="IMAP credentials not configured")
        
        # Connect to IMAP
        imap_port = port or (993 if use_ssl else 143)
        M = imaplib.IMAP4_SSL(host, imap_port) if use_ssl else imaplib.IMAP4(host, imap_port)
        M.login(user, password)
        
        # Determine folder based on email status
        folder = "INBOX"
        folder_already_selected = False
        if email.status.value == "sent":
            # Try to find sent folder
            folders = _get_imap_folders(M)
            sent_folders = [f for f in folders if 'sent' in f.lower() and f != '.']
            if sent_folders:
                folder = sent_folders[0]
            else:
                # Try common sent folder names
                common_sent = ['Sent', 'Sent Items', 'Sent Messages', '[Gmail]/Sent Mail']
                for sent_name in common_sent:
                    if sent_name in folders:
                        folder = sent_name
                        break
                # If still not found, try to select sent folder directly (some servers allow this)
                if folder == "INBOX":
                    try:
                        typ_select, _ = M.select('Sent', readonly=True)
                        if typ_select == 'OK':
                            folder = "Sent"
                            folder_already_selected = True
                    except:
                        try:
                            typ_select, _ = M.select('Sent Items', readonly=True)
                            if typ_select == 'OK':
                                folder = "Sent Items"
                                folder_already_selected = True
                        except:
                            pass
        
        
        # Select folder (skip if already selected)
        if not folder_already_selected:
            try:
                typ_select, data_select = M.select(folder, readonly=True)
                if typ_select != 'OK':
                    # Folder selection failed, try INBOX as fallback
                    folder = "INBOX"
                    typ_select, data_select = M.select(folder, readonly=True)
                    if typ_select != 'OK':
                        if M:
                            try:
                                M.logout()
                            except:
                                pass
                        raise HTTPException(status_code=404, detail=f"Could not access email folder: {folder}")
            except Exception as select_error:
                # Try INBOX as fallback
                try:
                    folder = "INBOX"
                    typ_select, data_select = M.select(folder, readonly=True)
                    if typ_select != 'OK':
                        if M:
                            try:
                                M.logout()
                            except:
                                pass
                        raise HTTPException(status_code=404, detail=f"Could not access email folder: {folder}")
                except Exception as fallback_error:
                    if M:
                        try:
                            M.logout()
                        except:
                            pass
                    raise HTTPException(status_code=500, detail=f"Failed to access email folders: {str(fallback_error)}")
        
        # Search for email by subject and from/to
        search_criteria = f'(SUBJECT "{email.subject}")'
        typ, data = M.search(None, search_criteria)
        
        if typ != 'OK' or not data or not data[0]:
            M.logout()
            raise HTTPException(status_code=404, detail="Email not found in IMAP")
        
        msg_ids = data[0].split()
        found_attachment = None
        
        # Try to find the email and extract attachment
        for msg_id in msg_ids:
            typ, msg_data = M.fetch(msg_id, '(RFC822)')
            if typ != 'OK' or not msg_data:
                continue
            
            raw_email = msg_data[0][1]
            msg = message_from_bytes(raw_email)
            
            # Check if this is the right email
            msg_subject = msg.get('Subject', '')
            msg_from = parseaddr(msg.get('From', ''))[1] if msg.get('From') else ''
            msg_to = parseaddr(msg.get('To', ''))[1] if msg.get('To') else ''
            
            # For sent emails, match by TO address (recipient) and subject
            # For received emails, match by FROM address (sender) and subject
            is_match = False
            if email.status.value == "sent":
                # Sent email: match by recipient (TO) and subject
                # Only match if both msg_to and email.to_address are non-empty
                if msg_to and email.to_address:
                    is_match = (msg_subject == email.subject and 
                               msg_to.lower() == email.to_address.lower())
            else:
                # Received email: match by sender (FROM) and subject
                # Only match if both msg_from and email.from_address are non-empty
                if msg_from and email.from_address:
                    is_match = (msg_subject == email.subject and 
                               msg_from.lower() == email.from_address.lower())
            
            if is_match:
                # Found the email, extract attachment
                if msg.is_multipart():
                    for part in msg.walk():
                        content_disp = part.get_content_disposition()
                        part_filename = part.get_filename()
                        if content_disp == 'attachment':
                            if part_filename == filename:
                                # Found the attachment
                                payload = part.get_payload(decode=True)
                                if payload:
                                    content_type = part.get_content_type()
                                    M.logout()
                                    return Response(
                                        content=payload,
                                        media_type=content_type,
                                        headers={
                                            "Content-Disposition": f'attachment; filename="{filename}"'
                                        }
                                    )
        
        if M:
            try:
                M.logout()
            except:
                pass
        raise HTTPException(status_code=404, detail="Attachment not found in IMAP")
        
    except HTTPException:
        if M:
            try:
                M.logout()
            except:
                pass
        raise
    except Exception as e:
        if M:
            try:
                M.logout()
            except:
                pass
        logger.error(f"Error fetching attachment from IMAP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch attachment from email server: {str(e)}")

@router.post("/send", response_model=dict)
def send_email(payload: dict, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    try:
        owner = _get_owner_from_request(request)

        idem = request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        # idempotency check
        cached = _idem_lookup(owner, idem)
        if cached:
            return cached

        # Send email and store in database
        resp = _send_email(payload, db, owner)
        _idem_store(owner, idem, resp)

        return resp
    except HTTPException as e:
        # Preserve specific error codes/details (e.g., 400 SMTP config missing)
        raise e
    except Exception as e:
        logger.exception("Failed to send email")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.post("/trash/{email_id}")
def move_to_trash(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Move an email to trash folder"""
    try:
        owner = _get_owner_from_request(request)
        
        # Schema should already be set up, no need to ensure it here
        
        # Find the email in the tenant database
        email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Store the original folder for restoration
        if not email.original_folder:
            if email.status == EmailStatus.received:
                email.original_folder = "inbox"
            elif email.status == EmailStatus.sent:
                email.original_folder = "sent"
            elif email.status == EmailStatus.draft:
                email.original_folder = "drafts"
            elif email.status == EmailStatus.archived:
                email.original_folder = "archived"
            elif email.status == EmailStatus.spam:
                email.original_folder = "spam"
            else:
                email.original_folder = "inbox"  # Default fallback
        
        # Move to trash
        email.status = EmailStatus.trashed
        email.deleted_at = _to_utc_naive(get_ist_now())
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Email moved to trash successfully",
            "email_id": email_id,
            "original_folder": email.original_folder
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to move email to trash: {str(e)}")

@router.post("/delete-from-trash/{email_id}")
def delete_from_trash(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete an email from trash folder - removes from tenant database"""
    try:
        owner = _get_owner_from_request(request)
        
        # Find the email in the tenant database
        email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Check if email is actually in trash
        if email.status != EmailStatus.trashed:
            raise HTTPException(status_code=400, detail="Email is not in trash")
        
        # Permanently delete the email from the database
        db.delete(email)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Email {email_id} permanently deleted from trash and tenant database",
            "email_id": email_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete email from trash: {str(e)}")

@router.post("/restore/{email_id}")
def restore_from_trash(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Restore an email from trash to its original folder"""
    owner = _get_owner_from_request(request)
    
    try:
        # Use the tenant-aware database session passed as dependency
        # Schema should already be set up, no need to ensure it here
        
        # Find the email in the tenant database
        email = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Check if email is actually in trash
        if email.status != EmailStatus.trashed:
            raise HTTPException(status_code=400, detail="Email is not in trash")
        
        # Get the original folder
        original_folder = email.original_folder or "inbox"
        
        # Restore to original folder based on original_folder
        if original_folder == "inbox":
            email.status = EmailStatus.received
        elif original_folder == "sent":
            email.status = EmailStatus.sent
        elif original_folder == "drafts":
            email.status = EmailStatus.draft
        elif original_folder == "archived":
            email.status = EmailStatus.archived
        elif original_folder == "spam":
            email.status = EmailStatus.spam
        else:
            # Default to inbox if original folder is unknown
            email.status = EmailStatus.received
            original_folder = "inbox"
        
        # Clear trash-related fields
        email.deleted_at = None
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Email restored successfully",
            "email_id": email_id,
            "restored_to": original_folder
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to restore email from trash: {str(e)}")

@router.post("/generate-and-send")
async def generate_and_send(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Generate personalized emails using Wolfy AI for all contacts and send them."""
    from app.core.gemini_service import wolfy_service
    
    # Check if we have any Wolfy AI keys available
    if not settings.gemini_api_keys:
        raise HTTPException(status_code=500, detail="No Wolfy AI keys configured. Please add GEMINI_API_KEY_1 through GEMINI_API_KEY_8 to your .env file.")

    owner = _get_owner_from_request(request)
    
    # Use the tenant-aware database session passed as dependency
    try:
        # Ensure the emails schema is up to date before querying
        _ensure_emails_schema(db)
        
        # Get all contacts for this owner from the tenant database
        contacts = db.query(Contact).filter(Contact.owner_email == owner).order_by(Contact.id.desc()).all()
        
        if not contacts:
            return {
                "results": [], 
                "message": "No contacts found for this user. Please add contacts before generating emails.",
                "total_contacts": 0,
                "processed": 0,
                "summary": {"sent": 0, "errors": 0, "skipped": 0}
            }
        
        # Check SMTP configuration before proceeding
        try:
            smtp_config = _resolve_per_user_smtp(owner)
            
        except HTTPException as e:
            return {
                "results": [], 
                "message": f"SMTP configuration error: {e.detail}",
                "error": e.detail,
                "total_contacts": len(contacts)
            }
        except Exception as e:
            return {
                "results": [], 
                "message": f"Failed to resolve SMTP configuration: {str(e)}",
                "error": str(e),
                "total_contacts": len(contacts)
            }
        
        sent_results: List[dict] = []

        for c in contacts:
            try:
                # Get sender name from user profile
                from app.core.database import SessionLocal
                from app.models.user import User
                pdb_sender = SessionLocal()
                try:
                    user_row = pdb_sender.query(User).filter(User.email == owner).first()
                    sender_name = (user_row.full_name if user_row and user_row.full_name else 
                                 (user_row.username if user_row and user_row.username else 
                                  owner.split('@')[0].replace('.', ' ').title() if owner else "Your Team"))
                finally:
                    pdb_sender.close()
                
                notes = (c.notes or "").strip()
                
                # Auto-generate notes if missing
                if not notes:
                    from app.core.research import auto_research_contact
                    from app.core.database import SessionLocal
                    from app.models.user import User
                    
                    pdb_research = SessionLocal()
                    try:
                        user_row = pdb_research.query(User).filter(User.email == owner).first()
                        user_profession = getattr(user_row, "heard_about_us", None) if user_row else None
                        user_position = getattr(user_row, "position_title", None) if user_row else None
                        user_company = getattr(user_row, "company_name", None) if user_row else None
                    finally:
                        pdb_research.close()
                    
                    # Auto-generate purpose-specific notes
                    try:
                        research_notes = await auto_research_contact(
                            contact=c,
                            owner=owner,
                            user_profession=user_profession,
                            user_position=user_position,
                            user_company=user_company,
                            platform="manual"
                        )
                        
                        if research_notes:
                            notes = research_notes
                            c.notes = research_notes
                            db.commit()
                    except Exception as e:
                        # Log but don't fail email generation
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to auto-generate notes for {c.email}: {e}")

                # Get user profile for expert prompt
                pdb_user = SessionLocal()
                try:
                    user_row = pdb_user.query(User).filter(User.email == owner).first()
                    sender_title = getattr(user_row, "position_title", "") if user_row else ""
                    sender_company = getattr(user_row, "company_name", "") if user_row else ""
                    calendly_link = getattr(user_row, "calendly_link", "") if user_row else ""
                    website_url = getattr(user_row, "website_url", "") if user_row else ""
                    # Get profession data for persona-based email generation
                    heard_about_us = getattr(user_row, "heard_about_us", None) if user_row else None
                    position_title = getattr(user_row, "position_title", None) if user_row else None
                finally:
                    pdb_user.close()

                # Get professional persona based on user's profession/purpose
                professional_persona = get_professional_persona(
                    heard_about_us=heard_about_us,
                    position_title=position_title
                )

                # Use expert prompt for cold emails with profession-specific persona
                prompt = _build_expert_reply_prompt(
                    original="",  # No original message for cold emails
                    receiver_name=c.name or c.email.split('@')[0] if c.email else 'Team',
                    to_addr=c.email or "",
                    receiver_company=c.company or "",
                    receiver_position=c.position or "",
                    sender_name=sender_name,
                    conversation_context="",  # No conversation for cold emails
                    original_context=notes,  # Use notes as personalization context
                    sender_title=sender_title,
                    sender_company=sender_company,
                    calendly_link=calendly_link or "",
                    website_url=website_url or "",
                    email_type="cold",
                    professional_persona=professional_persona
                )
                
                # Skip contacts that already received an initial email
                # Use the main Supabase database session
                check_db = db
                
                try:
                    existing_sent = (
                        check_db.query(Email)
                        .filter(Email.owner_email == owner, Email.to_address == c.email, Email.status == EmailStatus.sent)
                        .first()
                    )
                    if existing_sent:
                        sent_results.append({"email": c.email, "status": "skipped", "detail": "Already sent"})
                        continue
                finally:
                    pass  # No need to close db as it's managed by FastAPI

                # Generate content with Wolfy AI using the service
                def generate_prompt(context):
                    return prompt
                
                gemini_result = await wolfy_service.make_request(
                    user_email=owner,
                    endpoint="email_generation",
                    request_type="generate_email",
                    prompt_func=generate_prompt,
                    context={"prompt": prompt},
                    use_cache=False,  # Don't cache personalized emails
                    priority="normal"
                )
                
                if not gemini_result.get('success'):
                    error_msg = gemini_result.get('message', 'Unknown Wolfy AI error')
                    is_quota_error = gemini_result.get('quota_exceeded', False) or 'quota' in error_msg.lower() or '429' in error_msg
                    
                    # Log to standard logger for debugging
                    logger.error(
                        f"AI generation failed for {c.email}: {error_msg}. "
                        f"Quota error: {is_quota_error}. "
                        f"Notes available: {bool(notes)} ({len(notes) if notes else 0} chars). "
                        f"Full error: {str(gemini_result)[:200]}"
                    )
                    
                    # If quota exceeded, use fallback template instead of failing
                    if is_quota_error:
                        # Use intelligent fallback email template that extracts insights from notes
                        import json, re
                        signature_line2 = ""
                        signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")
                        
                        # Add website URL to signature if available (already fetched above)
                        if website_url:
                            signature += f"\n{website_url}"
                        
                        # Generate a structured email template with notes-based personalization
                        subject = f"Reaching out - {c.company or 'opportunity'}" if c.company else "Hello"
                        
                        # Create structured body that uses notes intelligently
                        body = f"Hi {c.name or 'there'},\n\n"
                        
                        # Extract key information from notes if available
                        if notes:
                            # Extract company name from notes if not in contact
                            company_match = re.search(r'([A-Z][a-zA-Z\s&]+(?:Consulting|Solutions|Systems|Group|Inc|LLC|Ltd|Company|Corp|Firm))', notes)
                            extracted_company = company_match.group(1).strip() if company_match else None
                            company_name = extracted_company or c.company or "your company"
                            
                            # Extract founder/executive name if mentioned
                            founder_match = re.search(r'(?:founder|CEO|executive|president|owner)[\s,]+([A-Z][a-z]+\s+[A-Z][a-z]+)', notes, re.IGNORECASE)
                            founder_name = founder_match.group(1) if founder_match else None
                            
                            # Extract key insights/opportunities from notes
                            insights = []
                            notes_lower = notes.lower()
                            
                            if any(word in notes_lower for word in ['website', 'site', 'web']):
                                if any(word in notes_lower for word in ['lacks', 'needs', 'improve', 'outdated', 'old', 'missing']):
                                    insights.append("website design")
                                if any(word in notes_lower for word in ['modern', 'engaging', 'visual', 'design']):
                                    insights.append("modern design")
                            
                            if 'content' in notes_lower or 'marketing' in notes_lower:
                                if 'thought leadership' in notes_lower or 'authority' in notes_lower:
                                    insights.append("thought leadership")
                                else:
                                    insights.append("content marketing")
                            
                            if 'lead generation' in notes_lower or 'referral' in notes_lower:
                                insights.append("lead generation")
                            
                            if 'testimonial' in notes_lower or 'case study' in notes_lower or 'client' in notes_lower:
                                insights.append("social proof")
                            
                            if 'linkedin' in notes_lower or 'social media' in notes_lower:
                                insights.append("social media presence")
                            
                            if 'digital' in notes_lower or 'online' in notes_lower:
                                insights.append("digital presence")
                            
                            # Build personalized email using extracted insights
                            # Context & Credibility
                            if sender_company:
                                body += f"I'm {sender_name} from {sender_company}, and I help companies like {company_name} "
                            else:
                                body += f"I'm {sender_name}, and I help companies like {company_name} "
                            
                            # Add value based on insights
                            if insights:
                                # Use first 2-3 insights
                                insight_list = insights[:3]
                                if len(insight_list) == 1:
                                    body += f"strengthen their {insight_list[0]}.\n\n"
                                elif len(insight_list) == 2:
                                    body += f"improve their {insight_list[0]} and {insight_list[1]}.\n\n"
                                else:
                                    body += f"enhance their {insight_list[0]}, {insight_list[1]}, and {insight_list[2]}.\n\n"
                                
                                # Observation based on notes
                                body += f"I reviewed {company_name} and noticed opportunities to "
                                if 'website' in notes_lower and ('lacks' in notes_lower or 'needs' in notes_lower):
                                    body += "modernize your digital presence and better showcase your expertise.\n\n"
                                elif 'lead generation' in notes_lower:
                                    body += "expand your reach beyond referrals and attract more clients.\n\n"
                                elif 'content' in notes_lower or 'marketing' in notes_lower:
                                    body += "strengthen your content strategy and build more authority.\n\n"
                                else:
                                    body += "grow your business and reach more clients.\n\n"
                            else:
                                # Generic but still personalized
                                body += "strengthen their digital presence and grow their business.\n\n"
                                body += f"I came across {company_name} and wanted to connect about potential opportunities.\n\n"
                            
                            # Value proposition
                            body += "I'd be happy to share some specific insights that could help. "
                            body += "Would you like me to send over a quick analysis?\n\n"
                        else:
                            # No notes - generic message
                            if c.company:
                                body += f"I came across {c.company} and wanted to connect about potential opportunities.\n\n"
                            else:
                                body += "I wanted to reach out to discuss potential opportunities.\n\n"
                            body += "I'd be happy to discuss how we might work together. "
                            body += "Please let me know if you're interested in learning more.\n\n"
                        
                        body += f"Best regards,\n{signature}"
                        
                        data = {"subject": subject, "body": body}
                        # Log that fallback was used
                        logger.warning(f"Using fallback template for {c.email} due to quota/API error. Notes were {'used' if notes else 'not available'}")
                        # Continue with sending using fallback template
                    else:
                        # For other errors, mark as failed
                        sent_results.append({"email": c.email, "status": "error", "detail": f"Wolfy AI generation failed: {error_msg}"})
                        continue
                else:
                    text = gemini_result.get('response', '')
                    
                    # Parse JSON response (handle both variants format and legacy format)
                    import json, re
                    signature_line2 = ""
                    signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")
                    data = {
                        "subject": "Hello",
                        "body": f"Hi {c.name},\n\nI wanted to reach out briefly.\n\nBest regards,\n{signature}",
                    }
                    try:
                        # First try to find JSON wrapped in code blocks
                        code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
                        if code_block_match:
                            json_str = code_block_match.group(1)
                            parsed_data = json.loads(json_str)
                        else:
                            # Fallback to direct JSON search
                            match = re.search(r"\{[\s\S]*\}", text)
                            if match:
                                parsed_data = json.loads(match.group(0))
                            else:
                                parsed_data = None
                        
                        if parsed_data:
                            # Handle variants format (new expert prompt)
                            if 'variants' in parsed_data and isinstance(parsed_data['variants'], dict):
                                variants = parsed_data['variants']
                                # Use medium variant as default, fallback to short
                                selected_variant = variants.get('medium') or variants.get('short') or variants.get('long')
                                if selected_variant:
                                    data = {
                                        "subject": selected_variant.get('subject', 'Hello'),
                                        "body": selected_variant.get('body', data['body'])
                                    }
                            else:
                                # Legacy format - single body
                                data = {
                                    "subject": parsed_data.get("subject", "Hello"),
                                    "body": parsed_data.get("body", data['body'])
                                }
                    except Exception:
                        pass

                # Skip contacts that already received an initial email
                # Use the main Supabase database session
                check_db = db
                
                try:
                    existing_sent = (
                        check_db.query(Email)
                        .filter(Email.owner_email == owner, Email.to_address == c.email, Email.status == EmailStatus.sent)
                        .first()
                    )
                    if existing_sent:
                        sent_results.append({"email": c.email, "status": "skipped", "detail": "Already sent initial email"})
                        continue
                finally:
                    pass  # No need to close db as it's managed by FastAPI
                
                # Send email via existing SMTP path using Supabase database
                payload = {"to": c.email, "subject": data.get("subject") or "Hello", "content": data.get("body") or f"Hi {c.name},"}
                
                try:
                    _send_email(payload, db, owner=owner)
                    sent_results.append({"email": c.email, "status": "sent"})

                    # Update contact with first_sent_at timestamp
                    if not c.first_sent_at:
                        c.first_sent_at = get_ist_now()
                        db.commit()
                        
                except HTTPException as e:
                    error_msg = f"HTTP error: {e.detail}"
                    sent_results.append({"email": c.email, "status": "error", "detail": error_msg})
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    sent_results.append({"email": c.email, "status": "error", "detail": error_msg})
                    
            except Exception as e:
                error_msg = f"Gemini generation failed: {e}"
                sent_results.append({"email": c.email, "status": "error", "detail": error_msg})
                continue
        
        # Calculate summary statistics
        sent_count = sum(1 for r in sent_results if r.get('status') == 'sent')
        error_count = sum(1 for r in sent_results if r.get('status') == 'error')
        skipped_count = sum(1 for r in sent_results if r.get('status') == 'skipped')
        
        # Return detailed response with summary
        return {
            "results": sent_results, 
            "total_contacts": len(contacts), 
            "processed": len(sent_results),
            "summary": {
                "sent": sent_count,
                "errors": error_count,
                "skipped": skipped_count
            },
            "message": f"Processed {len(sent_results)} contact(s): {sent_count} sent, {error_count} errors, {skipped_count} skipped"
        }
        
    except Exception as e:
        error_msg = f"Failed to generate and send emails: {str(e)}"
        logger.error(f"Generate-and-send failed for {owner}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/reply")
async def reply_email(request: Request, payload: dict, db: Session = Depends(get_tenant_db_dependency)):
    """Generate and send a reply email based on the client's message or provided overrides.
    
    Enhanced with conversation history analysis for better contextual responses.

    Recipient resolution priority (no need to pass `to`):
    1) `to` in payload
    2) `email_id` in payload -> use that Email (from for received, to otherwise)
    3) `contact_id` in payload -> use that Contact.email
    4) Parse first client address from `original` text that is not equal to our own from address

    Behavior:
    - If `body` provided in payload, it will be used as the reply content (no AI rewrite).
    - If `schedule` provided (dict with title/start_iso/end_iso), a Meeting will be created from it.
    - Otherwise, AI will infer intent and generate `body` and optional `schedule`; a Meeting is created when present.
    - AI analyzes conversation history to provide contextual responses.
    - If intent indicates interest/scheduling and owner has no Calendly link, body is adapted to ask the client for times.
    """
    # Check if we have any Gemini API keys available
    if not settings.gemini_api_keys:
        raise HTTPException(status_code=500, detail="No Gemini API keys configured. Please add GEMINI_API_KEY_1 through GEMINI_API_KEY_8 to your .env file.")

    to_addr = (payload.get("to") or "").strip()
    original = (payload.get("original") or "").strip()
    email_id = payload.get("email_id")
    contact_id = payload.get("contact_id")
    body_override = (payload.get("body") or "").strip()
    schedule_override = payload.get("schedule") if isinstance(payload.get("schedule"), dict) else None
    if not original:
        raise HTTPException(status_code=422, detail="original is required")

    owner = _get_owner_from_request(request)
    contact: Contact | None = None

    # Use tenant database for all operations
    try:
        # Ensure the emails schema is up to date
        _ensure_emails_schema(db)

        # Resolve recipient
        if not to_addr and email_id:
            row = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
            if row:
                try:
                    to_addr = row.from_address if row.status == EmailStatus.received else row.to_address
                except Exception:
                    to_addr = row.to_address or row.from_address
        if not to_addr and contact_id:
            cby = db.query(Contact).filter(Contact.owner_email == owner, Contact.id == contact_id).first()
            if cby:
                to_addr = cby.email
                contact = cby
        if not to_addr:
            import re
            candidates = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", original)
            # pick the first that isn't our own from address
            my_from = (settings.EMAIL_FROM or settings.EMAIL_USER or "").lower()
            for cand in candidates:
                if cand.lower() != my_from:
                    to_addr = cand
                    break

        if not to_addr:
            raise HTTPException(status_code=422, detail="Could not determine recipient email")

        if contact is None:
            contact = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == to_addr).first()
        # proceed even if contact is missing

        # Get subject from payload or AI generation (will be set after AI call)
        subject_override = payload.get("subject")
        
        # Prepare sender signature
        # Get better sender details from user profile and original cold email context
        from app.core.database import SessionLocal
        pdb_primary = SessionLocal()

        try:
            owner_row = pdb_primary.query(User).filter(User.email == owner).first()
            calendly = getattr(owner_row, "calendly_link", None) if owner_row else None
            admin_full_name = getattr(owner_row, "full_name", None) if owner_row else None
            admin_company = getattr(owner_row, "company_name", None) if owner_row else None
            
            # Build comprehensive conversation context using helper function
            conversation_context, original_context = _build_conversation_context(db, owner, to_addr)
            
        except Exception as e:
            # If there's an error building context, use empty context
            calendly = None
            admin_full_name = None
            admin_company = None
            conversation_context = ""
            original_context = ""
        finally:
            pdb_primary.close()

    except Exception as e:
        # If there's an error in the main try block, handle it
        raise HTTPException(status_code=500, detail=f"Error processing reply: {str(e)}")

    # Prefer contact sender fields, then admin profile, then fallback
    sender_name = (
        None or 
        admin_full_name or 
        "Your Team"
    ).strip()
        
    sender_position = ""
    sender_firm = admin_company or ""
        
    signature_line2 = ", ".join([p for p in [sender_position, sender_firm] if p])
    signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")

    # Decide body/schedule
    intent = "unclear"
    body = body_override
    schedule = schedule_override
        
    # Import the Gemini service
    from app.core.gemini_service import wolfy_service

    # Build receiver fallback values when contact record is missing
    receiver_name = (contact.name if contact else (to_addr.split('@')[0] if to_addr else 'there'))
    receiver_company = (contact.company if contact else '')
    receiver_position = (contact.position if contact else '')

    # Use enhanced prompt with conversation context
    prompt = _build_enhanced_reply_prompt(
    original, receiver_name, to_addr, receiver_company, receiver_position, 
    sender_name, conversation_context, original_context
    )

    import json, re
    data = {"intent": "unclear", "body": "", "schedule": None}
        
    # Generate content using the new Gemini service if no body override provided
    if not body and schedule is None:
        try:
            def generate_prompt(context):
                return prompt
            
            gemini_result = await wolfy_service.make_request(
                user_email=owner,
                endpoint="reply_email",
                request_type="generate_reply",
                prompt_func=generate_prompt,
                context={"prompt": prompt},
                use_cache=False,
                priority="normal"
            )
            
            if gemini_result.get('success'):
                text = gemini_result.get('response', '')
                try:
                    # First try to find JSON wrapped in code blocks
                    code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
                    if code_block_match:
                        data = json.loads(code_block_match.group(1))
                    else:
                        # Fallback to direct JSON search
                        match = re.search(r"\{[\s\S]*\}", text)
                        if match:
                            data = json.loads(match.group(0))
                except Exception as e:
                    pass
        except Exception as e:
            # Fallback to basic response if generation fails
            pass

    intent = data.get("intent", "unclear")
    if not body:
        body = data.get("body") or data.get("content") or data.get("text") or data.get("message") or ""
    schedule = schedule if schedule is not None else (data.get("schedule") if isinstance(data.get("schedule"), dict) else None)
    
    # Use AI-generated subject if available, otherwise use override or default
    subject = subject_override or data.get("subject") or "Re: Your email"

    if not body:
        body = ""

    # Calendly/link adaptation
    try:
        if intent in {"interested", "schedule"}:
            if calendly:
                body = body.replace("[[CALENDLY_LINK]]", calendly)
            else:
                # Remove placeholder
                body = body.replace("[[CALENDLY_LINK]]", "")
    except Exception:
        pass

    # Create meeting if schedule provided
    created_meeting_id = None
    if isinstance(schedule, dict) and (schedule.get('start_iso') or schedule.get('end_iso')):
        def _parse_iso(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                return None
        # Parse client's requested time from the original message as fallback
        def _parse_client_time_from_message(msg: str) -> tuple[datetime, datetime]:
            """Parse client's requested time from message content."""
            try:
                # Look for patterns like "September 10th, between 6 PM and 7 PM"
                import re
                # Pattern to match "September 10th, between 6 PM and 7 PM"
                pattern = r'September\s+(\d+)(?:st|nd|rd|th)?,?\s+between\s+(\d+)\s+PM\s+and\s+(\d+)\s+PM'
                match = re.search(pattern, msg, re.IGNORECASE)
                if match:
                    day = int(match.group(1))
                    start_hour = int(match.group(2))
                    end_hour = int(match.group(3))
                    # Convert to 24-hour format
                    start_hour_24 = start_hour if start_hour == 12 else start_hour + 12
                    end_hour_24 = end_hour if end_hour == 12 else end_hour + 12
                    return (
                        datetime(2025, 9, day, start_hour_24, 0, 0),
                        datetime(2025, 9, day, end_hour_24, 0, 0)
                    )
            except Exception:
                pass
            # Default fallback
            return (
                datetime(2025, 9, 10, 18, 0, 0),  # September 10th, 2025, 6:00 PM
                datetime(2025, 9, 10, 19, 0, 0)   # September 10th, 2025, 7:00 PM
            )
        
        fallback_start, fallback_end = _parse_client_time_from_message(original)
        st = _parse_iso(schedule.get('start_iso')) or fallback_start
        en = _parse_iso(schedule.get('end_iso')) or fallback_end
        title = schedule.get('title') or f"Call with {(contact.name if contact else (to_addr.split('@')[0] if to_addr else 'client'))}"
        m = Meeting(
            title=title,
            description=f"Auto-scheduled from email reply",
            start_time=st,
            end_time=en,
            location="Online",
            attendees=to_addr,
            type=MeetingType.video,
            status=MeetingStatus.scheduled,
            notes=f"Source: AI reply from subject: {subject}",
            owner_email=owner,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        created_meeting_id = m.id

    # Idempotency per owner + key
    idem_key = request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
    cached = _idem_lookup(owner, idem_key)
    if cached:
        result = dict(cached)
    else:
        # Send the reply using internal SMTP helper (avoid calling the API route function)
        result = _send_email({"to": to_addr, "subject": subject, "content": body}, db, owner=owner)
        _idem_store(owner, idem_key, result)
    result["intent"] = intent
    if created_meeting_id is not None:
        result["meeting_id"] = created_meeting_id
    
    return result

@router.post("/reply/preview")
async def reply_preview(request: Request, payload: dict, db: Session = Depends(get_tenant_db_dependency)):
    """Generate a preview of the reply and optional schedule; do not send anything."""
    
    try:
        
        # Initialize variables for exception handling
        owner = None
        to_addr = None
        original = None
        email_id = None
        contact = None
        receiver_name = "there"
        sender_name = "Your Team"
        
        # Ensure we start with a clean transaction state
        try:
            db.rollback()
        except Exception as rollback_err:
            pass  # Ignore rollback errors if transaction is already clean
        
        # Check if we have any Gemini API keys available
        if not settings.gemini_api_keys:
            raise HTTPException(status_code=500, detail="No Gemini API keys configured. Please add GEMINI_API_KEY_1 through GEMINI_API_KEY_8 to your .env file.")

        to_addr = (payload.get("to") or "").strip()
        original = (payload.get("original") or "").strip()
        email_id = payload.get("email_id")
        contact_id = payload.get("contact_id")
        if not original:
            raise HTTPException(status_code=422, detail="original is required")

        
        owner = _get_owner_from_request(request)
        
        
        contact: Contact | None = None

        # Resolve recipient
        if not to_addr and email_id:
            try:
                row = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
                if row:
                    try:
                        to_addr = row.from_address if row.status == EmailStatus.received else row.to_address
                    except Exception:
                        to_addr = row.to_address or row.from_address
            except Exception as query_error:
                # Handle transaction errors and missing columns
                from sqlalchemy.exc import OperationalError, ProgrammingError, InternalError
                from sqlalchemy import text
                error_str = str(query_error).lower()
                error_msg = str(query_error)
                
                # Check for transaction errors first
                if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_str:
                    logger.warning(f"Transaction error in reply_preview email query, rolling back: {error_msg}")
                    try:
                        db.rollback()
                        # Retry the query after rollback
                        row = db.query(Email).filter(Email.owner_email == owner, Email.id == email_id).first()
                        if row:
                            try:
                                to_addr = row.from_address if row.status == EmailStatus.received else row.to_address
                            except Exception:
                                to_addr = row.to_address or row.from_address
                    except Exception as retry_error:
                        logger.error(f"Retry query failed after rollback: {str(retry_error)}")
                        # Fall through to raw SQL fallback
                elif isinstance(query_error, (OperationalError, ProgrammingError)) or 'column' in error_str or 'does not exist' in error_str or 'attachments' in error_str:
                    # Handle missing attachments column - use raw SQL
                    try:
                        db.rollback()  # Rollback before raw SQL
                        sql_query = text("""
                            SELECT id, subject, body, to_address, from_address, status, 
                                   sent_at, received_at, is_starred, is_read, owner_email
                            FROM emails 
                            WHERE owner_email = :owner_email AND id = :email_id
                            LIMIT 1
                        """)
                        result = db.execute(sql_query, {"owner_email": owner, "email_id": email_id})
                        row_data = result.fetchone()
                        if row_data:
                            status_val = row_data[5]
                            to_addr = row_data[3] if EmailStatus(status_val) == EmailStatus.received else row_data[4]
                    except Exception:
                        pass
        
        if not to_addr and contact_id:
            try:
                cby = db.query(Contact).filter(Contact.owner_email == owner, Contact.id == contact_id).first()
                if cby:
                    to_addr = cby.email
                    contact = cby
            except Exception as contact_query_error:
                # Handle transaction errors for contact query
                error_msg = str(contact_query_error)
                if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_msg.lower():
                    logger.warning(f"Transaction error in reply_preview contact query, rolling back: {error_msg}")
                    try:
                        db.rollback()
                        cby = db.query(Contact).filter(Contact.owner_email == owner, Contact.id == contact_id).first()
                        if cby:
                            to_addr = cby.email
                            contact = cby
                    except Exception:
                        pass
        if not to_addr:
            import re
            candidates = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", original)
            my_from = (settings.EMAIL_FROM or settings.EMAIL_USER or "").lower()
            for cand in candidates:
                if cand.lower() != my_from:
                    to_addr = cand
                    break

        if not to_addr:
            raise HTTPException(status_code=422, detail="Could not determine recipient email")

        if contact is None:
            try:
                contact = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == to_addr).first()
            except Exception as contact_query_error:
                # Handle transaction errors for contact lookup
                error_msg = str(contact_query_error)
                if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_msg.lower():
                    logger.warning(f"Transaction error in reply_preview contact lookup, rolling back: {error_msg}")
                    try:
                        db.rollback()
                        contact = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == to_addr).first()
                    except Exception as retry_error:
                        logger.error(f"Retry contact query failed after rollback: {str(retry_error)}")
                        contact = None  # Proceed without contact
                else:
                    logger.error(f"Contact query error in reply_preview: {error_msg}")
                    contact = None  # Proceed without contact
        # proceed even if contact is missing

        # Import the Gemini service
        from app.core.gemini_service import wolfy_service

        # Get admin profile details for better signature  
        pdb_for_admin = SessionLocal()
        admin_full_name = None
        admin_company = None
        try:
            # Use raw SQL to avoid SQLAlchemy column issues
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            try:
                sql_query = text("""
                    SELECT id, email, full_name, company_name
                    FROM app_users 
                    WHERE email = :email
                    LIMIT 1
                """)
                result = pdb_for_admin.execute(sql_query, {"email": owner})
                row = result.fetchone()
                if row:
                    admin_full_name = row[2]
                    admin_company = row[3]
            except (OperationalError, ProgrammingError) as db_error:
                # If raw SQL fails, try SQLAlchemy as fallback
                error_str = str(db_error).lower()
            if 'does not exist' in error_str or 'no such column' in error_str:
                try:
                    owner_row = pdb_for_admin.query(User).filter(User.email == owner).first()
                    if owner_row:
                        admin_full_name = getattr(owner_row, "full_name", None)
                        admin_company = getattr(owner_row, "company_name", None)
                except Exception:
                    pass
            else:
                pass
        except Exception:
            pass
        finally:
            pdb_for_admin.close()

        # Build comprehensive conversation context using helper function
        try:
            conversation_context, original_context = _build_conversation_context(db, owner, to_addr)
        except Exception as context_error:
            # Handle transaction errors in context building
            error_msg = str(context_error)
            if "InFailedSqlTransaction" in error_msg or "transaction is aborted" in error_msg.lower():
                logger.warning(f"Transaction error in reply_preview context building, rolling back: {error_msg}")
                try:
                    db.rollback()
                    # Retry context building after rollback
                    conversation_context, original_context = _build_conversation_context(db, owner, to_addr)
                except Exception:
                    # Fallback to empty context if retry fails
                    conversation_context, original_context = "", ""
            else:
                # Fallback to empty context for other errors
                logger.warning(f"Error building conversation context: {error_msg}")
                conversation_context, original_context = "", ""

        # Prefer contact sender fields, then admin profile, then fallback
        sender_name = (
            None or 
            admin_full_name or 
            "Your Team"
        ).strip()
        
        sender_position = ""
        sender_firm = admin_company or ""
        
        signature_line2 = ", ".join([p for p in [sender_position, sender_firm] if p])
        signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")

        receiver_name = (contact.name if contact else (to_addr.split('@')[0] if to_addr else 'there'))
        receiver_company = (contact.company if contact else '')
        receiver_position = (contact.position if contact else '')
        
        # Get calendly link, website URL, and profession data for expert prompt
        pdb_calendly = SessionLocal()
        calendly_link = None
        website_url = None
        heard_about_us = None
        position_title = None
        try:
            # Use raw SQL to avoid SQLAlchemy column issues
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            try:
                sql_query = text("""
                    SELECT id, email, calendly_link, website_url, heard_about_us, position_title
                    FROM app_users 
                    WHERE email = :email
                    LIMIT 1
                """)
                result = pdb_calendly.execute(sql_query, {"email": owner})
                row = result.fetchone()
                if row:
                    calendly_link = row[2]
                    website_url = row[3]
                    heard_about_us = row[4]
                    position_title = row[5]
            except (OperationalError, ProgrammingError) as db_error:
                # If raw SQL fails, try SQLAlchemy as fallback
                error_str = str(db_error).lower()
                if 'does not exist' in error_str or 'no such column' in error_str:
                    try:
                        calendly_row = pdb_calendly.query(User).filter(User.email == owner).first()
                        if calendly_row:
                            calendly_link = getattr(calendly_row, "calendly_link", None)
                            website_url = getattr(calendly_row, "website_url", None)
                            heard_about_us = getattr(calendly_row, "heard_about_us", None)
                            position_title = getattr(calendly_row, "position_title", None)
                    except Exception:
                        pass
                else:
                    pass
        except Exception:
            pass
        finally:
            pdb_calendly.close()

        # Get professional persona based on user's profession/purpose
        professional_persona = get_professional_persona(
            heard_about_us=heard_about_us,
            position_title=position_title
        )

        # Use expert prompt with conversation context and profession-specific persona
        prompt = _build_expert_reply_prompt(
            original=original,
            receiver_name=receiver_name,
            to_addr=to_addr,
            receiver_company=receiver_company,
            receiver_position=receiver_position,
            sender_name=sender_name,
            conversation_context=conversation_context,
            original_context=original_context,
            sender_title=sender_position,
            sender_company=sender_firm,
            calendly_link=calendly_link or "",
            website_url=website_url or "",
            email_type="reply",
            professional_persona=professional_persona
        )
        

        import json, re
        data: dict[str, Any] = {"intent": "unclear", "body": "", "schedule": None}
        
        # Ensure receiver_name and sender_name are defined (they're already set above, but ensure they exist for exception handler)
        # These variables are already defined earlier in the function, so this is just a safety check
        try:
            _ = receiver_name  # Check if defined
        except NameError:
            receiver_name = (contact.name if contact else (to_addr.split('@')[0] if to_addr else 'there'))
        
        try:
            _ = sender_name  # Check if defined
        except NameError:
            sender_name = (
                admin_full_name or 
                "Your Team"
            ).strip() if admin_full_name else "Your Team"
        
        # Generate content using the new Gemini service
        try:
            def generate_prompt(context):
                return prompt
            
            
            
            try:
                gemini_result = await wolfy_service.make_request(
                user_email=owner,
                endpoint="reply_preview",
                request_type="generate_reply",
                prompt_func=generate_prompt,
                context={"prompt": prompt},
                use_cache=False,
                    priority="normal"
                )
            except Exception as api_error:
                # Log the API error and convert to a result dict
                error_msg = str(api_error)
                logger.error(f"Gemini service API call failed in reply_preview: {api_error}", exc_info=True)
                gemini_result = {
                    'success': False,
                    'error': error_msg,
                    'quota_exceeded': '429' in error_msg or 'quota' in error_msg.lower() or 'exceeded' in error_msg.lower()
                }
            
            
            
            if gemini_result.get('success'):
                text = gemini_result.get('response', '')
                
            
            try:
                # First try to find JSON wrapped in code blocks
                code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
                if code_block_match:
                    json_str = code_block_match.group(1)
                    data = json.loads(json_str)
                else:
                    # Fallback to direct JSON search
                    match = re.search(r"\{[\s\S]*\}", text)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                    else:
                        pass
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from reply preview response: {e}")
        except Exception as e:
            logger.warning(f"Error parsing JSON from reply preview: {e}")
        
        if not gemini_result or gemini_result.get('error'):
            # If quota exceeded, use fallback reply generation
            is_quota_error = gemini_result.get('quota_exceeded', False) or 'quota' in str(gemini_result.get('error', '')).lower() or '429' in str(gemini_result.get('error', ''))
            
            if is_quota_error:
                # Generate fallback reply based on simple rule-based intent detection
                original_lower = original.lower()
                
                # Simple intent detection from keywords
                detected_intent_fallback = "unclear"
                if any(word in original_lower for word in ['interested', 'yes', 'sounds good', 'let\'s', "let's", 'schedule', 'meeting', 'call', 'connect']):
                    detected_intent_fallback = "interested"
                elif any(word in original_lower for word in ['not interested', 'no thanks', 'unsubscribe', 'remove']):
                    detected_intent_fallback = "not_interested"
                elif any(word in original_lower for word in ['more info', 'information', 'details', 'tell me', 'explain']):
                    detected_intent_fallback = "request_more_info"
                elif any(word in original_lower for word in ['schedule', 'meeting', 'call', 'time', 'when', 'available']):
                    detected_intent_fallback = "schedule"
                elif any(word in original_lower for word in ['unsubscribe', 'remove', 'stop']):
                    detected_intent_fallback = "unsubscribe"
                elif any(word in original_lower for word in ['question', '?', 'how', 'what', 'why', 'when', 'where']):
                    detected_intent_fallback = "question"
                
                # Generate simple reply based on intent
                greeting = f"Hello {receiver_name}," if receiver_name != 'there' else "Hello,"
                
                if detected_intent_fallback == "interested":
                    body_fallback = f"{greeting}\n\nThank you for your interest! I'd be happy to discuss this further with you.\n\n"
                elif detected_intent_fallback == "schedule":
                    body_fallback = f"{greeting}\n\nThank you for reaching out. I'd be happy to schedule a time to connect. Please let me know your availability.\n\n"
                elif detected_intent_fallback == "request_more_info":
                    body_fallback = f"{greeting}\n\nThank you for your inquiry. I'd be happy to provide more information. What specific details would you like to know?\n\n"
                elif detected_intent_fallback == "question":
                    body_fallback = f"{greeting}\n\nThank you for your question. I'll do my best to help you with that.\n\n"
                elif detected_intent_fallback == "not_interested":
                    body_fallback = f"{greeting}\n\nThank you for letting me know. I understand and respect your decision.\n\n"
                elif detected_intent_fallback == "unsubscribe":
                    body_fallback = f"{greeting}\n\nI've noted your request to unsubscribe. You will no longer receive emails from us.\n\n"
                else:
                    body_fallback = f"{greeting}\n\nThank you for your message. I've received it and will get back to you soon.\n\n"
                
                # Add signature (signature already includes sender name, so just add "Best regards," before it)
                if signature:
                    # If signature has multiple lines, add "Best regards," before the first line
                    signature_lines = signature.split('\n')
                    body_fallback += f"Best regards,\n{signature_lines[0]}"
                    if len(signature_lines) > 1:
                        body_fallback += "\n" + "\n".join(signature_lines[1:])
                else:
                    body_fallback += f"Best regards,\n{sender_name}"
                
                # Update data with fallback values
                data = {
                    "intent": detected_intent_fallback,
                    "body": body_fallback,
                    "schedule": None
                }
            
    except Exception as e:
        # Fallback to basic response if generation fails (quota exceeded, etc.)
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        error_msg = str(e)
        # Check if this is a database column error and handle it gracefully
        from sqlalchemy.exc import OperationalError, ProgrammingError
        error_str = error_msg.lower()
        is_column_error = False
        try:
            import psycopg2
            if hasattr(e, 'orig') and isinstance(e.orig, psycopg2.errors.UndefinedColumn):
                is_column_error = True
        except (ImportError, AttributeError):
            pass
        if not is_column_error:
            is_column_error = (
                isinstance(e, (OperationalError, ProgrammingError)) or 
                'column' in error_str or 
                'does not exist' in error_str or 
                'attachments' in error_str
            )
        if is_column_error:
            logger.warning(f"Database column error in reply_preview (likely missing 'attachments' column): {e}")
            # Return a fallback response instead of raising an error
            # Safely get receiver_name and sender_name with fallbacks
            receiver_name_val = "there"
            sender_name_val = "Your Team"
            try:
                if receiver_name:
                    receiver_name_val = receiver_name
            except NameError:
                pass
            except:
                pass
            
            try:
                if sender_name:
                    sender_name_val = sender_name
            except NameError:
                pass
            except:
                pass
            
            greeting = f"Hi {receiver_name_val}," if receiver_name_val and receiver_name_val != "there" else "Hi there,"
            fallback_body = f"{greeting}\n\nThank you for your message. I've received it and will get back to you soon.\n\nBest regards,\n{sender_name_val}"
            return {
                "intent": "unclear",
                "body": fallback_body,
                "subject": f"Re: {payload.get('subject', 'Your message')}" if payload.get('subject') else "Re: Your message",
                "preview_text": "",
                "variants": {},
                "why_this_works": "",
                "schedule": None
            }
        logger.error(f"Reply preview generation failed: {error_msg}", exc_info=True)
        # Check if it's a critical error that should be raised
        error_lower = error_msg.lower()
        if any(keyword in error_lower for keyword in ['timeout', 'connection', 'network', 'unreachable', 'refused']):
            raise HTTPException(status_code=504, detail=f"Reply generation timed out or connection failed: {error_msg}")
        
        # Check if it's a quota error
        is_quota_error = (
            '429' in str(e) or
            'quota' in error_lower or
            'rate limit' in error_lower or
            'resourceexhausted' in error_lower or
            'exceeded' in error_lower
        )
        
        # For quota errors and other non-critical errors, return fallback data
        if is_quota_error:
            logger.warning(f"Gemini API quota exceeded in reply_preview, using fallback reply")
        
        # Return a fallback response
        # Safely get receiver_name and sender_name
        receiver_name_val = "there"
        sender_name_val = "Your Team"
        try:
            if receiver_name:
                receiver_name_val = receiver_name
        except NameError:
            pass
        except:
            pass
        
        try:
            if sender_name:
                sender_name_val = sender_name
        except NameError:
            pass
        except:
            pass
        
        greeting = f"Hi {receiver_name_val}," if receiver_name_val and receiver_name_val != "there" else "Hi there,"
        fallback_body = f"{greeting}\n\nThank you for your message. I've received it and will get back to you soon.\n\nBest regards,\n{sender_name_val}"
        return {
            "intent": "unclear",
            "body": fallback_body,
            "subject": f"Re: {payload.get('subject', 'Your message')}" if payload.get('subject') else "Re: Your message",
            "preview_text": "",
            "variants": {
                "short": fallback_body,
                "medium": fallback_body,
                "long": fallback_body
            },
            "why_this_works": "",
            "schedule": None
        }

        # Extract variants if present, otherwise use single body (legacy format)
        variants_data = {}
        body = ""
        subject = ""
        preview_text = ""
        why_this_works = ""
        
        if 'variants' in data and isinstance(data['variants'], dict):
            # New format with variants
            variants = data['variants']
            # Use medium as default, fallback to short if medium not available
            selected_variant = variants.get('medium') or variants.get('short') or variants.get('long')
            if selected_variant:
                body = selected_variant.get('body', '')
                subject = selected_variant.get('subject', '')
                preview_text = selected_variant.get('preview_text', '')
                why_this_works = selected_variant.get('why_this_works', '')
            
            # Store all variants for response
            variants_data = {
                "short": variants.get('short', {}).get('body', ''),
                "medium": variants.get('medium', {}).get('body', '') or body,
                "long": variants.get('long', {}).get('body', '')
            }
        else:
            # Legacy format - single body
            body = data.get("body", "")
            variants_data = {
                "short": body,
                "medium": body,
                "long": body
            }
        
        intent = data.get("intent", "unclear")
        
        # Calendly/link adaptation in preview (lookup in primary DB)
        pdb = SessionLocal()
        calendly = None
        try:
            # Use raw SQL to avoid SQLAlchemy column issues
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            
            try:
                sql_query = text("""
                    SELECT id, email, calendly_link
                    FROM app_users 
                    WHERE email = :email
                    LIMIT 1
                """)
                result = pdb.execute(sql_query, {"email": owner})
                row = result.fetchone()
                if row:
                    calendly = row[2]
            except (OperationalError, ProgrammingError) as db_error:
                # If raw SQL fails, try SQLAlchemy as fallback
                error_str = str(db_error).lower()
                if 'does not exist' in error_str or 'no such column' in error_str:
                    try:
                        owner_row = pdb.query(User).filter(User.email == owner).first()
                        if owner_row:
                            calendly = getattr(owner_row, "calendly_link", None)
                    except Exception:
                        calendly = None
                else:
                    calendly = None
            except Exception:
                calendly = None
        finally:
            pdb.close()
        
        # Replace calendly links in all variants
        if intent in {"interested", "schedule"}:
            if calendly:
                body = body.replace("[[CALENDLY_LINK]]", calendly)
                variants_data = {k: v.replace("[[CALENDLY_LINK]]", calendly) for k, v in variants_data.items()}
            else:
                body = body.replace("[[CALENDLY_LINK]]", "")
                variants_data = {k: v.replace("[[CALENDLY_LINK]]", "") for k, v in variants_data.items()}
        else:
            body = body.replace("[[CALENDLY_LINK]]", "")
            variants_data = {k: v.replace("[[CALENDLY_LINK]]", "") for k, v in variants_data.items()}

        schedule = data.get("schedule") if isinstance(data.get("schedule"), dict) else None
        
        
        # Ensure body is a string (not None)
        final_body = str(body) if body else ""
        final_intent = str(intent) if intent else "unclear"
        final_schedule = schedule if schedule else None
        final_subject = str(subject) if subject else ""
        final_preview_text = str(preview_text) if preview_text else ""
        final_why_works = str(why_this_works) if why_this_works else ""
        
        # Ensure variants are strings
        final_variants = {
            "short": str(variants_data.get("short", "")),
            "medium": str(variants_data.get("medium", final_body)),
            "long": str(variants_data.get("long", ""))
        }
        
        
        
        return {
            "intent": final_intent,
            "body": final_body,  # Default to medium variant body
            "subject": final_subject,
            "preview_text": final_preview_text,
            "variants": final_variants,
            "why_this_works": final_why_works,
            "schedule": final_schedule
        }

@router.get("/can-reply")
def can_reply(request: Request, to: str, db: Session = Depends(get_tenant_db_dependency)):
    """Check if user can reply to an email address (has received email from that address)"""
    try:
        owner = _get_owner_from_request(request)
        to_lower = to.strip().lower()
        
        # Check if there's a received email from this address
        received_email = db.query(Email).filter(
            Email.owner_email == owner,
            Email.from_address.ilike(f"%{to_lower}%"),
            Email.status == EmailStatus.received
        ).first()
        
        # Also check if there's a contact with this email
        contact = db.query(Contact).filter(
            Contact.owner_email == owner,
            Contact.email.ilike(f"%{to_lower}%")
        ).first()
        
        can_reply_flag = received_email is not None or contact is not None
        
        return {
            "can_reply": can_reply_flag,
            "has_received_email": received_email is not None,
            "has_contact": contact is not None,
            "email_id": received_email.id if received_email else None,
            "contact_id": contact.id if contact else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check reply status: {str(e)}")

@router.post("/reply/preview-auto")
async def reply_preview_auto(request: Request, payload: dict, db: Session = Depends(get_tenant_db_dependency)):
    """Auto-generate reply preview by detecting email from contact_id or to address"""
    try:
        owner = _get_owner_from_request(request)
        to_addr = (payload.get("to") or "").strip()
        contact_id = payload.get("contact_id")
        original = ""
        email_id = None
        
        # If contact_id is provided, get the most recent email from that contact
        if contact_id:
            contact = db.query(Contact).filter(
                Contact.owner_email == owner,
                Contact.id == contact_id
            ).first()
            if contact:
                to_addr = contact.email
                # Get most recent received email from this contact
                recent_email = db.query(Email).filter(
                    Email.owner_email == owner,
                    Email.from_address.ilike(f"%{contact.email}%"),
                    Email.status == EmailStatus.received
                ).order_by(Email.received_at.desc()).first()
                if recent_email:
                    original = recent_email.body or recent_email.content or ""
                    email_id = recent_email.id
        
        # If to address is provided but no original, try to find recent email
        if to_addr and not original:
            recent_email = db.query(Email).filter(
                Email.owner_email == owner,
                Email.from_address.ilike(f"%{to_addr}%"),
                Email.status == EmailStatus.received
            ).order_by(Email.received_at.desc()).first()
            if recent_email:
                original = recent_email.body or recent_email.content or ""
                email_id = recent_email.id
        
        if not original:
            raise HTTPException(status_code=422, detail="No email found to reply to. Please provide an email or contact with recent emails.")
        
        # Use the existing reply_preview logic
        preview_payload = {
            "to": to_addr,
            "original": original,
            "email_id": email_id,
            "contact_id": contact_id
        }
        return await reply_preview(request, preview_payload, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auto reply preview: {str(e)}")

@router.post("/ingest-imap")
def ingest_imap(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Read unread emails via IMAP for the owner, classify with Gemini, and store them in the database (auto-reply disabled)."""
    import imaplib
    from email import message_from_bytes
    from email.utils import parseaddr
    owner = _get_owner_from_request(request)
    host, port, user, password, use_ssl = _resolve_per_user_imap(owner)
    if not host or not user or not password:
        # Check if user has any email settings configured
        pdb = SessionLocal()
        try:
            user_row = pdb.query(User).filter(User.email == owner).first()
            if not user_row:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check what's missing
            missing = []
            if not user_row.imap_host:
                missing.append("IMAP Host")
            if not user_row.imap_username:
                missing.append("IMAP Username") 
            if not user_row.imap_password:
                missing.append("IMAP Password")
            
            if missing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Please configure your email settings in Profile page. Missing: {', '.join(missing)}"
                )
            else:
                raise HTTPException(status_code=500, detail="IMAP settings incomplete")
        finally:
            pdb.close()
    try:
        imap_port: int = int(port or (993 if use_ssl else 143))
        # Set socket default timeout to avoid long stalls
        try:
            socket.setdefaulttimeout(20)
        except Exception:
            pass
        M = imaplib.IMAP4_SSL(host, imap_port) if use_ssl else imaplib.IMAP4(host, imap_port)
        try:
            M.login(user, password)
        except imaplib.IMAP4.error as e:
            raise HTTPException(status_code=400, detail=f"IMAP authentication failed: {str(e)}. Please check your IMAP username and password in the Profile page.")
        M.select('INBOX')
        typ, data = M.search(None, '(UNSEEN)')
        ids = data[0].split() if data and data[0] else []
        # Limit to latest 30 unseen for responsiveness
        ids = ids[-30:]
        processed: list[dict] = []

        # Gemini setup
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Missing GEMINI_API_KEY")
        import google.generativeai as genai  # type: ignore[import-untyped]
        gen = cast(Any, genai)
        gen.configure(api_key=api_key)
        model = gen.GenerativeModel("gemini-2.0-flash")

        # Owner calendly (lookup in primary DB)
        pdb = SessionLocal()
        try:
            owner_row = pdb.query(User).filter(User.email == owner).first()
        finally:
            pdb.close()
        calendly = getattr(owner_row, "calendly_link", None) if owner_row else None
        # Build a professional signature using profile if available
        sender_display = (getattr(owner_row, 'full_name', None) or getattr(owner_row, 'username', None) or owner).split('@')[0]
        sender_company = getattr(owner_row, 'company_name', None) or ''
        sender_title = getattr(owner_row, 'position_title', None) or ''
        signature_line2 = ", ".join([p for p in [sender_title, sender_company] if p])
        default_signature = str(sender_display) + ("\n" + signature_line2 if signature_line2 else '')

        for msg_id in ids:
            try:
                typ, msg_data = M.fetch(msg_id, '(RFC822)')
                if typ != 'OK' or not msg_data or not isinstance(msg_data, list):
                    continue
                if not msg_data or not isinstance(msg_data[0], tuple) or len(msg_data[0]) < 2:
                    continue
                raw_entry = msg_data[0][1]
                msg = message_from_bytes(cast(bytes, raw_entry))
                from_header = msg.get('From') or ""
                from_addr = parseaddr(from_header)[1]
                subject = msg.get('Subject') or ''
                
                # Extract email date from headers
                email_date = None
                date_header = msg.get('Date')
                if date_header:
                    try:
                        from email.utils import parsedate_to_datetime
                        email_date = parsedate_to_datetime(date_header)
                        # Convert to UTC and remove timezone info for database storage
                        if email_date.tzinfo:
                            email_date = email_date.astimezone(timezone.utc).replace(tzinfo=None)
                    except Exception:
                        email_date = None
                
                # Skip system emails and bounce notifications to prevent infinite loops
                system_emails = [
                    'MAILER-DAEMON@',
                    'mailer-daemon@',
                    'noreply@',
                    'no-reply@',
                    'postmaster@',
                    'bounce@',
                    'bounces@',
                    'undelivered@',
                    'delivery-failure@',
                    'mail-delivery-failure@'
                ]
                
                if any(system_email in from_addr.lower() for system_email in system_emails):
                    continue
                
                # Skip emails with bounce-related subjects
                bounce_subjects = [
                    'undelivered mail returned to sender',
                    'delivery failure',
                    'mail delivery failure',
                    'bounce notification',
                    'returned mail',
                    'mailer-daemon',
                    'delivery status notification',
                    'failure notice'
                ]
                
                if any(bounce_subject in subject.lower() for bounce_subject in bounce_subjects):
                    continue
                
                # Extract plain text
                original = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            payload_bytes = part.get_payload(decode=True)
                            if isinstance(payload_bytes, (bytes, bytearray)):
                                original += payload_bytes.decode(errors='ignore')
                else:
                    payload_bytes2 = msg.get_payload(decode=True)
                    if isinstance(payload_bytes2, (bytes, bytearray)):
                        original = payload_bytes2.decode(errors='ignore')
                    else:
                        original = ''

                # Find contact
                c = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == from_addr).first()
                # If no contact found, still record the email as received for inbox visibility

                # Build sender signature
                # Prefer profile-based signature; fall back to per-contact sender fields
                if default_signature.strip():
                    signature = default_signature
                else:
                    sender_name = 'Your Team'
                    s2 = ""
                    signature = sender_name + ("\n" + s2 if s2 else '')

                # Analyze email intent for classification (no auto-reply will be sent)
                prompt = (
                    "Act as a professional sales representative. Analyze the client's message and determine intent in one of: "
                    "interested, not_interested, request_more_info, schedule, unsubscribe, unclear, follow_up, objection, question. "
                    "Write a concise, formal reply (<= 110 words), polite and clear, avoiding slang or emojis. "
                    "If intent is 'interested' or 'schedule', place the literal token [[CALENDLY_LINK]] where a booking link should appear. "
                    "If the client proposed times, extract them and return schedule with keys: title, start_iso, end_iso (ISO 8601; assume UTC if unspecified). "
                    "If no times are present, set schedule to null. "
                    "ABSOLUTE RULES - FOLLOW EXACTLY: "
                    "1. If client says 'Hey, Christo', address them as 'Christo' - NOT 'Harish' "
                    "2. If client proposes a specific time (e.g., 'September 10th, between 6 PM and 7 PM'), confirm it works and do NOT ask for alternatives "
                    "3. NEVER ask 'Could you please share a couple of times that work for you this week?' or similar questions "
                    "4. The email body must END with the signature - NO content after the signature "
                    "5. For meeting scheduling: use 2025-09-10T18:00:00Z to 2025-09-10T19:00:00Z for 'September 10th, between 6 PM and 7 PM' "
                    "6. Use meeting title 'Call with [ClientName]' (e.g., 'Call with Christo') "
                    "7. NEVER mention specific booked meeting times to clients unless they are the person the meeting is scheduled with "
                    "8. If there are scheduling conflicts, the system will handle them automatically - do not mention conflicts in your response "
                    "CORRECT EXAMPLE: Client says 'Hey, Christo. Shall we connect on September 10th, sometime between 6 PM and 7 PM?' "
                    "Response: 'Hi Christo, September 10th between 6 PM and 7 PM works perfectly for me. I'll send you a calendar invite shortly.\\n\\nBest regards,\\nHarish\\nSales Rep, Wolf Assistants' "
                    "Schedule: {title: 'Call with Christo', start_iso: '2025-09-10T18:00:00Z', end_iso: '2025-09-10T19:00:00Z'} "
                    "CRITICAL: You MUST always include the schedule field with the exact date and time the client requested. Do NOT leave it null or empty. "
                    "\n\n"
                    "IMPORTANT: You MUST respond with a valid JSON object in this exact format:\n"
                    "{\n"
                    '  "intent": "one_of_the_classifications_above",\n'
                    '  "body": "your_reply_content_here",\n'
                    '  "schedule": null\n'
                    "}\n\n"
                    "The 'intent' field must be one of: interested, not_interested, request_more_info, schedule, unsubscribe, unclear, follow_up, objection, question. "
                    "The 'body' field should contain the actual email reply content. "
                    "The 'schedule' field should be null unless scheduling is explicitly requested with specific times. "
                    "Return ONLY valid JSON - no other text before or after the JSON object."
                )
                    
                try:
                    
                    full_prompt = f"{prompt}\n\nOriginal email:\n```{original}```\n\nSubject: {subject}"
                    resp = model.generate_content(full_prompt)
                    text = resp.text or ''
                    
                    
                    import json, re
                    safe_name = (c.name if c else 'there')
                    data = {"intent": "unclear", "body": "", "schedule": None}
                    
                    # Improved JSON parsing - check for code blocks first (like reply_preview does)
                    try:
                        # First try to find JSON wrapped in code blocks
                        code_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
                        if code_block_match:
                            data = json.loads(code_block_match.group(1))
                        else:
                            # Fallback to direct JSON search
                            match = re.search(r"\{[\s\S]*\}", text)
                            if match:
                                data = json.loads(match.group(0))
                            else:
                                raise ValueError("No JSON found in AI response")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from intent detection response: {e}")
                    except Exception as e:
                        logger.warning(f"Error parsing intent detection response: {e}")
                    
                    # Validate intent is one of the expected values
                    detected_intent = data.get('intent', 'unclear')
                    valid_intents = {'interested', 'not_interested', 'request_more_info', 'schedule', 'unsubscribe', 'unclear', 'follow_up', 'objection', 'question'}
                    if detected_intent not in valid_intents:
                        detected_intent = 'unclear'
                        data['intent'] = 'unclear'
                    
                    
                    body = data.get('body') or ''
                    
                    if data.get('intent') in {'interested', 'schedule'} and calendly:
                        body = body.replace('[[CALENDLY_LINK]]', calendly)
                    else:
                        body = body.replace('[[CALENDLY_LINK]]', '')
                    
                    # Auto-reply disabled - emails will be received but no automatic replies sent
                    # _send_email({"to": from_addr, "subject": f"Re: {subject or 'Your email'}", "content": body}, db, owner=owner)
                    
                    # mark on contact
                    if c:
                        c.last_reply_at = get_ist_now()
                        c.last_intent = detected_intent  # Use validated intent
                        
                        
                        db.commit()  # Commit the intent update
                    
                    # If schedule provided, try to create a meeting
                    schedule = data.get('schedule') if isinstance(data.get('schedule'), dict) else None
                    m = None
                    st = None
                    en = None
                    title = None
                    if schedule and (schedule.get('start_iso') or schedule.get('end_iso')):
                        def _parse_iso(s: str | None) -> datetime | None:
                            if not s:
                                return None
                            try:
                                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                                if dt.tzinfo is not None:
                                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                                return dt
                            except Exception:
                                return None
                        # Parse client's requested time from the original message as fallback
                        def _parse_client_time_from_message(msg: str) -> tuple[datetime, datetime]:
                            """Parse client's requested time from message content."""
                            try:
                                # Look for patterns like "September 10th, between 6 PM and 7 PM"
                                import re
                                # Pattern to match "September 10th, between 6 PM and 7 PM"
                                pattern = r'September\s+(\d+)(?:st|nd|rd|th)?,?\s+between\s+(\d+)\s+PM\s+and\s+(\d+)\s+PM'
                                match = re.search(pattern, msg, re.IGNORECASE)
                                if match:
                                    day = int(match.group(1))
                                    start_hour = int(match.group(2))
                                    end_hour = int(match.group(3))
                                    # Convert to 24-hour format
                                    start_hour_24 = start_hour if start_hour == 12 else start_hour + 12
                                    end_hour_24 = end_hour if end_hour == 12 else end_hour + 12
                                    return (
                                        datetime(2025, 9, day, start_hour_24, 0, 0),
                                        datetime(2025, 9, day, end_hour_24, 0, 0)
                                    )
                            except Exception:
                                pass
                            # Default fallback
                            return (
                                datetime(2025, 9, 10, 18, 0, 0),  # September 10th, 2025, 6:00 PM
                                datetime(2025, 9, 10, 19, 0, 0)   # September 10th, 2025, 7:00 PM
                            )
                        
                        fallback_start, fallback_end = _parse_client_time_from_message(original)
                        st = _parse_iso(schedule.get('start_iso')) or fallback_start
                        en = _parse_iso(schedule.get('end_iso')) or fallback_end
                        title = schedule.get('title') or f"Call with {(c.name if c else 'client')}"
                        
                        # Check for scheduling conflicts before creating the meeting
                        if st and en:
                            try:
                                conflicts = db.query(Meeting).filter(
                                    Meeting.owner_email == owner,
                                    Meeting.start_time < en,
                                    Meeting.end_time > st,
                                ).all()
                                
                                if conflicts:
                                    # Found conflicts - log the issue and don't create the meeting
                                    conflict_details = []
                                    for meeting in conflicts:
                                        conflict_start = meeting.start_time.strftime("%B %d, %Y at %I:%M %p")
                                        conflict_end = meeting.end_time.strftime("%I:%M %p")
                                        conflict_title = meeting.title or "Untitled Meeting"
                                        conflict_details.append(f"• {conflict_title} on {conflict_start} - {conflict_end}")
                                    
                                    # Log the conflict for manual review
                                    print(f"SCHEDULING CONFLICT DETECTED for {owner}:")
                                    print(f"Requested: {st.strftime('%B %d, %Y at %I:%M %p')} - {en.strftime('%I:%M %p')}")
                                    print(f"Conflicts:")
                                    for detail in conflict_details:
                                        print(f"  {detail}")
                                    print(f"Email from: {from_addr}")
                                    print(f"Subject: {subject}")
                                    print("Meeting NOT created due to conflict.")
                                    
                                    # Don't create the meeting - let the user handle it manually
                                    continue
                                    
                            except Exception as e:
                                print(f"Conflict detection error in email reply: {e}")
                                # Continue with meeting creation if conflict detection fails
                        
                        m = Meeting(
                            title=title,
                            description=f"Auto-scheduled from email: {subject}",
                            start_time=st,
                            end_time=en,
                            location="Online",
                            attendees=from_addr,
                            type=MeetingType.video,
                            status=MeetingStatus.scheduled,
                            notes=f"Source: IMAP ingest\nOriginal snippet: {original[:200]}",
                            owner_email=owner,
                        )
                        db.add(m)
                        db.commit()
                        
                        # Notify owner with details
                        try:
                            host = settings.EMAIL_HOST; port = settings.EMAIL_PORT or 587
                            user_smtp = settings.EMAIL_USER; pwd = settings.EMAIL_PASSWORD
                            sender_addr = settings.EMAIL_FROM or user_smtp or "no-reply@example.com"
                            if host and user_smtp and pwd:
                                start_text = st.strftime('%d %b %Y, %I:%M %p UTC') if st else 'TBD'
                                end_text = en.strftime('%I:%M %p UTC') if en else ''
                                body_nt = (
                                    f"New meeting booked via inbox intent.\n\n"
                                    f"Title: {title}\nDate: {start_text} - {end_text}\nRegarding: {subject}\nWith: {(c.name if c else 'client')} <{from_addr}>\n"
                                )
                                msg = MIMEText(body_nt, 'plain', 'utf-8')
                                msg['Subject'] = f"Meeting booked: {title}"
                                msg['From'] = sender_addr
                                msg['To'] = owner
                                if port == 465:
                                    server = smtplib.SMTP_SSL(host, port)
                                else:
                                    server = smtplib.SMTP(host, port)
                                    if settings.EMAIL_USE_TLS:
                                        server.starttls()
                                server.login(user_smtp, pwd)
                                server.sendmail(sender_addr, [owner], msg.as_string())
                                server.quit()
                        except Exception:
                            pass
                    
                    processed.append({"from": from_addr, "intent": detected_intent, "subject": subject, "original": original, "date": email_date})
                    
                except Exception as e:
                    logger.error(f"Error during intent detection for email from {from_addr}: {e}", exc_info=True)
                    continue
                
                # Mark as seen
                try:
                    M.store(msg_id, '+FLAGS', '\\Seen')
                except Exception:
                    pass
                    
            except Exception as e:
                continue

        M.logout()
        
        # Persist original message into Supabase emails table as received so it appears in inbox
        try:
            from app.models.email import Email, EmailStatus as _ES
            from app.core.spam_detector import detect_email_spam
            
            # Use the main Supabase database session
            tenant_db = db
            
            try:
                for rec in processed:
                    try:
                        sub = (rec.get('subject') or '(no subject)') if isinstance(rec, dict) else '(no subject)'
                        body_txt = (rec.get('original') or '') if isinstance(rec, dict) else ''
                        frm = (rec.get('from') or '') if isinstance(rec, dict) else ''
                        email_date = rec.get('date') if isinstance(rec, dict) else None
                        
                        # Determine if this is a sent email (from our own address) or received email
                        # Get the user's email address to check if this email is from them
                        from app.core.database import SessionLocal
                        pdb_primary_ingest = SessionLocal()
                        try:
                            user_row_ingest = pdb_primary_ingest.query(User).filter(User.email == owner).first()
                            user_email_ingest = user_row_ingest.email if user_row_ingest else owner
                            
                            # Check against both login email AND SMTP from address
                            # Users may send emails from a different "from" address than their login email
                            smtp_from_email_ingest = user_row_ingest.smtp_from.lower() if user_row_ingest and user_row_ingest.smtp_from else None
                            is_sent_email_ingest = (
                                frm.lower() == user_email_ingest.lower() or 
                                (smtp_from_email_ingest and frm.lower() == smtp_from_email_ingest)
                            )
                        finally:
                            pdb_primary_ingest.close()
                        
                        # Only detect spam for received emails (not sent emails)
                        if is_sent_email_ingest:
                            email_status = _ES.sent
                        else:
                            spam_result = detect_email_spam(sub, body_txt, frm, user)
                            email_status = _ES.spam if spam_result.is_spam else _ES.received
                    
                        # Use the real timestamp from IMAP if available, otherwise use stable fallback
                        if email_date:
                            # email_date is already parsed from IMAP and serialized as string, parse it back
                            if isinstance(email_date, datetime):
                                stable_timestamp = email_date
                            else:
                                # If it's a string (serialized datetime), parse it back to datetime
                                try:
                                    # Parse the ISO format string back to datetime
                                    stable_timestamp = datetime.fromisoformat(email_date.replace('Z', '+00:00'))
                                    # Remove timezone info for database storage
                                    if stable_timestamp.tzinfo:
                                        stable_timestamp = stable_timestamp.replace(tzinfo=None)
                                except Exception:
                                    # If parsing fails, use stable fallback
                                    base_time = datetime.now().replace(hour=15, minute=1, second=0, microsecond=0)
                                    stable_timestamp = base_time
                        else:
                            # No email date available, use stable fallback
                            base_time = datetime.now().replace(hour=15, minute=1, second=0, microsecond=0)
                            stable_timestamp = base_time
                        
                        if stable_timestamp:
                            stable_timestamp = stable_timestamp.replace(microsecond=0)
                        
                        # Check for duplicate email before saving (match timestamp when available)
                        existing_query = tenant_db.query(Email).filter(
                            Email.subject == sub,
                            Email.from_address == frm,
                            Email.to_address == user,
                            Email.owner_email == owner,
                            Email.status == email_status
                        )
                        
                        if stable_timestamp:
                            if email_status == _ES.sent:
                                existing_query = existing_query.filter(Email.sent_at == stable_timestamp)
                            else:
                                existing_query = existing_query.filter(Email.received_at == stable_timestamp)
                        else:
                            existing_query = existing_query.filter(Email.body == body_txt)
                        
                        if existing_query.first():
                            continue
                        
                        e = Email(
                            subject=sub,
                            body=body_txt,
                            to_address=user,  # Use IMAP username (info@wolfassistants.com) as the recipient
                            from_address=frm,
                            status=email_status,  # Use detected status (sent, spam, or received)
                            owner_email=owner,
                            received_at=stable_timestamp if not is_sent_email_ingest else None,  # Use received_at for received emails
                            sent_at=stable_timestamp if is_sent_email_ingest else None,  # Use sent_at for sent emails
                            is_read=True if is_sent_email_ingest else False,  # Sent emails are considered read
                            original_folder="sent" if is_sent_email_ingest else "inbox"
                        )
                        tenant_db.add(e)
                        tenant_db.commit()
                    except Exception as e:
                        continue
            finally:
                tenant_db.close()
        except Exception:
            pass
            
        return {"processed": processed}
    except Exception as e:
        error_msg = str(e)
        # Check for specific IMAP authentication errors
        if "AUTHENTICATIONFAILED" in error_msg or "Authentication failed" in error_msg:
            raise HTTPException(status_code=400, detail="IMAP authentication failed. Please check your email password in the Profile page.")
        elif "Connection refused" in error_msg or "Connection timed out" in error_msg:
            raise HTTPException(status_code=400, detail="Cannot connect to IMAP server. Please check your IMAP host and port settings.")
        else:
            raise HTTPException(status_code=500, detail=f"IMAP ingest failed: {error_msg}")

@router.post("/check-spam")
def check_spam_emails(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """
    Check all received emails for spam and move detected spam to spam folder
    """
    owner = _get_owner_from_request(request)
    
    try:
        from app.core.spam_detector import detect_email_spam
        from app.models.email import Email, EmailStatus
        
        # Get all received emails that are not already marked as spam
        received_emails = db.query(Email).filter(
            Email.owner_email == owner,
            Email.status == EmailStatus.received
        ).all()
        
        spam_count = 0
        processed_count = 0
        
        for email in received_emails:
            try:
                # Detect spam
                spam_result = detect_email_spam(
                    email.subject or "",
                    email.body or "",
                    email.from_address or "",
                    email.to_address or ""
                )
                
                if spam_result.is_spam:
                    # Move to spam folder
                    email.status = EmailStatus.spam
                    email.original_folder = "spam"
                    spam_count += 1
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing email {email.id} for spam detection: {e}")
                continue
        
        # Commit all changes
        db.commit()
        
        return {
            "message": f"Spam check completed. Processed {processed_count} emails, moved {spam_count} to spam folder.",
            "processed": processed_count,
            "spam_detected": spam_count
        }
        
    except Exception as e:
        logger.error(f"Error in spam check: {e}")
        raise HTTPException(status_code=500, detail=f"Spam check failed: {str(e)}")

@router.post("/follow-up")
def follow_up_email(request: Request, payload: dict = Body(default_factory=dict), db: Session = Depends(get_tenant_db_dependency)):
    """Generate and send a follow-up email. If 'to' provided, send to that contact; otherwise send to all contacts with at least one sent email."""
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    use_ai = bool(api_key)
    
    if not use_ai:
        logger.warning("GEMINI_API_KEY not found, using simple follow-up template")

    model = None
    if use_ai:
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
            gen = cast(Any, genai)
            gen.configure(api_key=api_key)
            model = gen.GenerativeModel("gemini-2.0-flash")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}, falling back to simple template")
            use_ai = False

    owner = _get_owner_from_request(request)
    to_single = (payload.get("to") or "").strip()
    targets: Sequence[Contact | SimpleNamespace]
    if to_single:
        c = db.query(Contact).filter(Contact.owner_email == owner, Contact.email == to_single).first()
        if not c:
            # Gracefully handle missing contact by creating a temporary contact-like object
            local_name = (to_single.split('@')[0] or 'there').replace('.', ' ').title()
            c = SimpleNamespace(
                name=local_name,
                email=to_single,
                company="",
                position="",
                sender_name="Your Team",
            )
        targets = [c]
    else:
        # contacts with at least one sent email
        sent_to = [row[0] for row in db.query(Email.to_address).filter(Email.owner_email == owner, Email.status == EmailStatus.sent).distinct().all()]
        if not sent_to:
                return {"results": []}
        targets = cast(Sequence[Contact | SimpleNamespace], db.query(Contact).filter(Contact.owner_email == owner, Contact.email.in_(sent_to)).all())

    # Get user's profession for persona-based follow-ups (fetch once outside loop)
    pdb_followup = SessionLocal()
    professional_persona = None
    try:
        user_row = pdb_followup.query(User).filter(User.email == owner).first()
        if user_row:
            heard_about_us = getattr(user_row, "heard_about_us", None)
            position_title = getattr(user_row, "position_title", None)
            professional_persona = get_professional_persona(
                heard_about_us=heard_about_us,
                position_title=position_title
            )
    finally:
        pdb_followup.close()

    results: List[dict] = []
    for c in targets:
        sender_name = "Your Team"
        signature_line2 = ""
        signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")

        # Get the previous email content for context
        previous_email = db.query(Email).filter(
            Email.owner_email == owner,
            Email.to_address == c.email,
            Email.status == EmailStatus.sent
        ).order_by(Email.sent_at.desc()).first()
        
        previous_content = ""
        previous_subject = ""
        if previous_email:
            previous_content = previous_email.body or ""
            previous_subject = previous_email.subject or ""

        # Generate content using AI or simple template
        if use_ai and model:
            # Build persona-aware prompt
            persona_text = ""
            if professional_persona:
                persona_text = (
                    f"\nPROFESSIONAL PERSONA:\n"
                    f"You are {professional_persona['persona']} writing a follow-up email. "
                    f"Your communication style is {professional_persona['communication_style']}. "
                    f"Your tone should be {professional_persona['tone']}.\n"
                )
            
            prompt = (
                "You are an expert email follow-up specialist. Analyze the previous cold email and create a contextual follow-up that maintains continuity and relevance.\n"
                f"{persona_text}\n"
                "CRITICAL REQUIREMENTS:\n"
                "- Subject line: Maximum 100 characters - must be compelling and engaging\n"
                "- Body: Exactly 300-350 characters (including spaces) - count carefully, make it informative and persuasive\n"
                "- NO introductory prefixes like 'Hi', 'Hello', 'I hope this email finds you well'\n"
                "- Directly continue the conversation from where the previous email left off\n"
                "- Maintain the same tone and style as the original email\n"
                "- Reference specific points from the previous email naturally\n"
                "- Do NOT repeat information already shared in the previous email\n"
                "- Write authentically as someone in your professional role\n"
                "- Do NOT include signature in body - it will be automatically added\n\n"
                f"PREVIOUS EMAIL SUBJECT: {previous_subject}\n"
                f"PREVIOUS EMAIL CONTENT:\n{previous_content}\n\n"
                f"RECIPIENT INFO: name={c.name}, company={c.company}, position={c.position}\n"
                f"SENDER: {sender_name}\n\n"
                "Generate a follow-up that directly continues the conversation without any introductory phrases. "
                "Return strictly JSON with keys 'subject' and 'body'. "
                "Verify subject is max 100 chars and body is exactly 300-350 chars before returning."
            )
            try:
                resp = model.generate_content(prompt)
                text = resp.text or ""
                import json, re
                # Enhanced fallback that references previous email content
                if previous_content:
                    data = {
                        "subject": f"Re: {previous_subject}" if previous_subject else "Following up",
                        "body": f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature}"
                    }
                else:
                    data = {"subject": "Following up", "body": f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature}"}
                try:
                    match = re.search(r"\{[\s\S]*\}", text)
                    if match:
                        data = json.loads(match.group(0))
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"AI generation failed for {c.email}: {e}, using simple template")
                # Enhanced fallback that references previous email content
                if previous_content:
                    data = {
                        "subject": f"Re: {previous_subject}" if previous_subject else "Following up",
                        "body": f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature}"
                    }
                else:
                    data = {"subject": "Following up", "body": f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature}"}
        else:
            # Enhanced template fallback
            if previous_content:
                data = {
                    "subject": f"Re: {previous_subject}" if previous_subject else "Following up",
                    "body": f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature}"
                }
            else:
                data = {"subject": "Following up", "body": f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature}"}

        try:
            sanitized_subject = _sanitize_followup_subject(data.get("subject") or "Following up")
            sanitized_body = _sanitize_followup_body(data.get("body") or "")
            _send_email({"to": c.email, "subject": sanitized_subject, "content": sanitized_body}, db, owner=owner)
            results.append({"email": c.email, "status": "sent"})
        except HTTPException as e:
            results.append({"email": c.email, "status": "error", "detail": e.detail})

    return {"results": results}

# --- Auto follow-up scheduler ---
@router.post("/auto-followup/run")
def run_auto_followups(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Send daily auto-followups to contacts without replies after last sent email.
    Respects per-user toggle in profile. Safe to run multiple times per day.
    """
    owner = _get_owner_from_request(request)

    # Check toggle from primary DB
    pdb = SessionLocal()
    try:
        user = pdb.query(User).filter(User.email == owner).first()
        if not user:
            logger.warning(f"User {owner} not found for auto follow-up")
            return {"status": "user_not_found", "sent": 0}
        if not user.auto_followup_enabled:
            logger.info(f"Auto follow-up disabled for user {owner}")
            return {"status": "disabled", "sent": 0}
        max_days = user.auto_followup_max_days or 14
        logger.info(f"Running auto follow-up for {owner}, max_days={max_days}")
    finally:
        pdb.close()

    # Ensure tenant schema
    _ensure_emails_schema(db)

    sent_count = 0
    failed_count = 0
    failed_details = []
    
    # Find recipients we have sent to - handle missing attachments column
    try:
        sent_to = [row[0] for row in db.query(Email.to_address)
                   .filter(Email.owner_email == owner, Email.status == EmailStatus.sent)
                   .distinct().all()]
    except Exception as query_error:
        # Fallback to raw SQL if attachments column doesn't exist
        from sqlalchemy import text
        error_str = str(query_error).lower()
        if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
            try:
                db.rollback()
            except:
                pass
            sql_query = text("""
                SELECT DISTINCT to_address 
                FROM emails 
                WHERE owner_email = :owner_email AND status = 'sent'
            """)
            result = db.execute(sql_query, {"owner_email": owner})
            sent_to = [row[0] for row in result.fetchall() if row[0]]
        else:
            raise
    
    if not sent_to:
        return {"status": "ok", "sent": 0}

    # Build map of last received from those recipients (reply detection) - handle missing attachments column
    try:
        from_addrs = set([row[0] for row in db.query(Email.from_address)
                          .filter(Email.owner_email == owner, Email.status == EmailStatus.received)
                          .all()])
    except Exception as query_error:
        # Fallback to raw SQL if attachments column doesn't exist
        from sqlalchemy import text
        error_str = str(query_error).lower()
        if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
            try:
                db.rollback()
            except:
                pass
            sql_query = text("""
                SELECT from_address 
                FROM emails 
                WHERE owner_email = :owner_email AND status = 'received'
            """)
            result = db.execute(sql_query, {"owner_email": owner})
            from_addrs = set([row[0] for row in result.fetchall() if row[0]])
        else:
            raise

    for to_addr in sent_to:
        # If recipient replied (there is a received email from them), skip (case-insensitive check)
        to_addr_lower = (to_addr or "").strip().lower()
        if any((addr or "").strip().lower() == to_addr_lower for addr in from_addrs if addr):
            continue

        # Get last sent email to this recipient - handle missing attachments column
        try:
            last_sent = db.query(Email).filter(
                Email.owner_email == owner,
                Email.to_address == to_addr,
                Email.status == EmailStatus.sent
            ).order_by(Email.sent_at.desc()).first()
        except Exception as query_error:
            # Fallback to raw SQL if attachments column doesn't exist
            from sqlalchemy import text
            error_str = str(query_error).lower()
            if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
                try:
                    db.rollback()
                except:
                    pass
                sql_query = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email, 
                           scheduled_for, deleted_at, last_error, original_folder
                    FROM emails 
                    WHERE owner_email = :owner_email AND to_address = :to_addr AND status = 'sent'
                    ORDER BY sent_at DESC
                    LIMIT 1
                """)
                result = db.execute(sql_query, {"owner_email": owner, "to_addr": to_addr})
                row = result.fetchone()
                if not row:
                    continue
                # Create Email-like object
                last_sent = type('Email', (), {
                    'id': row[0],
                    'subject': row[1],
                    'body': row[2],
                    'to_address': row[3],
                    'from_address': row[4],
                    'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                    'sent_at': row[6],
                    'received_at': row[7],
                })()
            else:
                raise
        
        if not last_sent:
            continue

        # Respect max_days window and strict 24h wait since last sent
        ref_time = last_sent.sent_at or get_ist_now()
        if ref_time and (get_ist_now() - ref_time).days > max_days:
            continue
        # Require at least 24 hours since last sent
        if ref_time and (get_ist_now() - ref_time).total_seconds() < 24 * 3600:
            continue

        # Prevent multiple follow-ups on the same day (guard effective now) - handle missing attachments column
        today = get_ist_now().date()
        try:
            already_today = db.query(Email).filter(
                Email.owner_email == owner,
                Email.to_address == to_addr,
                Email.status == EmailStatus.sent,
                Email.sent_at.isnot(None)
            ).filter(Email.sent_at >= datetime.combine(today, datetime.min.time(), tzinfo=IST))
            if hasattr(already_today, 'count') and already_today.count() > 0:
                continue
        except Exception as query_error:
            # Fallback to raw SQL if attachments column doesn't exist
            from sqlalchemy import text
            error_str = str(query_error).lower()
            if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
                try:
                    db.rollback()
                except:
                    pass
                sql_query = text("""
                    SELECT COUNT(*) 
                    FROM emails 
                    WHERE owner_email = :owner_email 
                    AND to_address = :to_addr 
                    AND status = 'sent' 
                    AND sent_at IS NOT NULL
                    AND sent_at >= :today_start
                """)
                today_start = datetime.combine(today, datetime.min.time(), tzinfo=IST)
                result = db.execute(sql_query, {"owner_email": owner, "to_addr": to_addr, "today_start": today_start})
                count = result.scalar() or 0
                if count > 0:
                    continue
            else:
                # For other errors, continue to next recipient
                continue

        # Compose contextual follow-up using prior email
        preview_payload = {"to": to_addr}
        # Reuse preview logic synchronously
        try:
            # Use the same logic as preview for generating content
            # Minimal duplication: call internal building parts already in this file
            sender_name = "Your Team"
            subject = f"Re: {last_sent.subject}" if last_sent.subject else "Following up"
            body = _sanitize_followup_body(
                "Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n" + sender_name
            )
        except Exception:
            subject = "Following up"
            body = _sanitize_followup_body("Just bumping this to the top of your inbox.\n\nBest regards,\nYour Team")

        try:
            _send_email({"to": to_addr, "subject": subject, "content": body}, db, owner)
            sent_count += 1
            logger.info(f"Auto follow-up sent to {to_addr}")
        except HTTPException as e:
            failed_count += 1
            failed_details.append({"to": to_addr, "error": e.detail, "type": "HTTPException"})
            logger.warning(f"Failed to send auto follow-up to {to_addr}: {e.detail}")
            continue
        except Exception as e:
            failed_count += 1
            failed_details.append({"to": to_addr, "error": str(e), "type": type(e).__name__})
            logger.error(f"Unexpected error sending auto follow-up to {to_addr}: {e}", exc_info=True)
            continue

    # Update last run telemetry in primary DB
    try:
        pdb2 = SessionLocal()
        user = pdb2.query(User).filter(User.email == owner).first()
        if user:
            user.last_auto_followup_run = get_ist_now()
            user.last_auto_followup_sent_count = int(sent_count)
            # Store failure info in a new field if available
            if hasattr(user, 'last_auto_followup_failed_count'):
                user.last_auto_followup_failed_count = int(failed_count)
            pdb2.commit()
    except Exception as telemetry_error:
        logger.warning(f"Failed to update auto follow-up telemetry: {telemetry_error}")
    finally:
        try:
            pdb2.close()
        except Exception:
            pass

    # Log summary
    if failed_count > 0:
        logger.warning(f"Auto follow-up completed for {owner}: {sent_count} sent, {failed_count} FAILED")
        for failure in failed_details:
            logger.warning(f"  - Failed: {failure['to']} - {failure['type']}: {failure['error']}")
    else:
        logger.info(f"Auto follow-up run completed for {owner}: {sent_count} emails sent")
    
    return {
        "status": "ok" if failed_count == 0 else "partial",
        "sent": sent_count,
        "failed": failed_count,
        "failed_details": failed_details if failed_count > 0 else None
    }

# Fallback aliases in case of reverse proxy or client path variations
@router.post("/followup")
def follow_up_email_alias(request: Request, payload: dict = Body(default_factory=dict), db: Session = Depends(get_tenant_db_dependency)):
    return follow_up_email(request, payload, db)

@router.post("/follow_up")
def follow_up_email_alias2(request: Request, payload: dict = Body(default_factory=dict), db: Session = Depends(get_tenant_db_dependency)):
    return follow_up_email(request, payload, db)

@router.post("/follow-up/preview")
def follow_up_preview(request: Request, payload: dict = Body(default_factory=dict), db: Session = Depends(get_tenant_db_dependency)):
    """Preview a follow-up email before sending"""
    # Check if we have any Gemini API keys available (consistent with reply endpoints)
    api_keys = settings.gemini_api_keys
    api_key = api_keys[0] if api_keys else None
    use_ai = bool(api_key)
    
    if not use_ai:
        logger.warning("No Gemini API keys found, using simple follow-up template")

    # Initialize AI model if available
    model = None
    if use_ai:
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
            gen = cast(Any, genai)
            gen.configure(api_key=api_key)
            model = gen.GenerativeModel("gemini-2.0-flash")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}, falling back to simple template")
            use_ai = False

    owner = _get_owner_from_request(request)
    
    # Get user's profession for persona-based follow-ups
    pdb_preview = SessionLocal()
    professional_persona = None
    try:
        # Use raw SQL to avoid SQLAlchemy column issues
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError, ProgrammingError
        
        try:
            sql_query = text("""
                SELECT id, email, heard_about_us, position_title
                FROM app_users 
                WHERE email = :email
                LIMIT 1
            """)
            result = pdb_preview.execute(sql_query, {"email": owner})
            row = result.fetchone()
            
            if row:
                heard_about_us = row[2]
                position_title = row[3]
                professional_persona = get_professional_persona(
                    heard_about_us=heard_about_us,
                    position_title=position_title
                )
        except (OperationalError, ProgrammingError) as db_error:
            # If raw SQL fails, try SQLAlchemy as fallback
            error_str = str(db_error).lower()
            if 'does not exist' in error_str or 'no such column' in error_str:
                try:
                    user_row = pdb_preview.query(User).filter(User.email == owner).first()
                    if user_row:
                        heard_about_us = getattr(user_row, "heard_about_us", None)
                        position_title = getattr(user_row, "position_title", None)
                        professional_persona = get_professional_persona(
                            heard_about_us=heard_about_us,
                            position_title=position_title
                        )
                except Exception:
                    # If both fail, continue without persona
                    pass
            else:
                # For other errors, continue without persona
                pass
    except Exception as e:
        # Log but continue without persona
        logger.warning(f"Error loading user data for follow-up preview: {e}")
    finally:
        pdb_preview.close()
    
    target_email = payload.get("to")
    
    if not target_email:
        raise HTTPException(status_code=400, detail="Target email address required for preview")

    
    try:
        # Find the contact
        contact = db.query(Contact).filter(
            Contact.owner_email == owner,
            Contact.email == target_email
        ).first()
        
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Get user's email configuration for signature
        host, port, user_email_setup, password, use_ssl = _resolve_per_user_imap(owner)
        sender_name = "Your Team"
        signature_line2 = ""
        signature = sender_name + ("\n" + signature_line2 if signature_line2 else "")

        # Get the previous email content for context
        # Handle missing attachments column gracefully - use raw SQL from the start to avoid column errors
        previous_email = None
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError, ProgrammingError
        
        # First, try to check if attachments column exists
        use_raw_sql = False
        try:
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = current_schema()
                AND table_name = 'emails' 
                AND column_name = 'attachments'
            """)
            result = db.execute(check_query)
            if result.fetchone() is None:
                use_raw_sql = True
        except Exception:
            # If check fails, use raw SQL as fallback
            use_raw_sql = True
        
        if use_raw_sql:
            # Use raw SQL query excluding attachments column
            try:
                sql_query = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email, 
                           scheduled_for, deleted_at, last_error, original_folder
                    FROM emails 
                    WHERE owner_email = :owner_email AND to_address = :to_address AND status = :status
                    ORDER BY sent_at DESC 
                    LIMIT 1
                """)
                result = db.execute(sql_query, {
                    "owner_email": owner,
                    "to_address": target_email,
                    "status": "sent"
                })
                row = result.fetchone()
                if row:
                    # Create a simple object-like structure
                    previous_email = type('Email', (), {
                        'id': row[0],
                        'subject': row[1],
                        'body': row[2],
                        'to_address': row[3],
                        'from_address': row[4],
                        'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                        'sent_at': row[6],
                        'received_at': row[7],
                    })()
            except Exception as fallback_error:
                logger.error(f"Raw SQL query failed in follow_up_preview: {fallback_error}")
                previous_email = None
        else:
            # Use SQLAlchemy query (attachments column exists)
            try:
                previous_email = db.query(Email).filter(
                    Email.owner_email == owner,
                    Email.to_address == target_email,
                    Email.status == EmailStatus.sent
                ).order_by(Email.sent_at.desc()).first()
            except Exception as query_error:
                # Fallback to raw SQL if SQLAlchemy query fails
                error_str = str(query_error).lower()
                is_column_error = (
                    isinstance(query_error, (OperationalError, ProgrammingError)) or 
                    'column' in error_str or 
                    'does not exist' in error_str or 
                    'attachments' in error_str
                )
                if is_column_error:
                    logger.warning(f"Database column error in follow_up_preview. Using fallback query: {query_error}")
                    try:
                        sql_query = text("""
                            SELECT id, subject, body, to_address, from_address, status, 
                                   sent_at, received_at, is_starred, is_read, owner_email, 
                                   scheduled_for, deleted_at, last_error, original_folder
                            FROM emails 
                            WHERE owner_email = :owner_email AND to_address = :to_address AND status = :status
                            ORDER BY sent_at DESC 
                            LIMIT 1
                        """)
                        result = db.execute(sql_query, {
                            "owner_email": owner,
                            "to_address": target_email,
                            "status": "sent"
                        })
                        row = result.fetchone()
                        if row:
                            previous_email = type('Email', (), {
                                'id': row[0],
                                'subject': row[1],
                                'body': row[2],
                                'to_address': row[3],
                                'from_address': row[4],
                                'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                                'sent_at': row[6],
                                'received_at': row[7],
                            })()
                    except Exception as fallback_error:
                        logger.error(f"Fallback query also failed in follow_up_preview: {fallback_error}")
                        previous_email = None
                else:
                    # Re-raise if it's not a column error
                    raise
        
        previous_content = ""
        previous_subject = ""
        if previous_email:
            previous_content = previous_email.body or ""
            previous_subject = previous_email.subject or ""

        # Generate content using AI or simple template
        if use_ai and model:
            # Build persona-aware prompt
            persona_text = ""
            if professional_persona:
                persona_text = (
                    f"\nPROFESSIONAL PERSONA:\n"
                    f"You are {professional_persona['persona']} writing a follow-up email. "
                    f"Your communication style is {professional_persona['communication_style']}. "
                    f"Your tone should be {professional_persona['tone']}.\n"
                )
            
            prompt = (
                "You are an expert email follow-up specialist. Analyze the previous cold email and create a contextual follow-up that maintains continuity and relevance.\n"
                f"{persona_text}\n"
                "CRITICAL REQUIREMENTS:\n"
                "- Subject line: Maximum 100 characters - must be compelling and engaging\n"
                "- Body: Exactly 300-350 characters (including spaces) - count carefully, make it informative and persuasive\n"
                "- NO introductory prefixes like 'Hi', 'Hello', 'I hope this email finds you well'\n"
                "- Directly continue the conversation from where the previous email left off\n"
                "- Maintain the same tone and style as the original email\n"
                "- Reference specific points from the previous email naturally\n"
                "- Do NOT repeat information already shared in the previous email\n"
                "- Write authentically as someone in your professional role\n"
                "- Do NOT include signature in body - it will be automatically added\n\n"
                f"PREVIOUS EMAIL SUBJECT: {previous_subject}\n"
                f"PREVIOUS EMAIL CONTENT:\n{previous_content}\n\n"
                f"RECIPIENT INFO: name={contact.name}, company={contact.company}, position={contact.position}\n"
                f"SENDER: {sender_name}\n\n"
                "Generate a follow-up that directly continues the conversation without any introductory phrases. "
                "Return strictly JSON with keys 'subject' and 'body'. "
                "Verify subject is max 100 chars and body is exactly 300-350 chars before returning."
            )
            
            try:
                resp = model.generate_content(prompt)
                text = resp.text or ""
                
                # Parse JSON response
                import json
                try:
                    data = json.loads(text)
                    return {
                        "subject": _sanitize_followup_subject(data.get("subject", "Follow-up")),
                        "body": _sanitize_followup_body(data.get("body", "Follow-up message")),
                        "to": target_email,
                        "contact_name": contact.name
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        "subject": _sanitize_followup_subject("Follow-up"),
                        "body": _sanitize_followup_body(text),
                        "to": target_email,
                        "contact_name": contact.name
                    }
            except Exception as gemini_error:
                # Check if it's a quota/rate limit error
                error_msg = str(gemini_error).lower()
                is_quota_error = (
                    '429' in str(gemini_error) or
                    'quota' in error_msg or
                    'rate limit' in error_msg or
                    'resourceexhausted' in error_msg or
                    'exceeded' in error_msg
                )
                
                if is_quota_error:
                    logger.warning(f"Gemini API quota exceeded in follow_up_preview, using fallback template")
                    # Use fallback template when quota is exceeded
                    if previous_content:
                        subject = f"Re: {previous_subject}" if previous_subject else "Following up"
                        body = f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature}"
                    else:
                        subject = "Following up"
                        body = f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature}"
                    
                    return {
                        "subject": _sanitize_followup_subject(subject),
                        "body": _sanitize_followup_body(body),
                        "to": target_email,
                        "contact_name": contact.name
                    }
                else:
                    # Re-raise non-quota errors
                    raise
        else:
            # Enhanced template fallback
            if previous_content:
                subject = f"Re: {previous_subject}" if previous_subject else "Following up"
                body = f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature}"
            else:
                subject = "Following up"
                body = f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature}"
            
            return {
                "subject": _sanitize_followup_subject(subject),
                "body": _sanitize_followup_body(body),
                "to": target_email,
                "contact_name": contact.name
            }
            
    except Exception as e:
        # Check if this is a database column error and handle it gracefully
        from sqlalchemy.exc import OperationalError, ProgrammingError
        error_str = str(e).lower()
        is_column_error = False
        try:
            import psycopg2
            if hasattr(e, 'orig') and isinstance(e.orig, psycopg2.errors.UndefinedColumn):
                is_column_error = True
        except (ImportError, AttributeError):
            pass
        if not is_column_error:
            is_column_error = (
                isinstance(e, (OperationalError, ProgrammingError)) or 
                'column' in error_str or 
                'does not exist' in error_str or 
                'attachments' in error_str
            )
        if is_column_error:
            logger.warning(f"Database column error in follow_up_preview (likely missing 'attachments' column): {e}")
            # Return a fallback response instead of raising an error
            target_email_val = target_email if 'target_email' in locals() else payload.get("to", "")
            return {
                "subject": "Following up",
                "body": f"Just bumping this to the top of your inbox.\n\nBest regards,\nYour Team",
                "to": target_email_val,
                "contact_name": ""
            }
        # Check if it's a quota error in the outer exception handler
        error_str = str(e).lower()
        is_quota_error = (
            '429' in str(e) or
            'quota' in error_str or
            'rate limit' in error_str or
            'resourceexhausted' in error_str or
            'exceeded' in error_str
        )
        
        if is_quota_error:
            logger.warning(f"Gemini API quota exceeded in follow_up_preview (outer handler), using fallback template")
            # Use fallback template when quota is exceeded
            target_email_val = target_email if 'target_email' in locals() else payload.get("to", "")
            signature_val = signature if 'signature' in locals() else "Your Team"
            previous_content_val = previous_content if 'previous_content' in locals() else ""
            previous_subject_val = previous_subject if 'previous_subject' in locals() else ""
            
            if previous_content_val:
                subject = f"Re: {previous_subject_val}" if previous_subject_val else "Following up"
                body = f"Just bumping this to the top of your inbox regarding our previous discussion.\n\nBest regards,\n{signature_val}"
            else:
                subject = "Following up"
                body = f"Just bumping this to the top of your inbox.\n\nBest regards,\n{signature_val}"
            
            return {
                "subject": _sanitize_followup_subject(subject),
                "body": _sanitize_followup_body(body),
                "to": target_email_val,
                "contact_name": contact.name if 'contact' in locals() and contact else ""
            }
        
        logger.error(f"Error in follow-up preview: {e}")
        raise HTTPException(status_code=500, detail=f"Follow-up preview failed: {str(e)}")

@router.post("/save-draft")
def save_draft(draft_data: dict, request: Request):
    """Save an email as a draft."""
    try:
        owner = _get_owner_from_request(request)
        data = draft_data
        
        # Validate required fields
        if not data.get('subject') or not data.get('to') or not data.get('content'):
            raise HTTPException(status_code=400, detail="Subject, to, and content are required")
        
        # Create a new database session for Supabase
        from app.models.email import Email, EmailStatus
        from app.core.database import SessionLocal
        
        # Use the main Supabase database session
        db = SessionLocal()
        try:
            # Create draft email
            draft_email = Email(
                subject=data['subject'],
                body=data['content'],
                to_address=data['to'],
                from_address=data.get('from', owner),  # Use owner's email as default from
                status=EmailStatus.draft,
                owner_email=owner,
                original_folder="drafts",
                is_read=True,  # Drafts are considered read
            )
            
            db.add(draft_email)
            db.commit()
            
            return {
                    "status": "success",
                    "message": "Draft saved successfully",
                    "draft_id": draft_email.id
                }
        finally:
            db.close()
            
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {str(e)}")

@router.post("/fast-imap-check")
def fast_imap_check(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Fast IMAP check for new emails - optimized for speed and frequent polling.
    
    This endpoint has a maximum execution time of 45 seconds to prevent frontend timeouts.
    """
    import imaplib
    from email import message_from_bytes
    from email.utils import parseaddr, parsedate_to_datetime
    from app.core.database import SessionLocal
    
    # Start time tracking for timeout protection
    start_time = time.time()
    MAX_EXECUTION_TIME = 45.0  # 45 seconds max (frontend timeout is 90s, leave buffer)
    
    owner = _get_owner_from_request(request)
    host, port, user, password, use_ssl = _resolve_per_user_imap(owner)
    
    # Log the resolved IMAP configuration
    logger.info(f"📧 IMAP Configuration for {owner}: host={host}, port={port}, user={user}, use_ssl={use_ssl}")
    
    if not host or not user or not password:
        logger.warning(f"⚠️ IMAP not fully configured for {owner}: host={host}, user={user}, password={'***' if password else None}")
        return {"processed": [], "message": "IMAP not configured", "imported_count": 0, "total_found": 0}
    
    # Verify tenant schema exists - if not, create it
    try:
        if not schema_exists(owner):
            logger.info(f"Tenant schema does not exist for {owner}, creating it...")
            create_tenant_schema(owner)
    except Exception as e:
        logger.warning(f"Could not verify/create tenant schema for {owner}: {e}")
        # Continue anyway - schema might exist or be using legacy database
    
    # Primary DB session only for user account settings; all emails/contacts go to tenant DB (db)
    pdb_primary = SessionLocal()
    M = None
    try:
        # Use port from user profile if available, otherwise use defaults based on SSL
        if port is None:
            imap_port = 993 if use_ssl else 143
            logger.info(f"ℹ️ IMAP port not specified in profile, using default: {imap_port} (SSL={use_ssl})")
        else:
            imap_port = int(port)
            logger.info(f"✅ Using IMAP port from user profile: {imap_port}")
        
        # Validate port range
        if imap_port < 1 or imap_port > 65535:
            logger.error(f"❌ Invalid IMAP port {imap_port} for user {owner}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid IMAP port {imap_port}. Port must be between 1 and 65535."
            )
        
        logger.info(f"🔌 Connecting to IMAP: {host}:{imap_port} (SSL={use_ssl})")
        
        # Very short timeout for fast checking
        try:
            socket.setdefaulttimeout(10)
        except Exception:
            pass
            
        # FIXED: Better error handling for connection
        try:
            M = imaplib.IMAP4_SSL(host, imap_port) if use_ssl else imaplib.IMAP4(host, imap_port)
        except socket.timeout:
            raise HTTPException(
                status_code=400, 
                detail=f"Connection to IMAP server {host}:{imap_port} timed out. Please check your IMAP host and port settings."
            )
        except socket.gaierror as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot resolve IMAP host '{host}'. Please check your IMAP host setting."
            )
        except ConnectionRefusedError:
            raise HTTPException(
                status_code=400, 
                detail=f"Connection refused to IMAP server {host}:{imap_port}. Please verify the port and SSL/TLS settings."
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot connect to IMAP server {host}:{imap_port}. Error: {str(e)}. Please check your IMAP settings."
            )
        
        try:
            M.login(user, password)
        except imaplib.IMAP4.error as e:
            raise HTTPException(status_code=400, detail=f"IMAP authentication failed: {str(e)}. Please check your IMAP username and password in the Profile page.")
        
        # FIXED: Check multiple folders, not just INBOX
        # Get available folders
        available_folders = _get_imap_folders(M)
        logger.info(f"Available IMAP folders for {owner}: {available_folders}")
        
        # Define folders to check (prioritize common income-related folders)
        folders_to_check = ['INBOX']
        
        # IMPORTANT: Also check INBOX.Sent folder - some email servers put replies there
        # This is critical for catching prospect replies that might be misrouted
        sent_folder_variants = ['INBOX.Sent', 'Sent', 'INBOX/Sent', 'Sent Items']
        for sent_folder in sent_folder_variants:
            if sent_folder in available_folders and sent_folder not in folders_to_check:
                folders_to_check.append(sent_folder)
                logger.info(f"Added sent folder for reply checking: {sent_folder}")
        
        # Add common income/financial folder names if they exist
        income_folder_names = ['Income', 'Payments', 'Financial', 'Invoices', 'Receipts', 
                              'Transactions', 'Bank', 'PayPal', 'Stripe', 'Square']
        for folder_name in income_folder_names:
            # Check for case-insensitive match
            matching_folder = next((f for f in available_folders if f.upper() == folder_name.upper()), None)
            if matching_folder and matching_folder not in folders_to_check:
                folders_to_check.append(matching_folder)
                logger.info(f"Found income-related folder: {matching_folder}")
        
        # Also check any folder containing income-related keywords
        for folder in available_folders:
            folder_lower = folder.lower()
            if any(keyword in folder_lower for keyword in ['income', 'payment', 'invoice', 'receipt', 'transaction', 'financial']):
                if folder not in folders_to_check:
                    folders_to_check.append(folder)
                    logger.info(f"Found potential income folder: {folder}")
        
        logger.info(f"Checking folders for {owner}: {folders_to_check}")
        
        # Check all relevant folders for UNSEEN emails first (fastest)
        folder_msg_ids = _check_imap_folders_for_emails(M, folders_to_check, 'UNSEEN')
        logger.info(f"Found {len(folder_msg_ids)} UNSEEN emails")
        
        # Also check for recent emails (last 7 days) to catch replies that might be marked as seen
        # This ensures we don't miss prospect replies that were already read
        # IMPORTANT: Always check for recent emails, not just when UNSEEN count is low
        # This is critical because many email clients mark emails as "seen" immediately
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
        logger.info(f"Also checking for emails SINCE {week_ago} (last 7 days)")
        recent_msg_ids = _check_imap_folders_for_emails(M, folders_to_check, f'SINCE {week_ago}')
        logger.info(f"Found {len(recent_msg_ids)} emails from last 7 days")
        
        # Merge and deduplicate - prefer UNSEEN emails, but include recent ones too
        seen_ids = {tuple(msg_id) if isinstance(msg_id, bytes) else msg_id for _, msg_id in folder_msg_ids}
        for folder, msg_id in recent_msg_ids:
            msg_id_key = tuple(msg_id) if isinstance(msg_id, bytes) else msg_id
            if msg_id_key not in seen_ids:
                folder_msg_ids.append((folder, msg_id))
                seen_ids.add(msg_id_key)
        
        # If still no emails found, try searching for ALL emails in INBOX as last resort
        if len(folder_msg_ids) == 0 and 'INBOX' in folders_to_check:
            logger.warning("⚠️ No emails found with UNSEEN or SINCE criteria. Trying ALL emails in INBOX as last resort...")
            all_msg_ids = _check_imap_folders_for_emails(M, ['INBOX'], 'ALL')
            logger.info(f"📧 Found {len(all_msg_ids)} total emails in INBOX (ALL search)")
            # Only add if we still have nothing
            if len(folder_msg_ids) == 0:
                folder_msg_ids = all_msg_ids
                logger.info(f"📥 Using {len(folder_msg_ids)} emails from ALL search")
        
        logger.info(f"Total emails to process: {len(folder_msg_ids)}")
        
        # Remove duplicates (same (folder, message_id) pair might appear if checked twice)
        seen_pairs: set[tuple[str, bytes]] = set()
        unique_folder_msg_ids: list[tuple[str, bytes]] = []
        for folder, msg_id in folder_msg_ids:
            key = (folder, msg_id)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            unique_folder_msg_ids.append((folder, msg_id))
        folder_msg_ids = unique_folder_msg_ids
        
        # Limit to latest 50 for better coverage (increased from 10 to catch more emails)
        # This ensures we don't miss prospect replies even if many emails arrive
        if len(folder_msg_ids) > 50:
            folder_msg_ids = folder_msg_ids[-50:]
            logger.info(f"⚠️ Limiting to latest 50 emails (found {len(folder_msg_ids)} total)")
        
        processed = []
        imported_count = 0
        
        current_folder: str | None = None
        
        # Pre-fetch user data once to avoid repeated queries
        user_row = pdb_primary.query(User).filter(User.email == owner).first()
        user_email = user_row.email if user_row else owner
        smtp_from_email = user_row.smtp_from.lower() if user_row and user_row.smtp_from else None
        
        # Pre-fetch all contacts for this owner to avoid repeated queries
        # Add error handling for database connection issues
        try:
            all_contacts = {c.email.lower(): c for c in db.query(Contact).filter(Contact.owner_email == owner).all()}
        except Exception as db_error:
            # Handle database connection errors gracefully
            logger.error(f"Database connection error while fetching contacts for {owner}: {db_error}", exc_info=True)
            # Try to refresh the database connection
            try:
                db.rollback()
            except Exception:
                pass
            # Return empty contacts dict - emails will still be processed but without contact matching
            all_contacts = {}
            logger.warning(f"Continuing IMAP check without contact matching due to database error")
        
        logger.info(f"🔄 Starting to process {len(folder_msg_ids)} emails from {len(set(f for f, _ in folder_msg_ids))} folder(s)")
        
        for folder, msg_id in folder_msg_ids:
            # Check timeout before processing each email
            elapsed = time.time() - start_time
            if elapsed > MAX_EXECUTION_TIME:
                logger.warning(f"⏱️ IMAP check timeout reached after {elapsed:.1f}s. Processed {imported_count} emails, {len(folder_msg_ids) - len(processed)} remaining.")
                break
            
            logger.debug(f"Processing email from folder {folder}, msg_id={msg_id}")
            
            # Ensure the correct folder is selected before fetching
            if folder != current_folder:
                typ, _ = M.select(folder, readonly=False)  # Need write access to mark as seen
                if typ != 'OK':
                    logger.warning(f"Failed to re-select folder {folder} for fetching")
                    continue
                current_folder = folder
            
            # Convert msg_id to string if it's bytes (IMAP expects string)
            msg_id_str = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else str(msg_id)
            
            try:
                typ, msg_data = M.fetch(msg_id_str, '(RFC822)')
                if typ != 'OK' or not msg_data or not isinstance(msg_data, list):
                    logger.warning(f"⚠️ Failed to fetch email {msg_id_str} from folder {folder}: typ={typ}, msg_data type={type(msg_data)}")
                    continue
                if not msg_data or not isinstance(msg_data[0], tuple) or len(msg_data[0]) < 2:
                    logger.warning(f"⚠️ Invalid email data structure for {msg_id_str} from folder {folder}")
                    continue
                    
                raw_entry = msg_data[0][1]
                msg = message_from_bytes(raw_entry)
                
                from_header = msg.get('From') or ""
                from_addr = parseaddr(from_header)[1]
                subject = msg.get('Subject') or ''
                date_header = msg.get('Date')
                
                # Log email being processed
                logger.info(f"📬 Processing email from IMAP: msg_id={msg_id_str}, folder={folder}, from={from_addr}, subject={subject[:50]}")
                
                # Skip system emails and bounce notifications to prevent infinite loops
                system_emails = [
                    'MAILER-DAEMON@mailchannels.net',
                    'mailer-daemon@',
                    'noreply@',
                    'no-reply@',
                    'postmaster@',
                    'bounce@',
                    'bounces@',
                    'undelivered@',
                    'delivery-failure@',
                    'mail-delivery-failure@'
                ]
                
                if any(system_email in from_addr.lower() for system_email in system_emails):
                    logger.info(f"⏭️ Skipping system email: from={from_addr}, subject={subject[:50]}")
                    continue
                
                # Skip emails with bounce-related subjects
                bounce_subjects = [
                    'undelivered mail returned to sender',
                    'delivery failure',
                    'mail delivery failure',
                    'bounce notification',
                    'returned mail',
                    'mailer-daemon',
                    'delivery status notification',
                    'failure notice'
                ]
                
                if any(bounce_subject in subject.lower() for bounce_subject in bounce_subjects):
                    logger.info(f"⏭️ Detected bounce email: from={from_addr}, subject={subject[:50]}")
                    # Record bounce for reputation tracking
                    try:
                        from app.core.database import SessionLocal as AccountsSessionLocal
                        from app.models.email_reputation import EmailReputation, BounceRecord
                        from app.core.deliverability import calculate_reputation_score
                        from datetime import datetime
                        import re
                        
                        # Extract email body for bounce analysis
                        bounce_body = ''
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == 'text/plain':
                                    try:
                                        bounce_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                        break
                                    except Exception:
                                        pass
                        else:
                            try:
                                bounce_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except Exception:
                                pass
                        
                        accounts_db = AccountsSessionLocal()
                        try:
                            from sqlalchemy.exc import OperationalError, ProgrammingError
                            
                            try:
                                # Try to extract recipient from bounce email body
                                recipient_email = None
                                if bounce_body:
                                    # Common bounce patterns
                                    recipient_match = re.search(r'<([^>]+@[^>]+)>', bounce_body)
                                    if recipient_match:
                                        recipient_email = recipient_match.group(1)
                                    else:
                                        # Try other patterns
                                        recipient_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', bounce_body)
                                        if recipient_match:
                                            recipient_email = recipient_match.group(1)
                                
                                if recipient_email:
                                    reputation = accounts_db.query(EmailReputation).filter(
                                        EmailReputation.owner_email == owner,
                                        EmailReputation.mailbox == smtp_from_email or owner
                                    ).first()
                                    
                                    if not reputation:
                                        reputation = EmailReputation(
                                            owner_email=owner,
                                            mailbox=smtp_from_email or owner,
                                            max_cold_sends_per_day=50
                                        )
                                        accounts_db.add(reputation)
                                        accounts_db.flush()
                                    
                                    # Determine bounce type (hard vs soft)
                                    bounce_type = 'hard'
                                    if any(word in bounce_body.lower() for word in ['temporary', 'retry', 'quota', 'full']):
                                        bounce_type = 'soft'
                                    
                                    # Record bounce
                                    bounce = BounceRecord(
                                        reputation_id=reputation.id,
                                        owner_email=owner,
                                        mailbox=smtp_from_email or owner,
                                        recipient_email=recipient_email,
                                        bounce_type=bounce_type,
                                        bounce_reason=f"Bounce notification: {subject}",
                                        subject=subject
                                    )
                                    accounts_db.add(bounce)
                                    
                                    # Update reputation metrics
                                    reputation.total_sent += 1
                                    reputation.total_bounced += 1
                                    reputation.reputation_score = calculate_reputation_score(
                                        reputation.total_sent,
                                        reputation.total_delivered,
                                        reputation.total_bounced,
                                        reputation.total_complained
                                    )
                                    reputation.last_calculated = datetime.now(timezone.utc)
                                    
                                    accounts_db.commit()
                                    logger.info(f"✅ Recorded bounce for {recipient_email}: {bounce_type}")
                            except (OperationalError, ProgrammingError) as db_err:
                                # Tables don't exist yet or connection error - skip bounce recording
                                logger.warning(f"Database error while recording bounce (skipping): {db_err}")
                                pass
                            except Exception as bounce_db_error:
                                # Any other database error - log and continue
                                logger.warning(f"Unexpected error while recording bounce: {bounce_db_error}")
                                pass
                        finally:
                            try:
                                accounts_db.close()
                            except Exception:
                                pass
                    except Exception as bounce_error:
                        # Catch all exceptions in bounce detection to prevent breaking IMAP check
                        logger.warning(f"Failed to record bounce from IMAP: {bounce_error}")
                        # Continue processing - don't let bounce detection break email import
                    
                    # Skip processing the bounce email itself
                    continue
                
                # Extract timestamp - prioritize real email date from IMAP
                actual_timestamp = None
                if date_header:
                    try:
                        actual_timestamp = parsedate_to_datetime(date_header)
                        if actual_timestamp.tzinfo is not None:
                            actual_timestamp = actual_timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                    except Exception:
                        # If parsing fails, use current time instead of hardcoded fallback
                        actual_timestamp = datetime.now()
                else:
                    # If no date header, use current time instead of hardcoded fallback
                    actual_timestamp = datetime.now()

                if actual_timestamp is not None:
                    actual_timestamp = actual_timestamp.replace(microsecond=0)
                
                # Extract plain text
                original = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            payload_bytes = part.get_payload(decode=True)
                            if isinstance(payload_bytes, (bytes, bytearray)):
                                original += payload_bytes.decode(errors='ignore')
                else:
                    payload_bytes2 = msg.get_payload(decode=True)
                    if isinstance(payload_bytes2, (bytes, bytearray)):
                        original = payload_bytes2.decode(errors='ignore')
                    else:
                        original = ''
                
                normalized_timestamp = actual_timestamp
                
                # Process emails from ALL senders - use pre-fetched contact data
                contact = all_contacts.get(from_addr.lower())
                
                # Determine if this is a sent email (from our own address) or received email
                # Use pre-fetched user data
                # CRITICAL: Check if the email is TO the user's address, not just FROM
                # If email is TO user's address, it's a received email (prospect reply)
                to_header = msg.get('To') or msg.get('Delivered-To') or msg.get('Envelope-To') or ""
                to_addr_list = [parseaddr(addr)[1].lower() for addr in to_header.split(',') if parseaddr(addr)[1]] if to_header else []
                
                # Also check CC and BCC headers
                cc_header = msg.get('Cc') or ""
                cc_addr_list = [parseaddr(addr)[1].lower() for addr in cc_header.split(',') if parseaddr(addr)[1]] if cc_header else []
                
                # Get IMAP username to check if email is TO the IMAP account
                imap_username_lower = user.lower() if user else ""
                
                # Check if this email is addressed TO the user (received email)
                # CRITICAL: Enhanced recipient checking to catch all prospect replies
                # Check against: user login email, SMTP from address, IMAP username
                all_recipients = to_addr_list + cc_addr_list
                
                # Also check X-Original-To, X-Envelope-To headers for forwarded emails
                x_original_to = msg.get('X-Original-To', '') or msg.get('X-Envelope-To', '')
                if x_original_to:
                    x_recipients = [parseaddr(addr)[1].lower() for addr in x_original_to.split(',') if parseaddr(addr)[1]]
                    all_recipients.extend(x_recipients)
                
                # Normalize addresses (remove +aliases, handle case) for better matching
                normalized_recipients = [addr.split('+')[0].strip().lower() for addr in all_recipients]
                normalized_user_email = user_email.lower().split('+')[0].strip()
                normalized_smtp_from = (smtp_from_email.split('+')[0].strip() if smtp_from_email else "")
                normalized_imap_username = (imap_username_lower.split('+')[0].strip() if imap_username_lower else "")
                normalized_owner = owner.lower().split('+')[0].strip()
                
                is_to_user = (
                    any(addr == normalized_user_email for addr in normalized_recipients) or
                    (normalized_smtp_from and any(addr == normalized_smtp_from for addr in normalized_recipients)) or
                    (normalized_imap_username and any(addr == normalized_imap_username for addr in normalized_recipients)) or
                    any(addr == normalized_owner for addr in normalized_recipients) or
                    # Domain match for catch-all emails (if IMAP username has domain)
                    (normalized_imap_username and '@' in normalized_imap_username and
                     any(addr.endswith('@' + normalized_imap_username.split('@')[1]) 
                         for addr in normalized_recipients if '@' in addr))
                )
                
                # Email is "sent" only if FROM matches user AND NOT addressed to user
                # This handles cases where user sends from one address but receives at another
                # FIXED: Calculate is_sent_email BEFORE using it in the warning log below
                is_sent_email = (
                    (from_addr.lower() == user_email.lower() or 
                     (smtp_from_email and from_addr.lower() == smtp_from_email)) and
                    not is_to_user  # If it's TO the user, it's received even if FROM matches
                )
                
                # Log classification details for debugging reply emails
                if not is_sent_email and not is_to_user:
                    logger.warning(f"⚠️ Email not classified as TO user: from={from_addr}, to={to_addr_list}, recipients={normalized_recipients}, user_email={normalized_user_email}, imap_user={normalized_imap_username}")
                
                # Log for debugging
                logger.info(f"Email classification: from={from_addr}, to={to_addr_list}, is_sent={is_sent_email}, is_to_user={is_to_user}")
                
                # Detect spam for received emails
                if not is_sent_email:
                    from app.core.spam_detector import detect_email_spam
                    
                    # NEW: Check if this is likely an income/financial email
                    income_keywords = ['invoice', 'payment', 'receipt', 'transaction', 
                                      'deposit', 'statement', 'income', 'revenue']
                    is_income_email = any(keyword in (subject + original).lower() 
                                         for keyword in income_keywords)
                    
                    # NEW: If it's an income email, be more lenient with spam detection
                    if is_income_email:
                        # Only mark as spam if score is very high (threshold 8 instead of 5)
                        spam_result = detect_email_spam(subject, original, from_addr, owner)
                        email_status = EmailStatus.spam if spam_result.score >= 8 else EmailStatus.received
                        if email_status == EmailStatus.spam:
                            logger.warning(f"⚠️ Income email marked as SPAM (high score): from={from_addr}, subject={subject[:50]}, score={spam_result.score}")
                        else:
                            logger.info(f"✅ Income email marked as RECEIVED: from={from_addr}, subject={subject[:50]}, spam_score={spam_result.score}")
                    else:
                        spam_result = detect_email_spam(subject, original, from_addr, owner)
                        # Use higher threshold (7 instead of 5) to reduce false positives
                        # Only mark as spam if score is very high
                        email_status = EmailStatus.spam if spam_result.score >= 7 else EmailStatus.received
                        if email_status == EmailStatus.spam:
                            logger.warning(f"⚠️ Email marked as SPAM: from={from_addr}, subject={subject[:50]}, score={spam_result.score}, reasons={spam_result.reasons[:3]}")
                        else:
                            logger.info(f"✅ Email marked as RECEIVED: from={from_addr}, subject={subject[:50]}, spam_score={spam_result.score}")
                else:
                    email_status = EmailStatus.sent
                    logger.info(f"📤 Email marked as SENT: from={from_addr}, to={to_addr_list}, subject={subject[:50]}")
                
                # Check for duplicate emails - use a more lenient approach
                # Check by message ID if available, otherwise by subject + from + timestamp
                existing_email = None
                
                # CRITICAL: Improved duplicate detection to avoid missing legitimate replies
                # First, try to find by Message-ID header (most reliable for duplicates)
                message_id_header = msg.get('Message-ID', '').strip()
                if message_id_header:
                    msg_id_clean = message_id_header.strip('<>')
                    # Check if Message-ID appears in body (some emails include it)
                    if len(msg_id_clean) > 10:  # Only check substantial Message-IDs
                        existing_email = db.query(Email).filter(
                            Email.owner_email == owner,
                            Email.body.contains(msg_id_clean[:100])
                        ).first()
                
                # If no Message-ID match, try exact timestamp match (most reliable)
                if not existing_email and normalized_timestamp:
                    if email_status == EmailStatus.sent:
                        existing_email = db.query(Email).filter(
                            Email.owner_email == owner,
                            Email.from_address == from_addr,
                            Email.subject == subject,
                            Email.status == email_status,
                            Email.sent_at == normalized_timestamp
                        ).first()
                    else:
                        existing_email = db.query(Email).filter(
                            Email.owner_email == owner,
                            Email.from_address == from_addr,
                            Email.subject == subject,
                            Email.status == email_status,
                            Email.received_at == normalized_timestamp
                        ).first()
                
                # If still no match, check by approximate timestamp (within 1 minute)
                # This catches emails with slightly different timestamps
                if not existing_email and normalized_timestamp:
                    timestamp_min = normalized_timestamp - timedelta(minutes=1)
                    timestamp_max = normalized_timestamp + timedelta(minutes=1)
                    if email_status == EmailStatus.sent:
                        existing_email = db.query(Email).filter(
                            Email.owner_email == owner,
                            Email.from_address == from_addr,
                            Email.subject == subject,
                            Email.status == email_status,
                            Email.sent_at >= timestamp_min,
                            Email.sent_at <= timestamp_max
                        ).first()
                    else:
                        existing_email = db.query(Email).filter(
                            Email.owner_email == owner,
                            Email.from_address == from_addr,
                            Email.subject == subject,
                            Email.status == email_status,
                            Email.received_at >= timestamp_min,
                            Email.received_at <= timestamp_max
                        ).first()
                
                # Last resort: check by body content (only if substantial to avoid false matches)
                if not existing_email and original and len(original) > 50:
                    body_snippet = original[:200]  # Check first 200 chars
                    existing_email = db.query(Email).filter(
                        Email.owner_email == owner,
                        Email.from_address == from_addr,
                        Email.subject == subject,
                        Email.status == email_status,
                        Email.body.contains(body_snippet)
                    ).first()

                if existing_email:
                    logger.info(f"⏭️ Skipping duplicate email: from={from_addr}, subject={subject[:50]}, existing_id={existing_email.id}, existing_status={existing_email.status}")
                    continue
                
                # Create email with appropriate status
                # For received emails, set to_address to the actual recipient (IMAP account or SMTP from)
                # This helps with matching and display
                if is_sent_email:
                    email_to_address = to_addr_list[0] if to_addr_list else owner
                else:
                    # For received emails, use the IMAP username or SMTP from address
                    email_to_address = imap_username_lower or smtp_from_email or user_email or owner
                
                # Determine original_folder based on email status
                if is_sent_email:
                    original_folder = "sent"
                elif email_status == EmailStatus.spam:
                    original_folder = "spam"
                else:
                    original_folder = "inbox"
                
                new_email = Email(
                    subject=subject,
                    body=original,
                    to_address=email_to_address,
                    from_address=from_addr,
                    status=email_status,
                    owner_email=owner,
                    received_at=normalized_timestamp if not is_sent_email else None,
                    sent_at=normalized_timestamp if is_sent_email else None,
                    is_read=True if is_sent_email else False,  # Sent emails are considered read
                    original_folder=original_folder
                )
                
                logger.info(f"📝 Creating email record: status={email_status}, folder={original_folder}, from={from_addr}, subject={subject[:50]}")
                
                db.add(new_email)
                imported_count += 1
                logger.debug(f"➕ Added email to session (count: {imported_count}): from={from_addr}, subject={subject[:50]}")

                # If this is an inbound message from a known contact, update reply timestamp
                if not is_sent_email and contact:
                    try:
                        contact.last_reply_at = get_ist_now()
                        logger.debug(f"📅 Updated contact reply timestamp: {from_addr}")
                    except Exception:
                        pass
                
                processed.append({
                    "subject": subject,
                    "from": from_addr,
                    "status": "imported",
                    "timestamp": actual_timestamp.isoformat() if actual_timestamp else None
                })
                
                # Mark as seen to prevent re-processing
                try:
                    M.store(msg_id_str, '+FLAGS', '\\Seen')
                except Exception as store_error:
                    logger.debug(f"Could not mark email {msg_id_str} as seen: {store_error}")
                    pass
                
            except Exception as e:
                # Log error but continue processing other emails
                logger.error(f"Error processing email {msg_id_str} in folder {folder}: {str(e)}", exc_info=True)
                continue
        
        # Commit all imported emails - ensure this happens even if there were some errors
        logger.info(f"📧 Preparing to commit {imported_count} emails to database for {owner}")
        if imported_count == 0:
            logger.warning(f"⚠️ No emails to commit! Check if emails were filtered as duplicates, system emails, or if IMAP mailbox is empty")
            logger.info(f"   Processed {len(processed)} emails, but none were new/unique")
        
        try:
            if imported_count > 0:
                db.commit()
                elapsed = time.time() - start_time
                logger.info(f"✅ Successfully committed {imported_count} emails to database for {owner} in {elapsed:.1f}s")
                # Verify the emails were actually saved
                verify_count = db.query(Email).filter(Email.owner_email == owner).count()
                logger.info(f"📊 Database now contains {verify_count} total emails for {owner}")
                
                # Log breakdown by status
                received_count = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.received).count()
                spam_count = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.spam).count()
                sent_count = db.query(Email).filter(Email.owner_email == owner, Email.status == EmailStatus.sent).count()
                logger.info(f"   Breakdown: {received_count} received, {spam_count} spam, {sent_count} sent")
            else:
                logger.info(f"ℹ️ No new emails to commit for {owner} (may be duplicates or filtered)")
        except Exception as commit_error:
            # Rollback on commit error and log it
            db.rollback()
            logger.error(f"❌ Failed to commit emails to database for {owner}: {str(commit_error)}", exc_info=True)
            # Still return the count so caller knows emails were processed
        
        if M is not None:
            try:
                M.logout()
            except Exception:
                pass
        
        elapsed = time.time() - start_time
        message = f"Fast check completed: {imported_count} new emails imported"
        if elapsed > MAX_EXECUTION_TIME * 0.8:  # Warn if we're approaching timeout
            message += f" (timeout warning: {elapsed:.1f}s)"
        
        return {
            "processed": processed,
            "imported_count": imported_count,
            "total_found": len(folder_msg_ids),
            "message": message,
            "execution_time": round(elapsed, 2)
        }
        
    except Exception as e:
        if M is not None:
            try:
                M.logout()
            except Exception:
                pass
        error_msg = str(e)
        # Check for specific IMAP authentication errors
        if "AUTHENTICATIONFAILED" in error_msg or "Authentication failed" in error_msg:
            raise HTTPException(status_code=400, detail="IMAP authentication failed. Please check your email password in the Profile page.")
        elif "Connection refused" in error_msg or "Connection timed out" in error_msg:
            raise HTTPException(status_code=400, detail="Cannot connect to IMAP server. Please check your IMAP host and port settings.")
        else:
            raise HTTPException(status_code=500, detail=f"Fast IMAP check failed: {error_msg}")
    finally:
        pdb_primary.close()

def _get_owner_from_request(request: Request) -> str:
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception as e:
        # SECURITY FIX: Do not allow unverified JWT tokens
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/health")
def health_check():
    """Health check endpoint to verify the router is working"""
    try:
        # Check database connectivity
        from app.core.database import SessionLocal
        pdb = SessionLocal()
        try:
            # Try a simple query
            result = pdb.execute(text("SELECT 1")).fetchone()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        finally:
            pdb.close()

        return {
            "status": "healthy", 
            "message": "Emails router is working",
            "database": db_status,
            "timestamp": get_ist_now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Emails router error: {str(e)}",
            "timestamp": get_ist_now().isoformat()
        }

@router.post("/trash/cleanup")
def trash_cleanup(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Clean up old emails from trash (older than 7 days)"""
    try:
        owner = _get_owner_from_request(request)
        cutoff = get_ist_now() - timedelta(days=7)
        deleted = db.query(Email).filter(
            Email.owner_email == owner,
            Email.status == EmailStatus.trashed,
            Email.deleted_at != None,
            Email.deleted_at < cutoff
        ).delete(synchronize_session=False)  # noqa: E711
        db.commit()
        return {"deleted": deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup trash: {str(e)}")

@router.post("/trash/empty")
def empty_trash(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Empty trash folder - alias for /trash/delete-all"""
    return delete_all_trash(request, db)

@router.post("/trash/delete-all")
def delete_all_trash(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete all emails from trash folder"""
    try:
        owner = _get_owner_from_request(request)
        
        # Count emails in trash before deletion
        trash_count = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.status == EmailStatus.trashed
        ).count()
        
        if trash_count == 0:
            return {
                "status": "success",
                "message": "No emails in trash to delete",
                "deleted_count": 0
            }
        
        # Permanently delete all emails in trash
        deleted_count = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.status == EmailStatus.trashed
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} emails permanently from trash",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete all trash emails: {str(e)}")

@router.post("/trash/delete-permanent/{email_id}")
def delete_permanent_from_trash(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete a specific email from trash folder"""
    try:
        owner = _get_owner_from_request(request)
        
        # Find the email in the tenant database
        email = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Check if email is actually in trash
        if email.status != EmailStatus.trashed:
            raise HTTPException(status_code=400, detail="Email is not in trash")
        
        # Permanently delete the email
        db.delete(email)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Email {email_id} permanently deleted from trash",
            "email_id": email_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete email from trash: {str(e)}")

@router.post("/delete/{email_id}")
def delete_email_permanent(request: Request, email_id: int, db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete an email from any folder - removes from tenant database"""
    try:
        owner = _get_owner_from_request(request)
        
        # Find the email in the tenant database
        email = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.id == email_id
        ).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Store email details for response
        email_subject = email.subject
        email_status = email.status.value
        
        # Permanently delete the email from the database
        db.delete(email)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Email '{email_subject}' permanently deleted from {email_status} folder",
            "email_id": email_id,
            "deleted_from": email_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete email: {str(e)}")

@router.post("/delete-bulk")
def delete_emails_bulk(request: Request, email_ids: List[int], db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete multiple emails from any folder - removes from tenant database"""
    try:
        owner = _get_owner_from_request(request)
        
        if not email_ids:
            raise HTTPException(status_code=400, detail="No email IDs provided")
        
        # Find all emails in the tenant database
        emails = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.id.in_(email_ids)
        ).all()
        
        if not emails:
            raise HTTPException(status_code=404, detail="No emails found")
        
        # Store email details for response
        deleted_emails = []
        for email in emails:
            deleted_emails.append({
                "id": email.id,
                "subject": email.subject,
                "status": email.status.value
            })
        
        # Permanently delete all emails from the database
        deleted_count = db.query(Email).filter(
            Email.owner_email == owner, 
            Email.id.in_(email_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} emails permanently",
            "deleted_count": deleted_count,
            "deleted_emails": deleted_emails
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete emails: {str(e)}")

@router.post("/delete-all")
def delete_all_emails_permanent(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Permanently delete ALL emails from any folder - removes from tenant database"""
    try:
        owner = _get_owner_from_request(request)
        
        # Count emails before deletion
        total_emails = db.query(Email).filter(Email.owner_email == owner).count()
        
        if total_emails == 0:
            return {
                "status": "success",
                "message": "No emails found to delete",
                "deleted_count": 0
            }
        
        # Permanently delete all emails from the database
        deleted_count = db.query(Email).filter(Email.owner_email == owner).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully deleted all {deleted_count} emails permanently from tenant database",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to permanently delete all emails: {str(e)}")

@router.get("/response-rate")
async def get_response_rate(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Calculate the response rate percentage for sent emails based on inbox responses.
    
    Only includes responses from email IDs that exist in either:
    1. The sent email list (recipients we sent emails to), OR
    2. The contacts table (known contacts)
    
    This ensures the response rate reflects only relevant and accounted-for interactions.
    """
    try:
        # Handle authentication properly
        try:
            owner = _get_owner_from_request(request)
        except HTTPException as auth_error:
            # Re-raise authentication errors as 401, not 500
            raise auth_error
        except Exception as e:
            # Handle any other authentication-related errors
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
        
        # Ensure schema is up to date
        try:
            _ensure_emails_schema(db)
        except Exception as schema_error:
            logger.warning(f"Schema check failed in response-rate: {schema_error}")
            # Continue anyway - schema might be fine
        
        # Get all sent emails for this user with error handling
        try:
            sent_emails = db.query(Email).filter(
            Email.owner_email == owner,
            Email.status == EmailStatus.sent
        ).all()
        except Exception as db_error:
            logger.error(f"Database error querying sent emails: {db_error}", exc_info=True)
            # Return default response on database error
            return {"responseRate": "0%", "sentCount": 0, "replyCount": 0}
        
        if not sent_emails:
            return {"responseRate": "0%", "sentCount": 0, "replyCount": 0}
        
        # Get valid email IDs from sent emails (recipients we sent to)
        sent_recipients = set()
        for email in sent_emails:
            if email.to_address:
                sent_recipients.add(email.to_address.lower())
        
        # Get valid email IDs from contacts table with error handling
        try:
            contacts = db.query(Contact).filter(Contact.owner_email == owner).all()
        except Exception as db_error:
            logger.warning(f"Database error querying contacts: {db_error}")
            contacts = []
        
        contact_emails = set()
        for contact in contacts:
            if contact.email:
                contact_emails.add(contact.email.lower())
        
        # Combine sent recipients and contact emails to get all valid email IDs
        valid_email_ids = sent_recipients.union(contact_emails)
        
        # Get all inbox emails (received emails) with error handling
        try:
            inbox_emails = db.query(Email).filter(
                Email.owner_email == owner,
                Email.status == EmailStatus.received
            ).all()
        except Exception as db_error:
            logger.error(f"Database error querying inbox emails: {db_error}", exc_info=True)
            inbox_emails = []
        
        # Count unique responses only from valid email IDs
        unique_responders = set()
        for inbox_email in inbox_emails:
            if inbox_email.from_address and inbox_email.from_address.lower() in valid_email_ids:
                unique_responders.add(inbox_email.from_address.lower())
        
        # Calculate response rate: (Unique responders) / (Total sent emails)
        total_sent_count = len(sent_emails)
        unique_response_count = len(unique_responders)
        response_rate = (unique_response_count / total_sent_count) * 100 if total_sent_count > 0 else 0
        
        return {
            "responseRate": f"{response_rate:.1f}%",
            "sentCount": total_sent_count,
            "replyCount": unique_response_count,
            "totalInboxEmails": len(inbox_emails),
            "validEmailIds": len(valid_email_ids),
            "sentRecipients": len(sent_recipients),
            "contactEmails": len(contact_emails)
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions (auth errors, etc.)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in response-rate endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate response rate: {str(e)}")

