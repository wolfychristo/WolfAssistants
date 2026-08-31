#!/usr/bin/env python3
"""
Create invoice_clients table in all tenant schemas.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import tenant_engine
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_tenant_schemas():
    with tenant_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name LIKE 'tenant_%'
            ORDER BY schema_name
        """))
        return [row[0] for row in result.fetchall()]


def create_invoice_clients_table(schema_name: str):
    qualified_table = f'"{schema_name}".invoice_clients'
    with tenant_engine.connect() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {qualified_table} (
                id SERIAL PRIMARY KEY,
                public_id VARCHAR(36) NOT NULL,
                name VARCHAR NOT NULL,
                business_name VARCHAR NULL,
                address VARCHAR NULL,
                email VARCHAR NULL,
                phone VARCHAR NULL,
                tax_id VARCHAR NULL,
                country_code VARCHAR NULL,
                owner_email VARCHAR NULL,
                created_at TIMESTAMP NULL DEFAULT NOW()
            )
        """))
        conn.execute(text(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS invoice_clients_public_id_idx
            ON {qualified_table} (public_id)
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS invoice_clients_owner_email_idx
            ON {qualified_table} (owner_email)
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS invoice_clients_email_idx
            ON {qualified_table} (email)
        """))
        conn.commit()


def run():
    schemas = get_tenant_schemas()
    if not schemas:
        logger.info("No tenant schemas found.")
        return

    logger.info(f"Found {len(schemas)} tenant schemas.")
    for schema_name in schemas:
        try:
            logger.info(f"Creating invoice_clients in {schema_name}...")
            create_invoice_clients_table(schema_name)
            logger.info(f"✓ {schema_name}")
        except Exception as exc:
            logger.error(f"✗ {schema_name}: {exc}")


if __name__ == "__main__":
    run()
