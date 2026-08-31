from pydantic_settings import BaseSettings
from typing import Optional, List, Literal
import json
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Email Automation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database - Multi-tenant architecture
    # Accounts database: stores authentication and account data
    ACCOUNTS_DATABASE_URL: Optional[str] = None  # If not set, falls back to DATABASE_URL
    
    # Tenant database: stores user business data in schemas
    TENANT_DATABASE_URL: Optional[str] = None  # If not set, falls back to DATABASE_URL
    
    # Legacy: kept for backward compatibility
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@YOUR_SUPABASE_HOST:5432/postgres"
    
    # PostgreSQL connection (set in .env)
    # Supabase example: postgresql+psycopg://postgres.YOUR_REF:PASS@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    # For multi-tenant: Set ACCOUNTS_DATABASE_URL and TENANT_DATABASE_URL separately
    # Or use same DATABASE_URL for both (they can share the same database with different schemas)
    
    # Security
    SECRET_KEY: str = "your-new-secure-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # Email Configuration
    EMAIL_HOST: Optional[str] = None
    EMAIL_PORT: Optional[int] = None
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    EMAIL_USE_TLS: bool = True
    # Inbound Email (IMAP)
    IMAP_HOST: Optional[str] = None
    IMAP_PORT: Optional[int] = None
    IMAP_USER: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None
    IMAP_USE_SSL: bool = True
    
    # System Email Configuration (for OTPs and notifications)
    SYSTEM_EMAIL_HOST: Optional[str] = None
    SYSTEM_EMAIL_PORT: Optional[int] = None
    SYSTEM_EMAIL_USER: Optional[str] = None
    SYSTEM_EMAIL_PASSWORD: Optional[str] = None
    SYSTEM_EMAIL_FROM: str = "WolfAssistants <info@yourcompany.com>"
    SYSTEM_EMAIL_USE_TLS: bool = True
    
    # Wolfy AI API - Single key (legacy)
    GEMINI_API_KEY: Optional[str] = None
    
    # Wolfy AI API - Multiple keys for load balancing
    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    GEMINI_API_KEY_4: Optional[str] = None
    GEMINI_API_KEY_5: Optional[str] = None
    GEMINI_API_KEY_6: Optional[str] = None
    GEMINI_API_KEY_7: Optional[str] = None
    GEMINI_API_KEY_8: Optional[str] = None
    
    # API Key Categorization Settings
    API_KEY_CATEGORIZATION_ENABLED: bool = True
    API_KEY_ENTERPRISE_KEYS: str = "1,2"  # Comma-separated key numbers
    API_KEY_PROFESSIONAL_KEYS: str = "3,4"
    API_KEY_STARTER_KEYS: str = "5,6"
    API_KEY_FREE_KEYS: str = "7,8"
    
    # Engagement thresholds (emails sent in last 30 days)
    ENGAGEMENT_ENTERPRISE_EMAILS: int = 1000
    ENGAGEMENT_PROFESSIONAL_EMAILS: int = 100
    ENGAGEMENT_STARTER_EMAILS: int = 10
    
    # Request Queue Settings
    REQUEST_QUEUE_ENABLED: bool = False  # Disabled by default
    REQUEST_QUEUE_MAX_CONCURRENT: int = 20
    
    # Circuit Breaker Settings
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # seconds
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_CONNECT_CLIENT_ID: Optional[str] = None
    
    # CORS (string to avoid pydantic env JSON parsing; we parse ourselves)
    # Format: comma-separated list of origins
    # Example: "http://localhost:3000,https://wolfassistants.com,https://www.wolfassistants.com"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(x) for x in data]
            except Exception:
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]
    
    @property
    def gemini_api_keys(self) -> List[str]:
        """Get all available Gemini API keys for load balancing."""
        keys = []
        
        # Add single key if available (legacy support)
        if self.GEMINI_API_KEY:
            keys.append(self.GEMINI_API_KEY)
        
        # Add multiple keys
        for i in range(1, 9):  # GEMINI_API_KEY_1 to GEMINI_API_KEY_8
            key = getattr(self, f"GEMINI_API_KEY_{i}", None)
            if key:
                keys.append(key)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for key in keys:
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
        
        return unique_keys
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

# Create settings instance
settings = Settings()

# Override with environment variables if they exist
database_url = os.getenv("DATABASE_URL")
if database_url:
    settings.DATABASE_URL = database_url

secret_key = os.getenv("SECRET_KEY")
if secret_key:
    settings.SECRET_KEY = secret_key

gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    settings.GEMINI_API_KEY = gemini_api_key

# Override accounts and tenant database URLs if provided
accounts_db_url = os.getenv("ACCOUNTS_DATABASE_URL")
if accounts_db_url:
    settings.ACCOUNTS_DATABASE_URL = accounts_db_url

tenant_db_url = os.getenv("TENANT_DATABASE_URL")
if tenant_db_url:
    settings.TENANT_DATABASE_URL = tenant_db_url

def _validate_environment(cfg: Settings) -> None:
    env = (cfg.ENVIRONMENT or "development").lower()
    if "YOUR_SUPABASE_HOST" in cfg.DATABASE_URL:
        raise ValueError("DATABASE_URL must be updated with your actual Supabase connection string.")
    if env == "production":
        if cfg.DATABASE_URL.startswith("sqlite"):
            raise ValueError("DATABASE_URL must point to a production-ready database when ENVIRONMENT=production.")
        if "localhost" in cfg.DATABASE_URL or "127.0.0.1" in cfg.DATABASE_URL:
            raise ValueError("DATABASE_URL cannot use a localhost host when ENVIRONMENT=production.")
        if cfg.SECRET_KEY == "your-new-secure-secret-key-here-change-this-in-production":
            raise ValueError("SECRET_KEY must be provided via environment variables when ENVIRONMENT=production.")

_validate_environment(settings)
