-- Migration: Add attachments column to emails table
-- Run this SQL in your Supabase SQL editor or database migration tool
--
-- For multi-tenant setups, this will add the column to the public schema.
-- For tenant schemas, use the Python migration script: python run_migration.py
--
-- The attachments column stores JSON array of attachment metadata:
-- [{"filename": "document.pdf", "content_type": "application/pdf", "size": 12345}]

-- For public schema (if not using multi-tenant)
ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;

-- For multi-tenant schemas, run for each tenant schema:
-- Replace 'tenant_xxx' with actual schema name
-- ALTER TABLE "tenant_xxx".emails ADD COLUMN IF NOT EXISTS attachments TEXT;

-- To find all tenant schemas:
-- SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%';

