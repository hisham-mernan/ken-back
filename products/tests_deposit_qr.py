"""Regression tests for the deposit flow.

The bug these cover: the booking serializers generated a QR code on the fly for
any booking that lacked one. Merely *viewing* the payment or results page after
a 50% deposit minted a working entry pass and persisted it to storage and the
database, so a guest who had paid half could walk in.
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils.timezone import now

from .models import Booking, BookingDate, Hut
from .serializers import (
    BookingForPaymnetSerializer,
    GuestBookingSerializer,
    UpComingBookingSerializer,
)

MEDIA = tempfile.mkdtemp(prefix="ken-test-media-")

# Storage locally points at the live Supabase bucket, so pin it to a temp dir:
# these tests assert on files actually written, and must never touch production.
local_storage = override_settings(
    MEDIA_ROOT=MEDIA,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
)


@local_storage
class DepositQrTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="deposit-test@example.com", password="pw-not-a-real-secret"
        )
        self.hut = Hut.objects.create(
            title="Test Hut", description="d", size="small"
        )

    def make_booking(self, status, paid, not_paid):
        booking = Booking.objects.create(
            user=self.user, hut=self.hut, status=status,
            total_price=Decimal("5.00"), paid=paid, not_paid=not_paid,
            persons_max_num=2, kids_max_num=0,
        )
        today = now().date()
        BookingDate.objects.create(
            booking=booking, date_from=today + timedelta(days=3),
            date_to=today + timedelta(days=5), total_price=Decimal("5.00"),
            is_paid=True, is_confirmed=True,
        )
        return booking

    def files_written(self):
        import os
        found = []
        for root, _dirs, names in os.walk(MEDIA):
            found.extend(names)
        return found

    def test_deposit_yields_no_qr_and_writes_no_file(self):
        booking = self.make_booking(
            "partially_paid", Decimal("2.50"), Decimal("2.50")
        )
        for serializer in (
            UpComingBookingSerializer,
            BookingForPaymnetSerializer,
            GuestBookingSerializer,
        ):
            with self.subTest(serializer=serializer.__name__):
                data = serializer(booking).data
                self.assertIsNone(
                    data.get("qr_code_image"),
                    f"{serializer.__name__} handed out a QR for a deposit",
                )

        booking.refresh_from_db()
        self.assertFalse(booking.is_qr_genereated)
        self.assertFalse(booking.qr_code_image)
        self.assertEqual(
            self.files_written(), [],
            "serializing a deposit booking wrote a QR file to storage",
        )

    def test_paid_booking_still_gets_its_qr(self):
        booking = self.make_booking("paid", Decimal("5.00"), Decimal("0.00"))
        data = UpComingBookingSerializer(booking).data
        self.assertTrue(
            data.get("qr_code_image"), "a fully paid booking must get its QR"
        )


@local_storage
class DepositVisibleToOwnerTests(TestCase):
    """A deposit holds the dates, so the owner must still see the booking."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="deposit-list@example.com", password="pw-not-a-real-secret"
        )
        self.hut = Hut.objects.create(
            title="Test Hut", description="d", size="small"
        )
        self.booking = Booking.objects.create(
            user=self.user, hut=self.hut, status="partially_paid",
            total_price=Decimal("5.00"), paid=Decimal("2.50"),
            not_paid=Decimal("2.50"), persons_max_num=2, kids_max_num=0,
        )
        today = now().date()
        BookingDate.objects.create(
            booking=self.booking, date_from=today + timedelta(days=3),
            date_to=today + timedelta(days=5), total_price=Decimal("5.00"),
            is_paid=True, is_confirmed=True,
        )

    def test_upcoming_list_includes_partially_paid(self):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from .views import UpcomingBookingsView

        request = APIRequestFactory().get("/upcoming/")
        force_authenticate(request, user=self.user)
        response = UpcomingBookingsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("id"), self.booking.id)
        self.assertEqual(response.data.get("status"), "partially_paid")
        self.assertEqual(str(response.data.get("not_paid")), "2.50")
        self.assertIsNone(
            response.data.get("qr_code_image"),
            "the bookings list handed out a QR for a deposit",
        )
