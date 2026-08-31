# Vercel Deployment Guide for WolfAssistants

Complete step-by-step guide to deploy WolfAssistants on Vercel with custom domain www.wolfassistants.com.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Custom Domain Configuration](#custom-domain-configuration)
7. [Environment Variables Setup](#environment-variables-setup)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:

- [ ] Vercel account (sign up at https://vercel.com)
- [ ] GitHub repository with your code
- [ ] Supabase account and database configured
- [ ] Domain name (www.wolfassistants.com) ready
- [ ] Google Gemini API keys (at least one)
- [ ] SMTP email credentials (for system emails)

## Pre-Deployment Checklist

### 1. Database Migration

Run the database migration to add the `attachments` column:

```bash
cd backend
python run_migration.py
```

Or manually in Supabase SQL Editor:

```sql
ALTER TABLE emails ADD COLUMN IF NOT EXISTS attachments TEXT;
```

### 2. Local Build Test

Test your production build locally:

**Windows:**
```powershell
cd "Email Automation"
.\scripts\test-local-build.ps1
```

**Linux/Mac:**
```bash
cd Email\ Automation
chmod +x scripts/test-local-build.sh
./scripts/test-local-build.sh
```

### 3. Verify Code is Ready

- [ ] All code committed to GitHub
- [ ] No local-only changes
- [ ] Database migration completed
- [ ] Local build test passed

## Database Setup

### Supabase Configuration

1. **Create Supabase Project** (if not already done)
   - Go to https://supabase.com
   - Create new project
   - Note your connection string

2. **Get Connection String**
   - Go to Project Settings → Database
   - Copy the connection string
   - Format: `postgresql+psycopg://postgres.YOUR_REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

3. **Run Migration**
   - Use the migration script or SQL editor
   - Verify `attachments` column exists in `emails` table

## Backend Deployment

### Option A: Separate Backend Project (Recommended)

1. **Create New Vercel Project**
   - Go to Vercel Dashboard
   - Click "Add New Project"
   - Import your GitHub repository

2. **Configure Project Settings**
   - **Root Directory**: `Email Automation/backend`
   - **Framework Preset**: Other
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)
   - **Install Command**: `pip install -r requirements.txt`

3. **Add Environment Variables**
   - Go to Settings → Environment Variables
   - Add all variables from [VERCEL_ENV_VARIABLES.md](./VERCEL_ENV_VARIABLES.md)
   - Set scope to "Production"

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete
   - Note the deployment URL (e.g., `https://your-backend.vercel.app`)

### Option B: Monorepo Deployment

1. **Create Vercel Project**
   - Import GitHub repository
   - Root directory: `Email Automation`

2. **Configure vercel.json**
   - The root `vercel.json` is already configured
   - Vercel will detect both frontend and backend

3. **Add Environment Variables**
   - Add all backend variables
   - Vercel will apply them to backend routes

4. **Deploy**
   - Click "Deploy"
   - Backend will be available at `/api/*`

## Frontend Deployment

### Option A: Separate Frontend Project (Recommended)

1. **Create New Vercel Project**
   - Go to Vercel Dashboard
   - Click "Add New Project"
   - Import your GitHub repository

2. **Configure Project Settings**
   - **Root Directory**: `Email Automation/frontend`
   - **Framework Preset**: Create React App
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
   - **Install Command**: `npm install`

3. **Add Environment Variables**
   - **`REACT_APP_API_URL`**: Backend API URL
     - If backend on subdomain: `https://api.wolfassistants.com/api/v1`
     - If backend on same domain: `https://www.wolfassistants.com/api/v1`
     - Or use Vercel URL: `https://your-backend.vercel.app/api/v1`

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete

### Option B: Monorepo Deployment

If using monorepo, frontend is automatically deployed with backend.

## Custom Domain Configuration

### 1. Add Domain to Frontend Project

1. Go to your frontend Vercel project
2. Navigate to **Settings** → **Domains**
3. Click **Add Domain**
4. Enter: `www.wolfassistants.com`
5. Click **Add**

### 2. Configure DNS Records

Vercel will provide DNS configuration instructions:

**Option A: Using Vercel Nameservers (Recommended)**
- Update your domain's nameservers to Vercel's nameservers
- Vercel will handle all DNS automatically

**Option B: Using CNAME Record**
- Add CNAME record:
  - **Name**: `www`
  - **Value**: `cname.vercel-dns.com`
- Add A record for root domain (if needed):
  - **Name**: `@`
  - **Value**: `76.76.21.21` (Vercel's IP)

### 3. Add Domain to Backend (if using subdomain)

If deploying backend separately with subdomain:

1. Go to backend Vercel project
2. Navigate to **Settings** → **Domains**
3. Add domain: `api.wolfassistants.com`
4. Configure DNS:
   - **Name**: `api`
   - **Value**: `cname.vercel-dns.com`

### 4. Wait for SSL Certificate

- Vercel automatically provisions SSL certificates
- Wait 1-5 minutes for certificate to be issued
- Domain status will show "Valid" when ready

### 5. Update CORS Configuration

After domain is active, update backend environment variable:

- **`CORS_ORIGINS`**: `https://www.wolfassistants.com,https://wolfassistants.com`
- Redeploy backend after updating

## Environment Variables Setup

### Backend Variables

Set these in your backend Vercel project:

**Required:**
- `DATABASE_URL`: Supabase connection string
- `SECRET_KEY`: Strong random secret (generate with Python)
- `ENVIRONMENT`: `production`
- `CORS_ORIGINS`: `https://www.wolfassistants.com,https://wolfassistants.com`
- `GEMINI_API_KEY_1`: At least one Gemini API key

**Recommended:**
- `SYSTEM_EMAIL_*`: For OTP emails
- `GEMINI_API_KEY_2` through `GEMINI_API_KEY_8`: For load balancing

See [VERCEL_ENV_VARIABLES.md](./VERCEL_ENV_VARIABLES.md) for complete list.

### Frontend Variables

Set in your frontend Vercel project:

- `REACT_APP_API_URL`: Backend API URL
  - Subdomain: `https://api.wolfassistants.com/api/v1`
  - Same domain: `https://www.wolfassistants.com/api/v1`

### Setting Variables

1. Go to project Settings → Environment Variables
2. Click "Add New"
3. Enter Key and Value
4. Select environment (Production, Preview, Development)
5. Click "Save"
6. **Redeploy** for changes to take effect

## Post-Deployment Verification

### 1. Health Checks

**Backend:**
```bash
curl https://your-backend.vercel.app/health
# Should return: {"status":"healthy","message":"Email Automation API is running"}
```

**Frontend:**
- Visit: `https://www.wolfassistants.com`
- Should load without errors

### 2. CORS Testing

Open browser console on `https://www.wolfassistants.com`:

```javascript
fetch('https://your-backend.vercel.app/api/v1/health', {
  method: 'GET',
  credentials: 'include'
})
.then(r => r.json())
.then(data => console.log('✅ CORS working:', data))
.catch(err => console.error('❌ CORS error:', err));
```

### 3. Functional Testing

Test critical features:

- [ ] User registration
- [ ] User login
- [ ] Contact management
- [ ] Email sending (if SMTP configured)
- [ ] AI email generation (if API keys configured)
- [ ] Meeting scheduling
- [ ] Password reset (OTP system)

### 4. Performance Testing

- [ ] Page load times acceptable (< 3 seconds)
- [ ] API response times acceptable (< 1 second)
- [ ] No console errors
- [ ] Database queries perform well

## Troubleshooting

### Common Issues

#### 1. Build Failures

**Backend:**
- Check Python version (should be 3.9+)
- Verify `requirements.txt` is correct
- Check build logs for specific errors

**Frontend:**
- Check Node.js version (should be 18+)
- Verify `package.json` dependencies
- Check for TypeScript errors

#### 2. Database Connection Errors

- Verify `DATABASE_URL` is correct
- Check Supabase project is not paused
- Verify password is URL-encoded if it contains special characters
- Check firewall rules allow Vercel IPs

#### 3. CORS Errors

- Verify `CORS_ORIGINS` includes exact domain with `https://`
- Check frontend `REACT_APP_API_URL` matches backend URL
- Ensure both www and non-www versions are in CORS_ORIGINS
- Redeploy backend after updating CORS_ORIGINS

#### 4. Environment Variables Not Working

- Verify variable names are exact (case-sensitive)
- Check environment scope (Production/Preview/Development)
- Redeploy after adding/updating variables
- Check variable values don't have trailing spaces

#### 5. Domain Not Resolving

- Wait 24-48 hours for DNS propagation
- Check DNS records are correct
- Verify domain is added in Vercel dashboard
- Check SSL certificate status

#### 6. API Key Errors

- Verify at least one `GEMINI_API_KEY_*` is set
- Check API key is valid and not expired
- Verify API key has proper permissions
- Check rate limits haven't been exceeded

### Getting Help

1. **Check Vercel Logs**
   - Go to project → Deployments → Click deployment → View logs

2. **Check Supabase Logs**
   - Go to Supabase dashboard → Logs

3. **Check Browser Console**
   - Open DevTools → Console tab
   - Look for errors

4. **Check Network Tab**
   - Open DevTools → Network tab
   - Check API request/response details

## Maintenance

### Regular Tasks

- Monitor Vercel analytics
- Check Supabase database usage
- Review error logs weekly
- Update dependencies monthly
- Rotate API keys quarterly
- Backup database regularly

See [MAINTENANCE_CHECKLIST.md](./MAINTENANCE_CHECKLIST.md) for detailed maintenance procedures.

## Quick Reference

### Deployment URLs

- **Frontend**: `https://www.wolfassistants.com`
- **Backend**: `https://api.wolfassistants.com` or `https://www.wolfassistants.com/api`
- **Health Check**: `https://your-backend.vercel.app/health`

### Important Files

- `backend/vercel.json`: Backend Vercel configuration
- `frontend/vercel.json`: Frontend Vercel configuration
- `vercel.json`: Root monorepo configuration
- `VERCEL_ENV_VARIABLES.md`: Environment variables reference
- `scripts/test-local-build.sh`: Local build test script

### Support Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [React Documentation](https://react.dev)

