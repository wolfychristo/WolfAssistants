-- =====================================================
-- Simple Version: Add Missing Columns (without checks)
-- Run this if the DO blocks cause issues
-- =====================================================

-- Add subscription_id column
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS subscription_id VARCHAR;

-- Add is_freelancer column
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS is_freelancer BOOLEAN DEFAULT FALSE;

-- Add freelancer_profile_id column
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS freelancer_profile_id INTEGER;

-- Add stripe_connect_account_id column
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS stripe_connect_account_id VARCHAR;

-- Add marketplace_commission_rate column
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS marketplace_commission_rate FLOAT;

-- Verify columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'app_users' 
AND column_name IN ('subscription_id', 'is_freelancer', 'freelancer_profile_id', 'stripe_connect_account_id', 'marketplace_commission_rate')
ORDER BY column_name;
