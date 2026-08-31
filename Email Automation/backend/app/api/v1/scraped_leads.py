"""
API endpoints for managing scraped leads.
Allows users to review and transfer leads to contacts.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, exc
from app.core.database import get_tenant_db_dependency, tenant_engine
from app.models.scraped_lead import ScrapedLead
from app.models.contact import Contact, ContactStatus
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ScrapedLeadOut(BaseModel):
    id: int
    email: Optional[str]
    name: Optional[str]
    position: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    source_url: str
    source_type: str
    platform: str
    company_data: Optional[dict]
    validation_data: Optional[dict]
    transferred: bool
    transferred_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransferLeadRequest(BaseModel):
    lead_ids: List[int]
    status: Optional[str] = "prospect"


def _get_owner_from_request(request: Request) -> str:
    """Extract owner email from JWT token"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub", "")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def _ensure_scraped_leads_table(db: Session, owner_email: str) -> None:
    """Ensure scraped_leads table exists in the tenant schema.
    
    The db session already has search_path set to the tenant schema,
    so we can create the table directly without schema prefix.
    """
    try:
        # Try a simple query to check if table exists
        db.execute(text("SELECT 1 FROM scraped_leads LIMIT 1"))
        
        # Check if notes column exists (for existing tables created before notes was added)
        try:
            db.execute(text("SELECT notes FROM scraped_leads LIMIT 1"))
        except (exc.ProgrammingError, exc.OperationalError) as col_error:
            error_str = str(col_error).lower()
            if 'column' in error_str and 'does not exist' in error_str and 'notes' in error_str:
                logger.info(f"scraped_leads table missing notes column for {owner_email}, adding it...")
                try:
                    db.rollback()
                except Exception:
                    pass
                try:
                    db.execute(text("ALTER TABLE scraped_leads ADD COLUMN IF NOT EXISTS notes TEXT"))
                    db.commit()
                    logger.info(f"Added notes column to scraped_leads table for {owner_email}")
                except Exception as alter_error:
                    db.rollback()
                    error_msg = str(alter_error)
                    logger.error(f"Failed to add notes column: {error_msg}")
                    # Check if it's a transaction error and retry
                    if 'InFailedSqlTransaction' in error_msg or 'transaction is aborted' in error_msg.lower():
                        try:
                            db.rollback()
                            db.execute(text("ALTER TABLE scraped_leads ADD COLUMN IF NOT EXISTS notes TEXT"))
                            db.commit()
                            logger.info(f"Added notes column to scraped_leads table for {owner_email} after retry")
                        except Exception as retry_error:
                            db.rollback()
                            logger.error(f"Failed to add notes column after retry: {retry_error}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Failed to add notes column after retry: {str(retry_error)}"
                            )
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to add notes column: {error_msg}"
                        )
            else:
                # Different column error, re-raise
                raise
    except (exc.ProgrammingError, exc.OperationalError) as e:
        error_str = str(e).lower()
        # Check if error is about table not existing
        if 'does not exist' in error_str or 'relation' in error_str or 'no such table' in error_str:
            logger.info(f"scraped_leads table not found for {owner_email}, creating it...")
            # CRITICAL: Rollback the failed transaction before creating the table
            # PostgreSQL aborts the transaction when a query fails, so we must rollback
            try:
                db.rollback()
            except Exception:
                pass  # Ignore rollback errors if transaction is already clean
            
            try:
                # Since db session has search_path set to tenant schema, create table without schema prefix
                create_table_sql = '''
                CREATE TABLE IF NOT EXISTS scraped_leads (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255),
                    name VARCHAR(255),
                    position VARCHAR(255),
                    company VARCHAR(255),
                    phone VARCHAR(255),
                    address TEXT,
                    notes TEXT,
                    source_url VARCHAR(500) NOT NULL,
                    source_type VARCHAR(100) NOT NULL,
                    platform VARCHAR(100) NOT NULL,
                    company_data JSONB,
                    validation_data JSONB,
                    transferred BOOLEAN NOT NULL DEFAULT FALSE,
                    transferred_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    owner_email VARCHAR(255)
                );
                
                CREATE INDEX IF NOT EXISTS idx_scraped_leads_owner_email ON scraped_leads(owner_email);
                CREATE INDEX IF NOT EXISTS idx_scraped_leads_email ON scraped_leads(email);
                CREATE INDEX IF NOT EXISTS idx_scraped_leads_transferred ON scraped_leads(transferred);
                CREATE INDEX IF NOT EXISTS idx_scraped_leads_platform ON scraped_leads(platform);
                CREATE INDEX IF NOT EXISTS idx_scraped_leads_created_at ON scraped_leads(created_at DESC);
                '''
                
                db.execute(text(create_table_sql))
                db.commit()
                
                logger.info(f"Created scraped_leads table for {owner_email}")
            except Exception as create_error:
                db.rollback()
                error_msg = str(create_error)
                logger.error(f"Failed to create scraped_leads table: {error_msg}")
                
                # Check if it's a transaction error and retry once
                if 'InFailedSqlTransaction' in error_msg or 'transaction is aborted' in error_msg.lower():
                    try:
                        db.rollback()
                        # Retry table creation with fresh transaction
                        db.execute(text(create_table_sql))
                        db.commit()
                        logger.info(f"Created scraped_leads table for {owner_email} after retry")
                    except Exception as retry_error:
                        db.rollback()
                        logger.error(f"Failed to create scraped_leads table after retry: {retry_error}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to create scraped_leads table after retry: {str(retry_error)}"
                        )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create scraped_leads table: {error_msg}"
                    )
        else:
            # Re-raise if it's a different error
            raise


@router.get("/", response_model=List[ScrapedLeadOut])
def list_scraped_leads(
    request: Request,
    transferred: Optional[bool] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_tenant_db_dependency)
):
    """List all scraped leads for the current user"""
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
        # Continue anyway - table might exist
    
    query = db.query(ScrapedLead).filter(ScrapedLead.owner_email == owner_email)
    
    if transferred is not None:
        query = query.filter(ScrapedLead.transferred == transferred)
    
    if platform:
        query = query.filter(ScrapedLead.platform == platform)
    
    leads = query.order_by(ScrapedLead.created_at.desc()).all()
    return leads


@router.post("/transfer")
def transfer_leads_to_contacts(
    request: Request,
    payload: TransferLeadRequest,
    db: Session = Depends(get_tenant_db_dependency)
):
    """Transfer scraped leads to contacts (one or bulk)"""
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
        # Continue anyway - table might exist
    
    # Validate status
    if payload.status and payload.status not in {s.value for s in ContactStatus}:
        raise HTTPException(status_code=422, detail="Invalid status")
    
    # Get leads
    leads = db.query(ScrapedLead).filter(
        ScrapedLead.id.in_(payload.lead_ids),
        ScrapedLead.owner_email == owner_email,
        ScrapedLead.transferred == False
    ).all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found or already transferred")
    
    transferred_contacts = []
    skipped_contacts = []
    
    for lead in leads:
        # Validate: Must have at least email or phone
        if not lead.email and not lead.phone:
            skipped_contacts.append({
                "lead_id": lead.id,
                "name": lead.name or "Unknown",
                "reason": "Missing email and phone"
            })
            continue
        
        # Generate email if only phone provided
        email = lead.email
        if not email and lead.phone:
            email = f"noemail_{lead.phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}@placeholder.com"
        
        # Check if contact already exists
        existing = db.query(Contact).filter(
            Contact.email == email,
            Contact.owner_email == owner_email
        ).first()
        
        if existing:
            skipped_contacts.append({
                "lead_id": lead.id,
                "name": lead.name or email,
                "reason": "Contact already exists"
            })
            # Mark lead as transferred even if skipped
            lead.transferred = True
            lead.transferred_at = datetime.utcnow()
            continue
        
        # Create contact - include notes from lead if available
        transfer_note = f"Transferred from {lead.platform}: {lead.source_url}"
        if lead.notes:
            transfer_note = f"{lead.notes}\n\n{transfer_note}"
        
        contact = Contact(
            name=lead.name or "Unknown",
            email=email,
            company=lead.company,
            phone=lead.phone,
            position=lead.position,
            status=ContactStatus(payload.status or "prospect"),
            notes=transfer_note,
            owner_email=owner_email,
            last_contact=datetime.utcnow()
        )
        
        try:
            db.add(contact)
            db.commit()
            db.refresh(contact)
            transferred_contacts.append(contact)
            
            # Mark lead as transferred
            lead.transferred = True
            lead.transferred_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Transferred lead {lead.id} to contact {contact.id} for user {owner_email}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to transfer lead {lead.id}: {e}")
            skipped_contacts.append({
                "lead_id": lead.id,
                "name": lead.name or email or "Unknown",
                "reason": f"Database error: {str(e)}"
            })
    
    return {
        "success": True,
        "transferred_count": len(transferred_contacts),
        "skipped_count": len(skipped_contacts),
        "transferred_contacts": [
            {
                "id": c.id,
                "email": c.email,
                "name": c.name,
                "company": c.company
            }
            for c in transferred_contacts
        ],
        "skipped_contacts": skipped_contacts
    }


class UpdateLeadNotesRequest(BaseModel):
    notes: Optional[str] = None


@router.patch("/{lead_id}/notes")
def update_lead_notes(
    lead_id: int,
    request: Request,
    payload: UpdateLeadNotesRequest,
    db: Session = Depends(get_tenant_db_dependency)
):
    """Update notes for a scraped lead"""
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
    
    lead = db.query(ScrapedLead).filter(
        ScrapedLead.id == lead_id,
        ScrapedLead.owner_email == owner_email
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.notes = payload.notes
    db.commit()
    db.refresh(lead)
    
    return {"success": True, "notes": lead.notes}


@router.delete("/{lead_id}")
def delete_scraped_lead(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db_dependency)
):
    """Delete a scraped lead"""
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
        # Continue anyway - table might exist
    
    lead = db.query(ScrapedLead).filter(
        ScrapedLead.id == lead_id,
        ScrapedLead.owner_email == owner_email
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    db.delete(lead)
    db.commit()
    
    return {"success": True, "message": "Lead deleted"}


@router.post("/delete-multiple")
def delete_multiple_leads(
    request: Request,
    lead_ids: List[int],
    db: Session = Depends(get_tenant_db_dependency)
):
    """Delete multiple scraped leads"""
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
        # Continue anyway - table might exist
    
    leads = db.query(ScrapedLead).filter(
        ScrapedLead.id.in_(lead_ids),
        ScrapedLead.owner_email == owner_email
    ).all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found")
    
    for lead in leads:
        db.delete(lead)
    
    db.commit()
    
    return {"success": True, "message": f"Deleted {len(leads)} lead(s)"}

