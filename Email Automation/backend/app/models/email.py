from sqlalchemy import Integer, String, Enum, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
import uuid
from app.core.database import Base


class EmailStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"  # retained for backward-compat; no longer used by UI
    sent = "sent"
    received = "received"
    replied = "replied"
    archived = "archived"
    trashed = "trashed"
    spam = "spam"


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    to_address: Mapped[str] = mapped_column(String, nullable=False)
    from_address: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus), default=EmailStatus.draft, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When email was sent
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When email was received
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    # scheduled_for retained in DB for backward compatibility but unused
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_folder: Mapped[str | None] = mapped_column(String, nullable=True)  # Track original folder for restoration
    attachments: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array: [{"filename": "doc.pdf", "content_type": "application/pdf", "size": 12345}]
    



