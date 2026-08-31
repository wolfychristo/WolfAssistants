#!/usr/bin/env python3
"""
Database migration script to create deliverability protection tables.
Run this once to set up the email_reputation and bounce_records tables.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.config import settings
from app.models.email_reputation import EmailReputation, BounceRecord  # Import to ensure metadata is loaded

DATABASE_URL = settings.ACCOUNTS_DATABASE_URL or settings.DATABASE_URL
engine = create_engine(DATABASE_URL)

def create_deliverability_tables():
    """Create email_reputation and bounce_records tables"""
    with engine.connect() as connection:
        try:
            # Create email_reputation table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS email_reputation (
                    id SERIAL PRIMARY KEY,
                    owner_email VARCHAR NOT NULL,
                    mailbox VARCHAR NOT NULL,
                    spf_configured BOOLEAN DEFAULT FALSE,
                    dkim_configured BOOLEAN DEFAULT FALSE,
                    spf_last_checked TIMESTAMP,
                    dkim_last_checked TIMESTAMP,
                    total_sent INTEGER DEFAULT 0,
                    total_delivered INTEGER DEFAULT 0,
                    total_bounced INTEGER DEFAULT 0,
                    total_complained INTEGER DEFAULT 0,
                    cold_sends_today INTEGER DEFAULT 0,
                    cold_sends_reset_at TIMESTAMP,
                    max_cold_sends_per_day INTEGER DEFAULT 50,
                    reputation_score FLOAT DEFAULT 100.0,
                    last_calculated TIMESTAMP,
                    is_throttled BOOLEAN DEFAULT FALSE,
                    throttle_reason VARCHAR,
                    throttle_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes for email_reputation
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_reputation_owner 
                ON email_reputation(owner_email)
            """))
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_reputation_mailbox 
                ON email_reputation(mailbox)
            """))
            
            # Create bounce_records table
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS bounce_records (
                    id SERIAL PRIMARY KEY,
                    reputation_id INTEGER NOT NULL,
                    owner_email VARCHAR NOT NULL,
                    mailbox VARCHAR NOT NULL,
                    recipient_email VARCHAR NOT NULL,
                    bounce_type VARCHAR NOT NULL,
                    bounce_reason TEXT,
                    bounce_code VARCHAR,
                    email_id INTEGER,
                    subject VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reputation_id) REFERENCES email_reputation(id) ON DELETE CASCADE
                )
            """))
            
            # Create indexes for bounce_records
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bounce_records_owner 
                ON bounce_records(owner_email)
            """))
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bounce_records_reputation 
                ON bounce_records(reputation_id)
            """))
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bounce_records_created 
                ON bounce_records(created_at)
            """))
            
            connection.commit()
            print("✅ Successfully created deliverability protection tables!")
            print("   - email_reputation")
            print("   - bounce_records")
            
        except (OperationalError, ProgrammingError) as e:
            print(f"❌ Database error: {e}")
            connection.rollback()
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            connection.rollback()

if __name__ == "__main__":
    print("Creating deliverability protection tables...")
    create_deliverability_tables()
    print("\n✅ Migration completed!")
    print("You can now use the deliverability protection features.")

