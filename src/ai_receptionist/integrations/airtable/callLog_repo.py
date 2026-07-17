from dotenv import load_dotenv
import os
import requests
from functools import partial
from pyairtable.orm import Model
from pyairtable.orm import fields as F

load_dotenv()


class CallLog(Model):
    class Meta:
        api_key = partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appjaiC3Zpaz5UOcl'
        # TIP: replace with the tbl... ID (run: pyairtable base appjaiC3Zpaz5UOcl schema)
        # so a rename in the Airtable UI can't break the code.
        table_name = 'callLog'

    callid = F.TextField('callId')
    customer = F._ListField[str]('customer')          # linked record -> list of Customer record IDs
    appointment = F.TextField('appointment')
    callerphone = F.PhoneNumberField('callerPhone')
    timestamp = F.CreatedTimeField('timeStamp')       # read-only, set by Airtable
    durationseconds = F.NumberField('durationSeconds')
    outcome = F.SelectField('outcome')
    summary = F.TextField('summary')
    emergency = F.CheckboxField('emergency')
    emergencyreason = F.TextField('emergencyReason')
    transferredto = F.TextField('transferredTo')
    recordingurl = F.UrlField('recordingUrl')
    endedreason = F.TextField('endedReason')


__all__ = [
    'CallLog',
    'CallLogCreationError',
    'createCallLog',
    'findCallLogByCallId',
]


class CallLogCreationError(Exception):
    """Call log could not be saved due to technical reasons (API/network/auth)."""


def findCallLogByCallId(call_id: str) -> CallLog | None:
    """Return the log for a given Vapi call id, or None if not logged yet."""
    return CallLog.first(formula=CallLog.callid.eq(call_id))


def createCallLog(
    call_id: str,
    caller_phone: str,
    outcome: str,
    summary: str,
    duration_seconds: int | None = None,
    customer_record_id: str | None = None,
    appointment_id: str | None = None,
    emergency: bool = False,
    emergency_reason: str = "",
    transferred_to: str = "",
    recording_url: str = "",
    ended_reason: str = "",
) -> CallLog:
    """
    Log a completed call. Unlike customers, duplicates are not an error:
    if this call_id was already logged (e.g. webhook retry), the existing
    record is returned untouched so logging stays idempotent.
    """
    existing = findCallLogByCallId(call_id)
    if existing is not None:
        return existing

    log = CallLog(
        callid=call_id,
        callerphone=caller_phone,
        outcome=outcome,
        summary=summary,
        emergency=emergency,
    )

    # Optional fields — only set when provided, so Airtable keeps them empty otherwise.
    if duration_seconds is not None:
        log.durationseconds = duration_seconds
    if customer_record_id:
        log.customer = [customer_record_id]   # linked field expects a list of record IDs
    if appointment_id:
        log.appointment = appointment_id
    if emergency_reason:
        log.emergencyreason = emergency_reason
    if transferred_to:
        log.transferredto = transferred_to
    if recording_url:
        log.recordingurl = recording_url
    if ended_reason:
        log.endedreason = ended_reason

    try:
        log.save()
    except requests.exceptions.HTTPError as e:
        raise CallLogCreationError(f"Airtable API error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise CallLogCreationError(f"Network error while saving: {e}") from e

    return log


if __name__ == "__main__":
    # Quick manual test — runs only when executed directly, never on import.
    try:
        log = createCallLog(
            call_id="test-call-001",
            caller_phone="+91 95605 33748",
            outcome="booked",
            summary="Test caller booked an AC service visit.",
            duration_seconds=142,
        )
        print(f"Logged: {log.id} (callId={log.callid})")
    except CallLogCreationError as e:
        print(f"Logging failed: {e}")