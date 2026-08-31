from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.models.user import User

router = APIRouter()

class EmailSettingsPayload(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool | None = True

    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    imap_use_ssl: bool | None = True

    # Auto follow-up settings
    auto_followup_enabled: bool | None = None
    auto_followup_max_days: int | None = None
    auto_followup_daily_hour: int | None = None
    
def _get_owner_email(request: Request) -> str:
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

@router.get("/me")
def get_my_email_settings(request: Request, db: Session = Depends(get_db)):
    owner = _get_owner_email(request)
    
    # Use raw SQL to avoid SQLAlchemy column issues
    from app.core.database import SessionLocal
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    
    pdb = SessionLocal()
    try:
        # First check which columns exist
        from sqlalchemy import inspect
        inspector = inspect(pdb.bind)
        columns = [col['name'] for col in inspector.get_columns('app_users')]
        
        # Build query with only existing columns
        base_cols = ['id', 'email']
        optional_cols = [
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
            'smtp_from', 'smtp_use_tls', 'imap_host', 'imap_port', 
            'imap_username', 'imap_password', 'imap_use_ssl',
            'auto_followup_enabled', 'auto_followup_max_days', 
            'auto_followup_daily_hour', 'last_auto_followup_run',
            'last_auto_followup_sent_count'
        ]
        
        select_cols = base_cols + [col for col in optional_cols if col in columns]
        select_str = ', '.join(select_cols)
        
        # Use raw SQL query with only existing columns
        sql_query = text(f"""
            SELECT {select_str}
            FROM app_users 
            WHERE email = :email
            LIMIT 1
        """)
        result = pdb.execute(sql_query, {"email": owner})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create user object from row with safe defaults
        user_dict = {
            'id': row[0],
            'email': row[1],
        }
        
        # Map remaining columns
        col_idx = 2
        for col in optional_cols:
            if col in columns:
                user_dict[col] = row[col_idx] if col_idx < len(row) else None
                col_idx += 1
            else:
                user_dict[col] = None
        
        u = type('User', (), user_dict)()
        
        return {
            "smtp_host": u.smtp_host,
            "smtp_port": u.smtp_port,
            "smtp_username": u.smtp_username,
            "smtp_from": u.smtp_from,
            "smtp_use_tls": u.smtp_use_tls,
            "imap_host": u.imap_host,
            "imap_port": u.imap_port,
            "imap_username": u.imap_username,
            "imap_use_ssl": u.imap_use_ssl,
            # Never return passwords
            "has_smtp_password": bool(u.smtp_password),
            "has_imap_password": bool(u.imap_password),
            # Auto follow-up settings
            "auto_followup_enabled": bool(u.auto_followup_enabled) if u.auto_followup_enabled is not None else False,
            "auto_followup_max_days": u.auto_followup_max_days,
            "auto_followup_daily_hour": u.auto_followup_daily_hour,
            # Telemetry for UI status
            "last_auto_followup_run": u.last_auto_followup_run,
            "last_auto_followup_sent_count": u.last_auto_followup_sent_count,
        }
    except (OperationalError, ProgrammingError) as db_error:
        # If raw SQL fails, try SQLAlchemy as fallback
        error_str = str(db_error).lower()
        if 'does not exist' in error_str or 'no such column' in error_str:
            # Try SQLAlchemy fallback
            try:
                u = pdb.query(User).filter(User.email == owner).first()
                if not u:
                    raise HTTPException(status_code=404, detail="User not found")
                return {
                    "smtp_host": getattr(u, 'smtp_host', None),
                    "smtp_port": getattr(u, 'smtp_port', None),
                    "smtp_username": getattr(u, 'smtp_username', None),
                    "smtp_from": getattr(u, 'smtp_from', None),
                    "smtp_use_tls": getattr(u, 'smtp_use_tls', True),
                    "imap_host": getattr(u, 'imap_host', None),
                    "imap_port": getattr(u, 'imap_port', None),
                    "imap_username": getattr(u, 'imap_username', None),
                    "imap_use_ssl": getattr(u, 'imap_use_ssl', True),
                    "has_smtp_password": bool(getattr(u, 'smtp_password', None)),
                    "has_imap_password": bool(getattr(u, 'imap_password', None)),
                    "auto_followup_enabled": bool(getattr(u, 'auto_followup_enabled', False)),
                    "auto_followup_max_days": getattr(u, 'auto_followup_max_days', None),
                    "auto_followup_daily_hour": getattr(u, 'auto_followup_daily_hour', None),
                    "last_auto_followup_run": getattr(u, 'last_auto_followup_run', None),
                    "last_auto_followup_sent_count": getattr(u, 'last_auto_followup_sent_count', None),
                }
            except Exception:
                raise HTTPException(status_code=500, detail="Database error loading email settings")
        else:
            raise HTTPException(status_code=500, detail="Database error loading email settings")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading email settings: {str(e)}")
    finally:
        pdb.close()

@router.put("/me")
def update_my_email_settings(payload: EmailSettingsPayload, request: Request, db: Session = Depends(get_db)):
    owner = _get_owner_email(request)
    
    # Use primary database session for User model
    from app.core.database import SessionLocal
    pdb = SessionLocal()
    try:
        u = pdb.query(User).filter(User.email == owner).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get only fields provided by the client to avoid clearing existing values unintentionally
        data = payload.model_dump(exclude_unset=True)
        
        # Handle each field
        for k, v in data.items():
            if k == 'smtp_password':
                # Encrypt SMTP password using the User model's method
                if v:
                    u.set_smtp_password(v)
                else:
                    u.smtp_password = None
            elif k == 'imap_password':
                # Encrypt IMAP password using the User model's method
                if v:
                    u.set_imap_password(v)
                else:
                    u.imap_password = None
            elif k in ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_from'):
                # Required fields - save even if empty to clear them
                setattr(u, k, v)
            elif k in ('auto_followup_enabled', 'auto_followup_max_days', 'auto_followup_daily_hour', 'smtp_use_tls', 'imap_host', 'imap_port', 'imap_username', 'imap_use_ssl'):
                # These may be falsy but intentional; persist as-is
                setattr(u, k, v)
            else:
                # For other fields, only save if they have a value
                if v is not None:
                    setattr(u, k, v)
        
        pdb.commit()
        pdb.refresh(u)
        
        return {"status": "saved"}
    finally:
        pdb.close()