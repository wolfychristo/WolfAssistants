#!/usr/bin/env python3
"""
Add remaining marketplace columns
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import accounts_engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_remaining_columns():
    """Add remaining marketplace columns"""
    columns = [
        ("is_freelancer", "BOOLEAN DEFAULT FALSE"),
        ("freelancer_profile_id", "INTEGER"),
        ("stripe_connect_account_id", "VARCHAR"),
        ("marketplace_commission_rate", "FLOAT"),
    ]
    
    with accounts_engine.connect() as conn:
        for column_name, column_type in columns:
            try:
                conn.execute(text(f"""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = 'app_users' 
                            AND column_name = '{column_name}'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN {column_name} {column_type};
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info(f"✓ Added {column_name} column (or it already exists)")
            except Exception as e:
                logger.warning(f"✗ Failed to add {column_name}: {e}")
                conn.rollback()

if __name__ == "__main__":
    add_remaining_columns()
    logger.info("Done!")
