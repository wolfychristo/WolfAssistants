"""
Purpose-aware research module for auto-generating contact notes.
Includes website validation integration.
"""
import logging
from typing import Dict, Any, Optional, List
from app.core.gemini_service import WolfyService
from app.models.contact import Contact

logger = logging.getLogger(__name__)


def determine_research_focus(user_profession: str | None, user_position: str | None) -> dict:
    """
    Determine what to research based on user's purpose.
    """
    profession = " ".join([
        (user_profession or "").lower(),
        (user_position or "").lower()
    ]).strip()
    
    # Sales / Business Development
    if any(kw in profession for kw in ["sales", "business development", "bd", "account executive"]):
        return {
            "focus": "sales",
            "research_areas": [
                "company growth and funding",
                "recent news and announcements",
                "pain points and challenges",
                "buying signals",
                "company size and revenue",
                "industry trends affecting them"
            ]
        }
    
    # UX/UI Design
    elif any(kw in profession for kw in ["ux", "ui", "design", "designer", "user experience"]):
        return {
            "focus": "ux_ui",
            "research_areas": [
                "website design and user experience",
                "navigation and usability issues",
                "mobile responsiveness",
                "design patterns and trends",
                "accessibility concerns",
                "conversion optimization opportunities"
            ]
        }
    
    # Web Development
    elif any(kw in profession for kw in ["web", "developer", "development", "programmer", "software engineer", "frontend", "backend", "full stack"]):
        return {
            "focus": "web_dev",
            "research_areas": [
                "website technical stack and architecture",
                "performance issues",
                "security vulnerabilities",
                "modernization opportunities",
                "scalability concerns",
                "integration possibilities"
            ]
        }
    
    # Marketing
    elif any(kw in profession for kw in ["marketing", "marketer", "growth", "seo", "content"]):
        return {
            "focus": "marketing",
            "research_areas": [
                "SEO and content strategy",
                "social media presence",
                "brand positioning",
                "marketing campaigns and messaging",
                "competitor analysis",
                "lead generation strategies"
            ]
        }
    
    # Consulting / Business
    elif any(kw in profession for kw in ["consultant", "consulting", "advisor", "business", "strategy"]):
        return {
            "focus": "consulting",
            "research_areas": [
                "business challenges and opportunities",
                "market position and competition",
                "operational efficiency",
                "growth strategies",
                "industry trends",
                "potential collaboration areas"
            ]
        }
    
    # Default: General research
    else:
        return {
            "focus": "general",
            "research_areas": [
                "company overview and mission",
                "recent news and updates",
                "industry position",
                "key products or services",
                "team and leadership",
                "potential collaboration areas"
            ]
        }


async def auto_research_contact(
    contact: Contact,
    owner: str,
    user_profession: str | None = None,
    user_position: str | None = None,
    user_company: str | None = None,
    company_data: Dict[str, Any] | None = None,
    validation_results: Dict[str, Any] | None = None,
    platform: str = "website"
) -> str:
    """
    Automatically research a contact and generate personalized notes
    tailored to the USER'S PURPOSE with validation results.
    """
    # Get user profile if not provided
    if not user_profession or not user_position:
        from app.core.database import SessionLocal
        from app.models.user import User
        
        db_user = SessionLocal()
        try:
            user = db_user.query(User).filter(User.email == owner).first()
            if user:
                user_profession = user_profession or getattr(user, "heard_about_us", None)
                user_position = user_position or getattr(user, "position_title", None)
                user_company = user_company or getattr(user, "company_name", None)
        finally:
            db_user.close()
    
    # Determine research focus
    research_focus = determine_research_focus(user_profession, user_position)
    
    # Gather raw research data
    raw_research = _gather_company_research(
        contact=contact,
        company_data=company_data,
        validation_results=validation_results,
        research_focus=research_focus
    )
    
    # Generate purpose-specific notes using AI
    notes = await generate_purpose_specific_notes(
        contact=contact,
        raw_research=raw_research,
        user_profession=user_profession,
        user_position=user_position,
        user_company=user_company,
        research_focus=research_focus,
        owner=owner,
        platform=platform
    )
    
    return notes


def _gather_company_research(
    contact: Contact,
    company_data: Dict[str, Any] | None,
    validation_results: Dict[str, Any] | None,
    research_focus: dict
) -> dict:
    """
    Gather research data from available sources.
    """
    research = {
        "company_name": contact.company or "Unknown",
        "contact_name": contact.name or "Unknown",
        "contact_email": contact.email or "Unknown",
        "contact_position": contact.position or "Unknown",
        "research_focus": research_focus["focus"],
        "research_areas": research_focus["research_areas"]
    }
    
    # Add company data if available
    if company_data:
        research["company_data"] = {
            "industry": company_data.get("industry"),
            "size": company_data.get("company_size"),
            "location": company_data.get("location"),
            "description": company_data.get("description"),
            "website": company_data.get("website"),
            "tech_stack": company_data.get("tech_stack"),
            "social_links": company_data.get("social_links")
        }
    
    # Add validation results if available
    if validation_results:
        research["validation_results"] = {
            "seo_issues": validation_results.get("seo_issues", []),
            "ux_issues": validation_results.get("ux_issues", []),
            "performance_issues": validation_results.get("performance_issues", []),
            "accessibility_issues": validation_results.get("accessibility_issues", []),
            "overall_score": validation_results.get("overall_score"),
            "recommendations": validation_results.get("recommendations", [])
        }
    
    return research


async def generate_purpose_specific_notes(
    contact: Contact,
    raw_research: dict,
    user_profession: str | None,
    user_position: str | None,
    user_company: str | None,
    research_focus: dict,
    owner: str,
    platform: str = "website"
) -> str:
    """
    Generate purpose-specific research notes using AI.
    """
    wolfy_service = WolfyService()
    
    profession_context = f"{user_profession or 'Professional'}"
    if user_position:
        profession_context += f" ({user_position})"
    if user_company:
        profession_context += f" at {user_company}"
    
    prompt = f"""Research notes for: {contact.name} at {contact.company or 'Unknown Company'}

Contact Info:
- Name: {contact.name or 'Unknown'}
- Email: {contact.email or 'Unknown'}
- Position: {contact.position or 'Unknown'}

Company Info:
{raw_research.get('company_data', {})}

Research Focus: {research_focus['focus']}
Areas to investigate: {', '.join(research_focus['research_areas'])}

Validation Results (if available):
{raw_research.get('validation_results', {})}

Generate research notes from the perspective of a {profession_context} who wants to:
- Understand how {contact.company or 'this company'} could benefit from what {profession_context} can offer
- Write as research notes, NOT as an email draft
- If website issues were found, mention them as improvement opportunities

Format as natural research notes that will be used to personalize a cold email.
"""
    
    try:
        result = await wolfy_service.make_request(
            user_email=owner,
            endpoint="contact_research",
            request_type="generate_research_notes",
            prompt_func=lambda ctx: prompt,
            context={
                "contact": contact.name,
                "company": contact.company,
                "profession": user_profession,
                "focus": research_focus["focus"]
            },
            use_cache=True,
            priority="normal"
        )
        
        if result.get('success'):
            return result.get('response', '').strip()
    except Exception as e:
        logger.error(f"Failed to generate research notes: {e}")
    
    return ""

