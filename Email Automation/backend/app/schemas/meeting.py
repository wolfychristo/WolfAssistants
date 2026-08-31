from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime


class MeetingBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: List[str] = []
    type: str = "in-person"
    status: str = "scheduled"
    notes: Optional[str] = None
    meeting_link: Optional[str] = None
    platform: Optional[str] = None
    # Output-only fields removed per request


class MeetingCreate(MeetingBase):
    pass


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    meeting_link: Optional[str] = None
    platform: Optional[str] = None


class MeetingOut(MeetingBase):
    id: int
    public_id: str

    @field_serializer('start_time', 'end_time')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime with UTC timezone indicator"""
        if value is None:
            return None
        # Ensure the datetime is timezone-aware and in UTC
        if value.tzinfo is None:
            # If no timezone info, assume UTC
            value = value.replace(tzinfo=None)
        # Format with Z suffix for UTC
        return value.isoformat() + 'Z'

    class Config:
        from_attributes = True


