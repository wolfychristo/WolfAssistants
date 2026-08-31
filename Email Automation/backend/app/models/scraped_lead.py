from sqlalchemy import Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class ScrapedLead(Base):
    __tablename__ = "scraped_leads"
    __table_args__ = {'extend_existing': True}  # No schema specified - uses tenant schema via search_path

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Source information
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    
    # Additional data
    company_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Status
    transferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Multi-tenant ownership
    owner_email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)

