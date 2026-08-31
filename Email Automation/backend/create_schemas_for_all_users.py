#!/usr/bin/env python3
"""
Script to check and create tenant schemas for all existing users.
This ensures data isolation by creating a schema for each user.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AccountsSessionLocal
from app.core.tenant_database import (
    create_tenant_schema, 
    schema_exists, 
    get_tenant_schema_name,
    _get_tenant_engine
)
# Import all models to ensure relationships are properly initialized
from app.models.user import User
from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
from sqlalchemy import text
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_users():
    """Get all active users from accounts database."""
    from sqlalchemy import text
    
    # Retry logic for connection
    max_retries = 5
    for attempt in range(max_retries):
        try:
            db = AccountsSessionLocal()
            try:
                result = db.execute(text("SELECT email FROM app_users WHERE deleted_at IS NULL"))
                emails = [row[0] for row in result.fetchall()]
                return emails
            finally:
                db.close()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s, 8s
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to connect after {max_retries} attempts: {e}")

def check_existing_schemas():
    """Check which tenant schemas already exist."""
    engine = _get_tenant_engine()
    existing_schemas = set()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%'
                ORDER BY schema_name
            """))
            existing_schemas = {row[0] for row in result.fetchall()}
    except Exception as e:
        logger.error(f"Error checking existing schemas: {e}")
    
    return existing_schemas

def create_schemas_for_all_users():
    """Create tenant schemas for all users who don't have one."""
    print("=" * 80)
    print("TENANT SCHEMA CREATION SCRIPT")
    print("=" * 80)
    
    # Get all users
    print("\n[1] Fetching all users from accounts database...")
    user_emails = get_all_users()
    print(f"    Found {len(user_emails)} active users")
    
    if not user_emails:
        print("    No users found. Nothing to do.")
        return
    
    # Check existing schemas
    print("\n[2] Checking existing tenant schemas...")
    existing_schemas = check_existing_schemas()
    print(f"    Found {len(existing_schemas)} existing schemas")
    
    # Find users without schemas
    print("\n[3] Identifying users without schemas...")
    users_without_schemas = []
    for email in user_emails:
        schema_name = get_tenant_schema_name(email)
        if schema_name not in existing_schemas:
            users_without_schemas.append(email)
    
    print(f"    Found {len(users_without_schemas)} users without schemas")
    
    if not users_without_schemas:
        print("\n✅ All users already have tenant schemas!")
        return
    
    # Create schemas
    print(f"\n[4] Creating schemas for {len(users_without_schemas)} users...")
    print("    This may take a few minutes...\n")
    
    created_count = 0
    failed_count = 0
    failed_users = []
    
    for i, email in enumerate(users_without_schemas, 1):
        schema_name = get_tenant_schema_name(email)
        print(f"    [{i}/{len(users_without_schemas)}] Creating schema for {email}...", end=" ")
        
        try:
            success = create_tenant_schema(email)
            if success:
                print("✅ Created")
                created_count += 1
            else:
                # Check if it was created (might already exist)
                if schema_exists(email):
                    print("✅ Already exists")
                    created_count += 1
                else:
                    print("❌ Failed")
                    failed_count += 1
                    failed_users.append(email)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            failed_count += 1
            failed_users.append(email)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total users: {len(user_emails)}")
    print(f"Users with schemas: {len(user_emails) - len(users_without_schemas)}")
    print(f"Schemas created: {created_count}")
    print(f"Schemas failed: {failed_count}")
    
    if failed_users:
        print(f"\n⚠️  Failed to create schemas for:")
        for email in failed_users:
            print(f"   - {email}")
    
    if created_count > 0:
        print(f"\n✅ Successfully created {created_count} tenant schemas!")
        print("   Users can now access their isolated data.")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        create_schemas_for_all_users()
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        sys.exit(1)

