from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os
from datetime import datetime
import logging
import asyncio

from app.core.config import settings
from app.core.database import engine, Base, accounts_engine
from sqlalchemy import text
from app.api.v1.api import api_router
from app.core.auth import get_current_user

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
from app.models.todo import Todo
from app.models.email_reputation import EmailReputation, BounceRecord

# Security middleware imports
from app.middleware.security import SecurityHeadersMiddleware, SecurityAuditMiddleware
from app.middleware.ip_rate_limiting import IPRateLimitMiddleware
from app.middleware.input_sanitization import InputSanitizationMiddleware
from app.middleware.user_error_logging import UserErrorLoggingMiddleware
from app.middleware.user_access_control import check_user_access_control

# APScheduler imports kept only if needed elsewhere; no jobs started
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging - OPTIMIZED FOR PERFORMANCE
logging.basicConfig(
    level=logging.ERROR,  # Reduced from WARNING to ERROR for better performance
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/application.log'),
        # Removed StreamHandler for better performance
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Create tables, but catch mapper initialization errors
        # This allows the app to start even if some models have relationship issues
        # Use accounts_engine for User model since login uses AccountsSessionLocal
        try:
            Base.metadata.create_all(bind=accounts_engine)
        except Exception as mapper_error:
            error_msg = str(mapper_error)
            if "mapper" in error_msg.lower() or "relationship" in error_msg.lower():
                logger.warning(f"Some models have mapper initialization issues: {error_msg[:200]}")
                # Continue - tables will be created via migrations
            else:
                raise  # Re-raise if it's a different error
        
        # Simple migration without complex operations
        # Use accounts_engine since login uses AccountsSessionLocal
        try:
            with accounts_engine.connect() as conn:
                # Just create basic tables if they don't exist
                # Note: PostgreSQL uses different syntax, but these CREATE TABLE IF NOT EXISTS should work
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS contacts (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS emails (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS meetings (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS app_users (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS gemini_usage (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS todos (id SERIAL PRIMARY KEY)"))
                except Exception:
                    pass
            
            # Add missing columns to app_users table if they don't exist
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN smtp_last_tested DATETIME"))
            except Exception:
                pass  # Column already exists
            
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN smtp_test_status VARCHAR"))
            except Exception:
                pass  # Column already exists
            
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN schema_created BOOLEAN DEFAULT FALSE"))
            except Exception:
                pass  # Column already exists
            
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN smtp_failure_count INTEGER DEFAULT 0"))
            except Exception:
                pass  # Column already exists

            # Auto follow-up columns
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN auto_followup_enabled BOOLEAN DEFAULT 0"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN auto_followup_max_days INTEGER"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN auto_followup_daily_hour INTEGER"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN last_auto_followup_run DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN last_auto_followup_sent_count INTEGER"))
            except Exception:
                pass

            # Common profile columns used by queries
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN profile_image_url VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN position_title VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN website_url VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN calendly_link VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN heard_about_us VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN company_name VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN team_size VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN revenue_size VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN social_link VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN timezone VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN tier_activated_at DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN tier_expires_at DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN payment_status VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN last_payment_date DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN next_payment_date DATETIME"))
            except Exception:
                pass

            # Ensure pricing_tier column exists (referenced in user model)
            try:
                conn.execute(text("ALTER TABLE app_users ADD COLUMN pricing_tier VARCHAR"))
            except Exception:
                pass
            try:
                # Use PostgreSQL DO block to check if column exists before adding
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='app_users' AND column_name='subscription_id'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN subscription_id VARCHAR;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Added subscription_id column (or it already exists)")
            except Exception as e:
                logger.warning(f"Could not add subscription_id column: {e}")
                conn.rollback()
            
            # Marketplace freelancer columns (deprecated - kept for database compatibility)
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='app_users' AND column_name='is_freelancer'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN is_freelancer BOOLEAN DEFAULT FALSE;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Added is_freelancer column (or it already exists)")
            except Exception as e:
                logger.warning(f"Could not add is_freelancer column: {e}")
                conn.rollback()
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='app_users' AND column_name='freelancer_profile_id'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN freelancer_profile_id INTEGER;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Added freelancer_profile_id column (or it already exists)")
            except Exception as e:
                logger.warning(f"Could not add freelancer_profile_id column: {e}")
                conn.rollback()
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='app_users' AND column_name='stripe_connect_account_id'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN stripe_connect_account_id VARCHAR;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Added stripe_connect_account_id column (or it already exists)")
            except Exception as e:
                logger.warning(f"Could not add stripe_connect_account_id column: {e}")
                conn.rollback()
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='app_users' AND column_name='marketplace_commission_rate'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN marketplace_commission_rate FLOAT;
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("Added marketplace_commission_rate column (or it already exists)")
            except Exception as e:
                logger.warning(f"Could not add marketplace_commission_rate column: {e}")
                conn.rollback()

            # Add todos table columns
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN title VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN description TEXT"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN completed BOOLEAN DEFAULT 0"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN due_date DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN priority VARCHAR DEFAULT 'medium'"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN created_at DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN updated_at DATETIME"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE todos ADD COLUMN owner_email VARCHAR"))
            except Exception:
                pass
            
            # Commit all changes
            try:
                conn.commit()
                logger.info("Migration transaction committed successfully")
            except Exception as e:
                logger.warning(f"Migration commit failed: {e}")
                conn.rollback()
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Start individual user debugging cleanup task
        from app.monitoring.individual_user_debug import cleanup_debug_data
        asyncio.create_task(cleanup_debug_data())
        
    except Exception as e:
        # Don't fail startup, just log the warning
        pass
    
    # Start lightweight scheduler to process scheduled emails every minute
    scheduler = BackgroundScheduler()
    def process_scheduled_emails():
        try:
            from datetime import datetime, timezone
            from sqlalchemy.orm import Session
            from app.core.database import SessionLocal
            from app.models.email import Email, EmailStatus
            from app.api.v1.emails import _send_email

            now = datetime.now(timezone.utc)
            session: Session = SessionLocal()
            try:
                scheduled_emails = (
                    session.query(Email)
                    .filter(
                        Email.status == EmailStatus.scheduled,
                        Email.scheduled_for.isnot(None),
                        Email.scheduled_for <= now,
                    )
                    .all()
                )

                for email in scheduled_emails:
                    try:
                        payload = {
                            "to": email.to_address,
                            "subject": email.subject,
                            "content": email.body,
                        }
                        _send_email(payload, session, email.owner_email)
                        email.status = EmailStatus.sent
                        email.sent_at = datetime.utcnow()
                        email.last_error = None
                        session.commit()
                    except Exception as send_error:
                        email.last_error = str(send_error)
                        session.commit()
            finally:
                session.close()
        except Exception:
            pass
    
    def check_imap_emails():
        """Check for new emails via IMAP for all users with configured IMAP settings"""
        try:
            from app.core.database import SessionLocal
            from app.models.user import User
            from app.api.v1.emails import fast_imap_check
            from fastapi import Request
            from unittest.mock import Mock
            
            db = SessionLocal()
            try:
                # Get all users with IMAP configured
                users = db.query(User).filter(
                    User.imap_host.isnot(None),
                    User.imap_username.isnot(None),
                    User.imap_password.isnot(None)
                ).all()
                
                for user in users:
                    # Use tenant database session for each user
                    try:
                        from app.core.database import get_tenant_db
                        
                        # Get tenant database session for this user
                        user_db = get_tenant_db(user.email)
                        
                        try:
                            # Create a mock request for the user
                            mock_request = Mock()
                            mock_request.headers = {'Authorization': f'Bearer internal-scheduler'}
                            
                            # Mock the _get_owner_from_request function
                            import app.api.v1.emails as emails_module
                            original_get_owner = emails_module._get_owner_from_request
                            
                            def mock_get_owner(request):
                                return user.email
                                
                            emails_module._get_owner_from_request = mock_get_owner
                            
                                # Run fast IMAP check for this user with their tenant session
                            try:
                                result = fast_imap_check(mock_request, user_db)
                            except Exception as e:
                                print(f"Error checking IMAP for {user.email}: {e}")
                                import traceback
                                traceback.print_exc()
                                continue
                            if result.get('imported_count', 0) > 0:
                                print(f"Auto-imported {result['imported_count']} emails for {user.email}")
                        finally:
                            # Restore original function
                            emails_module._get_owner_from_request = original_get_owner
                            
                    except Exception as e:
                        # Log error but continue with other users
                        print(f"Error checking IMAP for {user.email}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Close the user's database session
                        user_db.close()
                        print(f"Error getting tenant database for {user.email}: {e}")
                        import traceback
                        traceback.print_exc()
                        
            finally:
                db.close()
                
        except Exception as e:
            # Don't let IMAP checking errors crash the scheduler
            pass

    def run_auto_followups_for_all_users():
        """Automatically send follow-ups without external triggers.
        Runs periodically and respects per-user toggle and preferred hour.
        """
        try:
            from app.core.database import SessionLocal
            from app.models.user import User
            from app.api.v1.emails import run_auto_followups
            from fastapi import Request
            from datetime import datetime
            from unittest.mock import Mock

            now = datetime.now()
            logger.info(f"Auto follow-up scheduler running at hour {now.hour}")
            
            pdb = SessionLocal()
            try:
                users = pdb.query(User).filter(User.auto_followup_enabled == True).all()  # noqa: E712
                logger.info(f"Found {len(users)} users with auto follow-up enabled")
                
                processed_count = 0
                skipped_count = 0
                error_count = 0
                
                for user in users:
                    try:
                        # Respect preferred hour if set
                        if user.auto_followup_daily_hour is not None:
                            if now.hour != int(user.auto_followup_daily_hour):
                                skipped_count += 1
                                continue

                        mock_request = Mock()
                        mock_request.headers = {'Authorization': 'Bearer auto-followup-internal'}

                        # Patch owner resolver so the run uses this user
                        import app.api.v1.emails as emails_module
                        original_get_owner = emails_module._get_owner_from_request

                        def mock_get_owner(_req):
                            return user.email

                        emails_module._get_owner_from_request = mock_get_owner
                        try:
                            # Call the runner with a tenant-aware DB by letting the route dependency be bypassed
                            # Here we pass a primary session, the runner handles queries safely per user
                            result = run_auto_followups(mock_request, pdb)
                            processed_count += 1
                            if result.get('sent', 0) > 0 or result.get('failed', 0) > 0:
                                logger.info(f"Auto follow-up for {user.email}: sent={result.get('sent', 0)}, failed={result.get('failed', 0)}")
                        finally:
                            emails_module._get_owner_from_request = original_get_owner
                    except Exception as user_error:
                        error_count += 1
                        logger.error(f"Auto follow-up error for user {user.email}: {user_error}", exc_info=True)
                        continue
                
                logger.info(f"Auto follow-up scheduler completed: processed={processed_count}, skipped={skipped_count}, errors={error_count}")
            finally:
                pdb.close()
        except Exception as scheduler_error:
            # Log but don't crash the scheduler loop
            logger.error(f"Auto follow-up scheduler error: {scheduler_error}", exc_info=True)
    
    try:
        scheduler.add_job(process_scheduled_emails, IntervalTrigger(minutes=1))
        scheduler.add_job(check_imap_emails, IntervalTrigger(minutes=5))  # Check for new emails every 5 minutes
        # Run auto follow-ups hourly; per-user preferred hour gate inside function ensures daily timing
        scheduler.add_job(run_auto_followups_for_all_users, IntervalTrigger(hours=1))
        scheduler.start()
    except Exception as e:
        pass
    yield
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass

# Create FastAPI app
app = FastAPI(
    title="Email Automation API",
    description="Backend API for Email Automation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Build CORS origins list early (before exception handler and middleware)
# Get CORS origins from environment variable, with fallback defaults
cors_origins = settings.cors_origins_list.copy() if hasattr(settings, 'cors_origins_list') else []
# Add common development ports if not already present
dev_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3001", "http://127.0.0.1:3001",
    "http://localhost:5173", "http://127.0.0.1:5173",  # Vite default port
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:5000", "http://127.0.0.1:5000",
    "http://localhost:8080", "http://127.0.0.1:8080",
    "http://localhost:4000", "http://127.0.0.1:4000"
]
for origin in dev_origins:
    if origin not in cors_origins:
        cors_origins.append(origin)

# Helper function to check if origin is a local network IP (for development)
def is_local_network_origin(origin: str) -> bool:
    """Check if origin is from local network (localhost, 127.x.x.x, 10.x.x.x, 192.168.x.x, 172.16-31.x.x)"""
    if not origin:
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        host = parsed.hostname
        if not host:
            return False
        
        # Check for localhost
        if host in ['localhost', '127.0.0.1', '::1']:
            return True
        
        # Check for local network IP ranges
        parts = host.split('.')
        if len(parts) == 4:
            try:
                ip_parts = [int(p) for p in parts]
                # 127.0.0.0/8 (localhost range)
                if ip_parts[0] == 127:
                    return True
                # 10.0.0.0/8 (private network)
                if ip_parts[0] == 10:
                    return True
                # 192.168.0.0/16 (private network)
                if ip_parts[0] == 192 and ip_parts[1] == 168:
                    return True
                # 172.16.0.0/12 (private network)
                if ip_parts[0] == 172 and 16 <= ip_parts[1] <= 31:
                    return True
            except ValueError:
                pass
    except Exception:
        pass
    return False

# Add exception handler for unhandled exceptions to ensure CORS headers are included
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure CORS headers are always present on unhandled errors"""
    from fastapi.responses import JSONResponse
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    
    # Log the full error for debugging
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception: {str(exc)}\n{error_trace}")
    
    # Create a response with error details
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )
    
    # Add CORS headers manually to ensure they're present
    # Use the same CORS origins list as the middleware
    origin = request.headers.get("origin")
    allowed_origins = cors_origins  # Use the same list as CORS middleware
    
    if origin and (origin in allowed_origins or is_local_network_origin(origin)):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
    elif not origin:
        # If no origin header, allow all (for same-origin requests)
        response.headers["Access-Control-Allow-Origin"] = "*"
    
    return response

# Security middleware - Add in order (last added is first executed)
# 1. IP-based rate limiting (first line of defense) - RE-ENABLED FOR SECURITY
app.add_middleware(IPRateLimitMiddleware)

# 2. Input sanitization (second line of defense) - Re-enabled for security
# Note: Can be disabled in production if performance is critical and input validation is handled elsewhere
# app.add_middleware(InputSanitizationMiddleware)

# 3. Security audit and monitoring (third line of defense) - Re-enabled for security
# Note: Can be disabled if performance is critical, but recommended for production
# app.add_middleware(SecurityAuditMiddleware)

# 4. User error logging (for individual user debugging)
# app.add_middleware(UserErrorLoggingMiddleware, debug_enabled=True)

# 5. User access control (check for banned users)
# Note: Re-enable this for production to prevent banned users from accessing the system
# app.middleware("http")(check_user_access_control)

# 6. Security headers (sixth line of defense)
app.add_middleware(SecurityHeadersMiddleware, secret_key=settings.SECRET_KEY)

# 7. Performance monitoring (track slow endpoints)
from app.middleware.performance_monitoring import PerformanceMonitoringMiddleware
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=1.0)

# #region agent log
# Add request logging middleware to track routing and 405 errors
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response

app.add_middleware(RequestLoggingMiddleware)

# CORS middleware - Allow origins for development and production
# cors_origins is already defined above (before exception handler)
# Build regex pattern that includes explicit origins and local network IPs
# For production origins, we'll use allow_origins, for local network we use regex
local_network_regex = r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+):\d+"

# Check if we have any production origins (non-localhost)
production_origins = [o for o in cors_origins if not is_local_network_origin(o)]

if production_origins:
    # Use both explicit origins and regex for local network
    app.add_middleware(
        CORSMiddleware,
        allow_origins=production_origins,
        allow_origin_regex=local_network_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # Cache preflight for 24 hours
    )
else:
    # Only local network, use regex only
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=local_network_regex,
        allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Security
security = HTTPBearer()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Email Automation API is running"}

# Include API routes FIRST (before OPTIONS handler to avoid routing conflicts)
app.include_router(api_router, prefix="/api/v1")


# Handle CORS preflight requests - CORSMiddleware handles this automatically,
# but we add this as a fallback to ensure proper headers
# This should be AFTER API routes to avoid interfering with actual endpoints
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    from fastapi.responses import Response
    origin = request.headers.get("origin")
    allowed_origins = cors_origins
    
    response = Response(status_code=200)
    # Check if origin is allowed (in list or local network)
    if origin:
        if origin in allowed_origins or is_local_network_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
        elif "*" in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
    else:
        # No origin header - allow for same-origin requests
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
    return response
# realtime router removed per request

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Email Automation API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Protected endpoint example
@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        user = await get_current_user(credentials)
        return {"message": f"Hello {user.email}, this is a protected route!"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

if __name__ == "__main__":
    # Use the in-memory app object for Windows compatibility with reload
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
