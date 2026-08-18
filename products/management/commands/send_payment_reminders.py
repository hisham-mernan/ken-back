"""Email guests who still owe a balance, once every 24 hours.

Driven by a scheduled GitHub Action rather than APScheduler: Vercel destroys
the process between requests, so an in-process scheduler never fires there.

Reminders stop at check-in. A booking still unpaid by then is left alone and
listed at the end of the run for someone to deal with, rather than cancelled
automatically -- a genuine guest whose email went to spam should not lose
their booking to a cron job.

    python manage.py send_payment_reminders --dry-run
    python manage.py send_payment_reminders
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils import timezone

REMINDER_INTERVAL = timedelta(hours=24)


class Command(BaseCommand):
    help = "Send balance reminders for part-paid bookings."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="List who would be emailed without sending.")
        parser.add_argument("--booking", type=int, default=None,
                            help="Only consider this booking id.")
        parser.add_argument("--sample-to", default=None, metavar="EMAIL",
                            help="Send one sample reminder to this address and "
                                 "stop. Proves the mail credentials and the pay "
                                 "link without needing a real part-paid booking.")

    def handle(self, *args, **options):
        from products.models import Booking
        from products.utils import send_balance_reminder

        if options["sample_to"]:
            return self._send_sample(options["sample_to"])

        dry_run = options["dry_run"]
        now = timezone.now()
        today = timezone.localdate()

        qs = Booking.objects.filter(status="partially_paid", not_paid__gt=0)
        if options["booking"]:
            qs = qs.filter(pk=options["booking"])
        # Annotate the check-in so past bookings can be separated from due ones.
        qs = qs.annotate(check_in=Min("dates__date_from")).select_related("hut", "user")

        due, waiting, overdue, sent, failed = [], [], [], 0, 0

        for booking in qs:
            if booking.check_in and booking.check_in < today:
                overdue.append(booking)
                continue
            last = booking.last_reminder_at
            if last and (now - last) < REMINDER_INTERVAL:
                waiting.append(booking)
                continue
            due.append(booking)

        mode = "DRY RUN" if dry_run else "SEND"
        self.stdout.write(f"[{mode}] part-paid bookings: {qs.count()}")
        self.stdout.write(
            f"[{mode}] due now: {len(due)}  "
            f"within 24h of last reminder: {len(waiting)}  "
            f"past check-in: {len(overdue)}\n"
        )

        for booking in due:
            label = (f"  #{booking.pk} {booking.contact_email or '(no email)'} "
                     f"owes {booking.not_paid} of {booking.total_price} "
                     f"| check-in {booking.check_in} "
                     f"| reminders so far {booking.reminder_count}")
            if dry_run:
                self.stdout.write(label)
                continue

            if send_balance_reminder(booking):
                Booking.objects.filter(pk=booking.pk).update(
                    last_reminder_at=now,
                    reminder_count=(booking.reminder_count or 0) + 1,
                )
                sent += 1
                self.stdout.write(self.style.SUCCESS(label))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(label + "  [SEND FAILED]"))

        if overdue:
            self.stdout.write(
                "\nPast check-in and still unpaid -- needs a human, not another email:"
            )
            for booking in overdue:
                self.stdout.write(
                    f"  #{booking.pk} {booking.contact_email or '(no email)'} "
                    f"owes {booking.not_paid} | check-in was {booking.check_in}"
                )

        if not dry_run:
            summary = f"\nsent={sent} failed={failed} skipped={len(waiting)} overdue={len(overdue)}"
            self.stdout.write(
                self.style.WARNING(summary) if failed else self.style.SUCCESS(summary)
            )
        else:
            self.stdout.write("\nDry run only. Re-run without --dry-run to send.")

    def _send_sample(self, recipient):
        """Send one reminder built from a throwaway booking, then discard it.

        The point is to exercise the real path -- template, SMTP credentials
        and FRONTEND_BASE_URL -- so a misconfiguration shows up here rather
        than on a guest's first real reminder. Nothing is committed: the
        booking is rolled back whether or not the send succeeds.
        """
        import datetime
        from decimal import Decimal

        from django.db import transaction
        from products.models import Booking, BookingDate, Hut
        from products.utils import booking_payment_link, send_balance_reminder

        self.stdout.write(f"Sending a sample reminder to {recipient} ...")
        sent = False
        link = ""
        try:
            with transaction.atomic():
                booking = Booking.objects.create(
                    user=None, guest_name="Sample Booking",
                    guest_email=recipient, guest_phone="+966500000000",
                    guest_id_num="0000000000", hut=Hut.objects.first(),
                    persons_max_num=2, kids_max_num=0,
                    total_price=Decimal("400.00"), paid=Decimal("200.00"),
                    not_paid=Decimal("200.00"), status="partially_paid",
                )
                start = timezone.localdate() + datetime.timedelta(days=30)
                BookingDate.objects.create(booking=booking, date_from=start,
                                           date_to=start + timedelta(days=2))
                link = booking_payment_link(booking)
                sent = send_balance_reminder(booking, is_sample=True)
                # Never keep the sample, no matter how the send went.
                raise _Rollback()
        except _Rollback:
            pass

        self.stdout.write(f"  pay link in the email: {link}")
        if link.startswith("https://ken.mernantech.com"):
            self.stdout.write(self.style.WARNING(
                "  FRONTEND_BASE_URL is not set - that host is parked and the "
                "link will not work."))
        if sent:
            self.stdout.write(self.style.SUCCESS("  sent. Check that inbox."))
        else:
            self.stdout.write(self.style.ERROR(
                "  NOT sent - check EMAIL_HOST_USER / EMAIL_HOST_PASSWORD."))
        self.stdout.write("  the sample booking was rolled back, nothing was kept.")
        self.stdout.write(
            "  NOTE: that link will show 'booking not found' -- the sample "
            "booking no longer exists. It proves the address and the mail "
            "settings, not a live booking."
        )


class _Rollback(Exception):
    """Used to unwind the sample booking; never escapes the command."""
