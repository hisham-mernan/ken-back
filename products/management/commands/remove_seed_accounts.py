"""Remove the demo accounts the seeder plants, without taking bookings with them.

seed_ken_data created supplier and guest accounts whose passwords were written
into the source (`supplier123`, `guest123`), and a public endpoint could create
them on production. Anyone reading the repository could sign in as a supplier
and read customer names, emails, phones and ID numbers.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from products.models import Booking

SEED_ACCOUNTS = [
    "supplier1@kenluxuryreef.com",
    "supplier2@kenluxuryreef.com",
    "guest1@kenluxuryreef.com",
]

# Never touched: this may well be the real administrator account, and deleting
# it would lock the operator out of their own dashboard. Reported only.
ADMIN_ACCOUNT = "admin@kenluxuryreef.com"


class Command(BaseCommand):
    help = "Delete the seeded demo accounts. Accounts holding bookings are disabled instead."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen and change nothing.")

    def handle(self, *args, **options):
        User = get_user_model()
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN -- nothing will be changed.\n"))

        for email in SEED_ACCOUNTS:
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(f"  {email}: not present")
                continue

            # Booking.user cascades, so deleting an account that owns bookings
            # would delete those bookings too. Disable those instead.
            bookings = Booking.objects.filter(user=user).count()
            if bookings:
                self.stdout.write(self.style.WARNING(
                    f"  {email}: holds {bookings} booking(s) -- disabling instead of deleting"
                ))
                if not dry:
                    user.is_active = False
                    user.set_unusable_password()
                    user.save(update_fields=["is_active", "password"])
            else:
                self.stdout.write(self.style.SUCCESS(f"  {email}: deleting (no bookings)"))
                if not dry:
                    user.delete()

        admin = User.objects.filter(email=ADMIN_ACCOUNT).first()
        if admin:
            self.stdout.write(self.style.WARNING(
                f"\n  {ADMIN_ACCOUNT} exists and was NOT modified -- it may be your real "
                "administrator. The seeder set its password to a value published in the "
                "source, so change that password now if it was ever run against this database."
            ))
        else:
            self.stdout.write(f"\n  {ADMIN_ACCOUNT}: not present")
