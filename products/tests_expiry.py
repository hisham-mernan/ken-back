"""Releasing dates held by a booking that was never paid for.

The rule that matters most is the one the old threading.Timer got wrong: a
booking with money against it is never cancelled, whatever its status says.
Booking #16 sat fully paid while still marked "confirmed", and that timer
would have cancelled it.
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Booking, BookingDate, Hut


class ExpireUnpaidBookingsTests(TestCase):
    def setUp(self):
        self.hut = Hut.objects.create(title="Qimmah Cottage (Large)", description="d",
                                      size="large", max_persons_num=8, max_kids_num=4)

    def make(self, *, status="confirmed", paid="0.00", held_minutes_ago=120):
        booking = Booking.objects.create(
            hut=self.hut, status=status, total_price=Decimal("1000.00"),
            paid=Decimal(paid), not_paid=Decimal("1000.00") - Decimal(paid),
            persons_max_num=2, kids_max_num=0,
            guest_name="Abandoned Checkout", guest_email="a@example.invalid",
            guest_phone="0500000009")
        start = timezone.localdate() + timedelta(days=40)
        BookingDate.objects.create(booking=booking, date_from=start,
                                   date_to=start + timedelta(days=2))
        # Set both stamps directly: auto_now_add would otherwise pin them to now.
        held = timezone.now() - timedelta(minutes=held_minutes_ago)
        Booking.objects.filter(pk=booking.pk).update(confirmed_at=held, created_at=held)
        return booking

    def run_command(self, **kwargs):
        out = StringIO()
        call_command("expire_unpaid_bookings", stdout=out, **kwargs)
        return out.getvalue()

    def status_of(self, booking):
        return Booking.objects.get(pk=booking.pk).status

    def test_an_abandoned_hold_is_released(self):
        booking = self.make()
        self.run_command()
        self.assertEqual(self.status_of(booking), "cancelled")

    def test_a_paid_booking_still_labelled_confirmed_is_never_touched(self):
        """This is booking #16. The old timer would have cancelled it."""
        booking = self.make(status="confirmed", paid="1000.00")
        self.run_command()
        self.assertEqual(self.status_of(booking), "confirmed")

    def test_a_deposit_holds_the_dates(self):
        booking = self.make(status="confirmed", paid="500.00")
        self.run_command()
        self.assertEqual(self.status_of(booking), "confirmed")

    def test_a_hold_inside_the_window_is_left_alone(self):
        booking = self.make(held_minutes_ago=5)
        self.run_command()
        self.assertEqual(self.status_of(booking), "confirmed")

    def test_the_window_is_thirty_minutes_which_is_what_the_guest_is_told(self):
        just_inside = self.make(held_minutes_ago=25)
        just_outside = self.make(held_minutes_ago=35)
        self.run_command()
        self.assertEqual(self.status_of(just_inside), "confirmed")
        self.assertEqual(self.status_of(just_outside), "cancelled")

    def test_paid_and_pending_bookings_are_not_its_business(self):
        paid = self.make(status="paid", paid="1000.00")
        pending = self.make(status="pending")
        self.run_command()
        self.assertEqual(self.status_of(paid), "paid")
        self.assertEqual(self.status_of(pending), "pending")

    def test_dry_run_changes_nothing(self):
        booking = self.make()
        output = self.run_command(dry_run=True)
        self.assertIn("dry run", output.lower())
        self.assertEqual(self.status_of(booking), "confirmed")

    def test_older_bookings_without_a_confirmed_stamp_still_expire(self):
        """confirmed_at was added late; the ones already stuck have none."""
        booking = self.make()
        Booking.objects.filter(pk=booking.pk).update(confirmed_at=None)
        self.run_command()
        self.assertEqual(self.status_of(booking), "cancelled")

    def test_released_dates_can_be_booked_again(self):
        from .utils import is_hut_available

        booking = self.make()
        held = booking.dates.first()
        available, _ = is_hut_available(self.hut.id, held.date_from, held.date_to, None)
        self.assertFalse(available, "the hold should block the dates first")

        self.run_command()
        available, _ = is_hut_available(self.hut.id, held.date_from, held.date_to, None)
        self.assertTrue(available, "cancelling should hand the dates back")
