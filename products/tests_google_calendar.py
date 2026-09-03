"""Putting bookings on a Google Calendar.

The rule that matters most is the one all-day calendar events get wrong: a
stay blocks date_from to date_to *inclusive*, while a Calendar event's end date
is *exclusive*. Off by one here and the desk sees a cottage free on a night it
is not.

The second rule is that nothing in this integration may fail a booking. The
calls are mocked throughout -- these tests never touch Google.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from .models import Booking, BookingDate, Hut
from . import google_calendar


class _Response:
    """Just enough of requests.Response for these paths."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


ENABLED = dict(
    GOOGLE_CALENDAR_ENABLED=True,
    GOOGLE_CALENDAR_ID="ken@group.calendar.google.com",
    GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account"}',
    FRONTEND_BASE_URL="https://www.kenluxuryreef.com",
)


class GoogleCalendarTests(TestCase):
    def setUp(self):
        self.hut = Hut.objects.create(title="Qimmah Cottage (Large)", description="d",
                                      size="large", max_persons_num=8, max_kids_num=4,
                                      weekday_price=Decimal("1450.00"),
                                      weekend_price=Decimal("1650.00"))

    def make(self, *, status="paid", paid="1000.00", not_paid="0.00",
             start=None, nights=2):
        booking = Booking.objects.create(
            hut=self.hut, status=status, total_price=Decimal("1000.00"),
            paid=Decimal(paid), not_paid=Decimal(not_paid),
            persons_max_num=4, kids_max_num=2,
            guest_name="Ahmed Al-Otaibi", guest_email="a@example.invalid",
            guest_phone="0500000003")
        start = start or date(2026, 9, 20)
        BookingDate.objects.create(booking=booking, date_from=start,
                                   date_to=start + timedelta(days=nights))
        return booking

    # ------------------------------------------------------------ event body

    def test_the_event_ends_a_day_after_the_last_blocked_day(self):
        """The whole point. date_to is blocked, so DTEND must be the day after."""
        booking = self.make(start=date(2026, 9, 20), nights=2)
        event = google_calendar.build_event(booking,
                                            google_calendar.stay_span(booking))
        self.assertEqual(event["start"]["date"], "2026-09-20")
        self.assertEqual(event["end"]["date"], "2026-09-23",
                         "22nd is blocked, so the exclusive end is the 23rd")

    def test_a_single_day_booking_still_spans_a_day(self):
        booking = self.make(start=date(2026, 9, 20), nights=0)
        event = google_calendar.build_event(booking,
                                            google_calendar.stay_span(booking))
        self.assertEqual(event["start"]["date"], "2026-09-20")
        self.assertEqual(event["end"]["date"], "2026-09-21")

    def test_extra_dates_extend_one_event_rather_than_making_another(self):
        booking = self.make(start=date(2026, 9, 20), nights=2)
        BookingDate.objects.create(booking=booking, date_from=date(2026, 9, 23),
                                   date_to=date(2026, 9, 25), is_extra=True)
        span = google_calendar.stay_span(booking)
        self.assertEqual(span.date_from, date(2026, 9, 20))
        self.assertEqual(span.date_to, date(2026, 9, 25))

    def test_a_booking_holding_no_dates_has_no_span(self):
        booking = self.make()
        booking.dates.all().delete()
        self.assertIsNone(google_calendar.stay_span(booking))

    @override_settings(**ENABLED)
    def test_an_outstanding_balance_is_visible_in_the_title(self):
        booking = self.make(status="partially_paid", paid="500.00", not_paid="500.00")
        event = google_calendar.build_event(booking,
                                            google_calendar.stay_span(booking))
        self.assertIn("balance due", event["summary"])
        self.assertEqual(event["colorId"], google_calendar.COLOR_OUTSTANDING)

    @override_settings(**ENABLED)
    def test_a_settled_booking_is_not_flagged(self):
        booking = self.make(status="paid", paid="1000.00", not_paid="0.00")
        event = google_calendar.build_event(booking,
                                            google_calendar.stay_span(booking))
        self.assertNotIn("balance due", event["summary"])
        self.assertEqual(event["colorId"], google_calendar.COLOR_PAID)

    @override_settings(**ENABLED)
    def test_the_description_carries_what_the_desk_needs(self):
        booking = self.make()
        text = google_calendar.describe(booking)
        for expected in ("Booking #{}".format(booking.pk), "Ahmed Al-Otaibi",
                         "0500000003", "4 adults", "2 children"):
            self.assertIn(expected, text)

    def test_the_event_id_is_derived_from_the_booking(self):
        self.assertEqual(google_calendar.event_id_for(16), "kenbooking16")

    def test_the_event_id_is_valid_base32hex(self):
        """Google rejects anything outside 0-9 and a-v."""
        allowed = set("0123456789abcdefghijklmnopqrstuv")
        self.assertTrue(set(google_calendar.event_id_for(12345)) <= allowed)

    # -------------------------------------------------------------- dormancy

    @override_settings(GOOGLE_CALENDAR_ENABLED=False)
    def test_nothing_is_called_when_it_is_not_configured(self):
        booking = self.make()
        with patch.object(google_calendar, "_session") as session:
            self.assertFalse(google_calendar.sync_booking(booking))
            self.assertFalse(google_calendar.remove_booking(booking))
        session.assert_not_called()

    # ------------------------------------------------------------- behaviour

    @override_settings(**ENABLED)
    def test_an_existing_event_is_updated_in_place(self):
        booking = self.make()
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call",
                          return_value=_Response(200)) as call:
            self.assertTrue(google_calendar.sync_booking(booking))
        self.assertEqual(call.call_args[0][1], "PUT")

    @override_settings(**ENABLED)
    def test_a_missing_event_is_created(self):
        booking = self.make()
        responses = [_Response(404), _Response(200)]
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call",
                          side_effect=responses) as call:
            self.assertTrue(google_calendar.sync_booking(booking))
        self.assertEqual([c[0][1] for c in call.call_args_list], ["PUT", "POST"])

    @override_settings(**ENABLED)
    def test_a_reinstated_booking_revives_its_cancelled_event(self):
        """Google keeps a deleted id reserved, answering 409 to a fresh insert."""
        booking = self.make()
        responses = [_Response(404), _Response(409), _Response(200)]
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call",
                          side_effect=responses) as call:
            self.assertTrue(google_calendar.sync_booking(booking))
        self.assertEqual([c[0][1] for c in call.call_args_list],
                         ["PUT", "POST", "PUT"])

    @override_settings(**ENABLED)
    def test_a_cancelled_booking_is_taken_off_the_calendar(self):
        booking = self.make(status="cancelled")
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call",
                          return_value=_Response(204)) as call:
            self.assertTrue(google_calendar.sync_booking(booking))
        self.assertEqual(call.call_args[0][1], "DELETE")

    @override_settings(**ENABLED)
    def test_deleting_an_event_that_is_already_gone_is_success(self):
        booking = self.make()
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call", return_value=_Response(404)):
            self.assertTrue(google_calendar.remove_booking(booking))

    # ---------------------------------------------------------- never raises

    @override_settings(**ENABLED)
    def test_an_outage_does_not_reach_the_caller(self):
        booking = self.make()
        with patch.object(google_calendar, "_session",
                          side_effect=RuntimeError("Google is down")):
            self.assertFalse(google_calendar.sync_booking(booking))
            self.assertFalse(google_calendar.remove_booking(booking))

    @override_settings(**ENABLED)
    def test_a_rejected_write_does_not_reach_the_caller(self):
        booking = self.make()
        with patch.object(google_calendar, "_session"), \
             patch.object(google_calendar, "_call",
                          return_value=_Response(403, text="forbidden")):
            self.assertFalse(google_calendar.sync_booking(booking))

    @override_settings(**ENABLED)
    def test_bad_credentials_do_not_reach_the_caller(self):
        booking = self.make()
        with override_settings(GOOGLE_SERVICE_ACCOUNT_JSON="not json at all"):
            self.assertFalse(google_calendar.sync_booking(booking))

    # ------------------------------------------------------------ the signal
    #
    # The handlers defer to transaction.on_commit so a checkout that rolls back
    # leaves no event behind. TestCase wraps each test in a transaction that is
    # never committed, so without captureOnCommitCallbacks nothing would run --
    # and the "pushes nothing" tests below would pass while proving nothing.

    @override_settings(**ENABLED)
    def test_confirming_a_booking_pushes_it(self):
        booking = self.make(status="pending")
        with patch.object(google_calendar, "sync_booking",
                          return_value=True) as sync:
            with self.captureOnCommitCallbacks(execute=True):
                booking.status = "paid"
                booking.save()
        sync.assert_called()

    @override_settings(**ENABLED)
    def test_cancelling_a_booking_removes_it(self):
        booking = self.make(status="paid")
        with patch.object(google_calendar, "remove_booking",
                          return_value=True) as remove:
            with self.captureOnCommitCallbacks(execute=True):
                booking.status = "cancelled"
                booking.save()
        remove.assert_called()

    @override_settings(**ENABLED)
    def test_saving_a_booking_unchanged_pushes_nothing(self):
        booking = self.make(status="paid")
        with patch.object(google_calendar, "sync_booking") as sync:
            with self.captureOnCommitCallbacks(execute=True):
                booking.save()
        sync.assert_not_called()

    @override_settings(**ENABLED)
    def test_a_pending_booking_is_never_pushed(self):
        with patch.object(google_calendar, "sync_booking") as sync:
            with self.captureOnCommitCallbacks(execute=True):
                self.make(status="pending")
        sync.assert_not_called()

    @override_settings(**ENABLED)
    def test_deleting_a_booking_takes_its_event_off_the_calendar(self):
        """Deleting a row fires no status change, so it needs its own handler."""
        booking = self.make(status="paid")
        pk = booking.pk
        with patch.object(google_calendar, "remove_booking",
                          return_value=True) as remove:
            with self.captureOnCommitCallbacks(execute=True):
                booking.delete()
        remove.assert_called()
        self.assertEqual(remove.call_args[0][0].pk, pk)

    @override_settings(**ENABLED)
    def test_adding_an_extra_night_pushes_the_new_span(self):
        booking = self.make(status="paid")
        with patch.object(google_calendar, "sync_booking",
                          return_value=True) as sync:
            with self.captureOnCommitCallbacks(execute=True):
                BookingDate.objects.create(booking=booking,
                                           date_from=date(2026, 9, 23),
                                           date_to=date(2026, 9, 24), is_extra=True)
        sync.assert_called()
