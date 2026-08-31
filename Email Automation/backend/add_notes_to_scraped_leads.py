#!/usr/bin/env python3
"""
Migration script to add 'notes' column to scraped_leads table in all tenant schemas.
This script handles both existing schemas and ensures new schemas have the column.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_schemas(engine):
    """Get all tenant schemas from the database"""
    schemas = []
    try:
        with engine.connect() as conn:
            # Get all schemas that match tenant pattern (user email hash)
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
                AND schema_name NOT LIKE 'pg_%'
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result]
            logger.info(f"Found {len(schemas)} schemas to check")
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
    return schemas


def add_notes_column_to_schema(engine, schema_name):
    """Add notes column to scraped_leads table in a specific schema"""
    try:
        with engine.begin() as conn:  # Use begin() for transaction
            # Set search_path to the schema
            conn.execute(text(f"SET LOCAL search_path TO {schema_name}"))
            
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    AND table_name = 'scraped_leads'
                )
            """), {"schema": schema_name})
            
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info(f"  Table scraped_leads does not exist in schema {schema_name}, skipping")
                return False
            
            # Check if notes column already exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = :schema 
                    AND table_name = 'scraped_leads'
                    AND column_name = 'notes'
                )
            """), {"schema": schema_name})
            
            column_exists = result.scalar()
            
            if column_exists:
                logger.info(f"  Column 'notes' already exists in {schema_name}.scraped_leads")
                return True
            
            # Add the notes column
            logger.info(f"  Adding 'notes' column to {schema_name}.scraped_leads...")
            conn.execute(text("""
                ALTER TABLE scraped_leads 
                ADD COLUMN IF NOT EXISTS notes TEXT
            """))
            
            logger.info(f"  ✓ Successfully added 'notes' column to {schema_name}.scraped_leads")
            return True
            
    except ProgrammingError as e:
        error_str = str(e).lower()
        if 'does not exist' in error_str or 'relation' in error_str:
            logger.warning(f"  Table scraped_leads does not exist in schema {schema_name}")
            return False
        else:
            logger.error(f"  ✗ Error adding notes column to {schema_name}: {e}")
            return False
    except Exception as e:
        logger.error(f"  ✗ Unexpected error for schema {schema_name}: {e}")
        return False


def main():
    """Main migration function"""
    logger.info("Starting migration: Add 'notes' column to scraped_leads table")
    
    # Create database engine
    database_url = settings.DATABASE_URL
    if not database_url:
        logger.error("DATABASE_URL not set in environment variables")
        sys.exit(1)
    
    engine = create_engine(database_url, pool_pre_ping=True)
    
    # Get all schemas
    schemas = get_all_schemas(engine)
    
    if not schemas:
        logger.warning("No schemas found. Migration will only affect new schemas created after this.")
        logger.info("Migration completed (no existing schemas to update)")
        return
    
    # Process each schema
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for schema in schemas:
        logger.info(f"Processing schema: {schema}")
        result = add_notes_column_to_schema(engine, schema)
        if result:
            success_count += 1
        elif result is False and "does not exist" in str(result):
            skip_count += 1
        else:
            error_count += 1
    
    logger.info("\n" + "="*60)
    logger.info("Migration Summary:")
    logger.info(f"  Successfully updated: {success_count} schemas")
    logger.info(f"  Skipped (no table): {skip_count} schemas")
    logger.info(f"  Errors: {error_count} schemas")
    logger.info("="*60)
    logger.info("Migration completed!")


if __name__ == "__main__":
    main()

