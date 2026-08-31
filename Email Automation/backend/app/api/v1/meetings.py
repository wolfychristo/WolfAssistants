from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import datetime
from typing import cast

from app.core.database import get_db
from app.core.tenant_database import get_tenant_db_dependency
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingOut
from app.core.config import settings
from jose import jwt
from email.mime.text import MIMEText
import smtplib
from app.core.database import SessionLocal
from app.models.user import User
from app.models.contact import Contact
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy import text

router = APIRouter()

def _ensure_meetings_schema(db: Session) -> None:
    """Ensure required columns exist in meetings table for Supabase."""
    # No-op for Supabase - schema is managed by migrations
    pass


def _attendees_to_list(attendees_text: str | None) -> list[str]:
    if not attendees_text:
        return []
    return [x.strip() for x in attendees_text.split(',') if x.strip()]


# Internal helpers (hidden templates and SMTP profile resolution)
def _owner_profile(owner_email: str | None) -> dict[str, Any]:
    """Resolve display info and SMTP sender for an owner."""
    from app.core.config import settings as cfg
    profile: dict[str, Any] = {
        "name": "Admin",
        "company": None,
        "position": None,
        "smtp_host": cfg.EMAIL_HOST,
        "smtp_port": cfg.EMAIL_PORT or 587,
        "smtp_user": cfg.EMAIL_USER,
        "smtp_password": cfg.EMAIL_PASSWORD,
        "smtp_from": cfg.EMAIL_FROM or cfg.EMAIL_USER or "no-reply@example.com",
        "use_tls": cfg.EMAIL_USE_TLS,
    }
    if not owner_email:
        return profile
    pdb = SessionLocal()
    try:
        u = pdb.query(User).filter(User.email == owner_email).first()
        if u:
            profile["name"] = (u.full_name or u.username or u.email.split('@')[0]).strip()
            profile["company"] = (u.company_name or '').strip() or None
            profile["position"] = (getattr(u, 'position_title', '') or '').strip() or None
            if u.smtp_host and u.smtp_username and u.smtp_password:
                profile["smtp_host"] = u.smtp_host
                profile["smtp_port"] = u.smtp_port or profile["smtp_port"]
                profile["smtp_user"] = u.smtp_username
                profile["smtp_password"] = u.smtp_password
                profile["smtp_from"] = u.smtp_from or u.smtp_username
                profile["use_tls"] = True if u.smtp_use_tls is None else bool(u.smtp_use_tls)
    finally:
        pdb.close()
    return profile


def _compose_meeting_email(kind: str, meeting: Meeting, profile: dict, user_timezone: str = 'Asia/Kolkata') -> tuple[str, str]:
    """Return (subject, body) for kind in {'created','updated','deleted'}"""
    import pytz
    from datetime import datetime
    
    try:
        # Convert UTC time to user's timezone
        utc_time = meeting.start_time
        if utc_time.tzinfo is None:
            utc_time = pytz.UTC.localize(utc_time)
        
        user_tz = pytz.timezone(user_timezone)
        local_time = utc_time.astimezone(user_tz)
        start_text = local_time.strftime('%d %b %Y, %I:%M %p %Z')
    except Exception:
        start_text = str(meeting.start_time)
    
    try:
        if meeting.end_time is not None:
            # Convert UTC time to user's timezone
            utc_end_time = meeting.end_time
            if utc_end_time.tzinfo is None:
                utc_end_time = pytz.UTC.localize(utc_end_time)
            
            user_tz = pytz.timezone(user_timezone)
            local_end_time = utc_end_time.astimezone(user_tz)
            end_text = local_end_time.strftime('%I:%M %p %Z')
        else:
            end_text = ''
    except Exception:
        end_text = ''
    
    # Get organizer information
    who = profile.get("name") or "Admin"
    company = profile.get("company")
    position = profile.get("position")
    who_line = who
    if position and company:
        who_line = f"{who}, {position} at {company}"
    elif company:
        who_line = f"{who} at {company}"
    elif position:
        who_line = f"{who}, {position}"
    
    # Handle SQLAlchemy Column types properly
    meeting_location = meeting.location
    meeting_type = meeting.type
    meeting_title = meeting.title
    meeting_description = meeting.description
    meeting_notes = meeting.notes
    meeting_status = meeting.status
    meeting_attendees = meeting.attendees
    
    # Format meeting type
    type_display = meeting_type.value if meeting_type is not None else 'Meeting'
    
    # Format meeting status
    status_display = meeting_status.value if meeting_status is not None else 'Scheduled'
    
    # Format attendees
    attendees_list = []
    if meeting_attendees is not None:
        try:
            import json
            attendees_data = json.loads(meeting_attendees) if isinstance(meeting_attendees, str) else meeting_attendees
            if isinstance(attendees_data, list):
                attendees_list = attendees_data
        except Exception:
            attendees_list = [meeting_attendees] if meeting_attendees is not None else []
    
    # Get attendee name for greeting (first attendee or generic)
    attendee_name = "there"
    if attendees_list:
        first_attendee = attendees_list[0]
        # Try to extract name from email if it's an email address
        if isinstance(first_attendee, str) and '@' in first_attendee:
            attendee_name = first_attendee.split('@')[0].replace('.', ' ').title()
        else:
            attendee_name = str(first_attendee)
    
    # Format location with link if it's a URL
    location_display = meeting_location if meeting_location is not None else type_display
    if meeting_location is not None and ('http' in str(meeting_location).lower() or 'www.' in str(meeting_location).lower()):
        location_display = f"[{meeting_location}]({meeting_location})"
    
    link_text = f"\n[Meeting Link] {getattr(meeting, 'meeting_link', None)}" if getattr(meeting, 'meeting_link', None) else ''

    if kind == 'created':
        subject = f"Meeting Scheduled: {meeting_title}"
        intro = f"You have a meeting scheduled with {who_line} at {location_display}. Please find the details below:"
    elif kind == 'updated':
        subject = f"Updated Meeting: {meeting_title}"
        intro = f"The meeting details have been updated. Please find the new details below:"
    elif kind == 'deleted':
        subject = f"Meeting Cancelled: {meeting_title}"
        intro = f"The meeting has been cancelled."
    else:
        subject = meeting_title or "Meeting"
        intro = "Meeting notification"

    # Build comprehensive email body
    body_parts = [
        f"Hello {attendee_name},",
        "",
        intro,
        "",
        f"Title: {meeting_title}",
        f"Description: {meeting_description or 'No description provided'}",
        f"Date & Time: {start_text} – {end_text}",
        f"Type: {type_display}",
        f"Status: {status_display}",
        f"Location: {location_display}{link_text}",
    ]
    
    # Add attendees if available
    if attendees_list:
        attendees_str = ", ".join([str(attendee) for attendee in attendees_list])
        body_parts.append(f"Attendees: {attendees_str}")
    
    # Add notes if available
    if meeting_notes is not None:
        body_parts.extend([
            "",
            "📌 Notes:",
            str(meeting_notes)
        ])
    
    # Add closing
    company_name = company or "Your Team"
    body_parts.extend([
        "",
        "Thank you,",
        f"— {company_name}"
    ])
    
    body = "\n".join(body_parts)
    
    # Ensure we return strings, not Column objects
    return str(subject), str(body)


@router.get("/", response_model=List[MeetingOut])
def list_meetings(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    items = db.query(Meeting).filter(Meeting.owner_email == owner).order_by(Meeting.start_time.desc()).all()
    result: list[dict] = []
    for m in items:
        result.append({
            "id": m.id,
            "public_id": m.public_id,
            "title": m.title,
            "description": m.description,
            "start_time": m.start_time,
            "end_time": m.end_time,
            "location": m.location,
            "attendees": _attendees_to_list(str(m.attendees) if m.attendees is not None else None),
            "type": m.type.value if m.type is not None else None,
            "status": m.status.value if m.status is not None else None,
            "notes": m.notes,
            "meeting_link": getattr(m, 'meeting_link', None),
            "platform": getattr(m, 'platform', None),
        })
    return result


@router.get("/by-public-id/{public_id}", response_model=MeetingOut)
def get_meeting_by_public_id(public_id: str, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Get meeting by public_id (UUID)."""
    owner = _get_owner_from_request(request)
    m = db.query(Meeting).filter(Meeting.public_id == public_id, Meeting.owner_email == owner).first()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {
        "id": m.id,
        "public_id": m.public_id,
        "title": m.title,
        "description": m.description,
        "start_time": m.start_time,
        "end_time": m.end_time,
        "location": m.location,
        "attendees": _attendees_to_list(str(m.attendees) if m.attendees is not None else None),
        "type": m.type.value if m.type is not None else None,
        "status": m.status.value if m.status is not None else None,
        "notes": m.notes,
        "meeting_link": getattr(m, 'meeting_link', None),
        "platform": getattr(m, 'platform', None),
    }


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    m = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.owner_email == owner).first()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {
        "id": m.id,
        "public_id": m.public_id,
        "title": m.title,
        "description": m.description,
        "start_time": m.start_time,
        "end_time": m.end_time,
        "location": m.location,
        "attendees": _attendees_to_list(str(m.attendees) if m.attendees is not None else None),
        "type": m.type.value if m.type is not None else None,
        "status": m.status.value if m.status is not None else None,
        "notes": m.notes,
        "meeting_link": getattr(m, 'meeting_link', None),
        "platform": getattr(m, 'platform', None),
    }


@router.post("/", response_model=MeetingOut, status_code=201)
def create_meeting(payload: MeetingCreate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    _ensure_meetings_schema(db)
    # validate enums
    if payload.type not in {t.value for t in MeetingType}:
        raise HTTPException(status_code=422, detail="Invalid meeting type")
    if payload.status not in {s.value for s in MeetingStatus}:
        raise HTTPException(status_code=422, detail="Invalid meeting status")

    meeting = Meeting(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        location=payload.location,
        attendees=",".join(payload.attendees or []),
        type=MeetingType(payload.type),
        status=MeetingStatus(payload.status),
        notes=payload.notes,
        owner_email=_get_owner_from_request(request),
        meeting_link=payload.meeting_link,
        platform=payload.platform,
    )
    # Custom online meeting links removed per request
    db.add(meeting)
    try:
        db.commit()
    except SAOperationalError as e:
        db.rollback()
        # Attempt runtime schema fix then retry once
        _ensure_meetings_schema(db)
        try:
            db.add(meeting)
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database schema is out of date and could not be updated automatically. Please restart the backend and try again.")
    db.refresh(meeting)

    # Notify attendees and owner via email (generic notification)
    # #region agent log
    try:
        from app.core.debug_logger import write_debug_log
        write_debug_log("meetings.py:296", "create_meeting: entering notification block", {
            "meeting_id": meeting.id if meeting else None,
            "meeting_title": str(meeting.title) if meeting.title else None,
            "has_owner_email": bool(meeting.owner_email),
            "owner_email": str(meeting.owner_email) if meeting.owner_email else None,
            "attendees_count": len(payload.attendees or [])
        }, "H1")
    except: pass
    # #endregion
    
    try:
        from app.core.config import settings as cfg
        from app.api.v1.emails import _resolve_per_user_smtp
        
        owner_email = meeting.owner_email
        
        # #region agent log
        try:
            from app.core.debug_logger import write_debug_log
            write_debug_log("meetings.py:302", "create_meeting: owner_email check", {
                "owner_email": str(owner_email) if owner_email else None,
                "is_none": owner_email is None,
                "is_empty": owner_email == "" if owner_email else True
            }, "H2")
        except: pass
        # #endregion
        if not owner_email:
            # #region agent log
            try:
                from app.core.debug_logger import write_debug_log
                write_debug_log("meetings.py:300", "meeting notification skipped - no owner_email", {}, "H6")
            except: pass
            # #endregion
        else:
            # Use the same SMTP resolution logic as emails.py (includes Hostinger username normalization)
            try:
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:312", "create_meeting: before SMTP resolution", {
                        "owner_email": str(owner_email)
                    }, "H3")
                except: pass
                # #endregion
                
                host, port, user, password, from_addr, use_tls = _resolve_per_user_smtp(owner_email)
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:320", "create_meeting: after SMTP resolution", {
                        "has_host": bool(host),
                        "has_user": bool(user),
                        "has_password": bool(password),
                        "port": port,
                        "from_addr": str(from_addr) if from_addr else None,
                        "use_tls": use_tls
                    }, "H3")
                except: pass
                # #endregion
                
                if not host or not user or not password:
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:332", "create_meeting: SMTP settings incomplete", {
                            "has_host": bool(host),
                            "has_user": bool(user),
                            "has_password": bool(password)
                        }, "H4")
                    except: pass
                    # #endregion
                    raise ValueError("SMTP settings incomplete")
                
                # from_addr is already normalized by _resolve_per_user_smtp
                sender = from_addr or user or "no-reply@example.com"
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:318", "meeting notification SMTP resolved", {
                        "host": host,
                        "port": port,
                        "username": user,
                        "from_addr": sender,
                        "use_tls": use_tls,
                        "has_password": bool(password)
                    }, "H6")
                except: pass
                # #endregion
                
                prof = _owner_profile(str(owner_email))
                # Get user's timezone
                user_timezone = 'Asia/Kolkata'  # Default to IST
                pdb = SessionLocal()
                try:
                    u = pdb.query(User).filter(User.email == owner_email).first()
                    if u and u.timezone:
                        user_timezone = u.timezone
                finally:
                    pdb.close()
                
                # Get base subject and compose email template
                base_subject, base_body_template = _compose_meeting_email('created', meeting, prof, user_timezone)
                
                # Build map of recipient email to display name from contacts for personalization
                all_recipients = [str(owner_email)] + (payload.attendees or [])
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:350", "create_meeting: recipients list built", {
                        "all_recipients": all_recipients,
                        "recipients_count": len(all_recipients),
                        "has_owner": str(owner_email) in all_recipients,
                        "attendees_from_payload": payload.attendees or []
                    }, "H5")
                except: pass
                # #endregion
                
                email_to_name: dict[str, str] = {}
                pdb = SessionLocal()
                try:
                    rows = pdb.query(Contact).filter(Contact.owner_email == owner_email, Contact.email.in_(all_recipients)).all()
                    for c in rows:
                        if c.email:
                            email_to_name[c.email] = (c.name or '').strip() or c.email
                finally:
                    pdb.close()
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:350", "sending meeting notification emails", {
                        "recipients": all_recipients,
                        "subject": base_subject,
                        "body_length": len(base_body_template),
                        "personalized_count": len(email_to_name)
                    }, "H6")
                except: pass
                # #endregion
                
                # Connect to SMTP server once and send individually for personalized greeting
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:375", "create_meeting: before SMTP connection", {
                        "host": host,
                        "port": port,
                        "use_ssl": port == 465,
                        "use_tls": use_tls
                    }, "H6")
                except: pass
                # #endregion
                
                if port == 465:
                    server = smtplib.SMTP_SSL(host, port, timeout=15)
                else:
                    server = smtplib.SMTP(host, port, timeout=15)
                    if use_tls:
                        server.starttls()
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:385", "create_meeting: before SMTP login", {
                        "user": user,
                        "has_password": bool(password)
                    }, "H6")
                except: pass
                # #endregion
                
                server.login(user, password)
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:390", "create_meeting: SMTP login successful", {}, "H6")
                except: pass
                # #endregion
                
                # Send personalized email to each recipient
                for rcpt in all_recipients:
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:395", "create_meeting: preparing email for recipient", {
                            "recipient": rcpt,
                            "subject": base_subject,
                            "sender": sender
                        }, "H6")
                    except: pass
                    # #endregion
                    
                    greet_name = email_to_name.get(rcpt) or (rcpt.split('@')[0].replace('.', ' ').title() if '@' in rcpt else rcpt)
                    
                    # Personalize the greeting in the email body
                    personalized_body = base_body_template.replace(f"Hello {base_body_template.split('Hello ')[1].split(',')[0] if 'Hello ' in base_body_template else 'there'},", f"Hello {greet_name},")
                    
                    msg = MIMEText(personalized_body, "plain", "utf-8")
                    msg["Subject"] = base_subject
                    msg["From"] = sender
                    msg["To"] = rcpt
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:410", "create_meeting: before sendmail", {
                            "recipient": rcpt,
                            "body_length": len(personalized_body)
                        }, "H6")
                    except: pass
                    # #endregion
                    
                    server.sendmail(sender, [rcpt], msg.as_string())
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:418", "create_meeting: sendmail completed", {
                            "recipient": rcpt
                        }, "H6")
                    except: pass
                    # #endregion
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:380", "meeting creation notification email sent", {
                            "recipient": rcpt,
                            "subject": base_subject,
                            "personalized": greet_name != rcpt
                        }, "H6")
                    except: pass
                    # #endregion
                
                server.quit()
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:405", "meeting notification emails sent successfully", {
                        "recipients_count": len(all_recipients)
                    }, "H6")
                except: pass
                # #endregion
                
            except Exception as e:
                # Log the error instead of silently failing
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                error_msg = str(e)
                error_type = type(e).__name__
                error_traceback = traceback.format_exc()
                logger.error(f"Failed to send meeting notification emails: {error_msg}")
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:440", "create_meeting: inner exception caught", {
                        "error": error_msg,
                        "error_type": error_type,
                        "traceback": error_traceback,
                        "owner_email": owner_email,
                        "meeting_id": meeting.id if meeting else None,
                        "attendees_count": len(payload.attendees or [])
                    }, "H6")
                except: pass
                # #endregion
                
                # Don't raise - meeting was created successfully, email failure shouldn't block it
                # But log it so we can debug
    except Exception as e:
        # Outer catch for any unexpected errors
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_msg = str(e)
        error_type = type(e).__name__
        error_traceback = traceback.format_exc()
        logger.error(f"Unexpected error in meeting notification: {error_msg}", exc_info=True)
        
        # #region agent log
        try:
            from app.core.debug_logger import write_debug_log
            write_debug_log("meetings.py:460", "create_meeting: outer exception caught", {
                "error": error_msg,
                "error_type": error_type,
                "traceback": error_traceback
            }, "H7")
        except: pass
        # #endregion
    return {
        "id": meeting.id,
        "public_id": meeting.public_id,
        "title": meeting.title,
        "description": meeting.description,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "location": meeting.location,
        "attendees": payload.attendees or [],
        "type": meeting.type.value,
        "status": meeting.status.value,
        "notes": meeting.notes,
        "meeting_link": getattr(meeting, 'meeting_link', None),
        "platform": getattr(meeting, 'platform', None),
    }


@router.put("/{meeting_id}", response_model=MeetingOut)
def update_meeting(meeting_id: int, payload: MeetingUpdate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    owner = _get_owner_from_request(request)
    if meeting.owner_email is not None and str(meeting.owner_email) != owner:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Capture previous values to detect and report changes
    prev_title = str(meeting.title) if meeting.title is not None else None
    prev_description = str(meeting.description) if meeting.description is not None else None
    prev_start = meeting.start_time
    prev_end = meeting.end_time
    prev_location = str(meeting.location) if meeting.location is not None else None
    prev_link = getattr(meeting, 'meeting_link', None)
    prev_type = meeting.type
    prev_status = meeting.status
    prev_notes = str(meeting.notes) if meeting.notes is not None else None
    prev_attendees = _attendees_to_list(str(meeting.attendees) if meeting.attendees is not None else None)

    raw_changes = payload.model_dump(exclude_unset=True)
    data = dict(raw_changes)
    if "type" in data:
        val = data["type"]
        if val not in {t.value for t in MeetingType}:
            raise HTTPException(status_code=422, detail="Invalid meeting type")
        # Use proper SQLAlchemy update method
        db.query(Meeting).filter(Meeting.id == meeting_id).update({"type": val})
        data.pop("type")
    if "status" in data:
        val = data["status"]
        if val not in {s.value for s in MeetingStatus}:
            raise HTTPException(status_code=422, detail="Invalid meeting status")
        # Use proper SQLAlchemy update method
        db.query(Meeting).filter(Meeting.id == meeting_id).update({"status": val})
        data.pop("status")
    if "attendees" in data and data["attendees"] is not None:
        meeting.attendees = ",".join(data["attendees"])  # type: ignore
        data.pop("attendees")
    # simple direct updates for other scalar fields
    if "meeting_link" in data:
        meeting.meeting_link = data["meeting_link"]  # type: ignore
        data.pop("meeting_link")
    if "platform" in data:
        meeting.platform = data["platform"]  # type: ignore
        data.pop("platform")

    for field, value in data.items():
        setattr(meeting, field, value)

    db.commit()
    db.refresh(meeting)

    # Notify attendees on changes with detailed diff
    try:
        attendees = _attendees_to_list(str(meeting.attendees) if meeting.attendees is not None else None)
        if raw_changes and attendees:
            from app.core.config import settings as cfg
            prof = _owner_profile(str(meeting.owner_email) if meeting.owner_email is not None else None)

            # Build human-readable change list
            def _fmt_dt(dt: datetime | None) -> str:
                if dt is None:
                    return ""
                try:
                    return dt.strftime('%d %b %Y, %I:%M %p UTC')
                except Exception:
                    return str(dt)

            def _fmt_type(mt: MeetingType | None) -> str:
                if not mt:
                    return ""
                v = mt.value
                if v == 'video':
                    return 'Video Call'
                if v == 'phone':
                    return 'Phone Call'
                return 'In Person'

            changes: list[str] = []
            
            # Extract current values safely after refresh - convert Column objects to actual values
            current_title = str(meeting.title) if meeting.title is not None else None
            current_type = meeting.type
            current_start = meeting.start_time
            current_end = meeting.end_time
            current_location = str(meeting.location) if meeting.location is not None else None
            current_link = getattr(meeting, 'meeting_link', None)
            
            # Use explicit null checks to avoid Column reference issues
            if prev_type is not None and current_type is not None and str(prev_type) != str(current_type):
                # Convert Column objects to actual MeetingType values before formatting
                prev_type_actual = cast(MeetingType, prev_type) if prev_type is not None else None
                current_type_actual = cast(MeetingType, current_type) if current_type is not None else None
                changes.append(f"Type changed: from {_fmt_type(prev_type_actual)} → {_fmt_type(current_type_actual)}")
            
            # Safe datetime comparisons - extract actual values
            start_changed = False
            end_changed = False
            if prev_start is not None and current_start is not None:
                start_changed = bool(prev_start != current_start)
            if prev_end is not None and current_end is not None:
                end_changed = bool(prev_end != current_end)
            
            if start_changed or end_changed:
                # Extract actual datetime values for formatting - convert Column objects to actual values
                start_dt_actual = cast(datetime, current_start) if current_start is not None else None
                end_dt_actual = cast(datetime, current_end) if current_end is not None else None
                changes.append(f"New Date/Time: {_fmt_dt(start_dt_actual)} – {_fmt_dt(end_dt_actual)}")
            
            if prev_title is not None and current_title is not None and str(prev_title) != str(current_title):
                changes.append(f"Title changed: from '{prev_title}' → '{current_title}'")
            
            # Safe type checking with explicit null checks
            prev_type_safe = prev_type if prev_type is not None and hasattr(prev_type, 'value') else None
            current_type_safe = current_type if current_type is not None and hasattr(current_type, 'value') else None
            
            # Safe boolean operations for type checks
            prev_is_inperson = prev_type_safe is not None and prev_type_safe.value == 'in-person'
            current_is_inperson = current_type_safe is not None and current_type_safe.value == 'in-person'
            prev_is_video = prev_type_safe is not None and prev_type_safe.value == 'video'
            current_is_video = current_type_safe is not None and current_type_safe.value == 'video'
            
            if prev_is_inperson or current_is_inperson:
                if prev_location is not None and current_location is not None and prev_location != current_location:
                    changes.append(f"Location changed: from '{prev_location or ''}' → '{current_location or ''}'")
            if prev_is_video or current_is_video:
                if (prev_link or '') != (current_link or ''):
                    changes.append("Meeting link updated")
            new_attendees = set(attendees)
            old_attendees = set(prev_attendees)
            added = sorted(list(new_attendees - old_attendees))
            removed = sorted(list(old_attendees - new_attendees))
            if added:
                changes.append(f"Attendees added: {', '.join(added)}")
            if removed:
                changes.append(f"Attendees removed: {', '.join(removed)}")

            # Subject and details
            subject = f"Updated Meeting Details – {current_title}"
            # Display line for location/type
            # Safe type checking with explicit null checks
            current_type_safe = current_type if current_type is not None and hasattr(current_type, 'value') else None
            
            if current_type_safe is not None and current_type_safe.value == 'video':
                loc_type_display = 'Video Call'
            elif current_type_safe is not None and current_type_safe.value == 'phone':
                loc_type_display = 'Phone Call'
            else:
                loc_type_display = current_location if current_location is not None else 'In Person'
            link_line = ''
            if current_link:
                link_line = f"\nMeeting Link: {current_link}"

            who = prof.get('name') or 'Admin'
            company = prof.get('company')
            position = prof.get('position')
            sig_lines = who
            if position:
                sig_lines = f"{sig_lines}\n{position}"
            if company:
                sig_lines = f"{sig_lines}\n{company}"

            # Build map of recipient email to display name from contacts
            email_to_name: dict[str, str] = {}
            if meeting.owner_email is not None:
                pdb = SessionLocal()
                try:
                    rows = pdb.query(Contact).filter(Contact.owner_email == meeting.owner_email, Contact.email.in_(attendees)).all()
                    for c in rows:
                        if c.email:
                            email_to_name[c.email] = (c.name or '').strip() or c.email
                finally:
                    pdb.close()

            # Use the same SMTP resolution logic as create_meeting (includes password decryption and Hostinger normalization)
            from app.api.v1.emails import _resolve_per_user_smtp
            
            owner_email = meeting.owner_email
            
            # #region agent log
            try:
                from app.core.debug_logger import write_debug_log
                write_debug_log("meetings.py:652", "update_meeting: owner_email check", {
                    "owner_email": str(owner_email) if owner_email else None,
                    "has_owner_email": bool(owner_email)
                }, "H2")
            except: pass
            # #endregion
            
            if owner_email:
                try:
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:662", "update_meeting: before SMTP resolution", {
                            "owner_email": str(owner_email)
                        }, "H3")
                    except: pass
                    # #endregion
                    
                    host, port, user, password, from_addr, use_tls = _resolve_per_user_smtp(owner_email)
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:670", "update_meeting: after SMTP resolution", {
                            "has_host": bool(host),
                            "has_user": bool(user),
                            "has_password": bool(password),
                            "port": port,
                            "from_addr": str(from_addr) if from_addr else None,
                            "use_tls": use_tls
                        }, "H3")
                    except: pass
                    # #endregion
                    
                    if not host or not user or not password:
                        # #region agent log
                        try:
                            from app.core.debug_logger import write_debug_log
                            write_debug_log("meetings.py:680", "update_meeting: SMTP settings incomplete", {
                                "has_host": bool(host),
                                "has_user": bool(user),
                                "has_password": bool(password)
                            }, "H4")
                        except: pass
                        # #endregion
                        raise ValueError("SMTP settings incomplete")
                    
                    sender = from_addr or user or "no-reply@example.com"
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:620", "update meeting notification SMTP resolved", {
                            "host": host,
                            "port": port,
                            "username": user,
                            "from_addr": sender,
                            "use_tls": use_tls,
                            "has_password": bool(password),
                            "attendees_count": len(attendees)
                        }, "H7")
                    except: pass
                    # #endregion
                    
                    # Connect to SMTP server once and send individually for personalized greeting
                    if port == 465:
                        server = smtplib.SMTP_SSL(host, port, timeout=15)
                    else:
                        server = smtplib.SMTP(host, port, timeout=15)
                        if use_tls:
                            server.starttls()
                    server.login(user, password)
                    
                    for rcpt in attendees:
                        greet_name = email_to_name.get(rcpt) or rcpt
                        changes_block = "\n".join(changes) if changes else "No specific field changes were detected."
                        
                        # Get current meeting details for comprehensive email
                        current_description = str(meeting.description) if meeting.description is not None else 'No description provided'
                        current_notes = str(meeting.notes) if meeting.notes is not None else ''
                        current_status = meeting.status.value if meeting.status is not None else 'Scheduled'
                        current_attendees = attendees
                        
                        # Format attendees list
                        attendees_str = ", ".join(current_attendees) if current_attendees else 'No attendees listed'
                        
                        # Convert times to user's timezone
                        import pytz
                        user_timezone = 'Asia/Kolkata'  # Default to IST
                        if meeting.owner_email is not None:
                            pdb = SessionLocal()
                            try:
                                u = pdb.query(User).filter(User.email == meeting.owner_email).first()
                                if u and u.timezone:
                                    user_timezone = u.timezone
                            finally:
                                pdb.close()
                        
                        # Format times in user's timezone
                        try:
                            utc_start = meeting.start_time
                            if utc_start.tzinfo is None:
                                utc_start = pytz.UTC.localize(utc_start)
                            user_tz = pytz.timezone(user_timezone)
                            local_start = utc_start.astimezone(user_tz)
                            start_time_str = local_start.strftime('%d %b %Y, %I:%M %p %Z')
                        except Exception:
                            start_time_str = meeting.start_time.strftime('%d %b %Y, %I:%M %p UTC')
                        
                        try:
                            if meeting.end_time is not None:
                                utc_end = meeting.end_time
                                if utc_end.tzinfo is None:
                                    utc_end = pytz.UTC.localize(utc_end)
                                user_tz = pytz.timezone(user_timezone)
                                local_end = utc_end.astimezone(user_tz)
                                end_time_str = local_end.strftime('%I:%M %p %Z')
                            else:
                                end_time_str = ''
                        except Exception:
                            end_time_str = meeting.end_time.strftime('%I:%M %p UTC') if meeting.end_time is not None else ''
                        
                        # Build comprehensive update email body
                        body_parts = [
                            f"Hello {greet_name},",
                            "",
                            f"The meeting details have been updated. Please note the following changes:",
                            "",
                            changes_block,
                            "",
                            "Updated Meeting Details:",
                            f"Title: {current_title}",
                            f"Description: {current_description}",
                            f"Date & Time: {start_time_str} – {end_time_str}",
                            f"Type: {current_type_safe.value if current_type_safe is not None else 'Meeting'}",
                            f"Status: {current_status}",
                            f"Location: {loc_type_display}{link_line}",
                            f"Attendees: {attendees_str}",
                        ]
                        
                        # Add notes if available
                        if current_notes:
                            body_parts.extend([
                                "",
                                "📌 Notes:",
                                str(current_notes)
                            ])
                        
                        # Add closing
                        body_parts.extend([
                            "",
                            "Kindly update your calendar accordingly.",
                            "",
                            "Thank you,",
                            sig_lines
                        ])
                        
                        body = "\n".join(body_parts)
                        msg = MIMEText(body, 'plain', 'utf-8')
                        msg['Subject'] = subject
                        msg['From'] = sender
                        msg['To'] = rcpt
                        server.sendmail(sender, [rcpt], msg.as_string())
                        
                        # #region agent log
                        try:
                            from app.core.debug_logger import write_debug_log
                            write_debug_log("meetings.py:741", "update meeting notification email sent", {
                                "recipient": rcpt,
                                "subject": subject
                            }, "H7")
                        except: pass
                        # #endregion
                    
                    server.quit()
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:750", "update meeting notification emails sent successfully", {
                            "recipients_count": len(attendees)
                        }, "H7")
                    except: pass
                    # #endregion
                    
                except Exception as e:
                    # Log the error instead of silently failing
                    import logging
                    logger = logging.getLogger(__name__)
                    error_msg = str(e)
                    error_type = type(e).__name__
                    logger.error(f"Failed to send update meeting notification emails: {error_msg}")
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:763", "update meeting notification email failed", {
                            "error": error_msg,
                            "error_type": error_type,
                            "owner_email": owner_email,
                            "meeting_id": meeting.id if meeting else None,
                            "attendees_count": len(attendees)
                        }, "H7")
                    except: pass
                    # #endregion
                    
                    # Don't raise - meeting was updated successfully, email failure shouldn't block it
    except Exception as e:
        # Outer catch for any unexpected errors
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_msg = str(e)
        error_type = type(e).__name__
        error_traceback = traceback.format_exc()
        logger.error(f"Unexpected error in update meeting notification: {error_msg}", exc_info=True)
        
        # #region agent log
        try:
            from app.core.debug_logger import write_debug_log
            write_debug_log("meetings.py:837", "update_meeting: outer exception caught", {
                "error": error_msg,
                "error_type": error_type,
                "traceback": error_traceback
            }, "H7")
        except: pass
        # #endregion

    return {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "location": meeting.location,
        "attendees": _attendees_to_list(str(meeting.attendees) if meeting.attendees is not None else None),
        "type": meeting.type.value if meeting.type is not None else None,
        "status": meeting.status.value if meeting.status is not None else None,
        "notes": meeting.notes,
        "meeting_link": getattr(meeting, 'meeting_link', None),
        "platform": getattr(meeting, 'platform', None),
    }


@router.delete("/{meeting_id}", status_code=200)
def delete_meeting(meeting_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    owner = _get_owner_from_request(request)
    # Allow deletion if the meeting belongs to the current owner, or if it is an orphan (no owner set)
    if meeting.owner_email is not None and str(meeting.owner_email) != owner:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Store meeting details before deletion for email notification
    meeting_title = str(meeting.title) if meeting.title else "Meeting"
    meeting_description = str(meeting.description) if meeting.description else None
    meeting_start_time = meeting.start_time
    meeting_end_time = meeting.end_time
    meeting_location = str(meeting.location) if meeting.location else None
    meeting_type = meeting.type
    meeting_attendees = _attendees_to_list(str(meeting.attendees) if meeting.attendees else None)
    owner_email = meeting.owner_email
    
    # Delete the meeting
    db.delete(meeting)
    db.commit()
    
    # Notify attendees about meeting cancellation
    if owner_email and meeting_attendees:
        try:
            from app.api.v1.emails import _resolve_per_user_smtp
            
            try:
                host, port, user, password, from_addr, use_tls = _resolve_per_user_smtp(owner_email)
                
                if not host or not user or not password:
                    raise ValueError("SMTP settings incomplete")
                
                sender = from_addr or user or "no-reply@example.com"
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:850", "delete meeting notification SMTP resolved", {
                        "host": host,
                        "port": port,
                        "username": user,
                        "from_addr": sender,
                        "use_tls": use_tls,
                        "has_password": bool(password),
                        "attendees_count": len(meeting_attendees)
                    }, "H8")
                except: pass
                # #endregion
                
                prof = _owner_profile(str(owner_email))
                # Get user's timezone
                user_timezone = 'Asia/Kolkata'  # Default to IST
                pdb = SessionLocal()
                try:
                    u = pdb.query(User).filter(User.email == owner_email).first()
                    if u and u.timezone:
                        user_timezone = u.timezone
                finally:
                    pdb.close()
                
                # Build cancellation email subject
                subject = f"Meeting Cancelled: {meeting_title}"
                
                # Build map of recipient email to display name from contacts
                email_to_name: dict[str, str] = {}
                pdb = SessionLocal()
                try:
                    rows = pdb.query(Contact).filter(Contact.owner_email == owner_email, Contact.email.in_(meeting_attendees)).all()
                    for c in rows:
                        if c.email:
                            email_to_name[c.email] = (c.name or '').strip() or c.email
                finally:
                    pdb.close()
                
                # Connect to SMTP server
                if port == 465:
                    server = smtplib.SMTP_SSL(host, port, timeout=15)
                else:
                    server = smtplib.SMTP(host, port, timeout=15)
                    if use_tls:
                        server.starttls()
                
                server.login(user, password)
                
                # Send to each attendee
                for rcpt in meeting_attendees:
                    greet_name = email_to_name.get(rcpt) or rcpt
                    
                    # Build cancellation email body
                    who = prof.get('name') or 'Admin'
                    company = prof.get('company')
                    position = prof.get('position')
                    sig_lines = who
                    if position:
                        sig_lines = f"{sig_lines}\n{position}"
                    if company:
                        sig_lines = f"{sig_lines}\n{company}"
                    
                    # Format meeting time in user's timezone
                    import pytz
                    start_time_str = ""
                    end_time_str = ""
                    try:
                        if meeting_start_time:
                            utc_start = meeting_start_time
                            if utc_start.tzinfo is None:
                                utc_start = pytz.UTC.localize(utc_start)
                            user_tz = pytz.timezone(user_timezone)
                            local_start = utc_start.astimezone(user_tz)
                            start_time_str = local_start.strftime('%d %b %Y, %I:%M %p %Z')
                    except Exception:
                        start_time_str = str(meeting_start_time) if meeting_start_time else ""
                    
                    try:
                        if meeting_end_time:
                            utc_end = meeting_end_time
                            if utc_end.tzinfo is None:
                                utc_end = pytz.UTC.localize(utc_end)
                            user_tz = pytz.timezone(user_timezone)
                            local_end = utc_end.astimezone(user_tz)
                            end_time_str = local_end.strftime('%I:%M %p %Z')
                    except Exception:
                        end_time_str = str(meeting_end_time) if meeting_end_time else ""
                    
                    time_display = f"{start_time_str} – {end_time_str}" if end_time_str else start_time_str
                    
                    cancellation_body = f"""Hello {greet_name},

The following meeting has been cancelled:

Title: {meeting_title}
Description: {meeting_description or 'No description provided'}
Date & Time: {time_display}
Location: {meeting_location or 'Not specified'}

Please update your calendar accordingly.

Thank you,
{sig_lines}"""
                    
                    msg = MIMEText(cancellation_body, "plain", "utf-8")
                    msg["Subject"] = subject
                    msg["From"] = sender
                    msg["To"] = rcpt
                    server.sendmail(sender, [rcpt], msg.as_string())
                    
                    # #region agent log
                    try:
                        from app.core.debug_logger import write_debug_log
                        write_debug_log("meetings.py:890", "delete meeting notification email sent", {
                            "recipient": rcpt,
                            "subject": subject
                        }, "H8")
                    except: pass
                    # #endregion
                
                server.quit()
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:900", "delete meeting notification emails sent successfully", {
                        "recipients_count": len(meeting_attendees)
                    }, "H8")
                except: pass
                # #endregion
                
            except Exception as e:
                # Log the error instead of silently failing
                import logging
                logger = logging.getLogger(__name__)
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(f"Failed to send delete meeting notification emails: {error_msg}")
                
                # #region agent log
                try:
                    from app.core.debug_logger import write_debug_log
                    write_debug_log("meetings.py:913", "delete meeting notification email failed", {
                        "error": error_msg,
                        "error_type": error_type,
                        "owner_email": owner_email,
                        "meeting_id": meeting_id,
                        "attendees_count": len(meeting_attendees)
                    }, "H8")
                except: pass
                # #endregion
                
                # Don't raise - meeting was deleted successfully, email failure shouldn't block it
        except Exception as e:
            # Outer catch for any unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in delete meeting notification: {str(e)}", exc_info=True)
            
            # #region agent log
            try:
                from app.core.debug_logger import write_debug_log
                write_debug_log("meetings.py:930", "unexpected error in delete meeting notification", {
                    "error": str(e),
                    "error_type": type(e).__name__
                }, "H8")
            except: pass
            # #endregion
    
    return {"status": "deleted"}


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
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


