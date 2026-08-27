"""Release dates held by a booking that was confirmed and never paid for.

Confirming a booking tells the guest, in as many words, "pay within 30 minutes
or the booking will be cancelled". That promise was never kept. It was wired
as a `threading.Timer` started inside a signal, and it failed three ways at
once: the timer was set to five minutes rather than thirty; the process is
frozen the moment the response is sent, so it almost never fired at all; and
it cancelled anything still marked "confirmed" without checking whether the
money had arrived, which would have cancelled a fully paid stay.

The result was abandoned checkouts holding cottages indefinitely. Run this on
a schedule instead -- see .github/workflows/expire-bookings.yml.

The safety rule here is the one the old timer got wrong: a booking with any
payment against it is never touched, whatever its status says.
"""
from django.core.management.base import BaseCommand
from django.db.models import DateTimeField
from django.db.models.functions import Coalesce
from django.utils import timezone

DEFAULT_MINUTES = 30


class Command(BaseCommand):
    help = "Cancel confirmed bookings that were never paid for, releasing their dates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes", type=int, default=DEFAULT_MINUTES,
            help="How long a hold may go unpaid before it is released "
                 f"(default {DEFAULT_MINUTES}, matching what the guest is told).")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would be released and change nothing.")

    def handle(self, *args, **options):
        from products.models import Booking
        from products.signals import cancel_unpaid_booking

        minutes = options["minutes"]
        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)

        # Older bookings predate confirmed_at, so fall back to when the booking
        # was made. Anything that old and still unpaid is abandoned either way.
        stale = (
            Booking.objects
            .filter(status="confirmed", paid__lte=0)
            .annotate(held_since=Coalesce("confirmed_at", "created_at",
                                          output_field=DateTimeField()))
            .filter(held_since__lt=cutoff)
            .select_related("hut")
            .order_by("pk")
        )

        if not stale.exists():
            self.stdout.write(f"Nothing held unpaid for more than {minutes} minutes.")
            return

        self.stdout.write(
            f"{stale.count()} booking(s) confirmed but unpaid for over {minutes} minutes:")

        released = 0
        for booking in stale:
            dates = booking.dates.filter(is_extra=False).first() or booking.dates.first()
            when = f"{dates.date_from} to {dates.date_to}" if dates else "no dates"
            who = booking.contact_name or booking.contact_email or "unknown"
            line = (f"  #{booking.pk} {booking.hut.title if booking.hut else '-'} "
                    f"| {when} | {who} | paid {booking.paid}")

            if options["dry_run"]:
                self.stdout.write(line + "  (dry run)")
                continue

            # Belt and braces: re-read the row before cancelling, in case a
            # payment landed between building the queryset and getting here.
            fresh = Booking.objects.filter(pk=booking.pk).first()
            if not fresh or fresh.status != "confirmed" or (fresh.paid or 0) > 0:
                self.stdout.write(self.style.WARNING(
                    f"  #{booking.pk} changed underneath us -- left alone."))
                continue

            cancel_unpaid_booking(fresh)
            released += 1
            self.stdout.write(self.style.SUCCESS(line + "  -> cancelled"))

        if options["dry_run"]:
            self.stdout.write("\nDry run. Re-run without --dry-run to release these.")
        else:
            self.stdout.write(f"\nReleased {released} booking(s).")
