"""Drop every cottage to a token rate, and put the real rates back afterwards.

Live testing of the payment flow needs a booking that costs almost nothing to
put through, so the rates get flattened to 5 SAR for a while. The danger is
obvious: the real rates only existed as rows in the production database, so
once they were overwritten the only record of them was whoever remembered.

They are recorded here instead. `--restore` puts back exactly what the huts
were charging before the change on 2026-08-27, so returning to normal is one
command and needs nobody's memory.

    python manage.py set_hut_prices              # show what is set now
    python manage.py set_hut_prices --test       # flatten to 5 SAR
    python manage.py set_hut_prices --restore    # put the real rates back
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

# The live rates as at 2026-08-27, immediately before the test change.
# Keyed by hut id, which is the stable identifier: the titles here are only
# to make the output readable and to flag if a row looks unfamiliar. They do
# change -- these three have already been "Hut" and are now "Cottage", and
# the dev database still carries the older names -- so a differing title is
# reported and not treated as a reason to refuse.
REAL_PRICES = {
    4: ("Qimmah Cottage (Large)", Decimal("1450.00"), Decimal("1650.00")),
    3: ("Malath Cottage (Medium)", Decimal("900.00"), Decimal("1100.00")),
    2: ("Wahad Cottage (Small)", Decimal("600.00"), Decimal("770.00")),
}

TEST_PRICE = Decimal("5.00")


class Command(BaseCommand):
    help = "Flatten cottage rates for live payment testing, or restore the real ones."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--test", action="store_true",
                           help=f"Set every cottage to {TEST_PRICE} SAR weekday and weekend.")
        group.add_argument("--restore", action="store_true",
                           help="Put back the real rates recorded in this file.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change and change nothing.")

    def handle(self, *args, **options):
        from products.models import Hut

        huts = list(Hut.objects.order_by("-id"))
        if not huts:
            raise CommandError("No cottages in this database -- wrong DATABASE_URL?")

        if not options["test"] and not options["restore"]:
            self.stdout.write("Current rates:")
            for hut in huts:
                self.stdout.write(f"  #{hut.pk} {hut.title}: weekday {hut.weekday_price}, "
                                  f"weekend {hut.weekend_price}")
            self.stdout.write("\nPass --test to flatten them, --restore to put them back.")
            return

        if options["restore"]:
            missing = [pk for pk in REAL_PRICES if not any(h.pk == pk for h in huts)]
            if missing:
                raise CommandError(
                    f"No cottage with id {missing} -- refusing to restore against a "
                    "database this file does not describe.")

        changed = 0
        for hut in huts:
            if options["restore"]:
                recorded = REAL_PRICES.get(hut.pk)
                if not recorded:
                    self.stdout.write(self.style.WARNING(
                        f"  #{hut.pk} {hut.title}: no recorded rate -- left alone."))
                    continue
                title, weekday, weekend = recorded
                if title != hut.title:
                    self.stdout.write(self.style.WARNING(
                        f"  #{hut.pk} is called {hut.title!r} now; the rate was recorded "
                        f"against {title!r}. Restoring by id."))
            else:
                weekday = weekend = TEST_PRICE

            if hut.weekday_price == weekday and hut.weekend_price == weekend:
                self.stdout.write(f"  #{hut.pk} {hut.title}: already {weekday}/{weekend}.")
                continue

            line = (f"  #{hut.pk} {hut.title}: {hut.weekday_price}/{hut.weekend_price} "
                    f"-> {weekday}/{weekend}")
            if options["dry_run"]:
                self.stdout.write(line + "  (dry run)")
                continue

            hut.weekday_price = weekday
            hut.weekend_price = weekend
            hut.save(update_fields=["weekday_price", "weekend_price"])
            changed += 1
            self.stdout.write(self.style.SUCCESS(line))

        if options["dry_run"]:
            self.stdout.write("\nDry run. Re-run without --dry-run to apply.")
        else:
            self.stdout.write(f"\nUpdated {changed} cottage(s).")
            if options["test"]:
                self.stdout.write(self.style.WARNING(
                    "Cottages are now at a test rate. Run --restore when finished."))
