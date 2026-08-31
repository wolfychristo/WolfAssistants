#!/usr/bin/env python3
"""
Script to list all users from the accounts database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AccountsSessionLocal
from sqlalchemy import text
import time

def get_all_users():
    """Get all users from accounts database using SQLAlchemy session."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1}/{max_retries}...")
            db = AccountsSessionLocal()
            try:
                # Get all users
                result = db.execute(text("""
                    SELECT 
                        id,
                        email,
                        username,
                        full_name,
                        is_active,
                        is_verified,
                        created_at,
                        deleted_at
                    FROM app_users 
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                """))
                
                users = result.fetchall()
                
                # Get user count
                count_result = db.execute(text("SELECT COUNT(*) FROM app_users WHERE deleted_at IS NULL"))
                total_count = count_result.scalar()
                
                return users, total_count
            finally:
                db.close()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection attempt {attempt + 1} failed: {str(e)[:100]}")
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"Failed to connect after {max_retries} attempts: {e}")
                raise

def list_users():
    """List all users."""
    print("=" * 100)
    print("LISTING ALL USERS FROM ACCOUNTS DATABASE")
    print("=" * 100)
    
    try:
        users, total_count = get_all_users()
        
        print(f"\n✅ Found {total_count} active user(s)\n")
        
        if not users:
            print("No users found in the database.")
            return
        
        print("-" * 100)
        print(f"{'ID':<8} {'Email':<40} {'Username':<20} {'Status':<15} {'Created At':<20}")
        print("-" * 100)
        
        for user in users:
            user_id, email, username, full_name, is_active, is_verified, created_at, deleted_at = user
            
            status = []
            if is_active:
                status.append("Active")
            else:
                status.append("Inactive")
            if is_verified:
                status.append("Verified")
            else:
                status.append("Unverified")
            
            status_str = ", ".join(status)
            username_str = username or "N/A"
            created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "N/A"
            
            print(f"{user_id:<8} {email:<40} {username_str:<20} {status_str:<15} {created_str:<20}")
        
        print("-" * 100)
        
        # Summary statistics
        print("\n" + "=" * 100)
        print("SUMMARY STATISTICS")
        print("=" * 100)
        
        active_count = sum(1 for u in users if u[4])  # is_active
        verified_count = sum(1 for u in users if u[5])  # is_verified
        
        print(f"Total users: {total_count}")
        print(f"Active users: {active_count}")
        print(f"Inactive users: {total_count - active_count}")
        print(f"Verified users: {verified_count}")
        print(f"Unverified users: {total_count - verified_count}")
        
        print("\n" + "=" * 100)
        
    except Exception as e:
        print(f"\n❌ Error listing users: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    list_users()
