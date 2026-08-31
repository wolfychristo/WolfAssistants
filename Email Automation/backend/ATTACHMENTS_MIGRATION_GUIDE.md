# Attachments Column Migration Guide

## Overview

This guide ensures the `attachments` column is properly added to the `emails` table in all tenant schemas.

## Quick Start

### Option 1: Automated Migration (Recommended)

Run the Python migration script which automatically finds and migrates all tenant schemas:

```bash
cd "Email Automation/backend"
python run_migration.py
```

This script will:
- ✅ Find all tenant schemas (`tenant_*`)
- ✅ Check public schema if it has emails table
- ✅ Add `attachments` column to each schema's emails table
- ✅ Skip schemas where column already exists
- ✅ Provide detailed logging and summary

### Option 2: Manual SQL Migration

If you prefer to run SQL manually:

1. **For Public Schema:**
   ```sql
   ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;
   ```

2. **For Each Tenant Schema:**
   ```sql
   -- First, find all tenant schemas:
   SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%';
   
   -- Then run for each schema (replace tenant_xxx with actual name):
   ALTER TABLE "tenant_xxx".emails ADD COLUMN IF NOT EXISTS attachments TEXT;
   ```

## Verification

After running the migration, verify it worked:

```bash
python verify_attachments_migration.py
```

This will check all schemas and report:
- ✅ Schemas with attachments column
- ❌ Schemas missing the column
- ⚠ Schemas without emails table

## What the Column Stores

The `attachments` column stores JSON metadata (not file paths):

```json
[
  {
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size": 12345
  },
  {
    "filename": "image.jpg",
    "content_type": "image/jpeg",
    "size": 56789
  }
]
```

**Note:** Actual files are stored temporarily in `temp_attachments/` and deleted after sending.

## Automatic Column Creation

When new tenant schemas are created (via `create_tenant_schema()`), the attachments column is automatically added if the Email model includes it. The migration script ensures existing schemas are also updated.

## Troubleshooting

### Column Already Exists Error

If you see "column already exists", this is safe to ignore. The migration script uses `IF NOT EXISTS` to prevent errors.

### Migration Script Fails

1. Check database connection settings in `.env`
2. Verify `TENANT_DATABASE_URL` or `DATABASE_URL` is set correctly
3. Ensure you have PostgreSQL/Supabase (not SQLite)
4. Check database user has ALTER TABLE permissions

### Column Missing After Migration

1. Run verification script: `python verify_attachments_migration.py`
2. Check logs for specific schema errors
3. Manually add column for that schema:
   ```sql
   ALTER TABLE "schema_name".emails ADD COLUMN attachments TEXT;
   ```

## Files

- **Migration Script**: `backend/run_migration.py`
- **Verification Script**: `backend/verify_attachments_migration.py`
- **SQL Migration**: `backend/migrations/add_attachments_to_emails.sql`
- **Model Definition**: `backend/app/models/email.py` (line 39)

## Status

✅ **Migration Script**: Complete and tested
✅ **Verification Script**: Complete
✅ **Automatic Column Creation**: Implemented in `create_tenant_schema()`
✅ **Database Model**: Includes attachments column definition

