"""Push every stay that holds dates onto a Google Calendar.

The dashboard calendar already shows this (AdminBookingCalendarView), but it
only exists inside the dashboard. This puts the same stays where the desk
already looks: alongside everyone's own appointments, on their phones.

Why the API rather than an .ics subscription
--------------------------------------------
Google refreshes a subscribed .ics feed on its own schedule -- several hours,
sometimes a day, with no way to force it and no webhook to push it. A booking
taken this morning would not appear until tomorrow, which is no use to a desk
asking who arrives today. Writing through the API lands within a second. It
also avoids publishing a URL that carries every client's name and phone to
anyone who gets hold of the link.

Failure policy
--------------
Identical to products/daftra.py, and for the same reason: by the time these
run the booking is already taken and usually already paid for. A Google outage
must never fail a booking. Every entry point swallows its errors and logs
them; the stay simply carries no calendar event until the next attempt, and
`manage.py sync_google_calendar` sweeps up whatever was missed.

Event identity
--------------
The event id is derived from the booking id rather than stored on the model,
so there is no column to migrate and no way for the two to drift apart. Google
requires base32hex, which is why the prefix uses letters a-v only.

Setup is documented in core/settings.py under GOOGLE_CALENDAR_ID.
"""
import base64
import json
import logging
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
API_ROOT = "https://www.googleapis.com/calendar/v3"

# Google's own palette. Settled stays read as settled at a glance, so anything
# still owing money stands out against them.
COLOR_PAID = "10"          # Basil, green
COLOR_OUTSTANDING = "6"    # Tangerine, orange


class GoogleCalendarError(Exception):
    """A Calendar call failed. Raised internally, never escapes this module."""


def is_enabled():
    return bool(getattr(settings, "GOOGLE_CALENDAR_ENABLED", False))


def event_id_for(booking_pk):
    """A stable Calendar event id for a booking.

    Google accepts base32hex only -- digits 0-9 and lowercase a-v -- so the
    prefix deliberately avoids w, x, y and z.
    """
    return "kenbooking{}".format(booking_pk)


def _credentials():
    """Service-account credentials from the environment.

    The JSON is accepted raw or base64-encoded, because a private key pasted
    into a hosting provider's environment editor tends to lose its newlines and
    base64 survives that.
    """
    from google.oauth2 import service_account

    raw = (getattr(settings, "GOOGLE_SERVICE_ACCOUNT_JSON", "") or "").strip()
    if not raw:
        raise GoogleCalendarError("GOOGLE_SERVICE_ACCOUNT_JSON is not set.")
    if not raw.startswith("{"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except Exception as exc:
            raise GoogleCalendarError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is neither JSON nor base64.") from exc
    try:
        info = json.loads(raw)
    except ValueError as exc:
        raise GoogleCalendarError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc

    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def _session():
    """An authorised session.

    google-auth on its own, not google-api-python-client: the only calls needed
    here are three REST endpoints, and the discovery machinery would be a large
    dependency on a serverless bundle for no benefit.
    """
    from google.auth.transport.requests import AuthorizedSession

    return AuthorizedSession(_credentials())


def _call(session, method, path, **kwargs):
    kwargs.setdefault("timeout", getattr(settings, "GOOGLE_CALENDAR_TIMEOUT", 10))
    try:
        return session.request(method, API_ROOT + path, **kwargs)
    except Exception as exc:  # network, token refresh, anything
        raise GoogleCalendarError("{} {} failed: {}".format(method, path, exc)) from exc


# ---------------------------------------------------------------- event body

def describe(booking):
    """The event description: what the desk needs without opening anything."""
    lines = ["Booking #{}".format(booking.pk)]

    who = booking.contact_name or "(no name)"
    lines.append("{}: {}".format("Guest" if booking.is_guest_booking else "Customer", who))
    if booking.contact_phone:
        lines.append("Phone: {}".format(booking.contact_phone))
    if booking.contact_email:
        lines.append("Email: {}".format(booking.contact_email))

    party = []
    if booking.persons_max_num:
        party.append("{} adults".format(booking.persons_max_num))
    if booking.kids_max_num:
        party.append("{} children".format(booking.kids_max_num))
    if party:
        lines.append("Party: " + ", ".join(party))

    lines.append("Status: {}".format(booking.status))
    lines.append("Total: {} SAR".format(booking.total_price))
    outstanding = booking.not_paid or 0
    paid_line = "Paid: {} SAR".format(booking.paid or 0)
    if outstanding and outstanding > 0:
        paid_line += "  |  Outstanding: {} SAR".format(outstanding)
    lines.append(paid_line)

    base = (getattr(settings, "FRONTEND_BASE_URL", "") or "").rstrip("/")
    if base:
        lines.append("\n{}/booking/{}".format(base, booking.pk))
    return "\n".join(lines)


def stay_span(booking):
    """The dates a booking holds, as one span.

    Extra dates added later belong to the same stay and extend it, so the event
    runs from the earliest start to the latest end rather than being split into
    several events the desk would have to read together. Returns None when the
    booking holds no dates at all.
    """
    stays = list(booking.dates.all())
    if not stays:
        return None
    return SimpleNamespace(
        date_from=min(s.date_from for s in stays),
        date_to=max(s.date_to for s in stays),
    )


def build_event(booking, span):
    """The Calendar event for a booking's span of dates.

    The end date is deliberately a day past ``date_to``. A stay blocks
    date_from to date_to *inclusive* -- that is what is_hut_available() enforces
    -- while an all-day Calendar event's end date is *exclusive*. Without the
    extra day Google would show the cottage free on the last blocked night and
    the desk would take a booking that cannot be honoured.
    """
    hut = booking.hut.title if booking.hut else "Cottage"
    who = booking.contact_name or "(no name)"
    settled = not (booking.not_paid and booking.not_paid > 0)
    base = (getattr(settings, "FRONTEND_BASE_URL", "") or "").rstrip("/")

    summary = "{} — {}".format(hut, who)
    if not settled:
        summary += " (balance due)"

    event = {
        "id": event_id_for(booking.pk),
        "summary": summary,
        "description": describe(booking),
        "start": {"date": span.date_from.isoformat()},
        "end": {"date": (span.date_to + timedelta(days=1)).isoformat()},
        "colorId": COLOR_PAID if settled else COLOR_OUTSTANDING,
        "transparency": "opaque",
    }
    if base:
        event["source"] = {"title": "Ken booking #{}".format(booking.pk),
                           "url": "{}/booking/{}".format(base, booking.pk)}
    return event


# ------------------------------------------------------------- entry points

def sync_booking(booking):
    """Create or update this booking's event. Never raises.

    Returns True when the calendar reflects the booking afterwards.
    """
    if not is_enabled():
        return False
    try:
        from .models import ACTIVE_BOOKING_STATUSES

        # A booking that no longer holds its dates should not hold a place on
        # the calendar either.
        if booking.status not in ACTIVE_BOOKING_STATUSES:
            return remove_booking(booking)

        span = stay_span(booking)
        if span is None:
            logger.info("Booking %s holds no dates -- nothing to put on the calendar.",
                        booking.pk)
            return False

        body = build_event(booking, span)
        session = _session()
        calendar = settings.GOOGLE_CALENDAR_ID
        path = "/calendars/{}/events/{}".format(calendar, body["id"])

        response = _call(session, "PUT", path, json=body)
        if response.status_code == 404:
            # No such event yet. Insert carries the id, so the next update finds it.
            response = _call(session, "POST",
                             "/calendars/{}/events".format(calendar), json=body)
        if response.status_code == 409:
            # The id belongs to an event Google still holds as cancelled, which
            # happens when a booking is cancelled and then reinstated. Updating
            # it revives the event in place.
            response = _call(session, "PUT", path, json=body)

        if response.status_code >= 400:
            raise GoogleCalendarError("booking {}: {} {}".format(
                booking.pk, response.status_code, response.text[:300]))

        logger.info("Booking %s synced to Google Calendar.", booking.pk)
        return True
    except Exception as exc:
        logger.warning("Google Calendar sync failed for booking %s: %s",
                       getattr(booking, "pk", "?"), exc)
        return False


def remove_booking(booking):
    """Delete this booking's event. Never raises.

    An already-absent event counts as success: the calendar ends up in the
    state the caller wanted either way.
    """
    if not is_enabled():
        return False
    try:
        response = _call(
            _session(), "DELETE",
            "/calendars/{}/events/{}".format(settings.GOOGLE_CALENDAR_ID,
                                             event_id_for(booking.pk)))
        if response.status_code in (200, 204, 404, 410):
            return True
        raise GoogleCalendarError("booking {}: {} {}".format(
            booking.pk, response.status_code, response.text[:300]))
    except Exception as exc:
        logger.warning("Google Calendar delete failed for booking %s: %s",
                       getattr(booking, "pk", "?"), exc)
        return False
