# Row Level Security (RLS) Setup

## Overview

Row Level Security (RLS) has been automatically enabled for all tenant tables when new schemas are created. This provides an additional layer of security for your Supabase database.

## What is RLS?

Row Level Security is a PostgreSQL feature that restricts which rows can be accessed by database queries. When enabled, tables are protected by default - no rows are accessible unless explicitly allowed by RLS policies.

## Current Implementation

### Automatic RLS Enablement

RLS is automatically enabled when:
- New tenant schemas are created via `create_tenant_schema()`
- Tables are initialized in tenant schemas

The following tables have RLS enabled:
- `contacts`
- `emails`
- `meetings`
- `todos`
- `chat_sessions`
- `chat_messages`
- `tax_records`
- `scraped_leads`

### Schema-Based Multi-Tenancy

**Important Note**: Since this application uses schema-based multi-tenancy (each user has their own schema), RLS is primarily a defense-in-depth measure. The schema isolation already provides strong data separation.

## Enabling RLS on Existing Schemas

If you have existing schemas created before RLS was implemented, run the migration script:

```bash
cd "Email Automation/backend"
python enable_rls_migration.py
```

This script will:
- Find all tenant schemas (`tenant_*`)
- Enable RLS on all tenant tables in each schema
- Skip tables where RLS is already enabled
- Provide a detailed summary

## RLS Policies (Optional)

By default, RLS is enabled but **no policies are created**. This means:

- **With schema-based multi-tenancy**: Your application already handles access control through schema isolation, so RLS policies may not be necessary.
- **If using Supabase Auth**: You may want to create RLS policies that use Supabase's `auth.uid()` function.

### Example RLS Policy (if needed)

If you want to add policies for Supabase Auth integration:

```sql
-- Example: Allow users to access their own emails
CREATE POLICY "Users can access own emails"
ON emails FOR ALL
USING (owner_email = current_setting('app.current_user_email', true));
```

**Note**: This is only needed if you're using Supabase's built-in authentication. With your current backend authentication, schema isolation is sufficient.

## Verification

To verify RLS is enabled on a table:

```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'tenant_your_schema' 
AND tablename = 'emails';
```

If `rowsecurity` is `true`, RLS is enabled.

## Disabling RLS (if needed)

If you need to disable RLS on a table (not recommended):

```sql
ALTER TABLE "schema_name".table_name DISABLE ROW LEVEL SECURITY;
```

## Benefits

1. **Defense in Depth**: Even if application logic has bugs, RLS provides database-level protection
2. **Supabase Compatibility**: Ready for Supabase Auth integration if needed in the future
3. **Security Best Practice**: Follows PostgreSQL security recommendations
4. **Audit Compliance**: Helps meet security audit requirements

## Files Modified

- `app/core/database.py` - Added RLS enablement to `create_tenant_schema()`
- `app/core/tenant_database.py` - Added RLS enablement to `create_tenant_schema()`
- `enable_rls_migration.py` - Migration script for existing schemas

## Troubleshooting

### "permission denied" errors

If you see permission errors after enabling RLS:
- Check that your application uses the correct database user
- Verify schema isolation is working correctly
- Review RLS policies if you've created any

### RLS already enabled warnings

These are safe to ignore - the migration script checks if RLS is already enabled before attempting to enable it.

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)

