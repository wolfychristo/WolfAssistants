from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Any

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.emails import _get_owner_from_request  # reuse JWT extraction
from app.core.tax import compute_total
from app.models.tax import TaxRecord
from app.schemas.tax import TaxComputeRequest, TaxComputeResponse, TaxRecordCreate, TaxRecordOut


router = APIRouter()


@router.get("/compute", response_model=TaxComputeResponse)
def compute_tax_get(price: float, country_code: str | None = None, sector: str | None = None, tax_id: str | None = None) -> Any:
    """Compute tax via GET (query params)."""
    return compute_total(price, country_code, sector, tax_id)

@router.post("/compute", response_model=TaxComputeResponse)
def compute_tax_post(payload: TaxComputeRequest) -> Any:
    """Compute tax via POST (JSON body)."""
    return compute_total(payload.price, payload.country_code, payload.sector, getattr(payload, 'tax_id', None))


@router.post("/record", response_model=TaxRecordOut)
def record_tax(request: Request, payload: TaxRecordCreate, db: Session = Depends(get_db)) -> Any:
    owner = _get_owner_from_request(request)
    rec = TaxRecord(
        owner_email=owner,
        invoice_number=payload.invoice_number,
        country_code=(payload.country_code or '').upper() or None,
        sector=(payload.sector or '').lower() or None,
        tax_name=payload.tax_name,
        tax_percent=float(payload.tax_percent),
        price=float(payload.price),
        tax_amount=float(payload.tax_amount),
        total=float(payload.total),
        currency_code=payload.currency_code,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


