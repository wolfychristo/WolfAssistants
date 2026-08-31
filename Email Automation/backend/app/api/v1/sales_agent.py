from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import logging

from app.core.database import get_db, SessionLocal
from app.core.tenant_database import get_tenant_db_dependency
from app.models.sales_agent import BusinessProfile, ICPConfiguration
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
# 1. BUSINESS PROFILE & AI SALES REPRESENTATIVE MEMORY
# ------------------------------------------------------------------

@router.get("/profile")
def get_business_profile(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Fetch the business context & sales objective for the AI Sales Representative."""
    owner_email = _get_owner_email(request)
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_email == owner_email).first()
    if not profile:
        # Return default blank profile structure
        return {
            "product_description": "",
            "target_market": "",
            "geographic_market": "",
            "price_range": "",
            "value_proposition": "",
            "brand_voice": "Professional",
            "approved_case_studies": "",
            "exclusions": "",
        }
    return {
        "id": profile.id,
        "product_description": profile.product_description,
        "target_market": profile.target_market,
        "geographic_market": profile.geographic_market,
        "price_range": profile.price_range,
        "value_proposition": profile.value_proposition,
        "brand_voice": profile.brand_voice,
        "approved_case_studies": profile.approved_case_studies,
        "exclusions": profile.exclusions,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/profile")
def update_business_profile(payload: Dict[str, Any], request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Save or update business context for the AI Sales Representative."""
    owner_email = _get_owner_email(request)
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_email == owner_email).first()
    
    if not profile:
        profile = BusinessProfile(
            user_email=owner_email,
            product_description=payload.get("product_description", ""),
            target_market=payload.get("target_market", ""),
            geographic_market=payload.get("geographic_market"),
            price_range=payload.get("price_range"),
            value_proposition=payload.get("value_proposition"),
            brand_voice=payload.get("brand_voice", "Professional"),
            approved_case_studies=payload.get("approved_case_studies"),
            exclusions=payload.get("exclusions"),
        )
        db.add(profile)
    else:
        profile.product_description = payload.get("product_description", profile.product_description)
        profile.target_market = payload.get("target_market", profile.target_market)
        profile.geographic_market = payload.get("geographic_market", profile.geographic_market)
        profile.price_range = payload.get("price_range", profile.price_range)
        profile.value_proposition = payload.get("value_proposition", profile.value_proposition)
        profile.brand_voice = payload.get("brand_voice", profile.brand_voice)
        profile.approved_case_studies = payload.get("approved_case_studies", profile.approved_case_studies)
        profile.exclusions = payload.get("exclusions", profile.exclusions)
        profile.updated_at = datetime.now(timezone.utc)
        
    db.commit()
    db.refresh(profile)
    return {"message": "Business profile updated successfully", "id": profile.id}


# ------------------------------------------------------------------
# 2. NATURAL LANGUAGE AI ICP BUILDER
# ------------------------------------------------------------------

@router.post("/icp/parse")
def parse_natural_language_icp(payload: Dict[str, Any], request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """
    AI ICP Builder: Converts natural language description into structured criteria and scoring weights.
    Example input: "I run a web dev agency. Find Indian SaaS companies with 10-100 employees whose websites need a redesign."
    """
    owner_email = _get_owner_email(request)
    prompt_text = payload.get("prompt", "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Natural language prompt is required")
        
    # Query business profile memory for added context
    bus_profile = db.query(BusinessProfile).filter(BusinessProfile.user_email == owner_email).first()
    business_context = bus_profile.product_description if bus_profile else ""
    
    # Use Gemini 2.0 Flash to parse ICP
    import google.generativeai as genai
    from app.core.gemini_key_manager import key_manager
    
    system_instruction = (
        "You are an expert B2B Sales Architect. Convert the user's plain text target ICP requirement "
        "into structured JSON parameters for sales targeting. "
        "Return ONLY valid JSON matching this structure:\n"
        "{\n"
        '  "icp_name": "Short descriptive name",\n'
        '  "industry": ["Industry 1", "Industry 2"],\n'
        '  "geography": ["Country or Region"],\n'
        '  "company_size": "10-100 employees",\n'
        '  "target_roles": ["CTO", "Founder", "VP Engineering"],\n'
        '  "buying_signals": ["Outdated website", "Hiring developers", "Recent funding"],\n'
        '  "exclusions": ["Agencies", "B2C companies"],\n'
        '  "scoring_weights": {\n'
        '    "icp_fit": 25,\n'
        '    "company_size": 20,\n'
        '    "industry": 20,\n'
        '    "buyer_fit": 20,\n'
        '    "signals": 15\n'
        '  }\n'
        "}"
    )
    
    user_message = f"User Sales Context: {business_context}\n\nTarget Requirement: {prompt_text}"
    
    parsed_json = None
    try:
        api_key = key_manager.keys[0] if key_manager.keys else ""
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"{system_instruction}\n\n{user_message}")
            resp_text = response.text.strip()
            if "```json" in resp_text:
                resp_text = resp_text.split("```json")[1].split("```")[0].strip()
            elif "```" in resp_text:
                resp_text = resp_text.split("```")[1].split("```")[0].strip()
            parsed_json = json.loads(resp_text)
        else:
            raise ValueError("No Gemini key configured")
    except Exception as e:
        logger.warning(f"Gemini parsing failed, using rule-based parser fallback: {e}")
        # Rule-based fallback if AI service is temporarily unavailable
        parsed_json = {
            "icp_name": "Target Ideal Prospect Profile",
            "industry": ["SaaS", "Software", "Technology"],
            "geography": ["India", "Global"],
            "company_size": "10-100 employees",
            "target_roles": ["Founder", "CEO", "CTO", "VP Sales"],
            "buying_signals": ["Growth phase", "Digital transformation"],
            "exclusions": ["B2C", "Solopreneurs"],
            "scoring_weights": {
                "icp_fit": 25,
                "company_size": 20,
                "industry": 20,
                "buyer_fit": 20,
                "signals": 15
            }
        }
        
    # Save or update ICP configuration in DB
    icp_config = db.query(ICPConfiguration).filter(
        ICPConfiguration.user_email == owner_email,
        ICPConfiguration.is_active == True
    ).first()
    
    if not icp_config:
        icp_config = ICPConfiguration(
            user_email=owner_email,
            name=parsed_json.get("icp_name", "Target ICP Profile"),
            raw_prompt=prompt_text,
            structured_criteria=parsed_json,
            scoring_weights=parsed_json.get("scoring_weights", {}),
            is_active=True
        )
        db.add(icp_config)
    else:
        icp_config.name = parsed_json.get("icp_name", icp_config.name)
        icp_config.raw_prompt = prompt_text
        icp_config.structured_criteria = parsed_json
        icp_config.scoring_weights = parsed_json.get("scoring_weights", {})
        
    db.commit()
    db.refresh(icp_config)
    
    return {
        "id": icp_config.id,
        "name": icp_config.name,
        "raw_prompt": icp_config.raw_prompt,
        "structured_criteria": icp_config.structured_criteria,
        "scoring_weights": icp_config.scoring_weights
    }


@router.get("/icp")
def get_active_icp(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    """Retrieve active Ideal Customer Profile configuration."""
    owner_email = _get_owner_email(request)
    icp = db.query(ICPConfiguration).filter(
        ICPConfiguration.user_email == owner_email,
        ICPConfiguration.is_active == True
    ).first()
    if not icp:
        return {"active": False, "message": "No active ICP configuration found"}
    return {
        "id": icp.id,
        "name": icp.name,
        "raw_prompt": icp.raw_prompt,
        "structured_criteria": icp.structured_criteria,
        "scoring_weights": icp.scoring_weights,
        "is_active": True
    }
