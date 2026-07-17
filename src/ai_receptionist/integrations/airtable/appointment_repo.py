from dotenv import load_dotenv
import os
import requests
from datetime import datetime
from functools import partial
from pyairtable.orm import Model
from pyairtable.orm import fields as F

load_dotenv()


class Appointment(Model):
    class Meta:
        api_key = partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appjaiC3Zpaz5UOcl'
        # TIP: replace with the tbl... ID (run: pyairtable base appjaiC3Zpaz5UOcl schema)
        # so a rename in the Airtable UI can't break the code.
        table_name = 'appointment'

    appointmentid = F.TextField('appointmentId')
    customer = F._ListField[str]('customer')          # linked record -> list of Customer record IDs
    calendareventid = F.TextField('calendarEventId')
    start = F.DatetimeField('start')
    durationminute = F.NumberField('durationMinute')
    servicetype = F.SelectField('serviceType')
    notes = F.TextField('notes')
    address = F.TextField('address')
    status = F.SelectField('status')
    isemergency = F.CheckboxField('isEmergency')
    createdat = F.CreatedTimeField('createdAt')       # read-only, set by Airtable
    lastmodified = F.LastModifiedTimeField('lastModified')  # read-only, set by Airtable


__all__ = [
    'Appointment',
    'AppointmentCreationError',
    'AppointmentNotFoundError',
    'AppointmentUpdateError',
    'createAppointment',
    'findAppointmentById',
    'findUpcomingAppointmentsForCustomer',
    'rescheduleAppointment',
    'cancelAppointment',
]

# Status values — must match the options of the 'status' single-select in Airtable.
STATUS_SCHEDULED = "scheduled"
STATUS_RESCHEDULED = "rescheduled"
STATUS_CANCELLED = "cancelled"
STATUS_COMPLETED = "completed"


class AppointmentCreationError(Exception):
    """Appointment could not be saved due to technical reasons (API/network/auth)."""


class AppointmentNotFoundError(Exception):
    """No appointment matches the given id."""


class AppointmentUpdateError(Exception):
    """Appointment update (reschedule/cancel) failed due to technical reasons."""


def _save(record: Appointment, error_cls: type[Exception]) -> Appointment:
    """Shared save-with-error-mapping used by create and update paths."""
    try:
        record.save()
    except requests.exceptions.HTTPError as e:
        raise error_cls(f"Airtable API error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise error_cls(f"Network error while saving: {e}") from e
    return record


def findAppointmentById(appointment_id: str) -> Appointment | None:
    """Look up by your business appointmentId field (not the Airtable rec... id)."""
    return Appointment.first(formula=Appointment.appointmentid.eq(appointment_id))


def findUpcomingAppointmentsForCustomer(customer_record_id: str) -> list[Appointment]:
    """
    All non-cancelled future appointments linked to a customer.
    Used for 'I want to reschedule my appointment' — the agent lists these
    back to the caller instead of asking for an appointment id they won't know.
    """
    # Filtering linked records by record ID inside an Airtable formula is
    # unreliable (formulas see display names, not rec... ids), so we filter
    # in Python — the linked field on each record holds the record IDs.
    now = datetime.now().astimezone()
    return [
        a for a in Appointment.all()
        if customer_record_id in (a.customer or [])
        and a.status != STATUS_CANCELLED
        and a.start is not None
        and a.start > now
    ]


def createAppointment(
    appointment_id: str,
    customer_record_id: str,
    start: datetime,
    duration_minute: int,
    service_type: str,
    address: str,
    calendar_event_id: str = "",
    notes: str = "",
    is_emergency: bool = False,
) -> Appointment:
    """
    Persist an appointment. Availability checking belongs to the Google
    Calendar layer — call this only AFTER the calendar slot is confirmed,
    and pass the resulting calendar_event_id so the two systems stay linked.
    """
    if findAppointmentById(appointment_id) is not None:
        # Same idempotency stance as call logs: a retry should not duplicate.
        raise AppointmentCreationError(
            f"An appointment with id {appointment_id!r} already exists."
        )

    appt = Appointment(
        appointmentid=appointment_id,
        customer=[customer_record_id],   # linked field expects a list of record IDs
        start=start,
        durationminute=duration_minute,
        servicetype=service_type,
        address=address,
        status=STATUS_SCHEDULED,
        isemergency=is_emergency,
    )
    if calendar_event_id:
        appt.calendareventid = calendar_event_id
    if notes:
        appt.notes = notes

    return _save(appt, AppointmentCreationError)


def rescheduleAppointment(
    appointment_id: str,
    new_start: datetime,
    new_duration_minute: int | None = None,
) -> Appointment:
    """
    Move an existing appointment. Update the Google Calendar event FIRST,
    then call this so Airtable reflects the confirmed new slot.
    """
    appt = findAppointmentById(appointment_id)
    if appt is None:
        raise AppointmentNotFoundError(f"No appointment with id {appointment_id!r}.")
    if appt.status == STATUS_CANCELLED:
        raise AppointmentUpdateError(
            f"Appointment {appointment_id!r} is cancelled and cannot be rescheduled; create a new one."
        )

    appt.start = new_start
    if new_duration_minute is not None:
        appt.durationminute = new_duration_minute
    appt.status = STATUS_RESCHEDULED

    return _save(appt, AppointmentUpdateError)


def cancelAppointment(appointment_id: str) -> Appointment:
    """
    Soft-cancel: flip status instead of deleting the record, so call history
    and reporting keep the full picture. Delete the Google Calendar event
    separately in the calendar layer.
    """
    appt = findAppointmentById(appointment_id)
    if appt is None:
        raise AppointmentNotFoundError(f"No appointment with id {appointment_id!r}.")
    if appt.status == STATUS_CANCELLED:
        return appt  # already cancelled — idempotent, not an error

    appt.status = STATUS_CANCELLED
    return _save(appt, AppointmentUpdateError)


if __name__ == "__main__":
    # Quick manual test — runs only when executed directly, never on import.
    from datetime import timedelta

    try:
        appt = createAppointment(
            appointment_id="test-appt-001",
            customer_record_id="recdv7BJreJFgoXLm",  # Neha Kapoor from your earlier test
            start=datetime.now().astimezone() + timedelta(days=2),
            duration_minute=60,
            service_type="AC service",
            address="123 Test Street, Ghaziabad",
            notes="Created from repo self-test.",
        )
        print(f"Created: {appt.id} (appointmentId={appt.appointmentid})")
    except AppointmentCreationError as e:
        print(f"Creation failed / duplicate: {e}")