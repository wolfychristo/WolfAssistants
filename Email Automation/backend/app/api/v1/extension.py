"""
Extension API endpoint for multi-platform lead scraping.
Supports: Websites, LinkedIn, Google Maps, Instagram
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, exc
from app.core.database import get_tenant_db_dependency, AccountsSessionLocal, tenant_engine
from app.models.contact import Contact, ContactStatus
from app.models.scraped_lead import ScrapedLead
from app.models.user import User
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ScrapedContact(BaseModel):
    """Scraped contact data - only real fields, no AI filling"""
    email: Optional[str] = None
    name: Optional[str] = None
    position: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    source_url: str
    source_type: str


class ScrapeAndAddRequest(BaseModel):
    contacts: List[ScrapedContact]
    company: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    platform: str = "website"


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


@router.post("/scrape-and-add")
async def scrape_and_add_multi_platform(
    request: Request,
    payload: ScrapeAndAddRequest,
    db: Session = Depends(get_tenant_db_dependency)
):
    """
    Save scraped leads from multiple platforms (Website, LinkedIn, Google Maps, Instagram).
    Leads are saved to scraped_leads table for review before transferring to contacts.
    """
    owner_email = _get_owner_from_request(request)
    
    # Ensure scraped_leads table exists
    try:
        _ensure_scraped_leads_table(db, owner_email)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring scraped_leads table: {e}")
        # Continue anyway - table might exist
    
    added_leads = []
    skipped_leads = []
    
    # Validate payload
    if not payload.contacts:
        return {
            "success": False,
            "error": "No contacts provided",
            "added_count": 0,
            "skipped_count": 0
        }
    
    # Process contacts - save as scraped leads
    for contact_data in payload.contacts:
        # Validate: Email is REQUIRED for personalized emails
        if not contact_data.email or not contact_data.email.strip():
            skipped_leads.append({
                "contact": contact_data.name or "Unknown",
                "reason": "Email is required for personalized emails"
            })
            continue
        
        # Basic email format validation
        email = contact_data.email.strip().lower()
        if '@' not in email or '.' not in email.split('@')[1]:
            skipped_leads.append({
                "contact": contact_data.name or email,
                "reason": "Invalid email format"
            })
            continue
        
        try:
            # Check if lead already exists (by source_url and owner)
            existing = db.query(ScrapedLead).filter(
                ScrapedLead.source_url == contact_data.source_url,
                ScrapedLead.owner_email == owner_email,
                ScrapedLead.transferred == False
            ).first()
            
            if existing:
                skipped_leads.append({
                    "contact": contact_data.name or contact_data.email or "Unknown",
                    "reason": "Lead already exists"
                })
                continue
            
            # Create scraped lead (email is already validated above)
            lead = ScrapedLead(
                email=email,  # Use normalized email
                name=contact_data.name,
                position=contact_data.position,
                company=contact_data.company,
                phone=contact_data.phone,
                address=contact_data.address,
                notes=contact_data.notes,  # Add notes field
                source_url=contact_data.source_url,
                source_type=contact_data.source_type,
                platform=payload.platform,
                company_data=payload.company,
                validation_data=payload.validation,
                owner_email=owner_email
            )
            
            db.add(lead)
            db.commit()
            db.refresh(lead)
            added_leads.append(lead)
            logger.info(f"Added scraped lead {lead.id} for user {owner_email}")
        except (exc.ProgrammingError, exc.OperationalError) as db_error:
            error_str = str(db_error).lower()
            # If table doesn't exist, try to create it and retry
            if 'does not exist' in error_str or 'relation' in error_str or 'no such table' in error_str:
                db.rollback()
                try:
                    _ensure_scraped_leads_table(db, owner_email)
                    # Retry creating the lead (email is already validated above)
                    email = contact_data.email.strip().lower()
                    lead = ScrapedLead(
                        email=email,  # Use normalized email
                        name=contact_data.name,
                        position=contact_data.position,
                        company=contact_data.company,
                        phone=contact_data.phone,
                        address=contact_data.address,
                        notes=contact_data.notes,  # Add notes field
                        source_url=contact_data.source_url,
                        source_type=contact_data.source_type,
                        platform=payload.platform,
                        company_data=payload.company,
                        validation_data=payload.validation,
                        owner_email=owner_email
                    )
                    db.add(lead)
                    db.commit()
                    db.refresh(lead)
                    added_leads.append(lead)
                    logger.info(f"Added scraped lead {lead.id} for user {owner_email} after table creation")
                except Exception as retry_error:
                    db.rollback()
                    logger.error(f"Failed to add scraped lead after table creation: {retry_error}")
                    skipped_leads.append({
                        "contact": contact_data.name or contact_data.email or "Unknown",
                        "reason": f"Database error: {str(retry_error)}"
                    })
            else:
                db.rollback()
                logger.error(f"Failed to add scraped lead {contact_data.email or contact_data.name}: {db_error}")
                skipped_leads.append({
                    "contact": contact_data.name or contact_data.email or "Unknown",
                    "reason": f"Database error: {str(db_error)}"
                })
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add scraped lead {contact_data.email or contact_data.name}: {e}")
            skipped_leads.append({
                "contact": contact_data.name or contact_data.email or "Unknown",
                "reason": f"Error: {str(e)}"
            })
    
    return {
        "success": True,
        "added_count": len(added_leads),
        "skipped_count": len(skipped_leads),
        "platform": payload.platform,
        "validation_included": payload.validation is not None,
        "added_leads": [
            {
                "id": l.id,
                "email": l.email,
                "name": l.name,
                "company": l.company
            }
            for l in added_leads
        ],
        "skipped_leads": skipped_leads
    }

