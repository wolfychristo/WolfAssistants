from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class BusinessProfile(Base):
    """Business context & sales goal memory for the AI Sales Representative."""
    __tablename__ = "business_profiles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    product_description = Column(Text, nullable=False)        # What you sell
    target_market = Column(Text, nullable=False)              # Who you sell to
    geographic_market = Column(String, nullable=True)         # E.g., US, India, Global
    price_range = Column(String, nullable=True)                # E.g. $5k-$20k / month
    value_proposition = Column(Text, nullable=True)            # Key benefits / transformation
    brand_voice = Column(String, default="Professional")
    approved_case_studies = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)                   # Competitors, undesirable sectors
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ICPConfiguration(Base):
    """Structured Ideal Customer Profile parameters created by the AI ICP Builder."""
    __tablename__ = "icp_configurations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    raw_prompt = Column(Text, nullable=False)                   # Natural language input prompt
    structured_criteria = Column(JSON, nullable=False)          # Parsed JSON: industry, company_size, roles, signals, tech
    scoring_weights = Column(JSON, nullable=False)              # Scoring weight rules for 0-100 total
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProspectProfile(Base):
    """Enriched prospect details, research summary, and transparent lead score."""
    __tablename__ = "prospect_profiles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=True)
    company_name = Column(String, nullable=False)
    company_website = Column(String, nullable=True)
    title = Column(String, nullable=True)                       # Buyer role / decision maker
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    # AI Lead Scoring & Transparent Rationales
    icp_score = Column(Integer, default=0)                      # Total score (0-100)
    score_breakdown = Column(JSON, nullable=True)                # Detailed breakdown breakdown {icp_fit: 25, company_size: 18, ...}
    score_rationale = Column(Text, nullable=True)                # Text explanation of the score
    
    # AI Prospect Research
    research_summary = Column(Text, nullable=True)               # Human-readable summary
    verified_facts = Column(JSON, nullable=True)                 # Verified factual data
    inferred_insights = Column(JSON, nullable=True)              # AI inferred capabilities/needs
    likely_pain_points = Column(JSON, nullable=True)             # Detected problems to target
    
    # Lifecycle & Pipeline Stage
    # Discovered -> Researched -> Qualified -> Outreach Prepared -> Contacted -> Follow-up -> Replied -> Qualified Opportunity -> Meeting Booked -> Won / Lost
    stage = Column(String, default="Discovered", index=True)
    source = Column(String, default="Imported")                  # Import, Scraper, API
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CadenceSequence(Base):
    """Multi-step outreach & follow-up sequence."""
    __tablename__ = "cadence_sequences"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CadenceStep(Base):
    """Individual step within a multi-touch cadence sequence."""
    __tablename__ = "cadence_steps"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("cadence_sequences.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    delay_days = Column(Integer, default=3)                     # Days after previous step
    template_subject = Column(String, nullable=False)
    template_body = Column(Text, nullable=False)


class ReplyIntelligence(Base):
    """Inbound reply analysis, intent classification, and AI response suggestions."""
    __tablename__ = "reply_intelligence"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospect_profiles.id"), nullable=False)
    user_email = Column(String, index=True, nullable=False)
    inbound_message = Column(Text, nullable=False)
    
    # Intent Classification
    intent = Column(String, nullable=False)                     # Interested, Asking Pricing, Objection, OOO, Unsubscribe, etc.
    confidence_score = Column(Float, default=0.90)
    recommended_action = Column(String, nullable=False)         # Propose Meeting, Send Info, Handle Objection, Archive
    suggested_reply = Column(Text, nullable=True)                # AI drafted reply
    approval_status = Column(String, default="Pending")          # Pending, Approved, Edited, Rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SalesOpportunity(Base):
    """Opportunity pipeline card for tracking qualified deals."""
    __tablename__ = "sales_opportunities"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospect_profiles.id"), nullable=False)
    user_email = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    estimated_value = Column(Float, default=0.0)
    stage = Column(String, default="Qualified Opportunity")     # Qualified Opportunity -> Meeting Booked -> Proposal -> Won / Lost
    meeting_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
