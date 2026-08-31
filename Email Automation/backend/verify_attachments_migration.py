#!/usr/bin/env python3
"""
Verification script to check if attachments column exists in all schemas.
Run this after migration to verify everything is set up correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import tenant_engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_migration():
    """Verify that attachments column exists in all schemas."""
    
    try:
        logger.info("=" * 60)
        logger.info("Verifying attachments column migration")
        logger.info("=" * 60)
        
        # Check if we're using PostgreSQL
        db_url = settings.TENANT_DATABASE_URL or settings.DATABASE_URL
        
        if not db_url or not db_url.startswith("postgresql"):
            logger.warning("This verification is for PostgreSQL/Supabase only.")
            return
        
        with tenant_engine.connect() as conn:
            # Get all tenant schemas
            schema_query = text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'
                ORDER BY schema_name
            """)
            
            result = conn.execute(schema_query)
            schemas = [row[0] for row in result.fetchall()]
            
            if not schemas:
                logger.warning("No schemas found.")
                return
            
            logger.info(f"Checking {len(schemas)} schema(s)...\n")
            
            all_ok = True
            schemas_with_emails = []
            schemas_missing_column = []
            schemas_without_table = []
            
            for schema in schemas:
                # Check if emails table exists
                table_check = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    AND table_name = 'emails'
                """)
                table_result = conn.execute(table_check, {"schema": schema})
                
                if not table_result.fetchone():
                    logger.info(f"{schema}: ⚠ No emails table found")
                    schemas_without_table.append(schema)
                    continue
                
                schemas_with_emails.append(schema)
                
                # Check if attachments column exists
                column_check = text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = :schema 
                    AND table_name = 'emails' 
                    AND column_name = 'attachments'
                """)
                column_result = conn.execute(column_check, {"schema": schema})
                column_info = column_result.fetchone()
                
                if column_info:
                    data_type = column_info[1]
                    logger.info(f"{schema}: ✅ attachments column exists (type: {data_type})")
                else:
                    logger.error(f"{schema}: ❌ attachments column MISSING")
                    schemas_missing_column.append(schema)
                    all_ok = False
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("Verification Summary:")
            logger.info(f"  Total schemas checked: {len(schemas)}")
            logger.info(f"  Schemas with emails table: {len(schemas_with_emails)}")
            logger.info(f"  Schemas with attachments column: {len(schemas_with_emails) - len(schemas_missing_column)}")
            logger.info(f"  Schemas missing attachments column: {len(schemas_missing_column)}")
            logger.info(f"  Schemas without emails table: {len(schemas_without_table)}")
            
            if schemas_missing_column:
                logger.error("\n❌ Schemas missing attachments column:")
                for schema in schemas_missing_column:
                    logger.error(f"  - {schema}")
                logger.error("\nRun migration script: python run_migration.py")
            
            if all_ok and schemas_with_emails:
                logger.info("\n✅ All schemas with emails table have attachments column!")
            elif not schemas_with_emails:
                logger.warning("\n⚠ No schemas with emails table found.")
            
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    verify_migration()

