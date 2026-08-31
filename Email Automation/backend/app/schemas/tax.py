from __future__ import annotations

from pydantic import BaseModel, Field


class TaxComputeRequest(BaseModel):
    price: float = Field(ge=0)
    country_code: str | None = None
    sector: str | None = None
    tax_id: str | None = None


class TaxComputeResponse(BaseModel):
    price: float
    tax_percent: float
    tax_name: str
    tax_amount: float
    total: float


class TaxRecordCreate(BaseModel):
    invoice_number: str | None = None
    price: float
    country_code: str | None = None
    sector: str | None = None
    tax_name: str
    tax_percent: float
    tax_amount: float
    total: float
    currency_code: str | None = None


class TaxRecordOut(TaxRecordCreate):
    id: int

    class Config:
        from_attributes = True


