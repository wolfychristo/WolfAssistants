# Supabase Setup Guide for WolfAssistants

This guide will help you migrate from SQLite to Supabase PostgreSQL.

## 🎯 Benefits of Supabase

- **Managed PostgreSQL**: No server management required
- **Free Tier**: 500MB database, 2GB bandwidth/month
- **Automatic Backups**: Built-in backup and point-in-time recovery
- **Real-time**: Optional real-time subscriptions (for future features)
- **Row-Level Security**: Built-in data protection
- **Easy Scaling**: Upgrade as you grow

## 📋 Step-by-Step Setup

### 1. Install PostgreSQL Driver

```powershell
cd "Email Automation\backend"
.\venv\Scripts\Activate.ps1
pip install psycopg2-binary
```

### 2. Create Supabase Project

1. Go to https://app.supabase.com/
2. Click "New Project"
3. Choose organization
4. Set project details:
   - **Name**: `wolfassistants` (or your choice)
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to your users
5. Click "Create new project"

Wait 2-3 minutes for project to initialize.

### 3. Get Connection String

1. Go to **Settings** → **Database**
2. Find **Connection string** section
3. Copy the **URI** format (not transaction mode)
4. It looks like:
   ```
   postgresql://postgres.[YOUR_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

### 4. Configure Backend

Create `backend/.env` file:

```env
# Supabase PostgreSQL
DATABASE_URL=postgresql+psycopg2://postgres.[YOUR_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Security
SECRET_KEY=your-super-secret-key-change-this

# System Email (for OTPs)
SYSTEM_EMAIL_HOST=smtp.sendgrid.net
SYSTEM_EMAIL_PORT=587
SYSTEM_EMAIL_USER=apikey
SYSTEM_EMAIL_PASSWORD=SG.xxxxxxxxxx
SYSTEM_EMAIL_FROM=WolfAssistants <info@wolfassistants.com>
SYSTEM_EMAIL_USE_TLS=true

# Gemini AI (optional)
GEMINI_API_KEY=your-gemini-key
```

**Replace:**
- `[YOUR_REF]` with your Supabase project reference
- `[PASSWORD]` with your Supabase password
- `your-super-secret-key-change-this` with a strong random key

Generate SECRET_KEY:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 5. Export Existing SQLite Data

```powershell
python migrate_to_supabase.py
```

This creates SQL files with all your data.

### 6. Start API (Creates Tables)

```powershell
python main.py
```

Visit: http://localhost:8000/health (should return `{"status": "healthy"}`)

### 7. Import Data to Supabase

1. Go to Supabase project → **SQL Editor**
2. Open the exported SQL files (from step 5)
3. Copy-paste and run each file

Or use command line:
```bash
psql "postgresql://postgres.[REF]:[PASS]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" < migration_primary_YYYYMMDD_HHMMSS.sql
```

### 8. Verify Connection

Visit: http://localhost:8000/api/v1/auth/me (login first)

## 🔧 Troubleshooting

### "No module named 'psycopg2'"
```powershell
pip install psycopg2-binary
```

### "connection refused"
- Check Supabase project is active (not paused)
- Verify connection string format
- Ensure password has no special characters (URL encode if needed)

### "permission denied"
- Check you're using the correct database password
- Verify project hasn't been paused

### "SSL required"
Add `?sslmode=require` to connection string:
```
postgresql+psycopg2://user:pass@host:port/db?sslmode=require
```

## 🗄️ Database Schema

The following tables will auto-create on first start:

**Primary Database:**
- `users`
- `referral_invitations`
- `referral_rewards`
- `user_credits`
- `referral_codes`
- `user_activities`
- `user_bans`
- `abuse_patterns`
- `admin_notifications`
- `todos`

**Tenant Data (per-user):**
- `contacts`
- `emails`
- `meetings`
- `chat_sessions`
- `chat_messages`

All tenant data uses `owner_email` as the partitioning key.

## 🔐 Security Notes

- Never commit `.env` to git
- Use strong, unique passwords
- Rotate `SECRET_KEY` periodically
- Enable Supabase Row Level Security (optional)

## 📊 Monitoring

Supabase Dashboard provides:
- Query performance metrics
- Database size
- Connection pool usage
- Slow query logs

## 💰 Cost Management

Supabase Free Tier includes:
- 500MB database
- 2GB bandwidth/month
- 500MB file storage
- 50,000 monthly active users

Upgrade pricing: https://supabase.com/pricing

## 🚀 Next Steps

1. ✅ Connect to Supabase
2. ✅ Migrate existing data
3. ✅ Test all features
4. ✅ Set up automated backups
5. ⏭️ Plan data migration script (if needed)

## 📚 Resources

- Supabase Docs: https://supabase.com/docs
- PostgreSQL Docs: https://www.postgresql.org/docs/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/

