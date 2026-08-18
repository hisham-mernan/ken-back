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

    def handle(self, *args, **options):
        from products.models import Booking
        from products.utils import send_balance_reminder

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
