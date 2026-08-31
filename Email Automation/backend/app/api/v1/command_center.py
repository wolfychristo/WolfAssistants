from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db, SessionLocal
from app.core.tenant_database import get_tenant_db_dependency
from app.models.sales_agent import ProspectProfile, ReplyIntelligence, SalesOpportunity, ICPConfiguration
from app.models.meeting import Meeting
from jose import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_owner_email(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return str(email)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ------------------------------------------------------------------
# 1. AI SALES REPRESENTATIVE DAILY BRIEFING & AGENT STATUS
# ------------------------------------------------------------------

@router.get("/daily-summary")
def get_daily_summary(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """
    AI Sales Representative Command Center Daily Briefing.
    Provides outcome-focused metrics instead of vanity email metrics:
    - Prospects Found
    - High-Fit Prospects Identified (Score >= 75)
    - Personalized Messages Prepared
    - Messages Sent
    - Replies Analyzed
    - Qualified Opportunities (North-Star Metric)
    - Meetings Booked
    """
    owner_email = _get_owner_email(request)
    
    total_prospects = db.query(ProspectProfile).filter(ProspectProfile.user_email == owner_email).count()
    high_fit_prospects = db.query(ProspectProfile).filter(ProspectProfile.user_email == owner_email, ProspectProfile.icp_score >= 75).count()
    outreach_prepared = db.query(ProspectProfile).filter(ProspectProfile.user_email == owner_email, ProspectProfile.stage == "Outreach Prepared").count()
    contacted_count = db.query(ProspectProfile).filter(ProspectProfile.user_email == owner_email, ProspectProfile.stage == "Contacted").count()
    replies_count = db.query(ReplyIntelligence).filter(ReplyIntelligence.user_email == owner_email).count()
    qualified_opps = db.query(SalesOpportunity).filter(SalesOpportunity.user_email == owner_email).count()
    meetings_booked = db.query(Meeting).filter(Meeting.owner_email == owner_email).count()
    
    # Calculate pipeline value
    opps = db.query(SalesOpportunity).filter(SalesOpportunity.user_email == owner_email).all()
    pipeline_value = sum(o.estimated_value or 0.0 for o in opps)
    
    # AI Executive Summary Message
    active_icp = db.query(ICPConfiguration).filter(ICPConfiguration.user_email == owner_email, ICPConfiguration.is_active == True).first()
    icp_name = active_icp.name if active_icp else "Default Target Profile"
    
    greeting = f"Good morning. Here is what I accomplished for your target ICP ({icp_name}):"
    ai_recommendation = (
        f"I have identified {high_fit_prospects} high-fit prospects with ICP scores of 75+. "
        f"There are currently {qualified_opps} qualified sales conversations requiring your review for closing."
    )
    
    return {
        "greeting": greeting,
        "ai_recommendation": ai_recommendation,
        "metrics": {
            "prospects_found": total_prospects,
            "high_fit_prospects": high_fit_prospects,
            "personalized_prepared": outreach_prepared,
            "messages_sent": contacted_count,
            "replies_analyzed": replies_count,
            "qualified_conversations": qualified_opps, # NORTH-STAR METRIC
            "meetings_booked": meetings_booked,
            "pipeline_value": pipeline_value,
        },
        "agent_status": "Ready & Monitoring Replies"
    }


# ------------------------------------------------------------------
# 2. SALES PIPELINE KANBAN
# ------------------------------------------------------------------

@router.get("/pipeline")
def get_sales_pipeline(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Fetch sales opportunity cards grouped by deal stage for Kanban board view."""
    owner_email = _get_owner_email(request)
    opps = db.query(SalesOpportunity).filter(SalesOpportunity.user_email == owner_email).all()
    
    pipeline_stages = {
        "Qualified Opportunity": [],
        "Meeting Booked": [],
        "Proposal": [],
        "Won": [],
        "Lost": []
    }
    
    for o in opps:
        prospect = db.query(ProspectProfile).filter(ProspectProfile.id == o.prospect_id).first()
        prospect_name = f"{prospect.first_name or ''} {prospect.last_name or ''}".strip() if prospect else "Prospect"
        company = prospect.company_name if prospect else "Company"
        
        item = {
            "id": o.id,
            "prospect_id": o.prospect_id,
            "title": o.title,
            "prospect_name": prospect_name,
            "company_name": company,
            "estimated_value": o.estimated_value,
            "stage": o.stage,
            "meeting_date": o.meeting_date.isoformat() if o.meeting_date else None,
            "notes": o.notes,
        }
        
        if o.stage in pipeline_stages:
            pipeline_stages[o.stage].append(item)
        else:
            pipeline_stages["Qualified Opportunity"].append(item)
            
    return pipeline_stages
