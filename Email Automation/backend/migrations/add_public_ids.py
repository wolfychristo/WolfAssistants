#!/usr/bin/env python3
"""
Migration script to add public_id columns to emails, contacts, meetings, chat_sessions, and chat_messages tables.
This script handles multi-tenant architecture by migrating all tenant schemas.

This script:
1. Finds all tenant schemas (tenant_*)
2. Adds public_id column to each table in each schema
3. Generates UUIDs for existing records
4. Adds unique constraint and index
5. Uses proper transactions for data safety
"""

import sys
import os
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import tenant_engine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tables to migrate
TABLES_TO_MIGRATE = ['emails', 'contacts', 'meetings', 'chat_sessions', 'chat_messages']


def add_public_id_column(schema_name: str, table_name: str) -> bool:
    """Add public_id column to a table in a given schema.
    
    Returns True if column was added or already exists, False on error.
    """
    conn = None
    try:
        conn = tenant_engine.connect()
        
        # Check if column already exists
        check_query = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = :schema 
            AND table_name = :table 
            AND column_name = 'public_id'
        """)
        result = conn.execute(check_query, {'schema': schema_name, 'table': table_name})
        
        if result.fetchone():
            logger.info(f"    ✓ Column 'public_id' already exists in {schema_name}.{table_name}")
            return True
        
        # Use schema-qualified table name for all operations
        qualified_table = f'"{schema_name}".{table_name}'
        
        # Add column (nullable initially)
        logger.info(f"    Adding public_id column to {schema_name}.{table_name}...")
        conn.execute(text(f"""
            ALTER TABLE {qualified_table} 
            ADD COLUMN public_id VARCHAR(36)
        """))
        conn.commit()
        
        # Generate UUIDs for existing records - use schema-qualified name
        logger.info(f"    Generating UUIDs for existing records in {schema_name}.{table_name}...")
        # Use parameterized query for safety
        select_query = text(f'SELECT id FROM {qualified_table} WHERE public_id IS NULL')
        result = conn.execute(select_query)
        records = result.fetchall()
        
        updated_count = 0
        if records:
            # Batch update for better performance
            for record in records:
                record_id = record[0]
                new_uuid = str(uuid.uuid4())
                update_query = text(f"""
                    UPDATE {qualified_table} 
                    SET public_id = :uuid 
                    WHERE id = :record_id
                """)
                conn.execute(update_query, {'uuid': new_uuid, 'record_id': record_id})
                updated_count += 1
            conn.commit()
        logger.info(f"    Generated {updated_count} UUIDs for {schema_name}.{table_name}")
        
        # Make column NOT NULL
        logger.info(f"    Adding NOT NULL constraint to {schema_name}.{table_name}...")
        conn.execute(text(f"""
            ALTER TABLE {qualified_table} 
            ALTER COLUMN public_id SET NOT NULL
        """))
        conn.commit()
        
        # Create unique index - check if exists first, then create
        index_name = f"{table_name}_public_id_idx"
        logger.info(f"    Creating unique index on {schema_name}.{table_name}...")
        
        # Check if index already exists
        check_index = text(f"""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = :schema 
            AND tablename = :table 
            AND indexname = :index_name
        """)
        index_result = conn.execute(check_index, {
            'schema': schema_name, 
            'table': table_name, 
            'index_name': index_name
        })
        
        if not index_result.fetchone():
            # Index doesn't exist, create it
            # Index will be created in the same schema as the table
            conn.execute(text(f"""
                CREATE UNIQUE INDEX {index_name} 
                ON {qualified_table}(public_id)
            """))
            conn.commit()
        else:
            logger.info(f"    Index {index_name} already exists, skipping")
        
        logger.info(f"    ✓ Completed {schema_name}.{table_name}")
        return True
        
    except Exception as e:
        logger.error(f"    ✗ Error migrating {schema_name}.{table_name}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def migrate_schema(schema_name: str) -> tuple[int, int]:
    """Migrate all tables in a schema.
    
    Returns (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    logger.info(f"\nMigrating schema: {schema_name}")
    
    for table_name in TABLES_TO_MIGRATE:
        # Check if table exists in this schema
        try:
            with tenant_engine.connect() as conn:
                check_table = text(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    AND table_name = :table
                """)
                result = conn.execute(check_table, {'schema': schema_name, 'table': table_name})
                
                if not result.fetchone():
                    logger.info(f"    ⊘ Table {table_name} does not exist in {schema_name}, skipping")
                    continue
                
                if add_public_id_column(schema_name, table_name):
                    success_count += 1
                else:
                    error_count += 1
        except Exception as e:
            logger.error(f"    ✗ Error checking table {schema_name}.{table_name}: {e}")
            error_count += 1
    
    return success_count, error_count


def run_migration():
    """Run the migration to add public_id columns to all tables."""
    
    try:
        logger.info("=" * 60)
        logger.info("Starting migration: Add public_id columns")
        logger.info("=" * 60)
        
        # Check if we're using PostgreSQL (Supabase)
        db_url = settings.TENANT_DATABASE_URL or settings.DATABASE_URL
        
        if not db_url or not db_url.startswith("postgresql"):
            logger.warning("This migration is for PostgreSQL/Supabase. Skipping for non-PostgreSQL databases.")
            return
        
        # Connect to database
        with tenant_engine.connect() as conn:
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
            
            # Check if public schema has any of our tables
            for table_name in TABLES_TO_MIGRATE:
                public_check = text(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table
                """)
                public_result = conn.execute(public_check, {'table': table_name})
                if public_result.fetchone():
                    if 'public' not in schemas_to_migrate:
                        schemas_to_migrate.append('public')
                    break
            
            if not schemas_to_migrate:
                logger.warning("No schemas found. Nothing to migrate.")
                return
            
            logger.info(f"Found {len(schemas_to_migrate)} schema(s) to migrate:")
            for schema in schemas_to_migrate:
                logger.info(f"  - {schema}")
        
        # Migrate each schema
        total_success = 0
        total_errors = 0
        
        for schema in schemas_to_migrate:
            success, errors = migrate_schema(schema)
            total_success += success
            total_errors += errors
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  ✅ Successfully migrated tables: {total_success}")
        logger.info(f"  ❌ Errors: {total_errors}")
        logger.info(f"  Total schemas processed: {len(schemas_to_migrate)}")
        logger.info("=" * 60)
        
        if total_errors == 0:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning(f"⚠ Migration completed with {total_errors} error(s). Please review the logs above.")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
