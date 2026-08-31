#!/usr/bin/env python3
"""
Check for locks on app_users table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AccountsSessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_locks():
    """Check for locks on app_users table"""
    db = AccountsSessionLocal()
    try:
        # Check for blocking queries
        result = db.execute(text("""
            SELECT 
                blocked_locks.pid AS blocked_pid,
                blocking_locks.pid AS blocking_pid,
                blocked_activity.usename AS blocked_user,
                blocking_activity.usename AS blocking_user,
                blocked_activity.query AS blocked_statement,
                blocking_activity.query AS blocking_statement
            FROM pg_catalog.pg_locks blocked_locks
            JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
            JOIN pg_catalog.pg_locks blocking_locks 
                ON blocking_locks.locktype = blocked_locks.locktype
                AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                AND blocking_locks.pid != blocked_locks.pid
            JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
            WHERE NOT blocked_locks.granted;
        """))
        
        locks = result.fetchall()
        if locks:
            logger.warning(f"Found {len(locks)} blocking locks:")
            for lock in locks:
                logger.warning(f"  Blocked PID: {lock[0]}, Blocking PID: {lock[1]}")
                logger.warning(f"  Blocked query: {lock[4][:100]}...")
                logger.warning(f"  Blocking query: {lock[5][:100]}...")
        else:
            logger.info("No blocking locks found")
        
        # Check for long-running transactions
        result = db.execute(text("""
            SELECT 
                pid,
                usename,
                state,
                query_start,
                now() - query_start AS duration,
                query
            FROM pg_stat_activity
            WHERE state != 'idle'
            AND query NOT LIKE '%pg_stat_activity%'
            ORDER BY query_start;
        """))
        
        transactions = result.fetchall()
        if transactions:
            logger.info(f"Found {len(transactions)} active transactions:")
            for tx in transactions:
                logger.info(f"  PID: {tx[0]}, User: {tx[1]}, State: {tx[2]}, Duration: {tx[4]}")
                logger.info(f"  Query: {tx[5][:100]}...")
        else:
            logger.info("No active transactions found")
        
    except Exception as e:
        logger.error(f"Error checking locks: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    check_locks()
