"""Daftra invoicing for bookings.

One invoice per booking. It is raised the first time money is taken and later
payments are appended to that same invoice, so a deposit leaves it partially
paid and the balance payment brings it to fully paid. That is why
``sync_booking_invoice`` is idempotent on creation but additive on payment.

Every entry point here is best-effort and never raises: by the time these run
the customer's card has already been charged, so a Daftra outage must not fail
the booking or the payment. Failures are logged and the booking simply carries
no invoice until the next attempt.
"""
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class DaftraError(Exception):
    """A Daftra call failed. Raised internally, never escapes this module."""


def is_enabled():
    return bool(getattr(settings, "DAFTRA_ENABLED", False))


class DaftraClient:
    """Thin wrapper over the Daftra api2 endpoints this project needs."""

    def __init__(self):
        self.base_url = settings.DAFTRA_BASE_URL
        self.timeout = settings.DAFTRA_TIMEOUT
        self.headers = {
            "APIKEY": settings.DAFTRA_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _call(self, method, path, **kwargs):
        url = f"{self.base_url}/api2/{path.lstrip('/')}"
        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise DaftraError(f"{method} {path} failed: {exc}") from exc

        if response.status_code >= 400:
            # Body carries Daftra's own validation messages, which are the only
            # useful signal when a layout or client id is wrong.
            raise DaftraError(
                f"{method} {path} returned {response.status_code}: {response.text[:400]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise DaftraError(f"{method} {path} returned non-JSON body") from exc

    # ------------------------------------------------------------------ clients

    def find_client_id(self, email):
        """Existing Daftra client for this email, or None."""
        if not email:
            return None
        data = self._call("GET", "clients.json", params={"filter[email]": email})
        for row in _rows(data):
            client = row.get("Client") or row
            if str(client.get("email") or "").lower() == email.lower():
                return client.get("id")
        return None

    def create_client(self, *, email, name, phone=None):
        payload = {
            "Client": {
                "business_name": name or email,
                "email": email,
                "phone1": phone or "",
                "country_code": "SA",
            }
        }
        data = self._call("POST", "clients.json", json=payload)
        return data.get("id") or (data.get("data") or {}).get("id")

    def ensure_client(self, *, email, name, phone=None):
        return self.find_client_id(email) or self.create_client(
            email=email, name=name, phone=phone
        )

    # ----------------------------------------------------------------- invoices

    def create_invoice(self, *, client_id, items, date, notes, payments):
        invoice = {
            "client_id": client_id,
            "type": 0,
            "draft": False,
            "currency_code": "SAR",
            "date": date,
            "notes": notes,
            "store_id": settings.DAFTRA_STORE_ID,
        }
        # Omitted entirely when unset so Daftra falls back to the account's
        # default layout rather than rejecting a null id.
        if settings.DAFTRA_INVOICE_LAYOUT_ID:
            invoice["invoice_layout_id"] = settings.DAFTRA_INVOICE_LAYOUT_ID

        payload = {"Invoice": invoice, "InvoiceItem": items}
        if payments:
            payload["Payment"] = payments
        data = self._call("POST", "invoices.json", json=payload)
        return data.get("id") or (data.get("data") or {}).get("id")

    def add_payment(self, *, invoice_id, amount, transaction_id=""):
        payload = {
            "InvoicePayment": {
                "invoice_id": invoice_id,
                "amount": float(amount),
                "payment_method": settings.DAFTRA_PAYMENT_METHOD,
                "transaction_id": transaction_id or "",
                "date": timezone.now().date().isoformat(),
            }
        }
        return self._call("POST", "invoice_payments.json", json=payload)

    def get_invoice(self, invoice_id):
        return self._call("GET", f"invoices/{invoice_id}.json")


def _rows(payload):
    """Daftra wraps list results inconsistently; yield whatever rows exist."""
    if isinstance(payload, list):
        return payload
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        return data
    return []


def _invoice_urls(details, base_url, invoice_id):
    """Pull the viewable and PDF links out of an invoice detail response."""
    invoice = ((details or {}).get("data") or {}).get("Invoice") or {}
    number = invoice.get("no") or invoice.get("invoice_number") or str(invoice_id)
    html_url = invoice.get("invoice_html_url") or ""
    # Daftra returns an absolute URL on a different host in some accounts; keep
    # only the path so the link always points at the configured subdomain.
    if "/invoices" in html_url:
        html_url = base_url + html_url[html_url.index("/invoices"):]
    else:
        html_url = f"{base_url}/invoices/view/{invoice_id}"
    pdf_url = html_url if html_url.endswith(".pdf") else f"{html_url}.pdf"
    return str(number), html_url, pdf_url


def build_invoice_items(booking):
    """Line items for a booking, priced exactly as the dashboard prices them.

    Reuses the admin order serializer rather than recomputing rates, so an
    invoice can never disagree with the order it bills for.
    """
    from .serializers import BookingDetailsAdminSerializer

    data = BookingDetailsAdminSerializer(booking).data
    rows = list(data.get("main_order") or []) + list(data.get("extra_order") or [])

    items = []
    for row in rows:
        quantity = row.get("quantity") or 1
        items.append(
            {
                "item": row.get("title") or f"Booking #{booking.pk}",
                "description": row.get("title_ar") or "",
                "unit_price": float(row.get("price") or 0),
                "quantity": quantity,
            }
        )

    if not items:
        # Never raise an empty invoice: bill the booking as a single line so the
        # customer still gets a document that matches what they paid.
        items = [
            {
                "item": f"Booking #{booking.pk}",
                "description": booking.hut.title if booking.hut else "",
                "unit_price": float(booking.total_price or 0),
                "quantity": 1,
            }
        ]
    return items


def sync_booking_invoice(booking, *, amount, transaction_id=""):
    """Raise or update this booking's invoice for a payment that just landed.

    First call creates the invoice with the payment on it; later calls append a
    payment to the same invoice, which is what turns a 50% invoice into a fully
    paid one. Returns the DaftraInvoice row, or None if anything went wrong.
    """
    from .models import DaftraInvoice

    if not is_enabled():
        logger.debug("Daftra not configured; skipping invoice for booking %s", booking.pk)
        return None

    amount = Decimal(str(amount or 0))
    client = DaftraClient()

    try:
        record = DaftraInvoice.objects.filter(booking=booking).first()

        if record is None:
            email = (booking.contact_email or "").strip()
            client_id = client.ensure_client(
                email=email,
                name=booking.contact_name or email,
                phone=booking.contact_phone,
            )
            main_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
            date = (main_date.date_from if main_date else timezone.now().date()).isoformat()

            payments = []
            if amount > 0:
                payments = [
                    {
                        "payment_method": settings.DAFTRA_PAYMENT_METHOD,
                        "amount": float(amount),
                        "transaction_id": transaction_id or "",
                        "date": timezone.now().date().isoformat(),
                    }
                ]

            invoice_id = client.create_invoice(
                client_id=client_id,
                items=build_invoice_items(booking),
                date=date,
                notes=f"Booking #{booking.pk}",
                payments=payments,
            )
            if not invoice_id:
                raise DaftraError("invoice created but no id returned")

            record = DaftraInvoice.objects.create(
                booking=booking,
                daftra_id=str(invoice_id),
                invoice_number=str(invoice_id),
            )
        elif amount > 0:
            client.add_payment(
                invoice_id=record.daftra_id,
                amount=amount,
                transaction_id=transaction_id,
            )

        number, html_url, pdf_url = _invoice_urls(
            _safe_details(client, record.daftra_id),
            settings.DAFTRA_BASE_URL,
            record.daftra_id,
        )
        record.invoice_number = number
        record.invoice_url = html_url
        record.pdf_url = pdf_url
        record.save(update_fields=["invoice_number", "invoice_url", "pdf_url"])

        # Mirrored onto the booking so existing serializers expose it without
        # every caller needing to know about DaftraInvoice.
        type(booking).objects.filter(pk=booking.pk).update(invoice_url=html_url)
        booking.invoice_url = html_url
        return record

    except DaftraError as exc:
        logger.warning("Daftra invoice sync failed for booking %s: %s", booking.pk, exc)
        return None
    except Exception as exc:  # noqa: BLE001 - invoicing must never break payment
        logger.exception("Unexpected Daftra failure for booking %s: %s", booking.pk, exc)
        return None


def _safe_details(client, invoice_id):
    try:
        return client.get_invoice(invoice_id)
    except DaftraError as exc:
        logger.warning("Could not read back Daftra invoice %s: %s", invoice_id, exc)
        return {}
