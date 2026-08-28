"""Tell me why the calendar integration is not working.

Every failure mode here produces the same symptom in production -- events
quietly do not appear, because products/google_calendar.py swallows its errors
by design. This command is where the errors are allowed to be loud.

    python manage.py check_google_calendar

It reads and writes nothing permanent: the write test creates an event in the
past and deletes it again.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from products import google_calendar


class Command(BaseCommand):
    help = "Check the Google Calendar credentials, sharing and write access."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-write", action="store_true",
            help="Check credentials and read access only, create nothing.")

    def handle(self, *args, **options):
        from django.conf import settings

        ok = self.style.SUCCESS
        bad = self.style.ERROR
        warn = self.style.WARNING

        # ---------------------------------------------------------- settings
        self.stdout.write("Configuration")
        if not settings.GOOGLE_CALENDAR_ID:
            self.stdout.write(bad("  GOOGLE_CALENDAR_ID is not set."))
            return
        self.stdout.write("  calendar id: {}".format(settings.GOOGLE_CALENDAR_ID))
        if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
            self.stdout.write(bad("  GOOGLE_SERVICE_ACCOUNT_JSON is not set."))
            return
        self.stdout.write("  service account json: {} characters".format(
            len(settings.GOOGLE_SERVICE_ACCOUNT_JSON)))

        # ------------------------------------------------------- credentials
        self.stdout.write("\nCredentials")
        try:
            creds = google_calendar._credentials()
        except Exception as exc:
            self.stdout.write(bad("  could not be read: {}".format(exc)))
            return
        email = getattr(creds, "service_account_email", "(unknown)")
        self.stdout.write(ok("  loaded. Service account: {}".format(email)))
        self.stdout.write("  The calendar must be shared with that address, with")
        self.stdout.write("  'Make changes to events'. Without the share every call")
        self.stdout.write("  returns 404 -- an unshared calendar does not exist to it.")

        # -------------------------------------------------------------- read
        self.stdout.write("\nReading the calendar")
        try:
            session = google_calendar._session()
            response = google_calendar._call(
                session, "GET",
                "/calendars/{}".format(settings.GOOGLE_CALENDAR_ID))
        except Exception as exc:
            self.stdout.write(bad("  failed: {}".format(exc)))
            return

        if response.status_code == 404:
            self.stdout.write(bad("  404. Either the calendar id is wrong, or it has"))
            self.stdout.write(bad("  not been shared with {}.".format(email)))
            return
        if response.status_code >= 400:
            self.stdout.write(bad("  {}: {}".format(response.status_code,
                                                    response.text[:300])))
            return
        body = response.json()
        self.stdout.write(ok("  reachable: {!r} ({})".format(
            body.get("summary", "?"), body.get("timeZone", "?"))))

        if options["skip_write"]:
            self.stdout.write(warn("\nWrite test skipped."))
            return

        # ------------------------------------------------------------- write
        self.stdout.write("\nWriting a throwaway event")
        # Dated well in the past so it cannot be mistaken for a real booking
        # even in the seconds before it is removed.
        long_ago = date.today() - timedelta(days=365)
        probe = {
            "id": "kenbookingcheck",
            "summary": "Ken integration check -- safe to ignore",
            "description": "Created by manage.py check_google_calendar.",
            "start": {"date": long_ago.isoformat()},
            "end": {"date": (long_ago + timedelta(days=1)).isoformat()},
        }
        path = "/calendars/{}/events".format(settings.GOOGLE_CALENDAR_ID)
        try:
            response = google_calendar._call(session, "POST", path, json=probe)
            if response.status_code == 409:
                # Left over from an earlier run; updating it proves the same thing.
                response = google_calendar._call(
                    session, "PUT", path + "/kenbookingcheck", json=probe)
            if response.status_code >= 400:
                self.stdout.write(bad("  {}: {}".format(response.status_code,
                                                        response.text[:300])))
                self.stdout.write(bad("  The share is probably read-only. It needs"))
                self.stdout.write(bad("  'Make changes to events'."))
                return
            self.stdout.write(ok("  created."))

            response = google_calendar._call(
                session, "DELETE", path + "/kenbookingcheck")
            if response.status_code in (200, 204, 404, 410):
                self.stdout.write(ok("  removed again."))
            else:
                self.stdout.write(warn(
                    "  created but not removed ({}). Delete 'Ken integration check'"
                    " by hand.".format(response.status_code)))
        except Exception as exc:
            self.stdout.write(bad("  failed: {}".format(exc)))
            return

        self.stdout.write(ok("\nGoogle Calendar is set up correctly."))
        self.stdout.write("Run `manage.py sync_google_calendar` to push existing bookings.")
