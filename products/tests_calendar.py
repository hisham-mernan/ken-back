"""The occupancy calendar behind the dashboard home page."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Booking, BookingDate, Hut


class CalendarTests(TestCase):
    def setUp(self):
        self.hut = Hut.objects.create(title="Qimmah Cottage (Large)", description="d",
                                      size="large", max_persons_num=8, max_kids_num=4)
        self.admin = get_user_model().objects.create_user(
            email="desk@example.invalid", password="pw-not-a-real-secret")
        self.admin.role = "admin"
        self.admin.is_staff = True
        self.admin.save()
        self.url = "/api/products/admin/calendar/"

    def book(self, start, nights, status="paid", **extra):
        booking = Booking.objects.create(
            hut=self.hut, status=status, total_price=Decimal("400.00"),
            paid=Decimal("400.00"), not_paid=Decimal("0.00"),
            persons_max_num=2, kids_max_num=0,
            guest_name=extra.get("name", "Guest Booker"),
            guest_email="g@example.invalid", guest_phone="0500000001")
        BookingDate.objects.create(booking=booking, date_from=start,
                                   date_to=start + timedelta(days=nights))
        return booking

    def get(self, **params):
        # Auth here is JWT only, so force_login proves nothing -- mint a real
        # token, or these tests quietly skip and cover none of the endpoint.
        from accounts.utils import generate_jwt_token

        token = generate_jwt_token(self.admin)
        if isinstance(token, dict):
            token = token.get("access") or token.get("token")
        return self.client.get(self.url, params,
                               HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_a_stranger_cannot_read_the_book(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_returns_stays_with_the_client_on_them(self):
        soon = date.today() + timedelta(days=10)
        self.book(soon, 2, name="Estelle Darcy")
        response = self.get()
        self.assertEqual(response.status_code, 200)
        stay = response.json()["stays"][0]
        self.assertEqual(stay["customer"], "Estelle Darcy")
        self.assertEqual(stay["phone"], "0500000001")
        self.assertTrue(stay["is_guest"])
        self.assertEqual(stay["hut"], self.hut.id)

    def test_pending_bookings_do_not_occupy_the_calendar(self):
        """They hold no dates, so showing them booked turns away real custom."""
        soon = date.today() + timedelta(days=20)
        self.book(soon, 2, status="pending")
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stays"], [])

    def test_window_covers_whole_months_and_excludes_what_falls_outside(self):
        inside = date.today().replace(day=1) + timedelta(days=40)
        outside = date.today().replace(day=1) + timedelta(days=800)
        self.book(inside, 1, name="Inside")
        self.book(outside, 1, name="Outside")
        response = self.get(months=12)
        self.assertEqual(response.status_code, 200)
        names = [s["customer"] for s in response.json()["stays"]]
        self.assertIn("Inside", names)
        self.assertNotIn("Outside", names)
