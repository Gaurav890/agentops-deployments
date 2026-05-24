"""
Quick smoke test for the context extractor.
Run from the backend/ directory with the .env loaded:
  cd backend && python test_extractor.py
"""
import json
import sys
import os

# Ensure parent path resolution works
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent.extractor import extract_context

SAMPLE_TRANSCRIPT = """Sarah: Hi Raj, good to connect again this week. How are things going with the new driver onboarding?

Raj: Hey Sarah! Going pretty well. We got 12 more drivers set up last week. Had a few questions about the fuel card integration though.

Sarah: Sure, what came up?

Raj: Some drivers are seeing a sync delay — the transactions are showing up about 2 hours late.

Sarah: Got it. That's a known issue with the Fleetcor API on weekends — we have a fix going out Thursday. I'll make sure you're notified when it's live.

Raj: Perfect. Also, Lisa wanted to know if we can get a report of driver activity by week.

Sarah: Absolutely. I'll set up a weekly auto-report to send to you and Lisa every Monday morning. What email should I use?

Raj: lisa@acmecorp.com and me at raj@acmecorp.com.

Sarah: Done. I'll have that configured by end of day. Anything else?

Raj: I think that's it. Thanks Sarah!

Sarah: Great, talk soon!"""

SAMPLE_METADATA = {
    "id": "test-meeting-001",
    "title": "Acme Corp — Weekly Sync",
    "start_time": "2026-04-13T14:00:00Z",
    "attendees": [
        {"name": "Sarah Chen", "email": "sarah@fleetpanda.com"},
        {"name": "Raj Patel", "email": "raj@acmecorp.com"},
    ],
}

if __name__ == "__main__":
    print("Running extractor test...\n")
    result = extract_context(SAMPLE_TRANSCRIPT, SAMPLE_METADATA)
    print(json.dumps(result, indent=2))
