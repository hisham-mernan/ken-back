"""Guards on the seeding path.

seed_ken_data opens by deleting every Booking, BookingDate and ticket. It was
reachable two ways that needed no intent: an unauthenticated GET on
/api/products/public-seed-ken-data/ (with ?force=true), and Django startup
whenever no active Event existed -- on Vercel, every cold start.
"""
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import Resolver404, resolve

from .models import Booking, Hut


class SeedEndpointIsGoneTests(TestCase):
    def test_public_seed_url_no_longer_exists(self):
        with self.assertRaises(Resolver404):
            resolve("/api/products/public-seed-ken-data/")


class SeedCommandRefusesByDefaultTests(TestCase):
    def setUp(self):
        hut = Hut.objects.create(title="T", description="d", size="small")
        Booking.objects.create(
            hut=hut, status="paid", total_price=Decimal("400.00"),
            persons_max_num=2, kids_max_num=0, guest_email="g@example.invalid",
        )

    def test_seeding_without_confirmation_raises_and_keeps_bookings(self):
        with self.assertRaises(CommandError):
            call_command("seed_ken_data")
        self.assertEqual(Booking.objects.count(), 1, "bookings must survive a refused seed")


class StartupDoesNotSeedTests(TestCase):
    def test_app_ready_does_not_call_the_destructive_seeder(self):
        import inspect

        from products.apps import ProductsConfig

        # Check the mechanism, not the name -- the comment in ready() names
        # the command deliberately to explain why it must not be called.
        source = inspect.getsource(ProductsConfig.ready)
        code = "".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        self.assertNotIn(
            "call_command", code,
            "startup must never run a management command: the seeder deletes every booking",
        )
