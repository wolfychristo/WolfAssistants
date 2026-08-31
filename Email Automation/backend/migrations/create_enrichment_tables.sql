-- Create enrichment schema (shared across all tenants)
CREATE SCHEMA IF NOT EXISTS enrichment;

-- Companies table
CREATE TABLE IF NOT EXISTS enrichment.companies (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    industry VARCHAR(100),
    company_size VARCHAR(50),
    location VARCHAR(255),
    website VARCHAR(500),
    founded_year INTEGER,
    revenue_range VARCHAR(100),
    employee_count INTEGER,
    tech_stack JSONB,
    social_links JSONB,
    description TEXT,
    logo_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for companies
CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_domain ON enrichment.companies(domain);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON enrichment.companies(industry);
CREATE INDEX IF NOT EXISTS idx_companies_name ON enrichment.companies(name);

-- Company enrichments table
CREATE TABLE IF NOT EXISTS enrichment.company_enrichments (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES enrichment.companies(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    confidence_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    last_verified TIMESTAMP WITH TIME ZONE,
    data_freshness_days INTEGER,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Contacts table (enrichment contacts)
CREATE TABLE IF NOT EXISTS enrichment.contacts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    job_title VARCHAR(200),
    company_domain VARCHAR(255),
    company_id INTEGER REFERENCES enrichment.companies(id) ON DELETE SET NULL,
    linkedin_url VARCHAR(500),
    phone VARCHAR(50),
    location VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for contacts
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_email ON enrichment.contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON enrichment.contacts(company_domain);

-- Contact enrichments table
CREATE TABLE IF NOT EXISTS enrichment.contact_enrichments (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES enrichment.contacts(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    quality_score FLOAT NOT NULL DEFAULT 0.0,
    confidence_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    last_verified TIMESTAMP WITH TIME ZONE,
    data_freshness_days INTEGER,
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Data sources table
CREATE TABLE IF NOT EXISTS enrichment.data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    reliability_score FLOAT NOT NULL DEFAULT 50.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    rate_limit_per_minute INTEGER,
    last_used_at TIMESTAMP WITH TIME ZONE,
    source_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Enrichment jobs table
CREATE TABLE IF NOT EXISTS enrichment.enrichment_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    target_identifier VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 5,
    error_message TEXT,
    result_data JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for enrichment jobs
CREATE INDEX IF NOT EXISTS idx_jobs_status ON enrichment.enrichment_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON enrichment.enrichment_jobs(created_at);

-- API Keys table (in accounts database, not enrichment schema)
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]',
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    rate_limit_per_day INTEGER NOT NULL DEFAULT 10000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    ip_whitelist JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for API keys
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- API Usage table (in accounts database)
CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    request_size INTEGER,
    response_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for API usage
CREATE INDEX IF NOT EXISTS idx_usage_api_key ON api_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_created ON api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_endpoint ON api_usage(endpoint);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON enrichment.companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_company_enrichments_updated_at BEFORE UPDATE ON enrichment.company_enrichments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON enrichment.contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contact_enrichments_updated_at BEFORE UPDATE ON enrichment.contact_enrichments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON enrichment.data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_enrichment_jobs_updated_at BEFORE UPDATE ON enrichment.enrichment_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

