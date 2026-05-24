from __future__ import annotations

"""
Google Calendar API integration — fallback for attendee email lookup.
Used when transcript parsing can't identify client email.
Scope: calendar.readonly
"""
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from auth.google_oauth import get_credentials_for_pm


def get_attendees_for_meeting(pm_id: str, start_time: str) -> list[dict]:
    """
    Find the calendar event closest to start_time and return its attendees.
    start_time: ISO 8601 string (e.g. "2025-01-15T14:00:00Z")
    Returns list of {"email": ..., "displayName": ...}
    """
    creds = get_credentials_for_pm(pm_id)
    service = build("calendar", "v3", credentials=creds)

    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    time_min = (dt - timedelta(minutes=5)).isoformat()
    time_max = (dt + timedelta(minutes=5)).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return []

    # Use first matching event
    attendees = events[0].get("attendees", [])
    return [
        {"email": a.get("email", ""), "displayName": a.get("displayName", "")}
        for a in attendees
        if a.get("email")
    ]
