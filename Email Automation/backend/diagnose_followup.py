"""
Diagnostic script for Auto Follow-up
Checks status, logs, and potential issues
"""
import os
import sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

USER_EMAIL = "harishchristophers@gmail.com"
SCHEMA_NAME = "tenant_harishchristophers_gmail_com"


def check_user_settings():
    """Check user auto follow-up settings."""
    print("\n" + "="*60)
    print("1. USER SETTINGS")
    print("="*60)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT email, auto_followup_enabled, auto_followup_max_days, 
                   auto_followup_daily_hour, last_auto_followup_run, last_auto_followup_sent_count
            FROM app_users WHERE email = :email
        """), {'email': USER_EMAIL})
        row = result.fetchone()
        
        if row:
            print(f"  Email:            {row[0]}")
            print(f"  Enabled:          {row[1]}")
            print(f"  Max Days:         {row[2] or 14}")
            print(f"  Preferred Hour:   {row[3] if row[3] is not None else 'Any (runs every hour)'}")
            print(f"  Last Run:         {row[4] or 'Never'}")
            print(f"  Last Sent Count:  {row[5] or 0}")
            
            # Check for issues
            issues = []
            if not row[1]:
                issues.append("[!] Auto follow-up is DISABLED")
            if row[2] and row[2] < 7:
                issues.append(f"[!] max_days is very short ({row[2]} days)")
            if row[3] is not None:
                current_hour = datetime.now().hour
                if row[3] != current_hour:
                    issues.append(f"[!] preferred_hour is {row[3]}, but current hour is {current_hour}")
            
            if issues:
                print("\n  ISSUES FOUND:")
                for issue in issues:
                    print(f"    {issue}")
            else:
                print("\n  [OK] Settings look good")
            
            return row
        else:
            print(f"  [X] User not found: {USER_EMAIL}")
            return None


def check_eligible_contacts():
    """Check contacts eligible for follow-up."""
    print("\n" + "="*60)
    print("2. ELIGIBLE CONTACTS")
    print("="*60)
    
    with engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{SCHEMA_NAME}", public'))
        
        result = conn.execute(text("""
            SELECT DISTINCT e.to_address, MAX(e.sent_at) as last_sent,
                   (SELECT COUNT(*) FROM emails e2 
                    WHERE e2.from_address = e.to_address 
                    AND e2.status = 'received') as reply_count
            FROM emails e
            WHERE e.owner_email = :owner
            AND e.status = 'sent'
            AND e.sent_at IS NOT NULL
            GROUP BY e.to_address
            ORDER BY last_sent DESC
            LIMIT 10
        """), {'owner': USER_EMAIL})
        
        contacts = result.fetchall()
        now = datetime.now()
        eligible_count = 0
        
        for contact in contacts:
            to_addr, last_sent, reply_count = contact
            if last_sent:
                hours_since = (now - last_sent).total_seconds() / 3600
                days_since = hours_since / 24
                
                is_eligible = hours_since >= 24 and reply_count == 0 and days_since <= 14
                if is_eligible:
                    eligible_count += 1
                    print(f"  [ELIGIBLE] {to_addr[:40]} - {hours_since:.1f}h ago")
                elif hours_since < 24:
                    print(f"  [WAITING]  {to_addr[:40]} - {hours_since:.1f}h ago (need 24h)")
                elif reply_count > 0:
                    print(f"  [REPLIED]  {to_addr[:40]} - has {reply_count} replies")
                else:
                    print(f"  [OLD]      {to_addr[:40]} - {days_since:.1f} days ago")
        
        print(f"\n  Total eligible: {eligible_count}")
        return eligible_count


def check_recent_emails():
    """Check recent follow-up emails sent."""
    print("\n" + "="*60)
    print("3. RECENT FOLLOW-UP EMAILS")
    print("="*60)
    
    with engine.connect() as conn:
        conn.execute(text(f'SET search_path TO "{SCHEMA_NAME}", public'))
        
        # Look for follow-up emails (subject starts with "Re:" or "Following up")
        result = conn.execute(text("""
            SELECT to_address, subject, sent_at, status, last_error
            FROM emails
            WHERE owner_email = :owner
            AND (subject LIKE 'Re:%' OR subject LIKE 'Following up%')
            AND sent_at > :since
            ORDER BY sent_at DESC
            LIMIT 10
        """), {'owner': USER_EMAIL, 'since': datetime.now() - timedelta(days=7)})
        
        emails = result.fetchall()
        
        if emails:
            for email in emails:
                to_addr, subject, sent_at, status, last_error = email
                status_str = "[OK]" if status == 'sent' else f"[{status.upper()}]"
                error_str = f" - ERROR: {last_error}" if last_error else ""
                print(f"  {status_str} {sent_at.strftime('%Y-%m-%d %H:%M')} -> {to_addr[:30]}")
                print(f"       Subject: {subject[:50]}{error_str}")
        else:
            print("  No follow-up emails in the last 7 days")


def check_logs():
    """Check application logs for follow-up related entries."""
    print("\n" + "="*60)
    print("4. RECENT LOG ENTRIES")
    print("="*60)
    
    log_file = os.path.join(os.path.dirname(__file__), "logs", "application.log")
    
    if not os.path.exists(log_file):
        print(f"  Log file not found: {log_file}")
        return
    
    # Read last 1000 lines and filter for follow-up entries
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-1000:]
        
        followup_lines = [l.strip() for l in lines if 'follow' in l.lower() or 'auto' in l.lower()]
        
        if followup_lines:
            print(f"  Found {len(followup_lines)} follow-up related log entries (last 5):")
            for line in followup_lines[-5:]:
                # Truncate long lines
                if len(line) > 100:
                    line = line[:100] + "..."
                print(f"    {line}")
        else:
            print("  No follow-up related log entries found")
    except Exception as e:
        print(f"  Error reading logs: {e}")


def check_smtp_config():
    """Check if SMTP is properly configured."""
    print("\n" + "="*60)
    print("5. SMTP CONFIGURATION")
    print("="*60)
    
    try:
        with engine.connect() as conn:
            # Try to get SMTP columns that exist
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'app_users' AND column_name LIKE 'smtp%'
            """))
            smtp_columns = [row[0] for row in result.fetchall()]
            
            if not smtp_columns:
                print("  SMTP columns not found in database")
                print("  (Email sending uses per-user profile settings)")
                return
            
            # Build dynamic query
            cols = ", ".join(smtp_columns)
            result = conn.execute(text(f"""
                SELECT {cols} FROM app_users WHERE email = :email
            """), {'email': USER_EMAIL})
            row = result.fetchone()
            
            if row:
                for i, col in enumerate(smtp_columns):
                    val = row[i]
                    if 'password' in col.lower():
                        val = '[SET]' if val else '[NOT SET]'
                    print(f"  {col}: {val or '[NOT SET]'}")
                print("\n  [OK] SMTP fields found")
            else:
                print("  User not found")
    except Exception as e:
        print(f"  Could not check SMTP: {e}")


def main():
    print("\n" + "="*60)
    print("     AUTO FOLLOW-UP DIAGNOSTIC REPORT")
    print("="*60)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: {USER_EMAIL}")
    
    check_user_settings()
    check_smtp_config()
    check_eligible_contacts()
    check_recent_emails()
    check_logs()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("\nIf auto follow-up isn't working, check:")
    print("  1. Is auto_followup_enabled = True?")
    print("  2. Is the current hour matching preferred_hour?")
    print("  3. Are there eligible contacts (24h+ since last email, no reply)?")
    print("  4. Is SMTP properly configured?")
    print("  5. Check application.log for errors")
    print("")


if __name__ == "__main__":
    main()
