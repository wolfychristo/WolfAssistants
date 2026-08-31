"""Directly trigger auto follow-up for testing (bypasses API auth)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

USER_EMAIL = "harishchristophers@gmail.com"
SCHEMA_NAME = "tenant_harishchristophers_gmail_com"

def run_followup():
    """Directly execute the auto follow-up logic."""
    from datetime import datetime, timedelta
    
    print("\n" + "="*60)
    print("Triggering Auto Follow-up")
    print("="*60)
    
    # Check user settings
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT auto_followup_enabled, auto_followup_max_days
            FROM app_users WHERE email = :email
        """), {'email': USER_EMAIL})
        row = result.fetchone()
        
        if not row or not row[0]:
            print("[X] Auto follow-up is disabled for this user")
            return
        
        max_days = row[1] or 14
        print(f"User: {USER_EMAIL}")
        print(f"Max Days: {max_days}")
    
    # Get eligible contacts
    with engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{SCHEMA_NAME}", public'))
        
        # Find contacts with sent emails, no replies, within max_days, and 24+ hours old
        now = datetime.now()
        cutoff_old = now - timedelta(days=max_days)
        cutoff_recent = now - timedelta(hours=24)
        
        result = conn.execute(text("""
            SELECT DISTINCT e.to_address, MAX(e.sent_at) as last_sent
            FROM emails e
            WHERE e.owner_email = :owner
            AND e.status = 'sent'
            AND e.sent_at IS NOT NULL
            AND e.sent_at > :cutoff_old
            AND e.sent_at < :cutoff_recent
            AND NOT EXISTS (
                SELECT 1 FROM emails e2 
                WHERE e2.from_address = e.to_address 
                AND e2.status = 'received'
            )
            GROUP BY e.to_address
        """), {
            'owner': USER_EMAIL,
            'cutoff_old': cutoff_old,
            'cutoff_recent': cutoff_recent
        })
        
        eligible = result.fetchall()
        
        print(f"\nEligible contacts: {len(eligible)}")
        for contact in eligible:
            print(f"  - {contact[0]} (last sent: {contact[1]})")
        
        if not eligible:
            print("\n[!] No eligible contacts found")
            return
        
        # Now attempt to send follow-ups
        print("\n" + "-"*60)
        print("Sending follow-ups...")
        print("-"*60)
        
        sent_count = 0
        for contact in eligible:
            to_addr = contact[0]
            last_sent_at = contact[1]
            
            # Get the last sent email details
            result = conn.execute(text("""
                SELECT subject, body FROM emails 
                WHERE owner_email = :owner AND to_address = :to_addr AND status = 'sent'
                ORDER BY sent_at DESC LIMIT 1
            """), {'owner': USER_EMAIL, 'to_addr': to_addr})
            
            last_email = result.fetchone()
            if not last_email:
                continue
            
            subject = f"Re: {last_email[0]}" if last_email[0] else "Following up"
            
            print(f"\n[>] Would send follow-up to: {to_addr}")
            print(f"    Subject: {subject}")
            print(f"    Last sent: {last_sent_at}")
            
            # To actually send, we need to call the email sending function
            # For now, just simulate
            sent_count += 1
        
        print("\n" + "="*60)
        print(f"[OK] Would have sent {sent_count} follow-up emails")
        print("="*60)
        print("\nTo actually send, you need to:")
        print("1. Get your JWT token from browser (DevTools > Application > Local Storage)")
        print("2. Call: POST http://localhost:8000/api/v1/emails/auto-followup/run")
        print("   with header: Authorization: Bearer YOUR_TOKEN")

if __name__ == "__main__":
    run_followup()
