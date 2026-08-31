from sqlalchemy import Column, Integer, String, Enum, DateTime, Text
from datetime import datetime
import enum
import uuid
from app.core.database import Base


class MeetingType(str, enum.Enum):
    in_person = "in-person"
    video = "video"
    phone = "phone"


class MeetingStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    attendees = Column(Text, nullable=True)  # comma-separated for now
    type = Column(Enum(MeetingType), default=MeetingType.in_person, nullable=False)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.scheduled, nullable=False)
    notes = Column(Text, nullable=True)
    owner_email = Column(String, index=True, nullable=True)
    # External calendar integration
    external_event_id = Column(String, nullable=True)
    meeting_link = Column(String, nullable=True)
    platform = Column(String, nullable=True)  # e.g., 'google_meet'


