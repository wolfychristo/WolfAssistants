from __future__ import annotations

"""
Tax engine for global digital services.

Responsibilities:
- Resolve tax rate by country and sector
- Provide calculation helpers compatible with Stripe Tax in future
"""

from dataclasses import dataclass
from typing import Literal, Optional


Sector = Literal["saas", "education", "healthcare", "other"]


@dataclass(frozen=True)
class TaxRule:
    country_code: str  # ISO-3166-1 alpha-2, e.g., IN, GB
    sector: Sector
    rate_percent: float
    name: str  # e.g., GST, VAT


# Minimal curated rules; extend over time or load from DB in future
_RULES: list[TaxRule] = [
    # India (GST)
    TaxRule(country_code="IN", sector="saas", rate_percent=18.0, name="GST"),
    TaxRule(country_code="IN", sector="education", rate_percent=12.0, name="GST"),
    TaxRule(country_code="IN", sector="healthcare", rate_percent=5.0, name="GST"),
    TaxRule(country_code="IN", sector="other", rate_percent=18.0, name="GST"),
    # United Kingdom (VAT)
    TaxRule(country_code="GB", sector="saas", rate_percent=20.0, name="VAT"),
    TaxRule(country_code="GB", sector="education", rate_percent=20.0, name="VAT"),
    TaxRule(country_code="GB", sector="healthcare", rate_percent=20.0, name="VAT"),
    TaxRule(country_code="GB", sector="other", rate_percent=20.0, name="VAT"),
]


def get_tax_rule(country_code: Optional[str], sector: Optional[str]) -> TaxRule | None:
    cc = (country_code or "").upper()
    sec: Sector = (sector or "other").lower()  # type: ignore[assignment]
    for rule in _RULES:
        if rule.country_code == cc and rule.sector == sec:
            return rule
    # No rule → 0% default (no applicable digital tax)
    return None


def resolve_tax_rate(country_code: Optional[str], sector: Optional[str]) -> tuple[float, str]:
    rule = get_tax_rule(country_code, sector)
    if rule is None:
        return 0.0, "NONE"
    return rule.rate_percent, rule.name


def validate_tax_id(country_code: Optional[str], tax_id: Optional[str]) -> bool:
    """Validate tax ID based on country code."""
    if not tax_id or not country_code:
        return False
    
    cc = (country_code or "").upper()
    clean_tax_id = (tax_id or "").strip()
    
    if cc == "IN":
        # GST validation: 15 characters with specific pattern
        import re
        gst_regex = r'^[0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}[1-9A-Za-z]{1}Z[0-9A-Za-z]{1}$'
        return bool(re.match(gst_regex, clean_tax_id))
    elif cc == "GB":
        # VAT validation: 9 or 12 digits
        import re
        vat_regex = r'^[0-9]{9}$|^[0-9]{12}$'
        return bool(re.match(vat_regex, clean_tax_id.replace(' ', '')))
    else:
        # For other countries, any non-empty tax ID is considered valid
        return len(clean_tax_id) > 0


def compute_total(price: float, country_code: Optional[str], sector: Optional[str], tax_id: Optional[str] = None) -> dict:
    """Compute breakdown Price + (Price × Tax%) = Total.

    Returns dict with: price, tax_percent, tax_name, tax_amount, total.
    Tax is only applied if a valid tax_id is provided.
    """
    if price is None:
        price = 0.0
    
    # Check if we have a valid tax ID before applying tax
    if not validate_tax_id(country_code, tax_id):
        return {
            "price": float(round(price, 2)),
            "tax_percent": 0.0,
            "tax_name": "NONE",
            "tax_amount": 0.0,
            "total": float(round(price, 2)),
            "country_code": country_code,
            "sector": sector,
        }
    
    rate_percent, tax_name = resolve_tax_rate(country_code, sector)
    tax_amount = round(price * (rate_percent / 100.0), 2)
    total = round(price + tax_amount, 2)
    return {
        "price": float(round(price, 2)),
        "tax_percent": float(rate_percent),
        "tax_name": tax_name,
        "tax_amount": float(tax_amount),
        "total": float(total),
        "country_code": country_code,
        "sector": sector,
    }


