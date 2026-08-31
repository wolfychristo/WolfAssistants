#!/usr/bin/env python3
"""
Demo Account Setup Script for WolfAssistants

This script creates a demo user account for testing and demonstration purposes.
It checks if the account already exists and creates it if needed.

Usage:
    python setup_demo_account.py
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all models to ensure relationships are properly initialized
from app.models import user, referral, user_activity

from app.core.database import get_accounts_db, SessionLocal
from app.models.user import User
from app.core.auth import get_password_hash, verify_password
from datetime import datetime, timezone

# Demo account credentials
DEMO_EMAIL = "demo@wolfassistants.com"
DEMO_PASSWORD = "DemoPassword123!"
DEMO_NAME = "Demo User"
DEMO_COMPANY = "WolfAssistants Demo"

def setup_demo_account():
    """Create or verify demo account exists"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("WolfAssistants - Demo Account Setup")
        print("=" * 60)
        print()
        
        # Check if demo account already exists
        existing_user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        
        if existing_user:
            print(f"[OK] Demo account already exists!")
            print(f"   Email: {DEMO_EMAIL}")
            print(f"   Name: {existing_user.full_name}")
            print(f"   Status: {'Active' if existing_user.is_active else 'Inactive'}")
            print()
            
            # Verify password works
            if verify_password(DEMO_PASSWORD, existing_user.hashed_password):
                print("[OK] Password verification: SUCCESS")
            else:
                print("[WARNING] Password verification: FAILED")
                print("   The existing account has a different password.")
                print(f"   Expected password: {DEMO_PASSWORD}")
            
            print()
            print("=" * 60)
            print("DEMO ACCOUNT CREDENTIALS")
            print("=" * 60)
            print(f"Email:    {DEMO_EMAIL}")
            print(f"Password: {DEMO_PASSWORD}")
            print("=" * 60)
            return True
        else:
            # Create new demo account
            print("[INFO] Creating new demo account...")
            
            try:
                # Create user
                user = User(
                    email=DEMO_EMAIL,
                    full_name=DEMO_NAME,
                    hashed_password=get_password_hash(DEMO_PASSWORD),
                    is_active=True,
                    company_name=DEMO_COMPANY,
                    tier_activated_at=datetime.now(timezone.utc),
                    payment_status="active"  # Free tier is always active
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                
                print("[OK] Demo account created successfully!")
                print()
                print("=" * 60)
                print("DEMO ACCOUNT CREDENTIALS")
                print("=" * 60)
                print(f"Email:    {DEMO_EMAIL}")
                print(f"Password: {DEMO_PASSWORD}")
                print("=" * 60)
                print()
                print("[TIP] You can now use these credentials to log in to WolfAssistants!")
                return True
                
            except Exception as e:
                db.rollback()
                print(f"[ERROR] Error creating demo account: {str(e)}")
                return False
                
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = setup_demo_account()
    sys.exit(0 if success else 1)

