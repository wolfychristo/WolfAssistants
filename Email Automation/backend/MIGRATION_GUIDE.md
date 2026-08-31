# Migration Guide: Add Attachments Column

## Problem
The `attachments` column doesn't exist in the `emails` table, causing 500 errors when querying emails.

## Good News! 🎉
**The application should work WITHOUT the migration** thanks to the fallback code that automatically detects missing columns and uses raw SQL queries.

However, to enable full attachment functionality, you should run the migration.

## Option 1: Run Migration Script (Recommended)

If Supabase SQL Editor is not accessible, use the Python migration script:

```bash
cd "Email Automation\backend"
python run_migration.py
```

This script will:
- Automatically find all tenant schemas
- Add the `attachments` column to each schema's `emails` table
- Skip schemas where the column already exists
- Provide detailed logging

## Option 2: Supabase SQL Editor

If Supabase SQL Editor is working:

1. Go to your Supabase Dashboard
2. Navigate to SQL Editor
3. Run this SQL:

```sql
-- For public schema (if not using multi-tenant)
ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;

-- For multi-tenant schemas, run for each tenant:
-- Replace 'tenant_xxx' with actual schema name
ALTER TABLE "tenant_xxx".emails ADD COLUMN IF NOT EXISTS attachments TEXT;
```

## Option 3: Direct PostgreSQL Connection

If you have direct PostgreSQL access:

```bash
psql "your-connection-string"

-- Then run:
ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;
```

## Troubleshooting Supabase Connection Error

If you're getting "Failed to fetch (api.supabase.com)":

1. **Check Supabase Status**: Visit https://status.supabase.com
2. **Try Again Later**: This is usually a temporary network issue
3. **Use Migration Script**: Run `python run_migration.py` instead
4. **Check Browser Console**: Look for CORS or network errors
5. **Try Different Browser**: Sometimes browser extensions cause issues
6. **Check Network**: Ensure you can access api.supabase.com

## Verification

After running the migration:

1. **Check Backend Logs**: Should see "Attachments column found" instead of "using raw SQL query"
2. **Test Email Endpoints**: `/api/v1/emails/?folder=inbox` should work
3. **Test Attachments**: Try uploading an attachment - it should be saved

## Current Behavior

**Without Migration:**
- ✅ Application works (uses raw SQL fallback)
- ✅ Emails display correctly
- ❌ Attachments won't be saved (column doesn't exist)
- ⚠️ Slightly slower queries (raw SQL)

**With Migration:**
- ✅ Full functionality
- ✅ Attachments are saved and retrieved
- ✅ Faster queries (normal SQLAlchemy)
- ✅ All features work as expected

## Need Help?

If the migration script fails, check:
1. Database connection string is correct in `.env`
2. You have write permissions to the database
3. The database is accessible (not paused/stopped)


