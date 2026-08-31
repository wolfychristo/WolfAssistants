"""
Multi-tenant database management using PostgreSQL schemas.

This module provides:
- Schema-based tenant isolation
- Automatic schema creation on registration
- Tenant database session management
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Request
from app.core.config import settings
from app.core.database import Base
from typing import Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Cache for tenant engines and sessions
_tenant_engine: Optional[Any] = None
_tenant_session_maker: Optional[sessionmaker] = None

def _get_tenant_db_url() -> str:
    """Get tenant database URL, falling back to DATABASE_URL if not set."""
    if settings.TENANT_DATABASE_URL:
        return settings.TENANT_DATABASE_URL
    return settings.DATABASE_URL

def _get_tenant_engine():
    """Get or create tenant database engine."""
    global _tenant_engine
    if _tenant_engine is None:
        import re
        
        db_url = _get_tenant_db_url()
        _is_postgres = db_url.startswith("postgresql")
        _is_sqlite = db_url.startswith("sqlite")
        _connect_args: Dict[str, Any] = {}
        
        if _is_sqlite:
            _connect_args["check_same_thread"] = False
            _tenant_engine = create_engine(
                db_url,
                connect_args=_connect_args,
                pool_pre_ping=True,
            )
            return _tenant_engine
        
        # Clean the database URL to remove pgbouncer and other unsupported parameters
        if _is_postgres:
            # Remove pgbouncer parameters using regex (simpler and more reliable)
            # Pattern matches: ?pgbouncer=true, &pgbouncer=true, ?pooler=..., etc.
            db_url = re.sub(r'[?&]pgbouncer=[^&]*', '', db_url, flags=re.IGNORECASE)
            db_url = re.sub(r'[?&]pooler=[^&]*', '', db_url, flags=re.IGNORECASE)
            
            # Clean up any double ? or & at the start/end
            db_url = re.sub(r'\?&', '?', db_url)
            db_url = re.sub(r'&+', '&', db_url)
            db_url = re.sub(r'\?+$', '', db_url)
            db_url = re.sub(r'&+$', '', db_url)
            
            # Add SSL mode for remote connections
            if all(host not in db_url for host in ("localhost", "127.0.0.1")):
                _connect_args["sslmode"] = "require"
        
        # Optimized pool settings for free tier Supabase
        _tenant_engine = create_engine(
            db_url,
            connect_args=_connect_args,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=10,        # Reduced from 20 for free tier compatibility
            max_overflow=5,     # Reduced from 10 for free tier compatibility
            pool_timeout=30,     # Keep at 30 seconds
        )
    return _tenant_engine

def _get_tenant_session_maker():
    """Get or create tenant session maker."""
    global _tenant_session_maker
    if _tenant_session_maker is None:
        engine = _get_tenant_engine()
        _tenant_session_maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _tenant_session_maker

def sanitize_email_for_schema(email: str) -> str:
    """
    Convert email to valid PostgreSQL schema name.
    
    Example: user@example.com -> tenant_user_example_com
    """
    # Convert to lowercase and replace invalid characters with underscore
    sanitized = re.sub(r'[^a-z0-9_]', '_', email.lower())
    # Ensure it starts with a letter (PostgreSQL requirement)
    if sanitized and sanitized[0].isdigit():
        sanitized = 't_' + sanitized
    return f"tenant_{sanitized}"

def get_tenant_schema_name(email: str) -> str:
    """Get the schema name for a given email."""
    return sanitize_email_for_schema(email)

def create_tenant_schema(email: str) -> bool:
    """
    Create a new tenant schema and initialize tables.
    
    Args:
        email: User's email address
        
    Returns:
        True if schema was created successfully, False otherwise
    """
    schema_name = get_tenant_schema_name(email)
    engine = _get_tenant_engine()
    
    try:
        with engine.connect() as conn:
            # Create schema if it doesn't exist
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()
            logger.info(f"Created schema {schema_name} for user {email}")
        
        # Create tables in the new schema
        # Import all models to ensure they're registered with Base
        from app.models import email as email_model, contact as contact_model, meeting as meeting_model, todo as todo_model, chat_session as chat_session_model, tax as tax_model, invoice_client as invoice_client_model
        
        # Define which tables belong to tenant schemas (not accounts DB)
        tenant_tables = {'contacts', 'emails', 'meetings', 'todos', 'chat_sessions', 
                        'chat_messages', 'tax_records', 'invoice_clients'}
        
        # Create tables with schema prefix using DDL
        with engine.connect() as table_conn:
            with table_conn.begin():
                # Create each tenant table in the schema
                for table in Base.metadata.tables.values():
                    if table.name not in tenant_tables:
                        continue  # Skip account tables
                    
                    # Generate CREATE TABLE statement with schema
                    from sqlalchemy.schema import CreateTable
                    create_stmt = CreateTable(table)
                    # Compile the statement
                    compiled = create_stmt.compile(dialect=engine.dialect)
                    # Replace table name with schema-qualified name
                    create_sql = str(compiled).replace(
                        f'CREATE TABLE {table.name}',
                        f'CREATE TABLE IF NOT EXISTS "{schema_name}".{table.name}'
                    )
                    try:
                        table_conn.execute(text(create_sql))
                        logger.debug(f"Created table {table.name} in schema {schema_name}")
                    except Exception as table_error:
                        # If table creation fails, log and continue
                        logger.warning(f"Failed to create table {table.name} in schema {schema_name}: {table_error}")
                        continue
        
        logger.info(f"Initialized tables in schema {schema_name} for user {email}")
        
        # Enable Row Level Security (RLS) on all tenant tables
        try:
            with engine.begin() as rls_conn:
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
        
        # Update user's schema_created flag in accounts database
        try:
            from app.core.database import AccountsSessionLocal
            from app.models.user import User
            
            accounts_db = AccountsSessionLocal()
            try:
                user = accounts_db.query(User).filter(User.email == email).first()
                if user:
                    user.schema_created = True
                    accounts_db.commit()
                    logger.info(f"Updated schema_created flag for user {email}")
                else:
                    logger.warning(f"User {email} not found in accounts database when updating schema_created flag")
            finally:
                accounts_db.close()
        except Exception as flag_error:
            # Log but don't fail schema creation if flag update fails
            logger.warning(f"Failed to update schema_created flag for {email}: {str(flag_error)}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create tenant schema {schema_name} for {email}: {str(e)}", exc_info=True)
        return False

def get_tenant_db(email: str) -> Session:
    """
    Get a database session for a specific tenant with retry logic for stale connections.
    
    The session is configured to use the tenant's schema via search_path.
    Uses an event listener to ensure search_path is set on every connection.
    
    Args:
        email: User's email address
        
    Returns:
        Database session configured for the tenant's schema
    """
    import time
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError, DisconnectionError
    
    session_maker = _get_tenant_session_maker()
    if _get_tenant_engine().dialect.name == "sqlite":
        return session_maker()

    schema_name = get_tenant_schema_name(email)
    max_retries = 3
    
    for attempt in range(max_retries):
        session = None
        try:
            # Create a new session
            session = session_maker()
            
            # Validate connection is alive by executing a simple query
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
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                    continue
                logger.error(f"Connection validation failed after {max_retries} attempts: {str(e)}", exc_info=True)
                raise
            except Exception as e:
                if session:
                    try:
                        session.close()
                    except Exception:
                        pass
                raise
            
            # Store schema name in session info for event listener
            session.info['tenant_schema'] = schema_name
            
            # Set search_path using event listener to ensure it's set on every connection
            @event.listens_for(session, "after_begin")
            def set_search_path(session, transaction, connection):
                """Set search_path when a transaction begins"""
                try:
                    connection.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
                except Exception as e:
                    logger.error(f"Failed to set LOCAL search_path in transaction: {str(e)}")
                    raise
            
            # Also set it immediately for the current connection (non-transactional)
            try:
                session.execute(text(f'SET search_path TO "{schema_name}", public'))
                # Don't commit here - let it be set per-transaction
            except (OperationalError, DisconnectionError) as e:
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to set search_path for schema {schema_name} (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                    continue
                logger.error(f"Failed to set search_path for schema {schema_name} after {max_retries} attempts: {str(e)}", exc_info=True)
                raise
            except Exception as e:
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass
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
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
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
    
    # Should never reach here, but just in case
    raise Exception(f"Failed to get tenant database session for {email} after {max_retries} attempts")

def get_tenant_db_dependency(request: Request):
    """
    FastAPI dependency to get tenant database session with improved error handling.
    
    Extracts the user's email from the JWT token and returns
    a database session configured for that tenant's schema.
    """
    from app.api.v1.emails import _get_owner_from_request
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
        logger.error(f"Failed to get tenant database session: {str(e)}", exc_info=True)
        raise

def schema_exists(email: str) -> bool:
    """Check if a tenant schema exists."""
    schema_name = get_tenant_schema_name(email)
    engine = _get_tenant_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name = :schema_name
                """),
                {"schema_name": schema_name}
            )
            return result.first() is not None
    except Exception as e:
        logger.error(f"Failed to check if schema exists: {str(e)}", exc_info=True)
        return False

def drop_tenant_schema(email: str) -> bool:
    """
    Drop a tenant schema (for account deletion).
    
    WARNING: This permanently deletes all tenant data!
    
    Args:
        email: User's email address
        
    Returns:
        True if schema was dropped successfully, False otherwise
    """
    schema_name = get_tenant_schema_name(email)
    engine = _get_tenant_engine()
    
    try:
        with engine.connect() as conn:
            # Drop schema and all its contents
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            conn.commit()
            logger.info(f"Dropped schema {schema_name} for user {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to drop tenant schema {schema_name} for {email}: {str(e)}", exc_info=True)
        return False

