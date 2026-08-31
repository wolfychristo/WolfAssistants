"""
Migration script to update schema_created flags for existing users.

This script:
1. Checks which users have tenant schemas
2. Updates the schema_created flag to True for users with existing schemas
3. Updates the schema_created flag to False for users without schemas
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AccountsSessionLocal
from app.core.tenant_database import get_tenant_schema_name, schema_exists, _get_tenant_engine
from app.models.user import User
# Import all related models to ensure relationships are properly initialized
from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
from app.models.user_activity import UserActivity, UserBan, AbusePattern, AdminNotification
from sqlalchemy import text

def update_schema_created_flags():
    """Update schema_created flags for all users based on actual schema existence."""
    print("=" * 80)
    print("SCHEMA CREATED FLAG MIGRATION")
    print("=" * 80)
    
    # Get all users
    print("\n[1] Fetching all users from accounts database...")
    accounts_db = AccountsSessionLocal()
    try:
        users = accounts_db.query(User).filter(User.deleted_at.is_(None)).all()
        print(f"    Found {len(users)} active users")
    except Exception as e:
        print(f"    ❌ Error fetching users: {str(e)}")
        return
    finally:
        accounts_db.close()
    
    if not users:
        print("    No users found. Nothing to do.")
        return
    
    # Check existing schemas
    print("\n[2] Checking existing tenant schemas...")
    engine = _get_tenant_engine()
    existing_schemas = set()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%'
            """))
            existing_schemas = {row[0] for row in result.fetchall()}
        print(f"    Found {len(existing_schemas)} existing schemas")
    except Exception as e:
        print(f"    ❌ Error checking schemas: {str(e)}")
        return
    
    # Update flags
    print("\n[3] Updating schema_created flags...")
    accounts_db = AccountsSessionLocal()
    try:
        updated_count = 0
        already_correct = 0
        errors = 0
        
        for user in users:
            try:
                schema_name = get_tenant_schema_name(user.email)
                schema_exists_flag = schema_name in existing_schemas
                
                if user.schema_created != schema_exists_flag:
                    user.schema_created = schema_exists_flag
                    updated_count += 1
                    status = "✅ Set to True" if schema_exists_flag else "❌ Set to False"
                    print(f"    [{updated_count}] {user.email}: {status}")
                else:
                    already_correct += 1
            except Exception as e:
                errors += 1
                print(f"    ❌ Error updating {user.email}: {str(e)}")
        
        if updated_count > 0:
            accounts_db.commit()
            print(f"\n    ✅ Committed {updated_count} updates")
        else:
            print(f"\n    ℹ️  No updates needed")
        
        print(f"\n    Summary:")
        print(f"      - Updated: {updated_count}")
        print(f"      - Already correct: {already_correct}")
        print(f"      - Errors: {errors}")
        
    except Exception as e:
        print(f"    ❌ Error during update: {str(e)}")
        accounts_db.rollback()
    finally:
        accounts_db.close()
    
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    try:
        update_schema_created_flags()
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

