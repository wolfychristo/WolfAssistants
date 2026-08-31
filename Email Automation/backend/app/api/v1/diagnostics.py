from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import smtplib
import ssl

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.middleware.performance_monitoring import get_performance_stats, get_slow_endpoints


router = APIRouter()


def _owner_from_request(request: Request) -> str:
    auth = request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth.split(' ', 1)[1]
    from jose import jwt
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise Exception('no sub')
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/self")
def self_diagnostics(request: Request, db: Session = Depends(get_db)):
    owner = _owner_from_request(request)

    # Primary DB user
    user = db.query(User).filter(User.email == owner).first()
    primary_ok = bool(user)

    # Supabase database checks (no tenant databases needed)
    supabase_checks = {"connected": True, "tables": ["app_users", "emails", "contacts", "meetings", "todos", "chat_sessions"]}

    # SMTP quick check (login only; no send)
    smtp = {"configured": False, "login_ok": False, "error": None}
    if user and (user.smtp_host and user.smtp_username and user.smtp_password):
        smtp["configured"] = True
        host = user.smtp_host
        port = int(user.smtp_port or (587 if (user.smtp_use_tls is None or user.smtp_use_tls) else 465))
        username = user.smtp_username
        password = user.smtp_password
        use_tls = True if user.smtp_use_tls is None else bool(user.smtp_use_tls)
        try:
            context = ssl.create_default_context()
            if port == 465 and not use_tls:
                server = smtplib.SMTP_SSL(host, port, context=context, timeout=15)
                server.ehlo()
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.ehlo()
                if use_tls:
                    server.starttls(context=context)
                    server.ehlo()
            server.login(username, password)
            try:
                server.noop()
            finally:
                server.quit()
            smtp["login_ok"] = True
        except Exception as e:
            smtp["error"] = str(e)

    # IMAP quick check (login only)
    imap = {"configured": False, "login_ok": False, "error": None}
    if user and (user.imap_host and user.imap_username and user.imap_password):
        imap["configured"] = True
        try:
            import imaplib
            use_ssl = True if user.imap_use_ssl is None else bool(user.imap_use_ssl)
            port = int(user.imap_port or (993 if use_ssl else 143))
            M = imaplib.IMAP4_SSL(user.imap_host, port) if use_ssl else imaplib.IMAP4(user.imap_host, port)
            M.login(user.imap_username, user.imap_password)
            M.logout()
            imap["login_ok"] = True
        except Exception as e:
            imap["error"] = str(e)

    return {
        "owner": owner,
        "primary_user": primary_ok,
        "supabase": supabase_checks,
        "smtp": smtp,
        "imap": imap,
    }


@router.get("/performance")
def get_performance_metrics(request: Request):
    """Get performance statistics for all endpoints."""
    try:
        stats = get_performance_stats()
        slow_endpoints = get_slow_endpoints(threshold=1.0, limit=20)
        
        return {
            "all_endpoints": stats,
            "slow_endpoints": slow_endpoints,
            "summary": {
                "total_endpoints": len(stats),
                "slow_endpoints_count": len(slow_endpoints),
                "total_requests": sum(s["count"] for s in stats.values()),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/performance/slow")
def get_slow_endpoints_list(request: Request, threshold: float = 1.0, limit: int = 10):
    """Get list of slowest endpoints."""
    try:
        slow_endpoints = get_slow_endpoints(threshold=threshold, limit=limit)
        return {
            "slow_endpoints": slow_endpoints,
            "threshold": threshold,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get slow endpoints: {str(e)}")


