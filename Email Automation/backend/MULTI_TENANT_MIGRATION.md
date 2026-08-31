# Multi-Tenant Schema Migration Guide

## Overview

This document describes the migration from a shared database with `owner_email` filtering to a schema-based multi-tenant architecture.

## Architecture

### Accounts Database
- **Purpose**: Authentication and account management
- **Tables**: `app_users`, `referral_codes`, `user_credits`, `user_activities`, etc.
- **Connection**: `get_accounts_db()` dependency

### Tenant Database (Schema-based)
- **Purpose**: User business data (isolated per user)
- **Schemas**: One schema per user (e.g., `tenant_user_example_com`)
- **Tables per schema**: `contacts`, `emails`, `meetings`, `todos`, `chat_sessions`, etc.
- **Connection**: `get_tenant_db_dependency()` dependency

## Implementation Status

### ✅ Completed
1. Database connection manager with schema support (`app/core/database.py`)
2. Registration flow creates tenant schemas
3. Login uses accounts database
4. Schema creation and management functions

### 🔄 In Progress
1. Updating API endpoints to use tenant databases
2. Removing `owner_email` filtering (no longer needed)

### ⏳ Pending
1. Update scheduler to use tenant databases
2. Create migration script for existing data
3. Update all remaining endpoints

## Migration Steps

### For New Users
- Registration automatically creates tenant schema
- All data goes to their schema automatically

### For Existing Users
1. Run migration script to:
   - Create schemas for all existing users
   - Move data from shared tables to tenant schemas
   - Remove `owner_email` columns (optional)

## API Endpoint Updates

### Pattern to Follow

**Before:**
```python
@router.get("/contacts")
def list_contacts(request: Request, db: Session = Depends(get_db)):
    owner = _get_owner_from_request(request)
    contacts = db.query(Contact).filter(Contact.owner_email == owner).all()
    return contacts
```

**After:**
```python
@router.get("/contacts")
def list_contacts(request: Request, db: Session = Depends(get_tenant_db_dependency)):
    # No owner_email filtering needed - schema isolation handles it
    contacts = db.query(Contact).all()
    return contacts
```

## Configuration

### Environment Variables

```env
# Accounts database (authentication)
ACCOUNTS_DATABASE_URL=postgresql://user:pass@host:port/accounts_db

# Tenant database (user data in schemas)
TENANT_DATABASE_URL=postgresql://user:pass@host:port/tenant_db

# Or use same database for both (they can share)
DATABASE_URL=postgresql://user:pass@host:port/shared_db
```

## Benefits

1. **Complete Data Isolation**: Each user's data is in a separate schema
2. **Simpler Queries**: No need to filter by `owner_email`
3. **Better Security**: Schema-level isolation
4. **Easier Backups**: Can backup individual tenant schemas
5. **Scalability**: Can move schemas to different databases if needed

## Notes

- Schema names are sanitized from email addresses
- Example: `user@example.com` → `tenant_user_example_com`
- All tables are created in each tenant's schema automatically
- Existing `owner_email` columns can be removed after migration (optional)

