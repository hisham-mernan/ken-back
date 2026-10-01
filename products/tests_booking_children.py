"""Leaving the children count empty when booking.

A stay with no children is the common case, and the form now lets the field be
left blank rather than demanding a nought. The model column is not nullable,
so the serializer has to turn absence into 0 before it reaches the database --
without that the API answers "This field is required." and the booking fails.

The capacity rule is unchanged and must stay unchanged: children come out of
the same allowance as adults, so an absent count has to read as 0 rather than
as "unknown, allow anything".
"""
from decimal import Decimal

from django.test import TestCase

from .models import Hut
from .serializers import BookingSerializer


class ChildrenAreOptionalTests(TestCase):
    def setUp(self):
        self.hut = Hut.objects.create(
            title="Wahad Cottage (Small)", description="d", size="small",
            max_persons_num=2, max_kids_num=1,
            weekday_price=Decimal("600.00"), weekend_price=Decimal("770.00"))

    def field(self):
        return BookingSerializer().fields["kids_max_num"]

    def test_the_count_is_not_required(self):
        self.assertFalse(self.field().required,
                         "the booking form leaves this blank for a party with no children")

    def test_an_absent_count_means_none_rather_than_unknown(self):
        self.assertEqual(self.field().default, 0)

    def test_a_negative_count_is_still_refused(self):
        field = self.field()
        with self.assertRaises(Exception):
            field.run_validation(-1)

    def test_a_supplied_count_is_still_honoured(self):
        self.assertEqual(self.field().run_validation(1), 1)

    def test_adults_are_still_required(self):
        """Only the children field became optional."""
        self.assertTrue(BookingSerializer().fields["persons_max_num"].required)
