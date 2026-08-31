-- =====================================================
-- Add Missing Columns to app_users Table
-- Run this in Supabase SQL Editor
-- =====================================================

-- First, check if columns exist (optional - for reference)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_schema = 'public' 
-- AND table_name = 'app_users' 
-- AND column_name IN ('subscription_id', 'is_freelancer', 'freelancer_profile_id', 'stripe_connect_account_id', 'marketplace_commission_rate')
-- ORDER BY column_name;

-- Add subscription_id column (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'app_users' 
        AND column_name = 'subscription_id'
    ) THEN
        ALTER TABLE app_users ADD COLUMN subscription_id VARCHAR;
        RAISE NOTICE 'Column subscription_id added successfully';
    ELSE
        RAISE NOTICE 'Column subscription_id already exists';
    END IF;
END $$;

-- Add is_freelancer column (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'app_users' 
        AND column_name = 'is_freelancer'
    ) THEN
        ALTER TABLE app_users ADD COLUMN is_freelancer BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Column is_freelancer added successfully';
    ELSE
        RAISE NOTICE 'Column is_freelancer already exists';
    END IF;
END $$;

-- Add freelancer_profile_id column (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'app_users' 
        AND column_name = 'freelancer_profile_id'
    ) THEN
        ALTER TABLE app_users ADD COLUMN freelancer_profile_id INTEGER;
        RAISE NOTICE 'Column freelancer_profile_id added successfully';
    ELSE
        RAISE NOTICE 'Column freelancer_profile_id already exists';
    END IF;
END $$;

-- Add stripe_connect_account_id column (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'app_users' 
        AND column_name = 'stripe_connect_account_id'
    ) THEN
        ALTER TABLE app_users ADD COLUMN stripe_connect_account_id VARCHAR;
        RAISE NOTICE 'Column stripe_connect_account_id added successfully';
    ELSE
        RAISE NOTICE 'Column stripe_connect_account_id already exists';
    END IF;
END $$;

-- Add marketplace_commission_rate column (if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'app_users' 
        AND column_name = 'marketplace_commission_rate'
    ) THEN
        ALTER TABLE app_users ADD COLUMN marketplace_commission_rate FLOAT;
        RAISE NOTICE 'Column marketplace_commission_rate added successfully';
    ELSE
        RAISE NOTICE 'Column marketplace_commission_rate already exists';
    END IF;
END $$;

-- Verify all columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'app_users' 
AND column_name IN ('subscription_id', 'is_freelancer', 'freelancer_profile_id', 'stripe_connect_account_id', 'marketplace_commission_rate')
ORDER BY column_name;
