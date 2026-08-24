"""Add a few more featured testimonials without touching anything else.

seed_ken_data is destructive (it wipes bookings) and only plants two reviews,
both under the same demo guest. This is a small, idempotent, non-destructive
companion: it only ever adds HutRating rows and the guest accounts they
belong to (HutRating.user is a required FK), and re-running it changes
nothing once those rows exist.

The content here is placeholder copy, not real guest reviews -- run this only
until real reviews accumulate, then these can be deleted (they're tagged
below so they're easy to find and remove later).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from products.models import Hut, HutRating

User = get_user_model()

# Kept distinct from seed_ken_data's guest1@kenluxuryreef.com so this can be
# added or removed independently of that seeder / remove_seed_accounts.
REVIEWERS = [
    {
        "email": "testimonial-guest1@kenluxuryreef.com",
        "full_name": "Sara Al-Harbi / سارة الحربي",
        "phone": "+966500000010",
        "content": (
            "Every detail felt considered, from check-in to the last morning "
            "coffee on the deck. We're already planning our next stay."
        ),
        "value": "5.00",
    },
    {
        "email": "testimonial-guest2@kenluxuryreef.com",
        "full_name": "Faisal Al-Qahtani / فيصل القحطاني",
        "phone": "+966500000011",
        "content": (
            "هدوء تام وإطلالة لا تُنسى. الحجز والاستقبال كانا سلسين، وسنعود "
            "بالتأكيد في الصيف القادم."
        ),
        "value": "4.90",
    },
    {
        "email": "testimonial-guest3@kenluxuryreef.com",
        "full_name": "Lama Al-Dossari / لمى الدوسري",
        "phone": "+966500000012",
        "content": (
            "A genuinely relaxing escape -- the hut was spotless, the staff "
            "were attentive without being intrusive, and the sunset view "
            "alone was worth the trip."
        ),
        "value": "5.00",
    },
    {
        "email": "testimonial-guest4@kenluxuryreef.com",
        "full_name": "Omar Al-Zahrani / عمر الزهراني",
        "phone": "+966500000013",
        "content": (
            "أفضل تجربة إقامة جربناها هذا العام. التصميم الداخلي راقٍ "
            "والخدمة كانت ممتازة من أول لحظة حتى المغادرة."
        ),
        "value": "4.80",
    },
]


class Command(BaseCommand):
    help = "Add a handful of placeholder testimonials (idempotent, non-destructive)."

    def handle(self, *args, **options):
        huts = list(Hut.objects.order_by("id"))
        if not huts:
            self.stdout.write(self.style.WARNING(
                "No huts exist yet -- testimonials need a hut to attach to. "
                "Add at least one hut first, then re-run this command."
            ))
            return

        for index, reviewer in enumerate(REVIEWERS):
            user, created = User.objects.get_or_create(
                email=reviewer["email"],
                defaults={
                    "full_name": reviewer["full_name"],
                    "role": "guest",
                    "is_active": True,
                    "phone": reviewer["phone"],
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            hut = huts[index % len(huts)]
            _, rating_created = HutRating.objects.get_or_create(
                user=user,
                hut=hut,
                content=reviewer["content"],
                defaults={"value": reviewer["value"], "is_testmonail": True},
            )

            # Console output stays ASCII-only: full names and hut titles here
            # can be Arabic, and Windows consoles default to a codepage that
            # can't encode them, which would crash the command after the
            # write already succeeded.
            if rating_created:
                self.stdout.write(self.style.SUCCESS(
                    f"  + testimonial from {reviewer['email']} on hut #{hut.pk}"
                ))
            else:
                self.stdout.write(f"  = {reviewer['email']}: already present")
