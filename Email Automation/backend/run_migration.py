#!/usr/bin/env python3
"""
Migration script to add attachments column to emails table.
This script can be run programmatically if Supabase SQL Editor is not accessible.

This script:
1. Finds all tenant schemas (tenant_*)
2. Adds attachments column to emails table in each schema
3. Also checks and migrates public schema if needed
4. Uses proper transactions for data safety
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import tenant_engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_attachments_column(schema_name: str) -> bool:
    """Ensure attachments column exists in emails table for a given schema.
    
    Uses its own connection and transaction for isolation.
    Returns True if column was added or already exists, False on error.
    """
    try:
        # Use a separate connection for checking (read-only operations)
        with tenant_engine.connect() as check_conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = :schema 
                AND table_name = 'emails' 
                AND column_name = 'attachments'
            """)
            
            check_result = check_conn.execute(check_query, {"schema": schema_name})
            if check_result.fetchone():
                logger.info(f"  ✓ Column 'attachments' already exists in {schema_name}.emails")
                return True
            
            # Check if emails table exists
            table_check = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema 
                AND table_name = 'emails'
            """)
            
            table_result = check_conn.execute(table_check, {"schema": schema_name})
            if not table_result.fetchone():
                logger.warning(f"  ⚠ Table 'emails' does not exist in schema {schema_name} - skipping")
                return False
        
        # Use engine.begin() for DDL operations - this creates a new connection with transaction
        with tenant_engine.begin() as ddl_conn:
            alter_query = text(f'ALTER TABLE "{schema_name}".emails ADD COLUMN attachments TEXT')
            ddl_conn.execute(alter_query)
        
        logger.info(f"  ✅ Successfully added 'attachments' column to {schema_name}.emails")
        return True
        
    except Exception as schema_error:
        logger.error(f"  ❌ Error migrating schema {schema_name}: {schema_error}")
        return False

def run_migration():
    """Run the migration to add attachments column to emails table."""
    
    try:
        logger.info("=" * 60)
        logger.info("Starting migration: Add attachments column to emails table")
        logger.info("=" * 60)
        
        # Check if we're using PostgreSQL (Supabase)
        db_url = settings.TENANT_DATABASE_URL or settings.DATABASE_URL
        
        if not db_url or not db_url.startswith("postgresql"):
            logger.warning("This migration is for PostgreSQL/Supabase. Skipping for non-PostgreSQL databases.")
            return
        
        # Connect to database - use begin() to manage transactions properly
        with tenant_engine.begin() as conn:
            # Get all tenant schemas
            logger.info("Finding tenant schemas...")
            schema_query = text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%'
                ORDER BY schema_name
            """)
            
            result = conn.execute(schema_query)
            tenant_schemas = [row[0] for row in result.fetchall()]
            
            # Also check public schema
            schemas_to_migrate = tenant_schemas.copy()
            
            # Check if public schema has emails table
            public_check = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'emails'
            """)
            public_result = conn.execute(public_check)
            if public_result.fetchone():
                schemas_to_migrate.append('public')
            
            if not schemas_to_migrate:
                logger.warning("No schemas with emails table found. Nothing to migrate.")
                return
            
            logger.info(f"Found {len(schemas_to_migrate)} schema(s) to migrate:")
            for schema in schemas_to_migrate:
                logger.info(f"  - {schema}")
            
            # Migrate each schema - each uses its own connection and transaction
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for schema in schemas_to_migrate:
                logger.info(f"\nMigrating schema: {schema}")
                # ensure_attachments_column uses its own connection internally
                if ensure_attachments_column(schema):
                    success_count += 1
                else:
                    error_count += 1
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("Migration Summary:")
            logger.info(f"  ✅ Successfully migrated: {success_count}")
            logger.info(f"  ❌ Errors: {error_count}")
            logger.info(f"  Total schemas processed: {len(schemas_to_migrate)}")
            logger.info("=" * 60)
            
            if error_count == 0:
                logger.info("✅ Migration completed successfully!")
            else:
                logger.warning(f"⚠ Migration completed with {error_count} error(s). Please review the logs above.")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()


