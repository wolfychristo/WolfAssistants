"""Deliverability protection utilities"""
import dns.resolver
import dns.exception
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configure DNS resolver with longer timeout and public DNS servers
_resolver = dns.resolver.Resolver()
_resolver.timeout = 10  # 10 seconds timeout
_resolver.lifetime = 10  # 10 seconds total lifetime
# Prepend public DNS servers to system DNS for better reliability
public_dns = ['8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1']  # Google and Cloudflare DNS
_resolver.nameservers = public_dns + _resolver.nameservers


def check_spf_record(domain: str) -> Tuple[bool, Optional[str]]:
    """
    Check if domain has SPF record configured.
    Returns (is_configured, error_message)
    """
    try:
        answers = _resolver.resolve(domain, 'TXT')
        for rdata in answers:
            txt_record = rdata.strings[0].decode('utf-8') if rdata.strings else ''
            if txt_record.startswith('v=spf1'):
                return True, None
        return False, "No SPF record found"
    except dns.resolver.NXDOMAIN:
        return False, f"Domain {domain} does not exist"
    except dns.resolver.NoAnswer:
        return False, "No TXT records found"
    except (dns.resolver.Timeout, dns.exception.Timeout) as e:
        logger.warning(f"DNS timeout checking SPF for {domain}: {e}")
        return False, "DNS lookup timed out. Please check your internet connection or try again later."
    except Exception as e:
        error_msg = str(e)
        exception_type = type(e).__name__
        # Simplify timeout error messages - check for any timeout-related keywords
        error_lower = error_msg.lower()
        is_timeout = (
            "timeout" in error_lower or 
            "timed out" in error_lower or 
            "lifetime expired" in error_lower or
            "resolution lifetime" in error_lower or
            "lifetime expired after" in error_lower or
            "expired after" in error_lower or
            exception_type in ("LifetimeTimeout", "Timeout") or
            "LifetimeTimeout" in exception_type or
            "Timeout" in exception_type
        )
        if is_timeout:
            return False, "DNS lookup timed out. Please check your internet connection or try again later."
        logger.error(f"Error checking SPF for {domain}: {e}")
        return False, f"Error checking SPF: {error_msg[:200]}"  # Limit error message length


def check_dkim_record(domain: str, selector: str = "default") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if domain has DKIM record configured by querying DNS directly.
    Returns (is_configured, error_message, found_record)
    found_record is the actual TXT record content if found (for debugging)
    """
    try:
        # DKIM record format: [selector]._domainkey.[domain]
        # For Hostinger: hostingermail1._domainkey.domain.com
        # For others: selector._domainkey.domain.com or default._domainkey.domain.com
        dkim_domain = f"{selector}._domainkey.{domain}"
        logger.debug(f"Checking DKIM for {dkim_domain}")
        answers = _resolver.resolve(dkim_domain, 'TXT')
        for rdata in answers:
            # Join all strings in the TXT record (DKIM records can be split across multiple strings)
            txt_record = ' '.join([s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings])
            logger.debug(f"Found TXT record for {dkim_domain}: {txt_record[:200]}")
            # Normalize to uppercase for case-insensitive matching
            txt_record_upper = txt_record.upper()
            # Normalize semicolons to spaces for easier matching (DKIM can use "v=DKIM1; k=rsa; p=..." or "v=DKIM1 k=rsa p=...")
            txt_record_normalized = txt_record_upper.replace(';', ' ').replace('  ', ' ').strip()
            
            # Check for DKIM record markers (case-insensitive)
            # DKIM records typically contain: v=DKIM1, k=rsa (or k=ed25519), p= (public key)
            # Format can be: "v=DKIM1; k=rsa; p=..." (with semicolons) or "v=DKIM1 k=rsa p=..." (with spaces)
            dkim_indicators = [
                'V=DKIM1',  # Version tag (required)
                'K=RSA',    # RSA key type
                'K=ED25519', # Ed25519 key type
                'P=MIGF',   # Public key starts with MIGF (RSA) or other base64
                'P=MIIB',   # Another common RSA public key prefix (MIIBIJAN...)
                'P=',       # Public key field present
            ]
            # Check if any DKIM indicator is present
            if any(indicator in txt_record_normalized for indicator in dkim_indicators):
                # Additional validation: ensure it looks like a DKIM record
                # Should have at least version (v=DKIM1) or key type (k=)
                if 'V=DKIM1' in txt_record_normalized or 'K=' in txt_record_normalized:
                    # Also check for public key field (p=) to ensure it's a complete DKIM record
                    if 'P=' in txt_record_normalized:
                        logger.info(f"DKIM record found for {dkim_domain} with selector '{selector}'")
                        logger.debug(f"DKIM record content: {txt_record[:150]}...")
                        return True, None, txt_record
                    else:
                        logger.debug(f"TXT record has DKIM markers but missing public key (p=): {txt_record[:100]}")
            else:
                logger.debug(f"TXT record found but doesn't match DKIM pattern: {txt_record[:100]}")
        return False, f"No DKIM record found for selector '{selector}'", None
    except dns.resolver.NXDOMAIN:
        return False, f"No DKIM record found for selector '{selector}'", None
    except dns.resolver.NoAnswer:
        return False, f"No DKIM record found for selector '{selector}'", None
    except (dns.resolver.Timeout, dns.resolver.LifetimeTimeout, dns.exception.Timeout) as e:
        logger.warning(f"DNS timeout checking DKIM for {domain} with selector {selector}: {e}")
        return False, "DNS lookup timed out. Please check your internet connection or try again later.", None
    except Exception as e:
        error_msg = str(e)
        exception_type = type(e).__name__
        # Simplify timeout error messages - check for any timeout-related keywords
        error_lower = error_msg.lower()
        is_timeout = (
            "timeout" in error_lower or 
            "timed out" in error_lower or 
            "lifetime expired" in error_lower or
            "resolution lifetime" in error_lower or
            "lifetime expired after" in error_lower or
            "expired after" in error_lower or
            exception_type in ("LifetimeTimeout", "Timeout") or
            "LifetimeTimeout" in exception_type or
            "Timeout" in exception_type
        )
        if is_timeout:
            return False, "DNS lookup timed out. Please check your internet connection or try again later.", None
        logger.error(f"Error checking DKIM for {domain} with selector {selector}: {e}")
        return False, f"Error checking DKIM: {error_msg[:200]}", None  # Limit error message length


def check_dmarc_record(domain: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if domain has DMARC record configured.
    DMARC records are at _dmarc.[domain]
    Returns (is_configured, error_message, found_record)
    """
    try:
        dmarc_domain = f"_dmarc.{domain}"
        logger.debug(f"Checking DMARC for {dmarc_domain}")
        answers = _resolver.resolve(dmarc_domain, 'TXT')
        for rdata in answers:
            txt_record = ' '.join([s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings])
            logger.debug(f"Found TXT record for {dmarc_domain}: {txt_record[:200]}")
            txt_record_upper = txt_record.upper()
            # DMARC records start with v=DMARC1
            if 'V=DMARC1' in txt_record_upper or txt_record.startswith('v=DMARC1'):
                logger.info(f"DMARC record found for {dmarc_domain}")
                return True, None, txt_record
        return False, "No DMARC record found", None
    except dns.resolver.NXDOMAIN:
        return False, "No DMARC record found", None
    except dns.resolver.NoAnswer:
        return False, "No DMARC record found", None
    except (dns.resolver.Timeout, dns.resolver.LifetimeTimeout, dns.exception.Timeout) as e:
        logger.warning(f"DNS timeout checking DMARC for {domain}: {e}")
        return False, "DNS lookup timed out. Please check your internet connection or try again later.", None
    except Exception as e:
        error_msg = str(e)
        exception_type = type(e).__name__
        error_lower = error_msg.lower()
        is_timeout = (
            "timeout" in error_lower or 
            "timed out" in error_lower or 
            "lifetime expired" in error_lower or
            "resolution lifetime" in error_lower or
            "lifetime expired after" in error_lower or
            "expired after" in error_lower or
            exception_type in ("LifetimeTimeout", "Timeout") or
            "LifetimeTimeout" in exception_type or
            "Timeout" in exception_type
        )
        if is_timeout:
            return False, "DNS lookup timed out. Please check your internet connection or try again later.", None
        logger.error(f"Error checking DMARC for {domain}: {e}")
        return False, f"Error checking DMARC: {error_msg[:200]}", None


def extract_domain_from_email(email: str) -> str:
    """Extract domain from email address"""
    if '@' not in email:
        return email
    return email.split('@')[1]


def calculate_reputation_score(
    total_sent: int,
    total_delivered: int,
    total_bounced: int,
    total_complained: int
) -> float:
    """
    Calculate reputation score (0-100) based on delivery metrics.
    Higher score = better reputation.
    """
    if total_sent == 0:
        return 100.0  # No sends = perfect score
    
    # Calculate rates
    delivery_rate = total_delivered / total_sent if total_sent > 0 else 0.0
    bounce_rate = total_bounced / total_sent if total_sent > 0 else 0.0
    complaint_rate = total_complained / total_sent if total_sent > 0 else 0.0
    
    # Start with delivery rate as base (0-100)
    score = delivery_rate * 100
    
    # Penalize bounces (hard penalty)
    # Bounce rate > 5% is very bad
    if bounce_rate > 0.05:
        score -= 50  # Heavy penalty
    elif bounce_rate > 0.02:
        score -= 25  # Moderate penalty
    elif bounce_rate > 0.01:
        score -= 10  # Light penalty
    
    # Penalize complaints (very hard penalty)
    # Complaint rate > 0.1% is very bad
    if complaint_rate > 0.001:
        score -= 30  # Heavy penalty
    elif complaint_rate > 0.0005:
        score -= 15  # Moderate penalty
    
    # Ensure score stays in 0-100 range
    score = max(0.0, min(100.0, score))
    
    return round(score, 2)


def should_throttle_sending(
    reputation_score: float,
    bounce_rate: float,
    complaint_rate: float,
    cold_sends_today: int,
    max_cold_sends: int
) -> Tuple[bool, Optional[str]]:
    """
    Determine if sending should be throttled.
    Returns (should_throttle, reason)
    """
    # Throttle if reputation is very low
    if reputation_score < 30:
        return True, f"Reputation score too low ({reputation_score:.1f}/100)"
    
    # Throttle if bounce rate is too high
    if bounce_rate > 0.05:  # > 5%
        return True, f"Bounce rate too high ({bounce_rate*100:.1f}%)"
    
    # Throttle if complaint rate is too high
    if complaint_rate > 0.001:  # > 0.1%
        return True, f"Complaint rate too high ({complaint_rate*100:.2f}%)"
    
    # Throttle if daily cold send limit reached
    if cold_sends_today >= max_cold_sends:
        return True, f"Daily cold send limit reached ({cold_sends_today}/{max_cold_sends})"
    
    return False, None


def get_recommended_cold_send_limit(reputation_score: float) -> int:
    """
    Get recommended daily cold send limit based on reputation score.
    """
    if reputation_score >= 90:
        return 100  # High reputation = more sends allowed
    elif reputation_score >= 70:
        return 50   # Good reputation = moderate sends
    elif reputation_score >= 50:
        return 25   # Fair reputation = limited sends
    elif reputation_score >= 30:
        return 10   # Poor reputation = very limited sends
    else:
        return 5    # Very poor reputation = minimal sends

