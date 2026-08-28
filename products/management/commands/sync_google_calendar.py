"""Reconcile the Google Calendar against the bookings.

The signals in products/signals.py push each booking as it changes, but they
are best-effort by design -- a Google outage or a timeout is logged and
dropped so it cannot fail a booking. This is what makes that safe: run it on a
schedule and anything the signals missed is put right.

    python manage.py sync_google_calendar                # next 12 months
    python manage.py sync_google_calendar --months 24
    python manage.py sync_google_calendar --prune        # also remove stale events
    python manage.py sync_google_calendar --dry-run

--prune deletes events for bookings that are no longer active -- cancelled
after the event was written, say. It only ever touches events this project
created, identified by their kenbooking* ids; anything else on the calendar is
left alone, so it is safe to run against a calendar that also holds real
appointments.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from products import google_calendar


class Command(BaseCommand):
    help = "Push active bookings to Google Calendar and optionally remove stale events."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=12,
                            help="How far ahead to sync (default 12).")
        parser.add_argument("--prune", action="store_true",
                            help="Remove events whose booking is no longer active.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change and change nothing.")

    def handle(self, *args, **options):
        from django.conf import settings
        from products.models import ACTIVE_BOOKING_STATUSES, Booking, BookingDate

        if not google_calendar.is_enabled():
            raise CommandError(
                "Google Calendar is not configured. Set GOOGLE_CALENDAR_ID and "
                "GOOGLE_SERVICE_ACCOUNT_JSON, then run check_google_calendar.")

        dry_run = options["dry_run"]
        start = date.today()
        end = start + timedelta(days=31 * max(1, options["months"]))

        booking_ids = (
            BookingDate.objects
            .filter(booking__status__in=ACTIVE_BOOKING_STATUSES,
                    date_from__lte=end, date_to__gte=start)
            .values_list("booking_id", flat=True)
            .distinct()
        )
        bookings = (Booking.objects.filter(pk__in=list(booking_ids))
                    .select_related("hut").order_by("pk"))

        self.stdout.write("{} active booking(s) between {} and {}.".format(
            bookings.count(), start, end))

        pushed = failed = 0
        for booking in bookings:
            span = google_calendar.stay_span(booking)
            when = "{} to {}".format(span.date_from, span.date_to) if span else "no dates"
            line = "  #{} {} | {} | {}".format(
                booking.pk, booking.hut.title if booking.hut else "-", when,
                booking.status)

            if dry_run:
                self.stdout.write(line + "  (dry run)")
                continue

            if google_calendar.sync_booking(booking):
                pushed += 1
                self.stdout.write(self.style.SUCCESS(line))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(line + "  -- not synced, see logs"))

        if options["prune"]:
            self.stdout.write("\nLooking for events whose booking is no longer active.")
            self._prune(settings, Booking, ACTIVE_BOOKING_STATUSES, dry_run)

        if dry_run:
            self.stdout.write("\nDry run. Re-run without --dry-run to apply.")
        else:
            self.stdout.write("\nSynced {}, failed {}.".format(pushed, failed))

    # ------------------------------------------------------------------ prune

    def _prune(self, settings, Booking, active_statuses, dry_run):
        session = google_calendar._session()
        path = "/calendars/{}/events".format(settings.GOOGLE_CALENDAR_ID)

        params = {"maxResults": 2500, "showDeleted": False, "singleEvents": True}
        removed = 0
        page_token = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            response = google_calendar._call(session, "GET", path, params=params)
            if response.status_code >= 400:
                self.stdout.write(self.style.ERROR(
                    "  listing failed: {} {}".format(response.status_code,
                                                     response.text[:200])))
                return
            body = response.json()

            for event in body.get("items", []):
                event_id = event.get("id") or ""
                # Ours and ours only. A calendar this is shared onto may well
                # carry real appointments, and they are none of our business.
                if not event_id.startswith("kenbooking"):
                    continue
                suffix = event_id[len("kenbooking"):]
                if not suffix.isdigit():
                    continue

                booking = Booking.objects.filter(pk=int(suffix)).first()
                if booking is not None and booking.status in active_statuses:
                    continue

                reason = "booking gone" if booking is None else booking.status
                line = "  {} ({})".format(event_id, reason)
                if dry_run:
                    self.stdout.write(line + "  (dry run)")
                    continue

                delete = google_calendar._call(
                    session, "DELETE", "{}/{}".format(path, event_id))
                if delete.status_code in (200, 204, 404, 410):
                    removed += 1
                    self.stdout.write(self.style.SUCCESS(line + "  -> removed"))
                else:
                    self.stdout.write(self.style.WARNING(
                        line + "  -> {} {}".format(delete.status_code,
                                                   delete.text[:120])))

            page_token = body.get("nextPageToken")
            if not page_token:
                break

        if not dry_run:
            self.stdout.write("  removed {} stale event(s).".format(removed))
