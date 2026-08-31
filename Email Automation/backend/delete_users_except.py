"""
Script to delete users from the database except for specified emails.

Usage:
    python delete_users_except.py

The script will:
1. Show all users in the database
2. Let you specify which emails to KEEP
3. Ask YES/NO before deleting
"""

import sys
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.user import User
from app.core.tenant_database import drop_tenant_schema
# Import all related models to ensure SQLAlchemy can resolve relationships
from app.models.referral import ReferralInvitation, ReferralReward, UserCredit, ReferralCode
from app.models.user_activity import UserActivity, UserBan, AbusePattern
from app.models.api_key import APIKey
from app.models.api_usage import APIUsage
from app.models.token import EmailVerificationToken, PasswordResetToken, ChangeEmailToken, PasswordResetOTP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of emails to KEEP (all other users will be deleted)
KEEP_EMAILS = [
    "harishchristophers@gmail.com",
    "2004tanvisharma@gmail.com",
    "theophilgaudence@icloud.com",
    "S.TANVEER0011@gmail.com",
    "jasicp60@gmail.com",
    "Henrybrad1342@gmail.com",
    "EliasStamadisGougos@hotmail.com",
    "dorcaschep973@gmail.com",
    "demo@wolfassistants.com",
]

def show_all_users(db):
    """Display all users in the database."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    print("\n" + "=" * 80)
    print("ALL USERS IN DATABASE")
    print("=" * 80)
    print(f"{'ID':<6} {'Email':<40} {'Name':<30} {'Created':<12} {'Status'}")
    print("-" * 80)
    
    for user in users:
        status = "ACTIVE" if user.is_active else "INACTIVE"
        if user.deleted_at:
            status = "DELETED"
        name = (user.full_name or "N/A")[:28]
        created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
        print(f"{user.id:<6} {user.email:<40} {name:<30} {created:<12} {status}")
    
    print("=" * 80)
    print(f"Total users: {len(users)}\n")
    
    return users

def get_emails_to_keep_interactive(users):
    """Interactive function to get emails to keep."""
    # Start with emails from KEEP_EMAILS list if defined
    keep_emails = []
    if KEEP_EMAILS:
        keep_emails = [email.lower() for email in KEEP_EMAILS]
        print("\n" + "=" * 80)
        print("EMAILS TO KEEP (from KEEP_EMAILS list)")
        print("=" * 80)
        for email in KEEP_EMAILS:
            print(f"  ✓ {email}")
        print(f"\n{len(KEEP_EMAILS)} emails are pre-configured to be kept.")
        response = input("Do you want to add more emails to keep? (y/n): ").strip().lower()
        if response != 'y':
            return keep_emails
    
    print("\n" + "=" * 80)
    print("SELECT ADDITIONAL USERS TO KEEP")
    print("=" * 80)
    print("\nYou can specify additional emails to KEEP:")
    print("  1. Enter emails one by one")
    print("  2. Enter 'all' to keep all users (cancels deletion)")
    print("  3. Enter 'list' to see all users again")
    print("  4. Press Enter with empty input to finish\n")
    
    all_emails = [u.email.lower() for u in users]
    
    while True:
        email = input("Enter additional email to KEEP (or press Enter to finish): ").strip()
        
        if not email:
            break
        
        email_lower = email.lower()
        
        if email_lower == 'all':
            print("\nAll users will be kept. No deletion will occur.")
            return all_emails
        
        if email_lower == 'list':
            # Re-display users (we'll need to pass db, but for now just show message)
            print("\nUse the list shown above. All users are listed with their emails.")
            continue
        
        if '@' not in email:
            print(f"  ⚠ Invalid email format: {email}")
            continue
        
        if email_lower in all_emails:
            if email_lower not in keep_emails:
                keep_emails.append(email_lower)
                print(f"  ✓ Added: {email}")
            else:
                print(f"  ⚠ Already added: {email}")
        else:
            print(f"  ⚠ Email not found in database: {email}")
            response = input("  Add anyway? (y/n): ").strip().lower()
            if response == 'y':
                keep_emails.append(email_lower)
                print(f"  ✓ Added: {email}")
    
    return keep_emails

def confirm_deletion(users_to_delete, users_to_keep):
    """Ask for YES/NO confirmation before deletion."""
    print("\n" + "=" * 80)
    print("DELETION SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal users in database: {len(users_to_delete) + len(users_to_keep)}")
    print(f"Users to KEEP: {len(users_to_keep)}")
    print(f"Users to DELETE: {len(users_to_delete)}")
    
    if users_to_keep:
        print(f"\n✓ Users that will be KEPT ({len(users_to_keep)}):")
        for user in users_to_keep:
            print(f"    - {user.email} (ID: {user.id})")
    
    if users_to_delete:
        print(f"\n✗ Users that will be DELETED ({len(users_to_delete)}):")
        for user in users_to_delete:
            print(f"    - {user.email} (ID: {user.id})")
    
    print("\n" + "=" * 80)
    print("WARNING: This will PERMANENTLY delete:")
    print("  - User accounts")
    print("  - Tenant schemas (contacts, emails, meetings, todos, etc.)")
    print("  - API keys and usage records")
    print("  - Referral data")
    print("  - User activity logs")
    print("  - All related tokens")
    print("\nThis action CANNOT be undone!")
    print("=" * 80)
    
    while True:
        response = input("\nDo you want to proceed with deletion? (YES/NO): ").strip().upper()
        
        if response == 'YES':
            return True
        elif response == 'NO':
            return False
        else:
            print("Please enter 'YES' or 'NO'")

def delete_user_completely(user: User, db):
    """Completely delete a user and all related data."""
    user_email = user.email
    user_id = user.id
    
    logger.info(f"Deleting user: {user_email} (ID: {user_id})")
    
    try:
        # 1. Drop tenant schema (contains all user's business data)
        logger.info(f"  Dropping tenant schema for {user_email}...")
        schema_dropped = drop_tenant_schema(user_email)
        if schema_dropped:
            logger.info(f"  ✓ Tenant schema dropped")
        else:
            logger.warning(f"  ⚠ Failed to drop tenant schema (may not exist)")
        
        # 2. Delete related tokens
        logger.info(f"  Deleting tokens...")
        db.execute(text("DELETE FROM email_verification_tokens WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM password_reset_tokens WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM change_email_tokens WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM password_reset_otps WHERE user_id = :uid"), {"uid": user_id})
        logger.info(f"  ✓ Tokens deleted")
        
        # 3. Delete API keys and usage
        logger.info(f"  Deleting API keys and usage...")
        db.execute(text("DELETE FROM api_usage WHERE api_key_id IN (SELECT id FROM api_keys WHERE user_id = :uid)"), {"uid": user_id})
        db.execute(text("DELETE FROM api_keys WHERE user_id = :uid"), {"uid": user_id})
        logger.info(f"  ✓ API keys and usage deleted")
        
        # 4. Delete referral data
        logger.info(f"  Deleting referral data...")
        db.execute(text("DELETE FROM referral_rewards WHERE referrer_id = :uid OR referee_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM referral_invitations WHERE referrer_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM user_credits WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM referral_codes WHERE user_id = :uid"), {"uid": user_id})
        logger.info(f"  ✓ Referral data deleted")
        
        # 5. Delete user activity and monitoring data
        logger.info(f"  Deleting user activity and monitoring data...")
        db.execute(text("DELETE FROM user_activities WHERE user_id = :uid"), {"uid": user_id})
        # Handle user_bans - need to handle foreign keys carefully
        db.execute(text("UPDATE user_bans SET banned_by = NULL WHERE banned_by = :uid"), {"uid": user_id})
        db.execute(text("UPDATE user_bans SET appeal_reviewed_by = NULL WHERE appeal_reviewed_by = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM user_bans WHERE user_id = :uid"), {"uid": user_id})
        db.execute(text("DELETE FROM abuse_patterns WHERE user_id = :uid"), {"uid": user_id})
        logger.info(f"  ✓ User activity and monitoring data deleted")
        
        # 6. Finally, delete the user
        logger.info(f"  Deleting user record...")
        db.delete(user)
        db.commit()
        logger.info(f"  ✓ User {user_email} completely deleted")
        
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"  ✗ Error deleting user {user_email}: {str(e)}", exc_info=True)
        return False

def main():
    """Main function to delete users except specified emails."""
    print("=" * 80)
    print("USER DELETION SCRIPT")
    print("=" * 80)
    print("\nThis script will help you delete users from the database.")
    print("You will be able to specify which users to KEEP.\n")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Show all users first
        all_users = show_all_users(db)
        
        if not all_users:
            print("No users found in database. Exiting.")
            return
        
        # Get emails to keep
        keep_emails = get_emails_to_keep_interactive(all_users)
        keep_emails_lower = [email.lower() for email in keep_emails]
        
        # Filter users
        users_to_delete = [u for u in all_users if u.email.lower() not in keep_emails_lower]
        users_to_keep = [u for u in all_users if u.email.lower() in keep_emails_lower]
        
        # Check if all users are being kept
        if not users_to_delete:
            print("\n✓ All users are being kept. No deletion needed.")
            return
        
        # Ask for YES/NO confirmation
        if not confirm_deletion(users_to_delete, users_to_keep):
            print("\n✗ Deletion cancelled. No users were deleted.")
            return
        
        # Proceed with deletion
        print(f"\n{'=' * 80}")
        print("Starting deletion process...")
        print(f"{'=' * 80}\n")
        
        deleted_count = 0
        failed_count = 0
        
        for i, user in enumerate(users_to_delete, 1):
            print(f"[{i}/{len(users_to_delete)}] Processing: {user.email}")
            success = delete_user_completely(user, db)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
            print()  # Empty line for readability
        
        # Final summary
        print(f"{'=' * 80}")
        print("DELETION COMPLETE")
        print(f"{'=' * 80}")
        print(f"  Successfully deleted: {deleted_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Kept: {len(users_to_keep)}")
        print(f"{'=' * 80}\n")
        
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user. No changes were made.")
        db.rollback()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        db.rollback()
        print(f"\n✗ Fatal error occurred. All changes rolled back.")
    finally:
        db.close()

if __name__ == "__main__":
    main()

