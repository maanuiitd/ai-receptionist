"""Manual smoke test for the Google Calendar integration.
Run: uv run python scripts/smoke_gcal.py
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ai_receptionist.config import settings
from ai_receptionist.integrations.google_calendar import client as gcal

tz = ZoneInfo(settings.business_timezone)
tomorrow_10am = (datetime.now(tz) + timedelta(days=1)).replace(
    hour=10, minute=0, second=0, microsecond=0
)

print("1) freebusy check for", tomorrow_10am.isoformat())
print("   free?", gcal.is_slot_free(tomorrow_10am))

print("2) creating test event...")
event = gcal.create_event(start=tomorrow_10am, summary="SMOKE TEST — delete me")
print("   created:", event["id"])

print("3) slot should now be busy:", not gcal.is_slot_free(tomorrow_10am))

print("4) moving it +1 hour...")
gcal.move_event(event["id"], tomorrow_10am + timedelta(hours=1))

print("5) deleting it...")
gcal.delete_event(event["id"])
print("   done — check the calendar UI, it should be gone")