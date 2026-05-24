"""
Data retention background job.
Runs once per day. Nulls out the transcript column on draft_history rows
older than 90 days to control database growth.
All other columns (draft, action items, summaries, escalation data) are kept forever.
"""
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from db.models import prune_old_transcripts


def run_retention_once() -> None:
    """Null out transcripts older than 90 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    count = prune_old_transcripts(cutoff)
    print(f"[retention] Pruned transcripts from {count} record(s) older than {cutoff.date()}")


def start_retention_scheduler() -> None:
    """Start daily retention job in a daemon thread. Call once at app startup."""
    def _loop():
        # Run first check after 1 hour (let app settle), then every 24h
        time.sleep(60 * 60)
        while True:
            try:
                run_retention_once()
            except Exception:
                print(f"[retention] Error:\n{traceback.format_exc()}")
            time.sleep(24 * 60 * 60)

    t = threading.Thread(target=_loop, daemon=True, name="retention")
    t.start()
    print("[retention] Daily transcript pruning scheduler started (90-day retention)")
