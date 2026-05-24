"""
Smoke test for the Avoma poller.
Calls poll_once() directly — processes any transcriptions from the last 30 minutes.

Usage:
  cd backend
  python test_poller.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from jobs.avoma_poller import poll_once

if __name__ == "__main__":
    print("Running one poll cycle...\n")
    poll_once()
    print("\nDone.")
