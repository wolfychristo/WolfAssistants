from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import csv
import io
import json

from app.core.database import get_db
from app.core.tenant_database import get_tenant_db_dependency
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy import text
from app.models.contact import Contact, ContactStatus
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut
from app.core.config import settings
from jose import jwt


router = APIRouter()


def _ensure_contacts_schema(db: Session) -> None:
    """Ensure required columns exist in contacts table for Supabase."""
    # No-op for Supabase - schema is managed by migrations
    pass

def _compute_contact_status(db: Session, owner: str, contact: Contact) -> str:
    """Derive contact status from recent activity with deterministic precedence."""
    try:
        from app.models.email import Email, EmailStatus
        from app.models.meeting import Meeting, MeetingStatus
        from sqlalchemy import func
        
        # Normalize contact email to lowercase for consistent matching
        contact_email = (contact.email or "").strip().lower()
        if not contact_email:
            # Fallback to stored status if no email
            return getattr(contact.status, 'value', str(contact.status) if contact.status else 'prospect')
        
        # Highest precedence: upcoming/completed meeting explicitly including this contact
        meetings = (
            db.query(Meeting)
            .filter(
                Meeting.owner_email == owner,
                Meeting.status == MeetingStatus.scheduled,
                Meeting.attendees.isnot(None),
            )
            .order_by(Meeting.start_time.desc())
            .all()
        )
        for meeting in meetings:
            raw_attendees = meeting.attendees
            attendee_list: list[str] = []
            if isinstance(raw_attendees, list):
                attendee_list = [str(addr).strip().lower() for addr in raw_attendees if str(addr).strip()]
            else:
                text_value = str(raw_attendees or "").strip()
                if text_value:
                    parsed: list[str] = []
                    # Attempt to load JSON array or dict containing attendees
                    try:
                        data = json.loads(text_value)
                        if isinstance(data, list):
                            parsed = [str(item) for item in data]
                        elif isinstance(data, dict):
                            maybe_list = data.get("attendees")
                            if isinstance(maybe_list, list):
                                parsed = [str(item) for item in maybe_list]
                    except Exception:
                        parsed = []
                    if not parsed:
                        # Normalize separators
                        normalized = text_value.replace(";", ",").replace("\n", ",")
                        parsed = normalized.split(",")
                    attendee_list = [item.strip().lower().strip("[]'\"") for item in parsed if item and item.strip()]
            if contact_email in attendee_list:
                return "meeting_scheduled"

        # Replies: any received from this email after last sent
        # Get all sent emails and filter manually to ensure case-insensitive matching
        # Handle missing attachments column gracefully
        try:
            all_sent_emails = (
                db.query(Email)
                .filter(
                    Email.owner_email == owner,
                    Email.status == EmailStatus.sent
                )
                .order_by(Email.sent_at.desc())
                .all()
            )
        except Exception as email_query_error:
            # If attachments column doesn't exist, use raw SQL query
            from sqlalchemy import text
            error_str = str(email_query_error).lower()
            if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
                # Rollback the failed transaction before retrying
                try:
                    db.rollback()
                except:
                    pass
                # Use raw SQL query excluding attachments column
                sql_query = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email, 
                           scheduled_for, deleted_at, last_error, original_folder
                    FROM emails 
                    WHERE owner_email = :owner_email AND status = 'sent'
                    ORDER BY sent_at DESC
                """)
                result = db.execute(sql_query, {"owner_email": owner})
                rows = result.fetchall()
                # Convert rows to Email-like objects
                all_sent_emails = []
                for row in rows:
                    email_obj = type('Email', (), {
                        'id': row[0],
                        'to_address': row[3],
                        'from_address': row[4],
                        'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                        'sent_at': row[6],
                        'received_at': row[7],
                    })()
                    all_sent_emails.append(email_obj)
            else:
                # Re-raise other errors
                raise
        # Find last sent email with case-insensitive matching
        last_sent = None
        matching_sent_emails = []
        for e in all_sent_emails:
            if e.to_address:
                email_normalized = e.to_address.strip().lower()
                if email_normalized == contact_email:
                    matching_sent_emails.append(e)
                    if not last_sent:
                        last_sent = e
        
        # Get all received emails and filter manually
        # Handle missing attachments column gracefully
        try:
            all_recv_emails = (
                db.query(Email)
                .filter(
                    Email.owner_email == owner,
                    Email.status == EmailStatus.received
                )
                .order_by(Email.received_at.desc())
                .all()
            )
        except Exception as email_query_error:
            # If attachments column doesn't exist, use raw SQL query
            from sqlalchemy import text
            error_str = str(email_query_error).lower()
            if 'attachments' in error_str or 'column' in error_str or 'does not exist' in error_str:
                # Rollback the failed transaction before retrying
                try:
                    db.rollback()
                except:
                    pass
                # Use raw SQL query excluding attachments column
                sql_query = text("""
                    SELECT id, subject, body, to_address, from_address, status, 
                           sent_at, received_at, is_starred, is_read, owner_email, 
                           scheduled_for, deleted_at, last_error, original_folder
                    FROM emails 
                    WHERE owner_email = :owner_email AND status = 'received'
                    ORDER BY received_at DESC
                """)
                result = db.execute(sql_query, {"owner_email": owner})
                rows = result.fetchall()
                # Convert rows to Email-like objects
                all_recv_emails = []
                for row in rows:
                    email_obj = type('Email', (), {
                        'id': row[0],
                        'to_address': row[3],
                        'from_address': row[4],
                        'status': EmailStatus(row[5]) if isinstance(row[5], str) else row[5],
                        'sent_at': row[6],
                        'received_at': row[7],
                    })()
                    all_recv_emails.append(email_obj)
            else:
                # Re-raise other errors
                raise
        # Find last received email with case-insensitive matching
        last_recv = None
        for e in all_recv_emails:
            if e.from_address:
                email_normalized = e.from_address.strip().lower()
                if email_normalized == contact_email:
                    if not last_recv:
                        last_recv = e
                    break
        if last_recv and (not last_sent or (last_recv.received_at or last_recv.sent_at) >= (last_sent.sent_at or last_sent.received_at)):
            # Optional: use intent column if you store it
            if (contact.last_intent or "").lower() in {"interested","schedule","question"}:
                return "interested"
            return "replied"

        # Follow-up count - use the matching emails we already found
        followups = len(matching_sent_emails)
        
        if followups > 1:
            result = f"follow_up_{min(followups-1,5)}"
        elif followups == 1:
            result = "sent"
        else:
            result = "new"
        
        return result
    except Exception as e:
        # Log error for debugging but fallback to stored status
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error computing contact status for {contact.email}: {e}", exc_info=True)
        # Fallback to stored status
        fallback_status = getattr(contact.status, 'value', str(contact.status) if contact.status else 'prospect')
        return fallback_status


@router.get("/", response_model=List[ContactOut])
def list_contacts(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    items = db.query(Contact).filter(Contact.owner_email == owner).order_by(Contact.id.desc()).all()
    result: list[ContactOut] = []
    for c in items:
        computed = _compute_contact_status(db, owner, c)
        # Build response model dict manually to include computed_status
        contact_out = ContactOut(
            id=c.id,
            public_id=c.public_id,
            name=c.name,
            email=c.email,
            company=c.company,
            phone=c.phone,
            position=c.position,
            status=(getattr(c.status, 'value', str(c.status)) if c.status else None) or 'prospect',
            notes=c.notes,
            last_contact=c.last_contact or datetime.utcnow(),
            computed_status=computed
        )
        result.append(contact_out)
    return result


@router.get("/export")
def export_contacts(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Export contacts as CSV. Placed before /{contact_id} to avoid 422 from path param matching."""
    owner = _get_owner_from_request(request)
    contacts = db.query(Contact).filter(Contact.owner_email == owner).order_by(Contact.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(["id", "name", "email", "company", "phone", "position", "status", "last_contact", "notes"])
    for c in contacts:
        writer.writerow([
            c.id,
            c.name or "",
            c.email or "",
            c.company or "",
            c.phone or "",
            c.position or "",
            getattr(c.status, "value", str(c.status)) if c.status else "",
            c.last_contact.isoformat() if c.last_contact else "",
            (c.notes or "").replace("\n", " ").replace("\r", " "),
        ])

    # Prepend UTF-8 BOM for better Excel compatibility on Windows
    csv_content = "\ufeff" + output.getvalue()
    headers = {
        "Content-Disposition": "attachment; filename=contacts.csv",
        "Cache-Control": "no-store",
    }
    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)


# Place import route BEFORE /{contact_id} to avoid path param 422 when posting to /import
@router.post("/import")
def import_contacts_alias(request: Request, file: UploadFile = File(...), db: Session = Depends(get_tenant_db_dependency)):
    return import_contacts_internal(request, file, db)


@router.get("/by-public-id/{public_id}", response_model=ContactOut)
def get_contact_by_public_id(public_id: str, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Get contact by public_id (UUID)."""
    owner = _get_owner_from_request(request)
    contact = db.query(Contact).filter(Contact.public_id == public_id, Contact.owner_email == owner).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    # Compute status for consistency with list endpoint
    computed = _compute_contact_status(db, owner, contact)
    contact_out = ContactOut(
        id=contact.id,
        public_id=contact.public_id,
        name=contact.name,
        email=contact.email,
        company=contact.company,
        phone=contact.phone,
        position=contact.position,
        status=(getattr(contact.status, 'value', str(contact.status)) if contact.status else None) or 'prospect',
        notes=contact.notes,
        last_contact=contact.last_contact or datetime.utcnow(),
        computed_status=computed
    )
    return contact_out


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.owner_email == owner).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    # Compute status for consistency with list endpoint
    computed = _compute_contact_status(db, owner, contact)
    contact_out = ContactOut(
        id=contact.id,
        public_id=contact.public_id,
        name=contact.name,
        email=contact.email,
        company=contact.company,
        phone=contact.phone,
        position=contact.position,
        status=(getattr(contact.status, 'value', str(contact.status)) if contact.status else None) or 'prospect',
        notes=contact.notes,
        last_contact=contact.last_contact or datetime.utcnow(),
        computed_status=computed
    )
    return contact_out


@router.post("/", response_model=ContactOut, status_code=201)
def create_contact(payload: ContactCreate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    # Proactively ensure schema for fresh tenants/old DBs
    _ensure_contacts_schema(db)
    # Validate status
    status_value = payload.status or "prospect"
    if status_value not in {s.value for s in ContactStatus}:
        raise HTTPException(status_code=422, detail="Invalid status")

    # Allow duplicate emails per request; remove uniqueness check per user request

    contact = Contact(
        name=payload.name,
        email=payload.email,
        company=payload.company,
        phone=payload.phone,
        position=payload.position,
        status=ContactStatus(status_value),
        last_contact=datetime.utcnow(),
        notes=payload.notes,
        owner_email=_get_owner_from_request(request),
    )
    db.add(contact)
    try:
        db.commit()
    except SAOperationalError as e:
        # For Supabase, just raise the error - schema is managed by migrations
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, payload: ContactUpdate, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact.owner_email != _get_owner_from_request(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.email and payload.email != contact.email:
        if db.query(Contact).filter(Contact.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] is not None:
        status_value = update_data["status"]
        if status_value not in {s.value for s in ContactStatus}:
            raise HTTPException(status_code=422, detail="Invalid status")
        contact.status = ContactStatus(status_value)
        update_data.pop("status")

    for field, value in update_data.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, request: Request, db: Session = Depends(get_tenant_db_dependency)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact.owner_email != _get_owner_from_request(request):
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(contact)
    db.commit()
    return None


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


def import_contacts_internal(request: Request, file: UploadFile = File(...), db: Session = Depends(get_tenant_db_dependency)):
    """Import contacts from a CSV file. Columns supported: name, email, company, phone, position, status, notes"""
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        # Read CSV content (handle UTF-8 BOM)
        content_bytes = file.file.read()
        content_str = content_bytes.decode("utf-8-sig")
        if not content_str.strip():
            raise ValueError("empty")
        reader = csv.DictReader(io.StringIO(content_str))
        if not reader.fieldnames:
            raise ValueError("missing header")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file. Ensure it has a header row and UTF-8 encoding.")

    valid_status_values = {s.value for s in ContactStatus}

    created_count = 0
    updated_count = 0
    skipped_count = 0

    owner = _get_owner_from_request(request)

    for row in reader:
        # Normalize headers to lower-case keys
        normalized = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }

        email = normalized.get("email")
        name = normalized.get("name")
        if not email or not name:
            skipped_count += 1
            continue

        existing = db.query(Contact).filter(Contact.email == email, Contact.owner_email == owner).first()

        status_value = (normalized.get("status") or "prospect").lower()
        if status_value not in valid_status_values:
            status_value = "prospect"

        if existing:
            # Update minimal fields if provided
            if normalized.get("name"):
                existing.name = str(normalized.get("name"))
            if normalized.get("company"):
                existing.company = normalized.get("company") or None
            if normalized.get("phone"):
                existing.phone = normalized.get("phone") or None
            if normalized.get("position"):
                existing.position = normalized.get("position") or None
            if normalized.get("notes"):
                existing.notes = normalized.get("notes") or None
            existing.status = ContactStatus(status_value)
            # Do not change last_contact on import
            updated_count += 1
        else:
            contact = Contact(
                name=name,
                email=email,
                company=normalized.get("company") or None,
                phone=normalized.get("phone") or None,
                position=normalized.get("position") or None,
                status=ContactStatus(status_value),
                last_contact=datetime.utcnow(),
                notes=normalized.get("notes") or None,
                owner_email=owner,
            )
            db.add(contact)
            created_count += 1

    db.commit()

    return {"created": created_count, "updated": updated_count, "skipped": skipped_count}