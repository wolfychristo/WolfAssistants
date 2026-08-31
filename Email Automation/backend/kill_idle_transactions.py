#!/usr/bin/env python3
"""
Kill idle transactions that are blocking ALTER TABLE
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AccountsSessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def kill_idle_transactions():
    """Kill idle transactions that are older than 1 hour"""
    db = AccountsSessionLocal()
    try:
        # Find idle transactions
        result = db.execute(text("""
            SELECT pid, usename, state, query_start, now() - query_start AS duration, query
            FROM pg_stat_activity
            WHERE state = 'idle in transaction'
            AND query_start < now() - interval '1 hour'
            ORDER BY query_start;
        """))
        
        transactions = result.fetchall()
        if not transactions:
            logger.info("No stale idle transactions found")
            return
        
        logger.info(f"Found {len(transactions)} stale idle transactions to kill:")
        for tx in transactions:
            logger.info(f"  PID: {tx[0]}, Duration: {tx[4]}, Query: {tx[5][:80]}...")
        
        # Kill them
        for tx in transactions:
            try:
                pid = tx[0]
                db.execute(text(f"SELECT pg_terminate_backend({pid})"))
                db.commit()
                logger.info(f"✓ Killed transaction PID {pid}")
            except Exception as e:
                logger.warning(f"✗ Failed to kill PID {tx[0]}: {e}")
                db.rollback()
        
        logger.info("Finished killing stale transactions")
        
    except Exception as e:
        logger.error(f"Error killing transactions: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    kill_idle_transactions()
