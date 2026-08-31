# Vercel Environment Variables Reference

This document lists all environment variables required for deploying WolfAssistants on Vercel.

## Backend Environment Variables

### Required Variables

#### Core Configuration
- **`DATABASE_URL`** (Required)
  - Supabase PostgreSQL connection string
  - Format: `postgresql+psycopg://postgres.YOUR_REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
  - Example: `postgresql+psycopg://postgres.abc123:SecurePass123@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

- **`SECRET_KEY`** (Required)
  - Strong random secret for JWT tokens and encryption
  - Minimum 32 characters recommended
  - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
  - Example: `your-super-secure-secret-key-here-minimum-32-characters`

- **`ENVIRONMENT`** (Required)
  - Set to `production` for production deployment
  - Values: `development`, `staging`, `production`

- **`CORS_ORIGINS`** (Required)
  - Comma-separated list of allowed frontend origins
  - Format: `https://www.wolfassistants.com,https://wolfassistants.com`
  - Include both www and non-www versions
  - Example: `https://www.wolfassistants.com,https://wolfassistants.com`

#### AI Configuration
- **`GEMINI_API_KEY_1`** through **`GEMINI_API_KEY_8`** (At least one required)
  - Google Gemini API keys for AI features
  - Add multiple keys for load balancing and rate limit distribution
  - Format: Alphanumeric API key from Google AI Studio
  - Example: `AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567`

### Optional Variables

#### Database Configuration
- **`ACCOUNTS_DATABASE_URL`** (Optional)
  - Separate database for authentication and account data
  - If not set, uses `DATABASE_URL`
  - Format: Same as `DATABASE_URL`

- **`TENANT_DATABASE_URL`** (Optional)
  - Separate database for tenant business data
  - If not set, uses `DATABASE_URL`
  - Format: Same as `DATABASE_URL`

#### System Email Configuration (for OTPs and notifications)
- **`SYSTEM_EMAIL_HOST`** (Optional but recommended)
  - SMTP server hostname
  - Example: `smtp.gmail.com`

- **`SYSTEM_EMAIL_PORT`** (Optional)
  - SMTP server port
  - Default: `587` (TLS) or `465` (SSL)

- **`SYSTEM_EMAIL_USER`** (Optional but recommended)
  - SMTP username/email address
  - Example: `info@wolfassistants.com`

- **`SYSTEM_EMAIL_PASSWORD`** (Optional but recommended)
  - SMTP password or app password
  - For Gmail, use App Password

- **`SYSTEM_EMAIL_FROM`** (Optional)
  - From address for system emails
  - Default: `WolfAssistants <info@wolfassistants.com>`

- **`SYSTEM_EMAIL_USE_TLS`** (Optional)
  - Enable TLS for SMTP
  - Default: `true`

#### Security Configuration
- **`JWT_SECRET_KEY`** (Optional)
  - Separate secret for JWT tokens
  - If not set, uses `SECRET_KEY`
  - Generate same way as `SECRET_KEY`

- **`JWT_ALGORITHM`** (Optional)
  - JWT signing algorithm
  - Default: `HS256`

- **`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`** (Optional)
  - JWT token expiration time in minutes
  - Default: `480` (8 hours)

#### Rate Limiting
- **`RATE_LIMIT_REQUESTS_PER_MINUTE`** (Optional)
  - Maximum requests per minute per IP
  - Default: `60`

- **`RATE_LIMIT_BURST`** (Optional)
  - Burst limit for rate limiting
  - Default: `10`

#### Monitoring
- **`ENABLE_MONITORING`** (Optional)
  - Enable system monitoring
  - Default: `true`

- **`LOG_LEVEL`** (Optional)
  - Logging level
  - Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`
  - Default: `INFO`

#### API Key Categorization (Optional)
- **`API_KEY_CATEGORIZATION_ENABLED`** (Optional)
  - Enable API key categorization by tier
  - Default: `true`

- **`API_KEY_ENTERPRISE_KEYS`** (Optional)
  - Comma-separated key numbers for Enterprise tier
  - Default: `1,2`

- **`API_KEY_PROFESSIONAL_KEYS`** (Optional)
  - Comma-separated key numbers for Professional tier
  - Default: `3,4`

- **`API_KEY_STARTER_KEYS`** (Optional)
  - Comma-separated key numbers for Starter tier
  - Default: `5,6`

- **`API_KEY_FREE_KEYS`** (Optional)
  - Comma-separated key numbers for Free tier
  - Default: `7,8`

#### Engagement Thresholds (Optional)
- **`ENGAGEMENT_ENTERPRISE_EMAILS`** (Optional)
  - Email threshold for Enterprise tier
  - Default: `1000`

- **`ENGAGEMENT_PROFESSIONAL_EMAILS`** (Optional)
  - Email threshold for Professional tier
  - Default: `100`

- **`ENGAGEMENT_STARTER_EMAILS`** (Optional)
  - Email threshold for Starter tier
  - Default: `10`

#### Request Queue (Optional)
- **`REQUEST_QUEUE_ENABLED`** (Optional)
  - Enable request queue for AI operations
  - Default: `false`

- **`REQUEST_QUEUE_MAX_CONCURRENT`** (Optional)
  - Maximum concurrent requests in queue
  - Default: `20`

#### Circuit Breaker (Optional)
- **`CIRCUIT_BREAKER_ENABLED`** (Optional)
  - Enable circuit breaker for API calls
  - Default: `true`

- **`CIRCUIT_BREAKER_FAILURE_THRESHOLD`** (Optional)
  - Number of failures before opening circuit
  - Default: `5`

- **`CIRCUIT_BREAKER_TIMEOUT`** (Optional)
  - Timeout in seconds before retry
  - Default: `60`

- **`CIRCUIT_BREAKER_SUCCESS_THRESHOLD`** (Optional)
  - Number of successes to close circuit
  - Default: `2`

## Frontend Environment Variables

### Required Variables

- **`REACT_APP_API_URL`** (Required)
  - Backend API URL
  - Options:
    - **Option A (Subdomain)**: `https://api.wolfassistants.com/api/v1`
    - **Option B (Same Domain)**: `https://www.wolfassistants.com/api/v1`
  - For Vercel preview deployments: `https://your-backend-project.vercel.app/api/v1`

## Setting Environment Variables in Vercel

### Via Vercel Dashboard

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add each variable:
   - **Key**: Variable name (e.g., `DATABASE_URL`)
   - **Value**: Variable value
   - **Environment**: Select `Production`, `Preview`, and/or `Development`
4. Click **Save**

### Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Link project
vercel link

# Add environment variable
vercel env add DATABASE_URL production
# Enter value when prompted

# Pull environment variables (for local development)
vercel env pull .env.local
```

### Via Vercel API

```bash
# Add environment variable via API
curl -X POST "https://api.vercel.com/v10/projects/{project_id}/env" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "DATABASE_URL",
    "value": "your-value",
    "type": "encrypted",
    "target": ["production"]
  }'
```

## Environment-Specific Configuration

### Production
- Set `ENVIRONMENT=production`
- Use production Supabase database
- Use production domain in `CORS_ORIGINS`
- Use production API URL in `REACT_APP_API_URL`

### Preview/Staging
- Set `ENVIRONMENT=staging` or `development`
- Can use staging database or production database
- Use preview domain in `CORS_ORIGINS` if needed
- Use preview API URL in `REACT_APP_API_URL`

### Development
- Set `ENVIRONMENT=development`
- Use development database or local Supabase
- Use `http://localhost:3000` in `CORS_ORIGINS`
- Use `http://localhost:8000/api/v1` in `REACT_APP_API_URL`

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use Vercel's encrypted environment variables** for sensitive data
3. **Rotate secrets regularly**, especially `SECRET_KEY` and API keys
4. **Use different keys for different environments** (production, staging, development)
5. **Limit access** to environment variables in Vercel dashboard
6. **Use strong, random secrets** - generate with secure random generators
7. **Monitor API key usage** to detect unauthorized access

## Verification

After setting environment variables:

1. **Backend**: Check `/health` endpoint returns 200
2. **Frontend**: Check browser console for API connection errors
3. **Database**: Verify connection in backend logs
4. **CORS**: Test from browser console on production domain
5. **AI Features**: Test email generation to verify API keys

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify `DATABASE_URL` is correct
   - Check Supabase project is not paused
   - Verify password has no special characters (URL encode if needed)

2. **CORS Errors**
   - Verify `CORS_ORIGINS` includes exact production domain with `https://`
   - Check frontend `REACT_APP_API_URL` matches backend URL
   - Ensure `allow_credentials=True` in CORS config

3. **API Key Errors**
   - Verify at least one `GEMINI_API_KEY_*` is set
   - Check API key is valid and not expired
   - Verify API key has proper permissions

4. **Environment Variable Not Found**
   - Verify variable name is exact (case-sensitive)
   - Check environment scope (production/preview/development)
   - Redeploy after adding new variables

## Quick Reference

### Minimum Required for Production

**Backend:**
```
DATABASE_URL=postgresql+psycopg://...
SECRET_KEY=your-secret-key
ENVIRONMENT=production
CORS_ORIGINS=https://www.wolfassistants.com,https://wolfassistants.com
GEMINI_API_KEY_1=your-api-key
```

**Frontend:**
```
REACT_APP_API_URL=https://api.wolfassistants.com/api/v1
```

### Recommended for Production

Add all optional variables for full functionality:
- System email configuration (for OTPs)
- Multiple Gemini API keys (for load balancing)
- Monitoring and logging configuration
- Rate limiting configuration

