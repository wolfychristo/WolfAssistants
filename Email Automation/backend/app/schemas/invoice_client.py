from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class InvoiceClientBase(BaseModel):
    name: str
    business_name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    country_code: Optional[str] = None


class InvoiceClientCreate(InvoiceClientBase):
    pass


class InvoiceClientUpdate(BaseModel):
    name: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    country_code: Optional[str] = None


class InvoiceClientOut(InvoiceClientBase):
    id: int
    public_id: str
    created_at: datetime

    class Config:
        from_attributes = True
