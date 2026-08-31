# Database URL Setup Guide for IMAP Testing

## Current Status
✅ Database connections are working
⚠️ `TENANT_DATABASE_URL` is not set (using `DATABASE_URL` for both accounts and tenant data)

## How to Add Test Database URL

### Step 1: Add to .env File

Create or edit `.env` file in the `backend` directory:

```env
# Production/Development Database (for accounts and fallback)
DATABASE_URL=postgresql+psycopg://postgres:password@host:5432/production_db

# Test Database for IMAP Testing (for emails/contacts/meetings)
TENANT_DATABASE_URL=postgresql+psycopg://postgres:password@test-host:5432/test_db
```

### Step 2: Verify Configuration

Run the verification script:
```bash
python verify_env_setup.py
```

Or test database connection:
```bash
python test_database_connection.py
```

### Step 3: Restart Backend Server

**Important**: After adding the database URL to `.env`, you must restart the backend server for changes to take effect.

```bash
# Stop the current server (Ctrl+C)
# Then restart:
python -m uvicorn app.main:app --reload
```

## Database URL Format

### PostgreSQL (Supabase/Standard)
```
postgresql+psycopg://username:password@host:port/database_name
```

### Example Formats:
```env
# Supabase
TENANT_DATABASE_URL=postgresql+psycopg://postgres.REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Standard PostgreSQL
TENANT_DATABASE_URL=postgresql+psycopg://postgres:mypassword@localhost:5432/test_db

# With SSL
TENANT_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db?sslmode=require
```

## What Each Database URL Does

### `DATABASE_URL`
- **Purpose**: Main database URL (fallback)
- **Used for**: Accounts database if `ACCOUNTS_DATABASE_URL` not set
- **Used for**: Tenant database if `TENANT_DATABASE_URL` not set

### `ACCOUNTS_DATABASE_URL` (Optional)
- **Purpose**: Separate database for authentication/account data
- **Stores**: User accounts, authentication tokens, referrals, bans
- **Falls back to**: `DATABASE_URL` if not set

### `TENANT_DATABASE_URL` (Optional) ⭐ **For IMAP Testing**
- **Purpose**: Separate database for user business data
- **Stores**: Emails, contacts, meetings, todos (in tenant schemas)
- **Falls back to**: `DATABASE_URL` if not set
- **Recommended**: Set this for IMAP testing to isolate test data

## Testing IMAP with Separate Database

### Recommended Setup:
```env
# Keep production accounts database
DATABASE_URL=postgresql+psycopg://...production_db

# Use test database for emails/IMAP data
TENANT_DATABASE_URL=postgresql+psycopg://...test_db
```

This way:
- ✅ User accounts stay in production database
- ✅ IMAP emails go to test database
- ✅ Easy to clean test data without affecting accounts
- ✅ Can test IMAP without affecting production emails

## Verification Checklist

After setting up:

- [ ] `.env` file has `TENANT_DATABASE_URL` set
- [ ] Backend server restarted
- [ ] `python verify_env_setup.py` shows `TENANT_DATABASE_URL` is set
- [ ] `python test_database_connection.py` shows successful connection
- [ ] Test IMAP import stores emails in test database
- [ ] Check tenant schemas are created in test database

## Troubleshooting

### Issue: Environment variable not loading
**Solution**: 
1. Check `.env` file is in `backend` directory
2. Check variable name is exactly `TENANT_DATABASE_URL` (case-sensitive)
3. Restart backend server
4. Check `.env` file has no syntax errors

### Issue: Connection failed
**Solution**:
1. Verify database URL format is correct
2. Check database credentials are correct
3. Verify database server is accessible
4. Check firewall/network settings

### Issue: Tenant schema not created
**Solution**:
1. Verify database connection works
2. Check user has CREATE SCHEMA permission
3. Check backend logs for errors
4. Run `python test_database_connection.py` to see detailed errors

## Next Steps After Setup

1. **Test IMAP Import**:
   ```bash
   python test_send_and_verify_email.py
   ```

2. **Check Database**:
   ```bash
   python test_check_imap_and_database.py
   ```

3. **Verify Emails in Test DB**:
   - Check tenant schemas in test database
   - Verify emails are stored correctly
   - Confirm no emails in production database

