-- Migration: Create scraped_leads table in tenant schemas
-- This migration creates the scraped_leads table in all existing tenant schemas
-- For PostgreSQL/Supabase multi-tenant setup
-- 
-- Run this SQL in your Supabase SQL editor or database migration tool
-- The table will be created in each tenant schema (tenant_*)

-- Function to create scraped_leads table in a specific schema
CREATE OR REPLACE FUNCTION create_scraped_leads_in_schema(schema_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.scraped_leads (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255),
            name VARCHAR(255),
            position VARCHAR(255),
            company VARCHAR(255),
            phone VARCHAR(255),
            address TEXT,
            source_url VARCHAR(500) NOT NULL,
            source_type VARCHAR(100) NOT NULL,
            platform VARCHAR(100) NOT NULL,
            company_data JSONB,
            validation_data JSONB,
            transferred BOOLEAN NOT NULL DEFAULT FALSE,
            transferred_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            owner_email VARCHAR(255)
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_scraped_leads_owner_email ON %I.scraped_leads(owner_email);
        CREATE INDEX IF NOT EXISTS idx_scraped_leads_email ON %I.scraped_leads(email);
        CREATE INDEX IF NOT EXISTS idx_scraped_leads_transferred ON %I.scraped_leads(transferred);
        CREATE INDEX IF NOT EXISTS idx_scraped_leads_platform ON %I.scraped_leads(platform);
        CREATE INDEX IF NOT EXISTS idx_scraped_leads_created_at ON %I.scraped_leads(created_at DESC);
    ', schema_name, schema_name, schema_name, schema_name, schema_name, schema_name);
END;
$$ LANGUAGE plpgsql;

-- Create table in all existing tenant schemas
DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN 
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name LIKE 'tenant_%'
    LOOP
        PERFORM create_scraped_leads_in_schema(schema_record.schema_name);
        RAISE NOTICE 'Created scraped_leads table in schema: %', schema_record.schema_name;
    END LOOP;
    
    -- Also create in public schema if no tenant schemas exist (for development/testing)
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%') THEN
        PERFORM create_scraped_leads_in_schema('public');
        RAISE NOTICE 'Created scraped_leads table in public schema (no tenant schemas found)';
    END IF;
END $$;

-- Clean up function
DROP FUNCTION IF EXISTS create_scraped_leads_in_schema(TEXT);

