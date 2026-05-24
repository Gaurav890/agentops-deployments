"""
Pull case-study metrics from draft_history.
Run from backend/: python pull_metrics.py
"""
import os, sys, json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent))
from db import get_db

SUBSTANTIVE_EDIT_CHARS = 50  # edits longer than this count as substantive

db = get_db()

# ── 1. Pull ALL draft_history rows (only fields we need) ─────────────────────
rows = (
    db.table("draft_history")
    .select(
        "id, created_at, status, was_edited, edit_diff, edit_lesson, "
        "escalation_risk, agent_draft, sent_draft, meeting_type, "
        "client_name, client_company, pm_id, slack_notified_at"
    )
    .order("created_at", desc=False)
    .limit(5000)
    .execute()
    .data
)

if not rows:
    print("No rows found in draft_history. Is the DB connected?")
    sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────

def week_label(iso: str) -> str:
    """Return 'YYYY-WNN' for grouping."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.strftime("%Y-W%W")

def edit_char_delta(row: dict) -> int:
    """Net chars changed: sum of removed + added line lengths from edit_diff."""
    diff = row.get("edit_diff") or {}
    if not isinstance(diff, dict):
        return 0
    removed = sum(len(l) for l in (diff.get("removed") or []))
    added   = sum(len(l) for l in (diff.get("added") or []))
    return removed + added

def is_substantive(row: dict) -> bool:
    return edit_char_delta(row) >= SUBSTANTIVE_EDIT_CHARS

# ── 2. Launch date & total meetings ──────────────────────────────────────────
launch_date = rows[0]["created_at"][:10]
total_meetings = len(rows)

# ── 3. Draft outcomes ─────────────────────────────────────────────────────────
sent_rows      = [r for r in rows if r.get("status") == "sent"]
unedited_sent  = [r for r in sent_rows if not r.get("was_edited")]
edited_sent    = [r for r in sent_rows if r.get("was_edited")]
substantive    = [r for r in edited_sent if is_substantive(r)]
pending_rows   = [r for r in rows if r.get("status") == "pending"]
discarded_rows = [r for r in rows if r.get("status") == "discarded"]

# ── 4. Edit rate by week ──────────────────────────────────────────────────────
by_week: dict[str, dict] = defaultdict(lambda: {"total": 0, "substantive": 0})
for r in rows:
    wk = week_label(r["created_at"])
    by_week[wk]["total"] += 1
    if is_substantive(r):
        by_week[wk]["substantive"] += 1

# ── 5. Latency: created_at → slack_notified_at (proxy for "draft in inbox") ──
latencies = []
for r in rows:
    if r.get("slack_notified_at"):
        try:
            t0 = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(r["slack_notified_at"].replace("Z", "+00:00"))
            delta_sec = (t1 - t0).total_seconds()
            if 0 < delta_sec < 7200:   # ignore outliers > 2 h (stale pings)
                latencies.append(delta_sec)
        except Exception:
            pass

latency_mean = sum(latencies) / len(latencies) if latencies else None
latencies_sorted = sorted(latencies)
p95_index = int(len(latencies_sorted) * 0.95)
latency_p95 = latencies_sorted[p95_index] if latencies_sorted else None

# ── 6. Escalation flags ───────────────────────────────────────────────────────
esc_counts: dict[str, int] = defaultdict(int)
for r in rows:
    level = (r.get("escalation_risk") or "unknown").lower()
    esc_counts[level] += 1

# ── 7. Edit lessons ───────────────────────────────────────────────────────────
lessons = [
    r["edit_lesson"] for r in rows
    if r.get("edit_lesson") and isinstance(r["edit_lesson"], dict)
]

# ── PRINT REPORT ──────────────────────────────────────────────────────────────
print("=" * 60)
print("FLEETPANDA AGENT — CASE STUDY METRICS")
print("=" * 60)

print(f"\n[0] TIME PERIOD")
print(f"    Launch date : {launch_date}")
print(f"    Report date : {datetime.now(timezone.utc).date()}")

print(f"\n[1] TOTAL MEETINGS PROCESSED")
print(f"    Total rows in draft_history : {total_meetings}")

print(f"\n[2] DRAFT OUTCOMES  (threshold: >{SUBSTANTIVE_EDIT_CHARS} chars changed)")
print(f"    Sent total              : {len(sent_rows)}")
print(f"    Sent unedited           : {len(unedited_sent)}")
print(f"    Sent with any edit      : {len(edited_sent)}")
print(f"    Sent with SUBSTANTIVE edit: {len(substantive)}")
print(f"    Still pending           : {len(pending_rows)}")
print(f"    Discarded (>48 h)       : {len(discarded_rows)}")
if sent_rows:
    sub_pct = len(substantive) / len(sent_rows) * 100
    print(f"    Substantive edit rate   : {sub_pct:.1f}%  ({len(substantive)}/{len(sent_rows)} sent)")

print(f"\n[3] EDIT RATE BY WEEK  (substantive edits / total meetings that week)")
for wk in sorted(by_week):
    d = by_week[wk]
    pct = d["substantive"] / d["total"] * 100 if d["total"] else 0
    print(f"    {wk}  :  {d['substantive']:>2}/{d['total']:<3}  ({pct:.0f}%)")

print(f"\n[4] LATENCY  (created_at → slack_notified_at)")
if latency_mean is not None:
    print(f"    Sample size : {len(latencies)} meetings with Slack timestamp")
    print(f"    Mean        : {latency_mean:.0f}s  ({latency_mean/60:.1f} min)")
    print(f"    p95         : {latency_p95:.0f}s  ({latency_p95/60:.1f} min)")
else:
    print("    No slack_notified_at timestamps found — latency not measurable.")

print(f"\n[5] ESCALATION FLAGS")
for level in ["high", "medium", "low", "healthy", "unknown"]:
    print(f"    {level:<10} : {esc_counts.get(level, 0)}")

print(f"\n[6] EDIT LESSONS")
print(f"    Total accumulated : {len(lessons)}")
if lessons:
    print(f"    Sample (up to 10):")
    for i, l in enumerate(lessons[:10], 1):
        issue  = l.get("issue_type", "?")
        sev    = l.get("severity", "?")
        lesson = l.get("lesson", "")
        print(f"    {i:>2}. [{issue} / {sev}]")
        print(f"        {lesson}")

print("\n" + "=" * 60)
print("Paste this output back to Claude.")
print("=" * 60)
