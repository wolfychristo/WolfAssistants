from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    due_date: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None


class TodoOut(TodoBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_email: str

    class Config:
        from_attributes = True
