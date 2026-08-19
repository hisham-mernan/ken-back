"""Verify the Daftra configuration without touching a booking.

Answers the two questions you cannot answer from the code alone: is the API key
accepted, and which invoice layout id should DAFTRA_INVOICE_LAYOUT_ID be set to.

Read-only. It never creates a client, an invoice or a payment.
"""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check Daftra credentials and list the invoice layouts you can use."

    def handle(self, *args, **options):
        ok = self.style.SUCCESS
        warn = self.style.WARNING
        bad = self.style.ERROR

        self.stdout.write("Configuration")
        base = getattr(settings, "DAFTRA_BASE_URL", "")
        key = getattr(settings, "DAFTRA_API_KEY", "")
        layout = getattr(settings, "DAFTRA_INVOICE_LAYOUT_ID", None)

        self.stdout.write(f"  DAFTRA_BASE_URL          {base or bad('not set')}")
        # Never print the key itself, only enough to tell which one is loaded.
        self.stdout.write(
            f"  DAFTRA_API_KEY           {ok(f'set ({len(key)} chars)') if key else bad('not set')}"
        )
        self.stdout.write(f"  DAFTRA_INVOICE_LAYOUT_ID {layout or warn('not set (account default will be used)')}")
        self.stdout.write(f"  DAFTRA_STORE_ID          {getattr(settings, 'DAFTRA_STORE_ID', '')}")
        self.stdout.write(f"  DAFTRA_PAYMENT_METHOD    {getattr(settings, 'DAFTRA_PAYMENT_METHOD', '')}")

        if not (base and key):
            self.stdout.write(
                bad("\nDaftra is dormant: set DAFTRA_BASE_URL and DAFTRA_API_KEY, then re-run.")
            )
            return

        from products.daftra import DaftraClient, DaftraError

        client = DaftraClient()

        self.stdout.write("\nAuthentication")
        try:
            client._call("GET", "clients.json", params={"limit": "1"})
            self.stdout.write(ok("  the API key was accepted"))
        except DaftraError as exc:
            self.stdout.write(bad(f"  rejected: {exc}"))
            self.stdout.write(
                warn("  Check the key and that the subdomain matches the account it belongs to.")
            )
            return

        self.stdout.write(
            "\nPayment methods active on this account "
            "(DAFTRA_PAYMENT_METHOD must be one of these)"
        )
        configured = getattr(settings, "DAFTRA_PAYMENT_METHOD", "")
        methods = []
        # There is no payment-methods endpoint. Daftra accepts
        # manual_payment_<treasury_id>, so the treasuries are the list -- free
        # text like "credit_card" is rejected as "not active or incorrect".
        try:
            data = client._call("GET", "treasuries.json")
        except DaftraError as exc:
            data = None
            self.stdout.write(warn(f"  could not list treasuries: {exc}"))

        for row in (data or {}).get("data") or []:
            treasury = row.get("Treasury") or row
            slug = f"manual_payment_{treasury.get('id')}"
            label = treasury.get("name") or ""
            live = str(treasury.get("active")) == "1"
            marker = ok("  <- configured") if slug == str(configured) else ""
            self.stdout.write(
                f"  {slug}  {label}{'' if live else ' (inactive)'}{marker}"
            )
            if live:
                methods.append(slug)

        if methods and str(configured) not in methods:
            self.stdout.write(
                bad(f"  '{configured}' is NOT one of the above - payments will be rejected.")
            )
            self.stdout.write(
                warn("  To label payments as a card, add that payment method in Daftra\n"
                     "  and set DAFTRA_PAYMENT_METHOD to its manual_payment_<id>.")
            )

        self.stdout.write("\nInvoice layouts (use one of these ids for DAFTRA_INVOICE_LAYOUT_ID)")
        found = False
        # Path differs between Daftra versions; try the likely ones rather than
        # guessing one and reporting a false negative.
        for path in ("invoice_layouts.json", "layouts.json", "settings/invoice_layouts.json"):
            try:
                data = client._call("GET", path)
            except DaftraError:
                continue
            rows = data if isinstance(data, list) else (data.get("data") or [])
            for row in rows:
                layout_row = row.get("InvoiceLayout") or row.get("Layout") or row
                self.stdout.write(
                    f"  id={layout_row.get('id')}  {layout_row.get('name') or layout_row.get('title') or ''}"
                )
                found = True
            if found:
                break

        if not found:
            self.stdout.write(
                warn(
                    "  Could not list layouts on this account. Read the id from the URL in\n"
                    "  Daftra > Settings > Invoice Layouts instead, or leave the setting unset\n"
                    "  to use the account default."
                )
            )
