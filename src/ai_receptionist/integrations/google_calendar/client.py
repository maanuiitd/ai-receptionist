"""
Google calendar integration for the following purspose:
1. Check the available slots in the calendar.
2. CRUD operations in the calendar
"""
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ai_receptionist.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def _service():
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def is_slot_free(start: datetime, duration_min: int | None = None) -> bool:
    duration = duration_min or settings.appointment_duration_minutes
    end = start + timedelta(minutes=duration)
    body = {
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "items": [{"id": settings.google_calendar_id}],
    }
    resp = _service().freebusy().query(body=body).execute()
    cal = resp["calendars"][settings.google_calendar_id]
    if cal.get("errors"):
        raise RuntimeError(f"freebusy failed for calendar: {cal['errors']}")
    busy = cal["busy"]
    return len(busy) == 0

def next_free_slots(from_dt: datetime, count: int = 3) -> list[datetime]:
    """Walk business hours forward and return the next `count` free slots."""
    tz = ZoneInfo(settings.business_timezone)
    h_start = datetime.strptime(settings.business_hours_start, "%H:%M").time()
    h_end = datetime.strptime(settings.business_hours_end, "%H:%M").time()
    step = timedelta(minutes=settings.appointment_duration_minutes)

    cursor = from_dt.astimezone(tz)
    slots: list[datetime] = []
    for _ in range(14 * 24):  # hard cap: two weeks of scanning
        if len(slots) >= count:
            break
        if h_start <= cursor.time() and (cursor + step).time() <= h_end:
            if is_slot_free(cursor):
                slots.append(cursor)
                cursor += step
                continue
        cursor += step
        if cursor.time() > h_end:
            cursor = datetime.combine(cursor.date() + timedelta(days=1), h_start, tz)
    return slots


def create_event(*, start: datetime, summary: str, description: str = "") -> dict[str, Any]:
    end = start + timedelta(minutes=settings.appointment_duration_minutes)
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }
    return _service().events().insert(
        calendarId=settings.google_calendar_id, body=event
    ).execute()


def move_event(event_id: str, new_start: datetime) -> dict[str, Any]:
    end = new_start + timedelta(minutes=settings.appointment_duration_minutes)
    return _service().events().patch(
        calendarId=settings.google_calendar_id,
        eventId=event_id,
        body={"start": {"dateTime": new_start.isoformat()}, "end": {"dateTime": end.isoformat()}},
    ).execute()


def delete_event(event_id: str) -> None:
    _service().events().delete(
        calendarId=settings.google_calendar_id, eventId=event_id
    ).execute()