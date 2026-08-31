from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from fastapi import Request
from app.core.config import settings
from typing import Any, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Create Base class (SQLAlchemy 2.0 typed ORM)
class Base(DeclarativeBase):
    pass

def _create_engine_from_url(db_url: str) -> Any:
    """Create a database engine with optimized settings."""
    import re
    
    _is_postgres = db_url.startswith("postgresql")
    _is_sqlite = db_url.startswith("sqlite")
    _connect_args: Dict[str, Any] = {}
    
    if _is_sqlite:
        _connect_args["check_same_thread"] = False
        return create_engine(
            db_url,
            connect_args=_connect_args,
            pool_pre_ping=True,
        )
    
    # Clean the database URL to remove pgbouncer and other unsupported parameters
    if _is_postgres:
        # Remove pgbouncer parameters using regex (simpler and more reliable)
        # Pattern matches: ?pgbouncer=true, &pgbouncer=true, ?pooler=..., etc.
        # Only match after the database path (after the last /)
        original_url = db_url
        
        # Find the query string part (after ?)
        if '?' in db_url:
            base_url, query_string = db_url.split('?', 1)
            # Remove pgbouncer and pooler parameters from query string
            query_parts = query_string.split('&')
            cleaned_parts = [part for part in query_parts 
                           if not part.lower().startswith('pgbouncer=') 
                           and not part.lower().startswith('pooler=')]
            
            if cleaned_parts:
                db_url = base_url + '?' + '&'.join(cleaned_parts)
            else:
                db_url = base_url
        
        if db_url != original_url:
            logger.info(f"Cleaned database URL: removed pgbouncer parameters")
        
        # Add SSL mode for remote connections
        if all(host not in db_url for host in ("localhost", "127.0.0.1")):
            _connect_args["sslmode"] = "require"
    
    pg_engine = create_engine(
        db_url,
        connect_args=_connect_args,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=10,        # Reduced from 20 for free tier compatibility
        max_overflow=5,     # Reduced from 10 for free tier compatibility
        pool_timeout=30,     # Keep at 30 seconds
    )
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return pg_engine
    except Exception as e:
        logger.warning(f"Could not connect to configured PostgreSQL database ({e}). Automatically falling back to local SQLite database (local_dev.db).")
        fallback_engine = create_engine(
            "sqlite:///./local_dev.db",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        try:
            from app.models import email, contact, meeting, todo, chat_session, tax, scraped_lead, invoice_client, sales_agent
            from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
            from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
            from app.models.gemini_usage import WolfyUsage
            Base.metadata.create_all(bind=fallback_engine)
        except Exception as init_err:
            logger.warning(f"Failed to auto-create tables on SQLite fallback: {init_err}")
        return fallback_engine

# Accounts database engine (for authentication and account data)
_accounts_db_url = settings.ACCOUNTS_DATABASE_URL or settings.DATABASE_URL
accounts_engine = _create_engine_from_url(_accounts_db_url)
AccountsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=accounts_engine)

# Legacy: Keep original engine for backward compatibility
# This will be used as fallback for tenant database if TENANT_DATABASE_URL is not set
engine = _create_engine_from_url(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class (SQLAlchemy 2.0 typed ORM)
class Base(DeclarativeBase):
    pass

# Dependency to get accounts database session (for authentication)
def get_accounts_db(request: Request):
    """Get database session for accounts database (authentication data)."""
    db = AccountsSessionLocal()
    try:
        # Ensure session is in a clean state by rolling back any existing transaction
        try:
            db.rollback()
        except Exception:
            pass  # Ignore if there's no active transaction
        yield db
    finally:
        try:
            db.rollback()  # Rollback any uncommitted changes
        except Exception:
            pass
        db.close()

# Tenant database engine (for user business data in schemas)
_tenant_db_url = settings.TENANT_DATABASE_URL or settings.DATABASE_URL
tenant_engine = _create_engine_from_url(_tenant_db_url)
TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)

# Cache for tenant schema sessions
_tenant_schema_sessions: Dict[str, sessionmaker] = {}

def sanitize_email_for_schema(email: str) -> str:
    """Convert email to valid PostgreSQL schema name.
    
    Example: user@example.com -> tenant_user_example_com
    """
    # Remove invalid characters and replace with underscore
    sanitized = re.sub(r'[^a-z0-9_]', '_', email.lower())
    # Ensure it starts with a letter
    if sanitized and sanitized[0].isdigit():
        sanitized = 't_' + sanitized
    return f"tenant_{sanitized}"

def get_tenant_schema_name(email: str) -> str:
    """Get the schema name for a user's email."""
    return sanitize_email_for_schema(email)

def create_tenant_schema(email: str) -> bool:
    """Create a new tenant schema and initialize all tables.
    
    Returns True if schema was created, False if it already exists.
    """
    if tenant_engine.dialect.name == "sqlite":
        from app.models import email, contact, meeting, todo, chat_session, tax, scraped_lead, invoice_client, sales_agent
        from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
        from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
        from app.models.gemini_usage import WolfyUsage
        Base.metadata.create_all(bind=tenant_engine)
        return True

    schema_name = get_tenant_schema_name(email)
    
    try:
        with tenant_engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": schema_name}
            )
            if result.fetchone():
                logger.info(f"Schema {schema_name} already exists for {email}")
                return False
            
            # Create schema
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()
            logger.info(f"Created schema {schema_name} for {email}")
            
        # Import all models to ensure they're registered with Base
        from app.models import email, contact, meeting, todo, chat_session, tax, scraped_lead, invoice_client, sales_agent
        from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
        from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
        from app.models.gemini_usage import WolfyUsage
        
        # Create tables in the schema using an event listener to set search_path
        from sqlalchemy import event
        
        # Define which tables belong to tenant schemas (not accounts DB)
        tenant_tables = {'contacts', 'emails', 'meetings', 'todos', 'chat_sessions', 
                        'chat_messages', 'tax_records', 'scraped_leads', 'invoice_clients',
                        'business_profiles', 'icp_configurations', 'prospect_profiles',
                        'cadence_sequences', 'cadence_steps', 'reply_intelligence', 'sales_opportunities'}
        
        # Create tables with schema prefix using DDL
        with tenant_engine.connect() as table_conn:
            with table_conn.begin():
                # Set search_path for this transaction
                table_conn.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
                
                # Create each tenant table in the schema
                for table in Base.metadata.tables.values():
                    if table.name not in tenant_tables:
                        continue  # Skip account tables
                    
                    # Generate CREATE TABLE statement with schema
                    from sqlalchemy.schema import CreateTable
                    create_stmt = CreateTable(table)
                    # Compile the statement
                    compiled = create_stmt.compile(dialect=tenant_engine.dialect)
                    # Replace table name with schema-qualified name
                    create_sql = str(compiled).replace(
                        f'CREATE TABLE {table.name}',
                        f'CREATE TABLE IF NOT EXISTS "{schema_name}".{table.name}'
                    )
                    try:
                        table_conn.execute(text(create_sql))
                    except Exception as table_error:
                        # If table creation fails, log and continue
                        logger.warning(f"Failed to create table {table.name} in schema {schema_name}: {table_error}")
                        continue
        
        logger.info(f"Initialized tables in schema {schema_name} for {email}")
        
        # Enable Row Level Security (RLS) on all tenant tables
        try:
            with tenant_engine.begin() as rls_conn:
                rls_conn.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
                
                for table_name in tenant_tables:
                    try:
                        # Check if table exists before enabling RLS
                        check_query = text("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = :schema 
                            AND table_name = :table
                        """)
                        result = rls_conn.execute(check_query, {"schema": schema_name, "table": table_name})
                        
                        if not result.fetchone():
                            continue  # Table doesn't exist, skip
                        
                        # Enable RLS on the table
                        rls_conn.execute(text(f'ALTER TABLE "{schema_name}".{table_name} ENABLE ROW LEVEL SECURITY'))
                        logger.info(f"Enabled RLS on {schema_name}.{table_name}")
                    except Exception as rls_error:
                        # Log but don't fail - RLS might already be enabled or table might not support it
                        logger.warning(f"Could not enable RLS on {table_name}: {rls_error}")
        except Exception as rls_setup_error:
            # Log but don't fail schema creation if RLS setup fails
            logger.warning(f"RLS setup failed for schema {schema_name}: {rls_setup_error}")
        
        # Ensure attachments column exists (in case model was updated after table creation)
        try:
            with tenant_engine.connect() as verify_conn:
                with verify_conn.begin():
                    verify_conn.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
                    # Check if attachments column exists
                    check_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = :schema 
                        AND table_name = 'emails' 
                        AND column_name = 'attachments'
                    """)
                    check_result = verify_conn.execute(check_query, {"schema": schema_name})
                    if not check_result.fetchone():
                        # Add the column if it doesn't exist
                        alter_query = text(f'ALTER TABLE "{schema_name}".emails ADD COLUMN attachments TEXT')
                        verify_conn.execute(alter_query)
                        logger.info(f"Added attachments column to {schema_name}.emails")
        except Exception as col_error:
            # Log but don't fail - column might already exist or table might not be created yet
            logger.warning(f"Could not verify/add attachments column: {col_error}")
        
        return True
            
    except Exception as e:
        logger.error(f"Failed to create tenant schema {schema_name} for {email}: {str(e)}", exc_info=True)
        raise

def get_tenant_db(email: str) -> Session:
    """Get a database session for a specific tenant's schema with retry logic.
    
    The session will automatically use the tenant's schema for all queries.
    """
    if tenant_engine.dialect.name == "sqlite":
        return TenantSessionLocal()

    import time
    from sqlalchemy.exc import OperationalError, DisconnectionError
    
    schema_name = get_tenant_schema_name(email)
    max_retries = 3
    
    for attempt in range(max_retries):
        session = None
        try:
            # Create a session with the schema set in search_path
            session = TenantSessionLocal()
            
            # Validate connection is alive
            try:
                session.execute(text("SELECT 1"))
            except (OperationalError, DisconnectionError) as e:
                if session:
                    try:
                        session.close()
                    except Exception:
                        pass
                if attempt < max_retries - 1:
                    logger.warning(f"Connection validation failed for tenant {email} (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                raise
            
            # Set the search_path to the tenant's schema
            try:
                session.execute(text(f'SET search_path TO "{schema_name}", public'))
                session.commit()
            except (OperationalError, DisconnectionError) as e:
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to set search_path for tenant {email} (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(0.1 * (2 ** attempt))
                    continue
                raise
            
            return session
            
        except (OperationalError, DisconnectionError) as e:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
            if attempt < max_retries - 1:
                logger.warning(f"Database connection error for tenant {email} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(0.1 * (2 ** attempt))
                continue
            logger.error(f"Failed to get tenant database session after {max_retries} attempts: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
            raise
    
    raise Exception(f"Failed to get tenant database session for {email} after {max_retries} attempts")

def _get_owner_from_request(request: Request) -> str:
    """Extract owner email from JWT token in request.
    
    This is a shared utility function used by both database and API modules.
    """
    from jose import jwt
    from app.core.config import settings
    from fastapi import HTTPException
    
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

def get_tenant_db_dependency(request: Request):
    """FastAPI dependency to get tenant database session based on authenticated user with improved error handling.
    
    This extracts the user's email from the JWT token and returns their tenant database session.
    """
    from fastapi import HTTPException
    from sqlalchemy.exc import OperationalError, DisconnectionError
    
    db = None
    try:
        owner_email = _get_owner_from_request(request)
        db = get_tenant_db(owner_email)
        try:
            yield db
        finally:
            if db:
                try:
                    # Rollback any uncommitted changes
                    db.rollback()
                except Exception:
                    pass
                try:
                    db.close()
                except Exception:
                    pass
    except (OperationalError, DisconnectionError) as e:
        if db:
            try:
                db.close()
            except Exception:
                pass
        logger.error(f"Database connection error in dependency: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Database connection error. Please try again in a moment."
        )
    except Exception as e:
        if db:
            try:
                db.close()
            except Exception:
                pass
        logger.error(f"Failed to get tenant database for request: {str(e)}", exc_info=True)
        raise

# Legacy dependency - kept for backward compatibility
# For new code, use get_accounts_db() for account data or get_tenant_db_dependency() for tenant data
def get_db(request: Request):
    """Legacy: Get database session. Use get_accounts_db() or get_tenant_db_dependency() instead."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
