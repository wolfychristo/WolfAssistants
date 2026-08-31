"""Deliverability protection API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.core.database import get_accounts_db, SessionLocal
from app.core.deliverability import (
    check_spf_record,
    check_dkim_record,
    check_dmarc_record,
    extract_domain_from_email,
    calculate_reputation_score,
    should_throttle_sending,
    get_recommended_cold_send_limit
)
from app.models.email_reputation import EmailReputation, BounceRecord
from app.models.user import User
from jose import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_owner_from_request(request: Request) -> str:
    """Extract owner email from JWT token"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _get_or_create_reputation(owner_email: str, mailbox: str, db: Session) -> Optional[EmailReputation]:
    """Get or create reputation record for mailbox"""
    try:
        reputation = db.query(EmailReputation).filter(
            EmailReputation.owner_email == owner_email,
            EmailReputation.mailbox == mailbox
        ).first()
        
        if not reputation:
            reputation = EmailReputation(
                owner_email=owner_email,
                mailbox=mailbox,
                max_cold_sends_per_day=get_recommended_cold_send_limit(100.0)  # Start with high limit
            )
            db.add(reputation)
            db.commit()
            db.refresh(reputation)
        
        return reputation
    except (OperationalError, ProgrammingError) as e:
        # Table doesn't exist or database error
        logger.warning(f"EmailReputation table not available: {e}")
        db.rollback()
        return None
    except Exception as e:
        logger.error(f"Unexpected error in _get_or_create_reputation: {e}")
        db.rollback()
        return None


@router.get("/spf-dkim-status")
def get_spf_dkim_status(request: Request, db: Session = Depends(get_accounts_db)):
    """Check SPF/DKIM status for user's email domain"""
    try:
        owner_email = _get_owner_from_request(request)
        
        # Get user's SMTP from address
        user = db.query(User).filter(User.email == owner_email).first()
        if not user or not user.smtp_from:
            raise HTTPException(status_code=400, detail="SMTP from address not configured")
        
        domain = extract_domain_from_email(user.smtp_from)
        
        # Check SPF
        spf_configured, spf_error = check_spf_record(domain)
        
        # Check DKIM (try common selectors) - validates directly via DNS
        dkim_configured = False
        dkim_error = None
        dkim_selector_used = None
        # Try common selectors for different email providers
        # Format: [selector]._domainkey.[domain]
        # Google Workspace: google._domainkey.domain.com, default._domainkey.domain.com
        # GoDaddy: selector1._domainkey.domain.com, selector2._domainkey.domain.com
        # Hostinger: hostingermail1._domainkey.domain.com, hostingermail2._domainkey.domain.com
        # Microsoft/Outlook: selector1._domainkey.domain.com, selector2._domainkey.domain.com
        # Zoho: zoho._domainkey.domain.com, default._domainkey.domain.com
        selectors_to_try = [
            # Hostinger specific (based on actual DNS records - verified format)
            'hostinger',  # Most common Hostinger selector (verified from DNS records)
            'hostingermail1', 'hostingermail2', 'hostingermail3',
            'maill', 'mainkey',  # Alternative Hostinger selectors seen in DNS
            # Generic/common selectors
            'default', 'mail', 'selector1', 'selector2', 
            'google', 's1', 's2', 'zoho',
            'godaddy', 'outlook', 'microsoft',
            'key1', 'key2', 'dkim', 'dkim1', 'dkim2',
            '20221208', '20230601',  # Some providers use date-based selectors
            'x', 'y', 'z'  # Generic single-letter selectors
        ]
        for selector in selectors_to_try:
            dkim_configured, dkim_error, found_record = check_dkim_record(domain, selector)
            if dkim_configured:
                dkim_selector_used = selector
                logger.info(f"DKIM verified for {domain} using selector '{selector}'")
                if found_record:
                    logger.debug(f"DKIM record content: {found_record[:100]}...")
                break
            elif found_record:
                # Found a TXT record but it doesn't match DKIM pattern - log for debugging
                logger.warning(f"Found TXT record for {selector}._domainkey.{domain} but it doesn't match DKIM pattern: {found_record[:100]}")
        
        # If no DKIM found and we have an error, use a generic message instead of the last selector's error
        if not dkim_configured and dkim_error:
            dkim_error = "No DKIM record found. Please check your DNS settings or contact your email provider for the correct DKIM selector."
        
        # Check DMARC
        dmarc_configured, dmarc_error, dmarc_record = check_dmarc_record(domain)
        
        # Update or create reputation record (if tables exist)
        last_checked_spf = None
        last_checked_dkim = None
        reputation = _get_or_create_reputation(owner_email, user.smtp_from, db)
        if reputation:
            try:
                reputation.spf_configured = spf_configured
                reputation.dkim_configured = dkim_configured
                reputation.spf_last_checked = datetime.utcnow()
                reputation.dkim_last_checked = datetime.utcnow()
                db.commit()
                last_checked_spf = reputation.spf_last_checked.isoformat() if reputation.spf_last_checked else None
                last_checked_dkim = reputation.dkim_last_checked.isoformat() if reputation.dkim_last_checked else None
            except Exception as e:
                logger.warning(f"Failed to update reputation record: {e}")
                db.rollback()
        
        return {
            "domain": domain,
            "spf": {
                "configured": spf_configured,
                "error": spf_error,
                "last_checked": last_checked_spf
            },
            "dkim": {
                "configured": dkim_configured,
                "error": dkim_error,
                "last_checked": last_checked_dkim,
                "selector_used": dkim_selector_used
            },
            "dmarc": {
                "configured": dmarc_configured,
                "error": dmarc_error,
                "record": dmarc_record[:200] if dmarc_record else None
            },
            "setup_guide": {
                "spf": {
                    "description": f"Add a TXT record to your DNS for {domain}",
                    "record_type": "TXT",
                    "name": "@ (or your domain root)",
                    "value": "v=spf1 include:_spf.google.com ~all",
                    "ttl": "3600",
                    "common_providers": {
                        "google": "v=spf1 include:_spf.google.com ~all",
                        "microsoft": "v=spf1 include:spf.protection.outlook.com ~all",
                        "hostinger": "v=spf1 include:spf.hostinger.com ~all",
                        "zoho": "v=spf1 include:zoho.com ~all",
                        "sendgrid": "v=spf1 include:sendgrid.net ~all",
                        "mailchimp": "v=spf1 include:servers.mcsv.net ~all"
                    },
                    "instructions": [
                        f"1. Log in to your DNS provider (where you manage DNS for {domain})",
                        "2. Navigate to DNS Management / DNS Records",
                        "3. Add a new TXT record:",
                        "   - Name/Host: @ (or leave blank, or use your domain root)",
                        "   - Type: TXT",
                        "   - Value: v=spf1 include:_spf.google.com ~all",
                        "   - TTL: 3600 (or default)",
                        "4. Save the record",
                        "5. Wait 5-10 minutes for DNS propagation",
                        "6. Click 'Check Status' button above to verify"
                    ]
                },
                "dkim": {
                    "description": f"Add DKIM TXT records to your DNS for {domain}",
                    "record_type": "TXT",
                    "common_selectors": ["default", "mail", "selector1", "selector2", "google", "s1", "s2", "zoho", "hostinger", "godaddy", "outlook", "microsoft"],
                    "instructions": [
                        f"1. Contact your email provider (Gmail, Hostinger, etc.) to get your DKIM keys",
                        "2. They will provide you with:",
                        "   - A selector name (e.g., 'default', 'mail', 'google')",
                        "   - A public key (long string of characters)",
                        "3. Log in to your DNS provider",
                        "4. Add a new TXT record:",
                        "   - Name/Host: [selector]._domainkey (e.g., 'default._domainkey' or 'mail._domainkey')",
                        "   - Type: TXT",
                        "   - Value: [the public key provided by your email provider]",
                        "   - TTL: 3600 (or default)",
                        "5. Save the record",
                        "6. Wait 5-10 minutes for DNS propagation",
                        "7. Click 'Check Status' button above to verify"
                    ],
                    "provider_links": {
                        "google": "https://support.google.com/a/answer/174124",
                        "microsoft": "https://docs.microsoft.com/en-us/microsoft-365/security/office-365-security/use-dkim-to-validate-outbound-email",
                        "hostinger": "https://www.hostinger.com/tutorials/how-to-set-up-dkim"
                    }
                },
                "dmarc": {
                    "description": f"Add DMARC TXT record to your DNS for {domain}",
                    "record_type": "TXT",
                    "name": "_dmarc (or _dmarc.yourdomain.com)",
                    "value": "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
                    "ttl": "3600",
                    "common_policies": {
                        "none": "v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com",
                        "quarantine": "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
                        "reject": "v=DMARC1; p=reject; rua=mailto:dmarc@yourdomain.com"
                    },
                    "instructions": [
                        f"1. Log in to your DNS provider (where you manage DNS for {domain})",
                        "2. Navigate to DNS Management / DNS Records",
                        "3. Add a new TXT record:",
                        "   - Name/Host: _dmarc (or _dmarc.yourdomain.com)",
                        "   - Type: TXT",
                        "   - Value: v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
                        "   - Replace 'yourdomain.com' with your actual domain",
                        "   - Replace 'dmarc@yourdomain.com' with an email where you want DMARC reports",
                        "   - Policy options:",
                        "     * p=none: Monitor only (recommended for testing)",
                        "     * p=quarantine: Send failed emails to spam folder",
                        "     * p=reject: Reject failed emails (most strict)",
                        "   - TTL: 3600 (or default)",
                        "4. Save the record",
                        "5. Wait 5-10 minutes for DNS propagation",
                        "6. Click 'Check Status' button above to verify"
                    ],
                    "provider_links": {
                        "google": "https://support.google.com/a/answer/2466563",
                        "microsoft": "https://docs.microsoft.com/en-us/microsoft-365/security/office-365-security/use-dmarc-to-validate-email",
                        "hostinger": "https://www.hostinger.com/tutorials/how-to-set-up-dmarc"
                    }
                }
            }
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 401)
        raise
    except Exception as e:
        logger.error(f"Error in get_spf_dkim_status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/reputation")
def get_reputation(request: Request, db: Session = Depends(get_accounts_db)):
    """Get email reputation metrics for user"""
    owner_email = _get_owner_from_request(request)
    
    # Get user's SMTP from address
    user = db.query(User).filter(User.email == owner_email).first()
    if not user or not user.smtp_from:
        raise HTTPException(status_code=400, detail="SMTP from address not configured")
    
    reputation = _get_or_create_reputation(owner_email, user.smtp_from, db)
    if not reputation:
        # Tables don't exist - return default values
        return {
            "mailbox": user.smtp_from,
            "reputation_score": 100.0,
            "metrics": {
                "total_sent": 0,
                "total_delivered": 0,
                "total_bounced": 0,
                "total_complained": 0,
                "delivery_rate": 100.0,
                "bounce_rate": 0.0,
                "complaint_rate": 0.0
            },
            "rate_limiting": {
                "cold_sends_today": 0,
                "max_cold_sends_per_day": 50,
                "recommended_limit": 50
            },
            "status": {
                "is_throttled": False,
                "throttle_reason": None,
                "throttle_until": None
            },
            "spf_dkim": {
                "spf_configured": False,
                "dkim_configured": False
            },
            "last_updated": None,
            "note": "Deliverability tables not yet created. Run create_deliverability_tables.py to enable full tracking."
        }
    
    # Calculate current rates
    total_sent = reputation.total_sent or 0
    bounce_rate = (reputation.total_bounced / total_sent) if total_sent > 0 else 0.0
    complaint_rate = (reputation.total_complained / total_sent) if total_sent > 0 else 0.0
    delivery_rate = (reputation.total_delivered / total_sent) if total_sent > 0 else 1.0
    
    # Recalculate reputation score if needed
    if not reputation.last_calculated or (datetime.utcnow() - reputation.last_calculated) > timedelta(hours=1):
        reputation.reputation_score = calculate_reputation_score(
            total_sent,
            reputation.total_delivered,
            reputation.total_bounced,
            reputation.total_complained
        )
        reputation.last_calculated = datetime.utcnow()
        db.commit()
    
    # Check if throttled
    should_throttle, throttle_reason = should_throttle_sending(
        reputation.reputation_score,
        bounce_rate,
        complaint_rate,
        reputation.cold_sends_today,
        reputation.max_cold_sends_per_day
    )
    
    return {
        "mailbox": reputation.mailbox,
        "reputation_score": reputation.reputation_score,
        "metrics": {
            "total_sent": total_sent,
            "total_delivered": reputation.total_delivered,
            "total_bounced": reputation.total_bounced,
            "total_complained": reputation.total_complained,
            "delivery_rate": round(delivery_rate * 100, 2),
            "bounce_rate": round(bounce_rate * 100, 2),
            "complaint_rate": round(complaint_rate * 100, 3)
        },
        "rate_limiting": {
            "cold_sends_today": reputation.cold_sends_today,
            "max_cold_sends_per_day": reputation.max_cold_sends_per_day,
            "recommended_limit": get_recommended_cold_send_limit(reputation.reputation_score)
        },
        "status": {
            "is_throttled": should_throttle or reputation.is_throttled,
            "throttle_reason": throttle_reason or reputation.throttle_reason,
            "throttle_until": reputation.throttle_until.isoformat() if reputation.throttle_until else None
        },
        "spf_dkim": {
            "spf_configured": reputation.spf_configured,
            "dkim_configured": reputation.dkim_configured
        },
        "last_updated": reputation.updated_at.isoformat() if reputation.updated_at else None
    }


@router.post("/record-bounce")
def record_bounce(
    payload: dict,
    request: Request,
    db: Session = Depends(get_accounts_db)
):
    """Record a bounce event"""
    owner_email = _get_owner_from_request(request)
    mailbox = payload.get('mailbox') or owner_email
    recipient_email = payload.get('recipient_email')
    bounce_type = payload.get('bounce_type', 'soft')  # 'hard', 'soft', 'complaint'
    bounce_reason = payload.get('bounce_reason')
    bounce_code = payload.get('bounce_code')
    email_id = payload.get('email_id')
    subject = payload.get('subject')
    
    if not recipient_email:
        raise HTTPException(status_code=400, detail="recipient_email is required")
    
    # Get or create reputation
    reputation = _get_or_create_reputation(owner_email, mailbox, db)
    if not reputation:
        return {"status": "skipped", "message": "Deliverability tables not yet created"}
    
    # Record bounce
    bounce = BounceRecord(
        reputation_id=reputation.id,
        owner_email=owner_email,
        mailbox=mailbox,
        recipient_email=recipient_email,
        bounce_type=bounce_type,
        bounce_reason=bounce_reason,
        bounce_code=bounce_code,
        email_id=email_id,
        subject=subject
    )
    db.add(bounce)
    
    # Update reputation metrics
    reputation.total_bounced += 1
    if bounce_type == 'complaint':
        reputation.total_complained += 1
    
    # Recalculate reputation score
    reputation.reputation_score = calculate_reputation_score(
        reputation.total_sent,
        reputation.total_delivered,
        reputation.total_bounced,
        reputation.total_complained
    )
    reputation.last_calculated = datetime.utcnow()
    
    # Check if should throttle
    total_sent = reputation.total_sent or 1
    bounce_rate = reputation.total_bounced / total_sent
    complaint_rate = reputation.total_complained / total_sent
    
    should_throttle, throttle_reason = should_throttle_sending(
        reputation.reputation_score,
        bounce_rate,
        complaint_rate,
        reputation.cold_sends_today,
        reputation.max_cold_sends_per_day
    )
    
    if should_throttle:
        reputation.is_throttled = True
        reputation.throttle_reason = throttle_reason
        # Throttle for 24 hours
        reputation.throttle_until = datetime.utcnow() + timedelta(hours=24)
    
    db.commit()
    
    return {"status": "recorded", "reputation_score": reputation.reputation_score}


@router.post("/record-delivery")
def record_delivery(
    payload: dict,
    request: Request,
    db: Session = Depends(get_accounts_db)
):
    """Record a successful delivery"""
    owner_email = _get_owner_from_request(request)
    mailbox = payload.get('mailbox') or owner_email
    is_cold_send: bool = payload.get('is_cold_send', False)
    
    reputation = _get_or_create_reputation(owner_email, mailbox, db)
    if not reputation:
        return {"status": "skipped", "message": "Deliverability tables not yet created"}
    
    # Update metrics
    reputation.total_sent += 1
    reputation.total_delivered += 1
    
    # Track cold sends
    if is_cold_send:
        # Reset daily counter if needed
        if not reputation.cold_sends_reset_at or (datetime.utcnow() - reputation.cold_sends_reset_at) > timedelta(days=1):
            reputation.cold_sends_today = 0
            reputation.cold_sends_reset_at = datetime.utcnow()
        
        reputation.cold_sends_today += 1
    
    # Recalculate reputation score
    reputation.reputation_score = calculate_reputation_score(
        reputation.total_sent,
        reputation.total_delivered,
        reputation.total_bounced,
        reputation.total_complained
    )
    reputation.last_calculated = datetime.utcnow()
    
    db.commit()
    
    return {"status": "recorded", "reputation_score": reputation.reputation_score}

