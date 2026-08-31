#!/usr/bin/env python3
"""
Admin Management System for WolfAssistants
Provides comprehensive admin management capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from datetime import datetime

class AdminManager:
    """Comprehensive admin management system"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_primary_admin(self) -> User:
        """Get the primary admin user (admin@yourcompany.com)"""
        admin = self.db.query(User).filter(
            User.email == 'admin@yourcompany.com',
            User.is_admin == True
        ).first()
        
        if not admin:
            raise Exception("Primary admin not found! This is a critical security issue.")
        
        return admin
    
    def verify_primary_admin_status(self) -> bool:
        """Verify that admin@yourcompany.com is the primary admin"""
        try:
            admin = self.get_primary_admin()
            print(f"Primary Admin Verified: {admin.email}")
            print(f"   - Full Name: {admin.full_name}")
            print(f"   - Admin Status: {admin.is_admin}")
            print(f"   - Active Status: {admin.is_active}")
            print(f"   - Created: {admin.created_at}")
            return True
        except Exception as e:
            print(f"Primary Admin Verification Failed: {e}")
            return False
    
    def list_all_admins(self):
        """List all admin users"""
        admins = self.db.query(User).filter(User.is_admin == True).all()
        
        print(f"\nAdmin Users ({len(admins)} total):")
        print("-" * 60)
        
        for admin in admins:
            status = "Active" if admin.is_active else "Inactive"
            primary = "PRIMARY" if admin.email == 'admin@yourcompany.com' else "Regular"
            
            print(f"{primary} {admin.email}")
            print(f"   Name: {admin.full_name}")
            print(f"   Status: {status}")
            print(f"   Created: {admin.created_at}")
            print()
    
    def promote_user_to_admin(self, email: str, reason: str = "Promoted by primary admin") -> bool:
        """Promote a user to admin status"""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                print(f"❌ User {email} not found")
                return False
            
            if user.is_admin:
                print(f"⚠️  User {email} is already an admin")
                return False
            
            user.is_admin = True
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            print(f"✅ User {email} has been promoted to admin")
            print(f"   Reason: {reason}")
            print(f"   Promoted by: Primary Admin (admin@yourcompany.com)")
            return True
            
        except Exception as e:
            print(f"❌ Error promoting user: {e}")
            self.db.rollback()
            return False
    
    def demote_admin(self, email: str, reason: str = "Demoted by primary admin") -> bool:
        """Demote an admin user (except primary admin)"""
        try:
            # Prevent demotion of primary admin
            if email == 'admin@yourcompany.com':
                print(f"Cannot demote primary admin {email}")
                print("   Primary admin privileges are protected and cannot be removed")
                return False
            
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                print(f"User {email} not found")
                return False
            
            if not user.is_admin:
                print(f"User {email} is not an admin")
                return False
            
            user.is_admin = False
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            print(f"User {email} has been demoted from admin")
            print(f"   Reason: {reason}")
            print(f"   Demoted by: Primary Admin (admin@yourcompany.com)")
            return True
            
        except Exception as e:
            print(f"Error demoting user: {e}")
            self.db.rollback()
            return False
    
    def get_admin_capabilities(self):
        """Display admin capabilities and privileges"""
        print("\nADMIN CAPABILITIES & PRIVILEGES")
        print("=" * 50)
        print("PRIMARY ADMIN (admin@yourcompany.com):")
        print("   - Full system access")
        print("   - User management (create, delete, restore)")
        print("   - Admin promotion/demotion")
        print("   - System analytics and reporting")
        print("   - Feedback analysis")
        print("   - System health monitoring")
        print("   - Protected from self-demotion")
        print("   - Indefinite admin status")
        print()
        print("REGULAR ADMINS:")
        print("   - System access")
        print("   - User management")
        print("   - Analytics and reporting")
        print("   - Cannot promote/demote other admins")
        print("   - Can be demoted by primary admin")
        print()
        print("SECURITY FEATURES:")
        print("   - JWT token authentication")
        print("   - Database-level admin verification")
        print("   - Primary admin protection")
        print("   - Audit logging")
        print("   - Session management")

def main():
    """Main admin management interface"""
    print("WOLFASSISTANTS ADMIN MANAGEMENT SYSTEM")
    print("=" * 50)
    
    manager = AdminManager()
    
    # Verify primary admin status
    if not manager.verify_primary_admin_status():
        print("\nCRITICAL: Primary admin verification failed!")
        print("   Please ensure admin@yourcompany.com is properly configured as admin.")
        return
    
    # Display admin capabilities
    manager.get_admin_capabilities()
    
    # List all admins
    manager.list_all_admins()
    
    print("\nAdmin management system is operational")
    print("   Primary admin: admin@yourcompany.com")
    print("   Status: FULL ADMINISTRATIVE PRIVILEGES")
    print("   Protection: INDEFINITE ADMIN STATUS")

if __name__ == "__main__":
    main()
