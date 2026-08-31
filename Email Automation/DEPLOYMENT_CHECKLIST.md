# Deployment Checklist

## Pre-Deployment Verification

### 1. CORS Configuration
- [ ] Set `CORS_ORIGINS` environment variable with production frontend URLs
  - Format: `CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com`
  - Include all production domains (with and without www)
  - Development URLs are automatically included

### 2. Environment Variables
Required environment variables for production:
- [ ] `DATABASE_URL` - Production database connection string
- [ ] `ACCOUNTS_DATABASE_URL` - (Optional) Separate accounts database
- [ ] `TENANT_DATABASE_URL` - (Optional) Separate tenant database
- [ ] `SECRET_KEY` - Strong secret key for JWT tokens
- [ ] `CORS_ORIGINS` - Comma-separated list of allowed origins
- [ ] `ENVIRONMENT=production` - Set to production mode
- [ ] `GEMINI_API_KEY_1` through `GEMINI_API_KEY_8` - API keys for AI features

### 3. Endpoint Verification
Run the verification script before deployment:
```bash
cd backend
python verify_endpoints.py
```

This will test:
- Health check endpoints
- Authentication endpoints
- CORS configuration
- All router registrations

### 4. Frontend Configuration
- [ ] Set `REACT_APP_API_URL` environment variable to production backend URL
  - Example: `REACT_APP_API_URL=https://api.yourdomain.com/api/v1`
- [ ] Build frontend: `npm run build`
- [ ] Verify build output in `build/` directory

### 5. Database Setup
- [ ] Ensure all database migrations are applied
- [ ] Verify database schema is up to date
- [ ] Test database connectivity from production server

### 6. Security Checklist
- [ ] Change default `SECRET_KEY` (never use default in production)
- [ ] Verify HTTPS is enabled (required for production)
- [ ] Check that sensitive endpoints require authentication
- [ ] Review CORS origins list (no wildcards in production)
- [ ] Ensure API keys are stored securely (environment variables, not in code)

### 7. Testing
- [ ] Test user registration
- [ ] Test user login
- [ ] Test protected endpoints with authentication
- [ ] Test CORS from production frontend domain
- [ ] Test all major features (contacts, emails, meetings, etc.)

## Post-Deployment Verification

### 1. Health Checks
- [ ] Verify `/health` endpoint returns 200
- [ ] Verify `/api/v1/emails/health` endpoint returns 200

### 2. CORS Testing
Test from browser console on production frontend:
```javascript
fetch('https://api.yourdomain.com/api/v1/health', {
  method: 'GET',
  credentials: 'include'
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

### 3. Monitoring
- [ ] Set up error logging/monitoring
- [ ] Monitor API response times
- [ ] Check database connection pool usage
- [ ] Monitor API key usage/quotas

## Common Issues

### CORS Errors
- Verify `CORS_ORIGINS` includes exact production domain (with protocol)
- Check that frontend is making requests to correct backend URL
- Ensure `allow_credentials=True` matches frontend `credentials: 'include'`

### Database Connection Issues
- Verify database URL is correct
- Check firewall rules allow connections
- Verify database credentials are correct
- Test connection from production server

### Authentication Issues
- Verify `SECRET_KEY` is set and matches across all instances
- Check token expiration settings
- Verify JWT algorithm matches (`HS256`)

## Quick Reference

### Setting CORS for Production
```bash
export CORS_ORIGINS="https://wolfassistants.com,https://www.wolfassistants.com"
```

### Testing Endpoints Locally
```bash
# Start backend server
cd backend
python main.py

# In another terminal, run verification
python verify_endpoints.py
```

### Frontend Build
```bash
cd frontend
export REACT_APP_API_URL=https://api.yourdomain.com/api/v1
npm run build
```

