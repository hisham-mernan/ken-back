"""The Daftra invoicing flow.

One invoice per booking: raised when the first payment lands, then topped up
with a second payment when the balance is settled. The invoice must never be
duplicated, and a Daftra outage must never break a payment that already went
through.
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils.timezone import now

from .models import Booking, BookingDate, DaftraInvoice, Hut

MEDIA = tempfile.mkdtemp(prefix="ken-daftra-test-")

# Storage locally points at the live Supabase bucket, and marking a booking paid
# generates a QR, so pin storage to a temp dir for these tests.
LOCAL_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

daftra_env = override_settings(
    MEDIA_ROOT=MEDIA,
    STORAGES=LOCAL_STORAGE,
    DAFTRA_ENABLED=True,
    DAFTRA_BASE_URL="https://example-sub.daftra.com",
    DAFTRA_API_KEY="test-key-not-real",
    DAFTRA_INVOICE_LAYOUT_ID="42",
    DAFTRA_STORE_ID="0",
    DAFTRA_PAYMENT_METHOD="credit_card",
    DAFTRA_TIMEOUT=5,
    # Most tests assert on the customer-facing link, so opt in explicitly.
    DAFTRA_INVOICE_LINKS_PUBLIC=True,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeDaftra:
    """Records every call and answers the way Daftra would."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get("json")))
        if "clients.json" in url and method == "GET":
            return FakeResponse({"data": []})
        if "clients.json" in url and method == "POST":
            return FakeResponse({"id": 501})
        if "invoices.json" in url and method == "POST":
            return FakeResponse({"id": 9001})
        if "invoice_payments.json" in url:
            return FakeResponse({"id": 77})
        if "invoices/9001.json" in url:
            return FakeResponse(
                {
                    "data": {
                        "Invoice": {
                            "no": "INV-9001",
                            "invoice_html_url": "https://other.daftra.com/invoices/view/9001",
                        }
                    }
                }
            )
        return FakeResponse({}, status_code=404)

    def posted_to(self, fragment):
        return [c for c in self.calls if fragment in c[1] and c[0] == "POST"]


class DaftraFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def make_booking(self):
        hut = Hut.objects.create(title="Test Hut", description="d", size="small")
        booking = Booking.objects.create(
            hut=hut,
            status="confirmed",
            total_price=Decimal("400.00"),
            paid=Decimal("0.00"),
            not_paid=Decimal("400.00"),
            persons_max_num=2,
            kids_max_num=0,
            guest_name="Guest Booker",
            guest_email="guest@example.invalid",
            guest_phone="+966500000000",
            guest_id_num="1234567890",
        )
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

    def pay_deposit(self, booking):
        booking.paid = Decimal("200.00")
        booking.not_paid = Decimal("200.00")
        booking.status = "partially_paid"
        booking.save()

    def pay_balance(self, booking):
        booking.status = "paid"
        booking.save()

    @daftra_env
    def test_deposit_raises_one_invoice_and_balance_tops_it_up(self):
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()
            self.pay_deposit(booking)

            invoices = fake.posted_to("invoices.json")
            self.assertEqual(len(invoices), 1, "deposit must raise exactly one invoice")
            body = invoices[0][2]
            self.assertEqual(
                body["Invoice"]["invoice_layout_id"],
                "42",
                "the configured template must be used",
            )
            self.assertEqual(
                body["Payment"][0]["amount"],
                200.0,
                "the deposit must be recorded on the invoice",
            )

            record = DaftraInvoice.objects.get(booking=booking)
            self.assertEqual(record.invoice_number, "INV-9001")
            booking.refresh_from_db()
            self.assertIn("/invoices/view/9001", booking.invoice_url)
            self.assertTrue(
                booking.invoice_url.startswith("https://example-sub.daftra.com"),
                "link must point at the configured subdomain",
            )

            # Balance: same invoice, extra payment, no second invoice.
            self.pay_balance(booking)
            self.assertEqual(
                len(fake.posted_to("invoices.json")),
                1,
                "the balance must not raise a second invoice",
            )
            payments = fake.posted_to("invoice_payments.json")
            self.assertEqual(len(payments), 1)
            self.assertEqual(payments[0][2]["InvoicePayment"]["amount"], 200.0)
            self.assertEqual(DaftraInvoice.objects.filter(booking=booking).count(), 1)

    @daftra_env
    def test_both_emails_link_to_our_invoice_not_daftras(self):
        """Daftra's link needs a Daftra login, so the email points at the copy
        we serve, carrying the guest token so a guest can open it."""
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()
            mail.outbox = []
            self.pay_deposit(booking)
            deposit_mail = [m for m in mail.outbox if "Deposit received" in m.subject]
            self.assertTrue(deposit_mail, "deposit email should have been sent")

            mail.outbox = []
            self.pay_balance(booking)
            confirmations = [m for m in mail.outbox if "confirmed" in m.subject]
            self.assertTrue(confirmations, "confirmation email should have been sent")

        expected = f"/api/products/bookings/{booking.pk}/invoice.pdf"
        for label, message in (("deposit", deposit_mail[0]), ("confirmation", confirmations[0])):
            with self.subTest(email=label):
                html = message.alternatives[0][0]
                self.assertIn(expected, html)
                self.assertIn(str(booking.access_token), html,
                              "a guest needs the token to open it")
                self.assertNotIn("daftra.com", html,
                                 "must not send anyone to a Daftra sign-in")

    @daftra_env
    def test_both_emails_carry_the_invoice_pdf(self):
        """Daftra's links need a Daftra login, so the document itself travels
        with the email rather than a link to it."""
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()
            mail.outbox = []
            self.pay_deposit(booking)
            deposit = [m for m in mail.outbox if "Deposit received" in m.subject][0]

            mail.outbox = []
            self.pay_balance(booking)
            confirmation = [m for m in mail.outbox if "confirmed" in m.subject][0]

        for label, message in (("deposit", deposit), ("confirmation", confirmation)):
            with self.subTest(email=label):
                # The confirmation also carries the entry QR as a MIMEImage,
                # so attachments is a mixed list of tuples and MIME objects.
                pdfs = [
                    a for a in message.attachments
                    if isinstance(a, tuple) and str(a[0]).endswith(".pdf")
                ]
                self.assertEqual(len(pdfs), 1, f"{label} email must carry the invoice")
                self.assertTrue(pdfs[0][1].startswith(b"%PDF"))
                self.assertEqual(pdfs[0][2], "application/pdf")

    @daftra_env
    def test_configured_payment_method_reaches_both_payments(self):
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()
            self.pay_deposit(booking)
            self.pay_balance(booking)

        opening = fake.posted_to("invoices.json")[0][2]["Payment"][0]
        self.assertEqual(opening["payment_method"], "credit_card")

        balance = fake.posted_to("invoice_payments.json")[0][2]["InvoicePayment"]
        self.assertEqual(balance["payment_method"], "credit_card")

    @daftra_env
    def test_guest_booking_gets_a_daftra_client_from_its_own_details(self):
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()  # no user attached
            self.pay_deposit(booking)
        created = fake.posted_to("clients.json")
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][2]["Client"]["email"], "guest@example.invalid")

    @override_settings(
        MEDIA_ROOT=MEDIA,
        STORAGES=LOCAL_STORAGE,
        DAFTRA_ENABLED=True,
        DAFTRA_BASE_URL="https://example-sub.daftra.com",
        DAFTRA_API_KEY="test-key-not-real",
        DAFTRA_PAYMENT_METHOD="manual_payment_1",
        DAFTRA_TIMEOUT=5,
        DAFTRA_INVOICE_LINKS_PUBLIC=False,
    )
    def test_link_is_withheld_from_customers_until_it_is_viewable(self):
        """Daftra's links redirect to a sign-in page unless the account exposes
        them, and a guest has no Daftra account. The invoice is still raised
        and recorded for staff -- only the customer-facing link is held back."""
        fake = FakeDaftra()
        with patch("products.daftra.requests.request", side_effect=fake):
            booking = self.make_booking()
            mail.outbox = []
            self.pay_deposit(booking)

        self.assertEqual(len(fake.posted_to("invoices.json")), 1,
                         "the invoice must still be raised in Daftra")
        record = DaftraInvoice.objects.get(booking=booking)
        self.assertTrue(record.invoice_url, "staff record must keep the link")

        booking.refresh_from_db()
        self.assertFalse(booking.invoice_url, "customers must not get a sign-in link")
        for message in mail.outbox:
            self.assertNotIn("daftra.com", message.alternatives[0][0])

    @daftra_env
    def test_daftra_outage_does_not_break_the_payment(self):
        import requests as requests_module

        with patch(
            "products.daftra.requests.request",
            side_effect=requests_module.RequestException("connection refused"),
        ):
            booking = self.make_booking()
            self.pay_deposit(booking)
            self.pay_balance(booking)

        booking.refresh_from_db()
        self.assertEqual(
            booking.status, "paid", "payment must stand even if invoicing fails"
        )
        self.assertFalse(DaftraInvoice.objects.filter(booking=booking).exists())

    @override_settings(
        MEDIA_ROOT=MEDIA, STORAGES=LOCAL_STORAGE, DAFTRA_ENABLED=False
    )
    def test_nothing_is_called_when_daftra_is_not_configured(self):
        with patch("products.daftra.requests.request") as request:
            booking = self.make_booking()
            self.pay_deposit(booking)
            self.pay_balance(booking)
        request.assert_not_called()
        booking.refresh_from_db()
        self.assertEqual(booking.status, "paid")
