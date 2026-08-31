"""
Migration script to add trial_start_date and trial_end_date fields to User model
and backfill trial dates for existing users (14 days from their creation date)
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AccountsSessionLocal
from app.models.user import User
from sqlalchemy import text

def migrate():
    """Add trial fields and backfill for existing users"""
    db = AccountsSessionLocal()
    try:
        # Check if columns already exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'app_users' 
            AND column_name IN ('trial_start_date', 'trial_end_date')
        """))
        existing_columns = [row[0] for row in result]
        
        # Add trial_start_date if it doesn't exist
        if 'trial_start_date' not in existing_columns:
            print("Adding trial_start_date column...")
            db.execute(text("""
                ALTER TABLE app_users 
                ADD COLUMN trial_start_date TIMESTAMP
            """))
            db.commit()
            print("[OK] Added trial_start_date column")
        else:
            print("[SKIP] trial_start_date column already exists")
        
        # Add trial_end_date if it doesn't exist
        if 'trial_end_date' not in existing_columns:
            print("Adding trial_end_date column...")
            db.execute(text("""
                ALTER TABLE app_users 
                ADD COLUMN trial_end_date TIMESTAMP
            """))
            db.commit()
            print("[OK] Added trial_end_date column")
        else:
            print("[SKIP] trial_end_date column already exists")
        
        # Backfill trial dates for existing users who don't have them
        print("\nBackfilling trial dates for existing users...")
        users = db.query(User).filter(
            (User.trial_start_date.is_(None)) | (User.trial_end_date.is_(None))
        ).all()
        
        updated_count = 0
        for user in users:
            # Set trial start to creation date or now
            trial_start = user.created_at if user.created_at else datetime.utcnow()
            trial_end = trial_start + timedelta(days=14)
            
            # Only update if trial hasn't expired yet (give them benefit of the doubt)
            if trial_end > datetime.utcnow():
                user.trial_start_date = trial_start
                user.trial_end_date = trial_end
                if user.payment_status != "active" and user.payment_status != "cancelled":
                    user.payment_status = "trialing"
                updated_count += 1
        
        db.commit()
        print(f"[OK] Updated {updated_count} users with trial dates")
        
        # For users whose trial would have expired, set payment_status appropriately
        print("\nUpdating payment status for expired trials...")
        try:
            expired_users = db.query(User).filter(
                User.trial_end_date.isnot(None),
                text("trial_end_date < NOW()")
            ).all()
            
            expired_count = 0
            for user in expired_users:
                if user.payment_status == "trialing":
                    # Set to inactive or keep as is based on tier
                    if user.pricing_tier == "starter" or user.pricing_tier == "free":
                        user.payment_status = "active"  # Free tier stays active
                    else:
                        user.payment_status = "past_due"  # Paid tiers become past_due
                    expired_count += 1
            
            db.commit()
            print(f"[OK] Updated {expired_count} users with expired trials")
        except Exception as expired_error:
            print(f"[WARN] Could not update expired trials: {expired_error}")
            db.rollback()
        
        print("\n[OK] Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
