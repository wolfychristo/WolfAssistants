"""Quick check for eligible contacts."""
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text('SET search_path TO "tenant_harishchristophers_gmail_com", public'))
    
    result = conn.execute(text("""
        SELECT DISTINCT e.to_address, MAX(e.sent_at) as last_sent,
               (SELECT COUNT(*) FROM emails e2 
                WHERE e2.from_address = e.to_address 
                AND e2.status = 'received') as reply_count
        FROM emails e
        WHERE e.owner_email = 'harishchristophers@gmail.com'
        AND e.status = 'sent'
        AND e.sent_at IS NOT NULL
        GROUP BY e.to_address
        ORDER BY last_sent DESC
        LIMIT 15
    """))
    
    contacts = result.fetchall()
    
    print()
    print('Contacts with Sent Emails (max_days=14):')
    print('-'*95)
    
    now = datetime.now()
    eligible_count = 0
    
    for contact in contacts:
        to_addr, last_sent, reply_count = contact
        if last_sent:
            hours_since = (now - last_sent).total_seconds() / 3600
            days_since = hours_since / 24
            
            is_eligible = hours_since >= 24 and reply_count == 0 and days_since <= 14
            
            if hours_since < 24:
                status = 'WAITING (< 24h)'
            elif reply_count > 0:
                status = 'HAS REPLY'
            elif days_since > 14:
                status = 'TOO OLD (> 14d)'
            else:
                status = '[ELIGIBLE]'
                eligible_count += 1
            
            print(f'{to_addr[:38]:<38} | {last_sent.strftime("%Y-%m-%d %H:%M")} | {hours_since:>6.1f}h | {days_since:>4.1f}d | R:{reply_count} | {status}')
    
    print('-'*95)
    print(f'Total eligible for auto follow-up: {eligible_count}')
