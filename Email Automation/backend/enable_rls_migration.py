#!/usr/bin/env python3
"""
Migration script to enable Row Level Security (RLS) on all tenant tables.
Run this once to enable RLS on existing tables in all schemas.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import tenant_engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def enable_rls_for_schema(schema_name: str) -> bool:
    """Enable RLS on all tenant tables in a schema."""
    tenant_tables = ['contacts', 'emails', 'meetings', 'todos', 'chat_sessions', 
                     'chat_messages', 'tax_records', 'scraped_leads']
    
    try:
        with tenant_engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
            
            enabled_count = 0
            skipped_count = 0
            
            for table_name in tenant_tables:
                try:
                    # Check if table exists
                    check_query = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = :schema 
                        AND table_name = :table
                    """)
                    result = conn.execute(check_query, {"schema": schema_name, "table": table_name})
                    
                    if not result.fetchone():
                        skipped_count += 1
                        continue
                    
                    # Check if RLS is already enabled
                    rls_check = text("""
                        SELECT tablename, rowsecurity 
                        FROM pg_tables 
                        WHERE schemaname = :schema 
                        AND tablename = :table
                    """)
                    rls_result = conn.execute(rls_check, {"schema": schema_name, "table": table_name})
                    row = rls_result.fetchone()
                    
                    if row and row[1]:  # rowsecurity is True
                        logger.info(f"  ✓ RLS already enabled on {schema_name}.{table_name}")
                        skipped_count += 1
                        continue
                    
                    # Enable RLS
                    conn.execute(text(f'ALTER TABLE "{schema_name}".{table_name} ENABLE ROW LEVEL SECURITY'))
                    logger.info(f"  ✅ Enabled RLS on {schema_name}.{table_name}")
                    enabled_count += 1
                    
                except Exception as table_error:
                    logger.error(f"  ❌ Error enabling RLS on {table_name}: {table_error}")
                    continue
            
            if enabled_count > 0:
                logger.info(f"  Summary: Enabled RLS on {enabled_count} table(s), {skipped_count} skipped")
            return True
        
    except Exception as schema_error:
        logger.error(f"  ❌ Error processing schema {schema_name}: {schema_error}")
        return False

def run_rls_migration():
    """Enable RLS on all tenant schemas."""
    try:
        logger.info("=" * 60)
        logger.info("Enabling Row Level Security (RLS) on tenant tables")
        logger.info("=" * 60)
        
        db_url = settings.TENANT_DATABASE_URL or settings.DATABASE_URL
        
        if not db_url or not db_url.startswith("postgresql"):
            logger.warning("This migration is for PostgreSQL/Supabase only.")
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
            
            logger.info(f"Found {len(schemas)} schema(s) to process\n")
            
            success_count = 0
            error_count = 0
            
            for schema in schemas:
                logger.info(f"Processing schema: {schema}")
                if enable_rls_for_schema(schema):
                    success_count += 1
                else:
                    error_count += 1
                logger.info("")
            
            logger.info("=" * 60)
            logger.info("RLS Migration Summary:")
            logger.info(f"  ✅ Successfully processed: {success_count}")
            logger.info(f"  ❌ Errors: {error_count}")
            logger.info(f"  Total schemas: {len(schemas)}")
            logger.info("=" * 60)
            
            if error_count == 0:
                logger.info("✅ RLS migration completed successfully!")
                logger.info("\nNote: RLS is now enabled. Make sure you have appropriate RLS policies")
                logger.info("if you're using Supabase's built-in authentication.")
            else:
                logger.warning(f"⚠ RLS migration completed with {error_count} error(s).")
            
    except Exception as e:
        logger.error(f"❌ RLS migration failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_rls_migration()

