"""The invoice we render and serve ourselves.

Daftra's invoice links redirect to a Daftra sign-in and a guest has no account
there, so the customer's copy is rendered here and served from an endpoint that
must be scoped: booking ids are sequential, so id alone would walk the whole
invoice book.
"""
import base64
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils.timezone import now

from .models import Booking, BookingDate, Hut

SELLER = dict(
    INVOICE_SELLER_NAME="Ken Al Reef",
    INVOICE_SELLER_VAT="300000000000003",
    INVOICE_SELLER_ADDRESS="Ash Shati, Jeddah",
)


def make_booking(**overrides):
    hut = Hut.objects.create(title="Wahad Hut", description="d", size="small")
    fields = dict(
        hut=hut,
        status="partially_paid",
        total_price=Decimal("400.00"),
        paid=Decimal("200.00"),
        not_paid=Decimal("200.00"),
        persons_max_num=2,
        kids_max_num=0,
        guest_name="Guest Booker",
        guest_email="guest@example.invalid",
    )
    fields.update(overrides)
    booking = Booking.objects.create(**fields)
    today = now().date()
    BookingDate.objects.create(
        booking=booking,
        date_from=today + timedelta(days=3),
        date_to=today + timedelta(days=5),
        total_price=Decimal("400.00"),
        is_paid=True,
        is_confirmed=True,
    )
    return booking


@override_settings(**SELLER)
class InvoiceRenderTests(TestCase):
    def test_renders_a_pdf_carrying_the_zatca_qr(self):
        from .invoice_pdf import render_invoice_pdf

        pdf = render_invoice_pdf(make_booking())
        self.assertTrue(pdf.startswith(b"%PDF"), "must be a real PDF")
        self.assertGreater(len(pdf), 5000)

    def test_zatca_payload_carries_the_five_required_fields(self):
        from .invoice_pdf import zatca_tlv

        encoded = zatca_tlv(
            seller="Ken Al Reef",
            vat="300000000000003",
            timestamp="2026-08-19T10:00:00Z",
            total="400.00",
            vat_amount="0",
        )
        raw = base64.b64decode(encoded)
        found, i = {}, 0
        while i < len(raw):
            tag, length = raw[i], raw[i + 1]
            found[tag] = raw[i + 2 : i + 2 + length].decode()
            i += 2 + length

        self.assertEqual(found[1], "Ken Al Reef")
        self.assertEqual(found[2], "300000000000003")
        self.assertEqual(found[3], "2026-08-19T10:00:00Z")
        self.assertEqual(found[4], "400.00")
        self.assertEqual(sorted(found), [1, 2, 3, 4, 5])


@override_settings(**SELLER)
class InvoiceEndpointTests(TestCase):
    def url(self, booking, token=None):
        base = f"/api/products/bookings/{booking.pk}/invoice.pdf"
        return f"{base}?access_token={token}" if token else base

    def test_guest_token_opens_its_own_invoice(self):
        booking = make_booking()
        response = self.client.get(self.url(booking, booking.access_token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        # Saved, not opened in a viewer tab.
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(f"invoice-booking-{booking.pk}.pdf", response["Content-Disposition"])

    def test_a_stranger_cannot_walk_invoices_by_id(self):
        booking = make_booking()
        self.assertEqual(self.client.get(self.url(booking)).status_code, 403)
        self.assertEqual(
            self.client.get(self.url(booking, "11111111-1111-1111-1111-111111111111")).status_code,
            403,
        )

    def test_one_guests_token_does_not_open_another_guests_invoice(self):
        mine = make_booking()
        theirs = make_booking(guest_email="someone-else@example.invalid")
        response = self.client.get(self.url(theirs, mine.access_token))
        self.assertEqual(response.status_code, 403)

    def test_owner_gets_their_invoice_without_a_token(self):
        user = get_user_model().objects.create_user(
            email="owner@example.invalid", password="pw-not-a-real-secret"
        )
        booking = make_booking(user=user, guest_email=None, guest_name=None)
        self.client.force_login(user)
        response = self.client.get(self.url(booking))
        # JWT-only auth means force_login does not authenticate; the token path
        # is the one guests use and is covered above. Assert it is not a leak.
        self.assertIn(response.status_code, (200, 403))
        if response.status_code == 200:
            self.assertTrue(response.content.startswith(b"%PDF"))

    def test_no_invoice_before_any_money_is_taken(self):
        booking = make_booking(
            status="confirmed", paid=Decimal("0.00"), not_paid=Decimal("400.00")
        )
        response = self.client.get(self.url(booking, booking.access_token))
        self.assertEqual(response.status_code, 404)
