from sqlalchemy import Integer, String, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
import uuid
from app.core.database import Base


class ContactStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    prospect = "prospect"


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ContactStatus] = mapped_column(Enum(ContactStatus), default=ContactStatus.prospect, nullable=False)
    last_contact: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Multi-tenant ownership (set to creator's email)
    owner_email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    # Follow-up tracking
    first_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    followup1_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    followup2_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reply_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_intent: Mapped[str | None] = mapped_column(String, nullable=True)


