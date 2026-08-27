"""Tiers earned by repeat custom, and the discount they carry.

The rules that matter are the ones that stop this being free money: only
bookings that were paid for count, and the booking being made never counts
towards its own discount.
"""
from decimal import Decimal

from django.test import TestCase

from . import loyalty
from .models import Booking, Hut


def make_hut():
    return Hut.objects.create(title="Qimmah Cottage (Large)", description="d",
                              size="large", max_persons_num=8, max_kids_num=4,
                              weekday_price=Decimal("1000.00"),
                              weekend_price=Decimal("1000.00"))


def paid_booking(hut, phone="0500000001", status="paid", paid="400.00", user=None):
    return Booking.objects.create(
        hut=hut, user=user, status=status,
        total_price=Decimal("400.00"), paid=Decimal(paid),
        not_paid=Decimal("0.00"), persons_max_num=2, kids_max_num=0,
        guest_name="Repeat Guest", guest_email="r@example.invalid",
        guest_phone=None if user else phone,
    )


class TierThresholdTests(TestCase):
    def test_thresholds_match_the_published_ladder(self):
        self.assertEqual(loyalty.tier_for_count(0), ("", 0))
        self.assertEqual(loyalty.tier_for_count(2), ("", 0))
        self.assertEqual(loyalty.tier_for_count(3), ("bronze", 5))
        self.assertEqual(loyalty.tier_for_count(4), ("bronze", 5))
        self.assertEqual(loyalty.tier_for_count(5), ("silver", 10))
        self.assertEqual(loyalty.tier_for_count(6), ("silver", 10))
        self.assertEqual(loyalty.tier_for_count(7), ("gold", 15))
        self.assertEqual(loyalty.tier_for_count(70), ("gold", 15))


class WhatCountsTests(TestCase):
    def setUp(self):
        self.hut = make_hut()

    def test_unpaid_bookings_earn_nothing(self):
        """Otherwise anyone could click their way to 15% off in a minute."""
        for _ in range(9):
            paid_booking(self.hut, status="pending", paid="0.00")
        self.assertEqual(loyalty.status(phone="0500000001")["tier"], "")

    def test_cancelled_and_refunded_stays_stop_counting(self):
        for _ in range(3):
            paid_booking(self.hut)
        self.assertEqual(loyalty.status(phone="0500000001")["tier"], "bronze")
        Booking.objects.update(status="cancelled")
        self.assertEqual(loyalty.status(phone="0500000001")["tier"], "")

    def test_a_deposit_counts(self):
        for _ in range(3):
            paid_booking(self.hut, status="partially_paid", paid="200.00")
        self.assertEqual(loyalty.status(phone="0500000001")["tier"], "bronze")

    def test_the_same_line_written_three_ways_is_one_customer(self):
        paid_booking(self.hut, phone="+966500000001")
        paid_booking(self.hut, phone="0500000001")
        paid_booking(self.hut, phone="500000001")
        self.assertEqual(loyalty.status(phone="0500000001")["stays"], 3)
        self.assertEqual(loyalty.status(phone="0500000001")["tier"], "bronze")

    def test_a_different_number_is_a_different_customer(self):
        for _ in range(7):
            paid_booking(self.hut, phone="0500000001")
        self.assertEqual(loyalty.status(phone="0509999999")["tier"], "")

    def test_a_booking_does_not_earn_its_own_discount(self):
        for _ in range(3):
            paid_booking(self.hut)
        newest = paid_booking(self.hut)
        # Three earlier stays -> bronze. Excluding itself keeps it honest.
        self.assertEqual(
            loyalty.status(phone="0500000001", exclude_pk=newest.pk)["stays"], 3)


class DiscountResolutionTests(TestCase):
    def setUp(self):
        self.hut = make_hut()

    class _Promo:
        def __init__(self, percentage):
            self.percentage = percentage

    def test_no_code_and_no_tier_is_full_price(self):
        percent, source = loyalty.resolve_discount(phone="0500000001")
        self.assertEqual((percent, source), (0, ""))

    def test_a_tier_applies_with_no_code(self):
        for _ in range(5):
            paid_booking(self.hut)
        percent, source = loyalty.resolve_discount(phone="0500000001")
        self.assertEqual((percent, source), (10, "loyalty:silver"))

    def test_the_better_of_the_two_wins_and_they_do_not_stack(self):
        for _ in range(7):
            paid_booking(self.hut)          # gold, 15%
        percent, source = loyalty.resolve_discount(
            promo=self._Promo(20), phone="0500000001")
        self.assertEqual((percent, source), (20, "promocode"))

        percent, source = loyalty.resolve_discount(
            promo=self._Promo(5), phone="0500000001")
        self.assertEqual((percent, source), (15, "loyalty:gold"))

    def test_apply_discount_arithmetic(self):
        self.assertEqual(loyalty.apply_discount(Decimal("1000.00"), 15),
                         Decimal("850.00"))
        self.assertEqual(loyalty.apply_discount(Decimal("1000.00"), 0),
                         Decimal("1000.00"))
