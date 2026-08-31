from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from jose import jwt

from app.core.config import settings
from app.core.tenant_database import get_tenant_db_dependency
from app.models.invoice_client import InvoiceClient
from app.schemas.invoice_client import InvoiceClientCreate, InvoiceClientOut

router = APIRouter()


def _get_owner_from_request(request: Request) -> str:
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


def _ensure_invoice_clients_schema(db: Session, owner_email: str) -> None:
    """Self-healing schema check: ensure invoice_clients table exists with required columns."""
    from sqlalchemy import text, inspect
    from app.core.tenant_database import get_tenant_schema_name
    
    schema_name = get_tenant_schema_name(owner_email)
    
    try:
        # Check if table exists
        inspector = inspect(db.bind)
        tables = inspector.get_table_names(schema=schema_name)
        
        if 'invoice_clients' not in tables:
            # Create table
            qualified_table = f'"{schema_name}".invoice_clients'
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {qualified_table} (
                    id SERIAL PRIMARY KEY,
                    public_id VARCHAR(36) UNIQUE,
                    name VARCHAR NOT NULL,
                    business_name VARCHAR,
                    address TEXT,
                    email VARCHAR,
                    phone VARCHAR,
                    tax_id VARCHAR,
                    country_code VARCHAR,
                    owner_email VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
        else:
            # Check if required columns exist
            columns = [col['name'] for col in inspector.get_columns('invoice_clients', schema=schema_name)]
            required_columns = {
                'id', 'public_id', 'name', 'business_name', 'address', 
                'email', 'phone', 'tax_id', 'country_code', 'owner_email', 'created_at'
            }
            missing_columns = required_columns - set(columns)
            
            if missing_columns:
                qualified_table = f'"{schema_name}".invoice_clients'
                for col in missing_columns:
                    if col == 'id':
                        continue  # Skip primary key
                    elif col == 'public_id':
                        # Use uuid_generate_v4() if extension exists, otherwise use a simple default
                        try:
                            db.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS public_id VARCHAR(36) UNIQUE'))
                            # Update existing rows with UUIDs if any
                            from uuid import uuid4
                            db.execute(text(f"UPDATE {qualified_table} SET public_id = :uuid WHERE public_id IS NULL"), {"uuid": str(uuid4())})
                        except Exception:
                            # If that fails, just add the column without default
                            db.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS public_id VARCHAR(36)'))
                    elif col == 'created_at':
                        db.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
                    else:
                        db.execute(text(f'ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {col} VARCHAR'))
                db.commit()
    except Exception as e:
        # Log but don't fail - let the query attempt proceed
        import logging
        logging.getLogger(__name__).warning(f"Schema check failed for invoice_clients: {e}")
        db.rollback()


@router.get("", response_model=List[InvoiceClientOut])
@router.get("/", response_model=List[InvoiceClientOut])
def list_invoice_clients(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    owner = _get_owner_from_request(request)
    
    # Self-healing schema check (wrap in try-except to avoid blocking)
    try:
        _ensure_invoice_clients_schema(db, owner)
    except Exception as schema_error:
        # Log but continue - schema check is best effort
        import logging
        logging.getLogger(__name__).warning(f"Schema check failed (non-blocking): {schema_error}")
    
    try:
        clients = (
            db.query(InvoiceClient)
            .filter(InvoiceClient.owner_email == owner)
            .order_by(InvoiceClient.created_at.desc())
            .all()
        )
        return clients
    except Exception as e:
        # If query fails, try raw SQL
        from sqlalchemy import text
        try:
            sql_query = text("""
                SELECT id, public_id, name, business_name, address, email, phone,
                       tax_id, country_code, owner_email, created_at
                FROM invoice_clients 
                WHERE owner_email = :owner_email
                ORDER BY created_at DESC
            """)
            result = db.execute(sql_query, {"owner_email": owner})
            rows = result.fetchall()
            clients = []
            for row in rows:
                clients.append({
                    "id": row[0],
                    "public_id": row[1] if row[1] else str(row[0]),  # Fallback if public_id is None
                    "name": row[2],
                    "business_name": row[3],
                    "address": row[4],
                    "email": row[5],
                    "phone": row[6],
                    "tax_id": row[7],
                    "country_code": row[8],
                    "owner_email": row[9],
                    "created_at": row[10],
                })
            return clients
        except Exception as sql_error:
            # If table doesn't exist, return empty list instead of error
            error_str = str(sql_error).lower()
            if 'does not exist' in error_str or 'relation' in error_str:
                return []
            raise HTTPException(status_code=500, detail=f"Error loading invoice clients: {str(sql_error)}")


@router.post("/", response_model=InvoiceClientOut)
def create_invoice_client(
    payload: InvoiceClientCreate,
    request: Request,
    db: Session = Depends(get_tenant_db_dependency)
):
    owner = _get_owner_from_request(request)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Client name is required")

    email_normalized = (payload.email or "").strip().lower() or None

    existing = None
    if email_normalized:
        existing = (
            db.query(InvoiceClient)
            .filter(
                InvoiceClient.owner_email == owner,
                InvoiceClient.email == email_normalized
            )
            .first()
        )

    if existing:
        existing.name = name
        existing.business_name = payload.business_name
        existing.address = payload.address
        existing.email = email_normalized
        existing.phone = payload.phone
        existing.tax_id = payload.tax_id
        existing.country_code = payload.country_code
        db.commit()
        db.refresh(existing)
        return existing

    client = InvoiceClient(
        name=name,
        business_name=payload.business_name,
        address=payload.address,
        email=email_normalized,
        phone=payload.phone,
        tax_id=payload.tax_id,
        country_code=payload.country_code,
        owner_email=owner,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_invoice_client(
    client_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db_dependency)
):
    owner = _get_owner_from_request(request)
    client = (
        db.query(InvoiceClient)
        .filter(InvoiceClient.id == client_id, InvoiceClient.owner_email == owner)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"ok": True}
