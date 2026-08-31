#!/usr/bin/env python3
"""
Force add subscription_id column with retry logic and timeout handling
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import accounts_engine
from sqlalchemy import text
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_add_column():
    """Force add subscription_id column with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries} to add subscription_id column...")
            
            # Use a connection with autocommit to avoid transaction issues
            with accounts_engine.connect() as conn:
                # Use DO block to check and add column atomically
                result = conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = 'app_users' 
                            AND column_name = 'subscription_id'
                        ) THEN
                            ALTER TABLE app_users ADD COLUMN subscription_id VARCHAR;
                            RAISE NOTICE 'Column subscription_id added successfully';
                        ELSE
                            RAISE NOTICE 'Column subscription_id already exists';
                        END IF;
                    END $$;
                """))
                conn.commit()
                logger.info("✓ Successfully added subscription_id column (or it already exists)")
                return True
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"✗ Attempt {attempt + 1} failed: {error_msg}")
            
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                logger.info("Column already exists, skipping")
                return True
                
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to add column after {max_retries} attempts")
                return False
    
    return False

if __name__ == "__main__":
    success = force_add_column()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed. You may need to check for database locks.")
        sys.exit(1)
