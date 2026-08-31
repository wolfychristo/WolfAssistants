-- Migration script to drop duplicate indexes on api_usage table
-- These indexes were created automatically by SQLAlchemy (index=True on columns)
-- but we already have explicit indexes defined in __table_args__

-- Drop duplicate index on created_at (ix_api_usage_created_at)
-- The explicit index idx_usage_created will remain
DROP INDEX IF EXISTS public.ix_api_usage_created_at;

-- Drop duplicate index on endpoint (ix_api_usage_endpoint)
-- The explicit index idx_usage_endpoint will remain
DROP INDEX IF EXISTS public.ix_api_usage_endpoint;

