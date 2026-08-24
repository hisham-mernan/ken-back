"""The weekday/weekend nightly pricing rule.

The two headline cases are the ones the rule was specified with, using a
1000 weekday / 1500 weekend hut:

    check in Fri, out Mon  -> 3 nights -> 3000  (long-stay weekday rate)
    check in Fri, out Sun  -> 2 nights -> 3000  (two weekend nights)

Both land on 3000, which is the point of the rule: the third night should not
make the stay dearer than the weekend alone.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AvailableDateRanges, Booking, BookingDate, Hut
from .pricing import price_for_stay, quote, stay_nights

# August 2026: 21st is a Friday, so 22nd Sat, 23rd Sun, 24th Mon, 25th Tue.
FRI = date(2026, 8, 21)
SAT = date(2026, 8, 22)
SUN = date(2026, 8, 23)
MON = date(2026, 8, 24)
TUE = date(2026, 8, 25)
WED = date(2026, 8, 26)


def make_hut(weekday="1000.00", weekend="1500.00"):
    return Hut(
        title="Test Hut",
        description="d",
        size="small",
        weekday_price=Decimal(weekday),
        weekend_price=Decimal(weekend),
    )


class CalendarAssumptionsTests(TestCase):
    """Guard the dates the rest of this file is built on."""

    def test_the_fixture_dates_are_the_days_we_think_they_are(self):
        self.assertEqual(FRI.weekday(), 4, "FRI must be a Friday")
        self.assertEqual(SAT.weekday(), 5, "SAT must be a Saturday")
        self.assertEqual(SUN.weekday(), 6, "SUN must be a Sunday")
        self.assertEqual(MON.weekday(), 0, "MON must be a Monday")


class StayNightsTests(TestCase):
    def test_checkout_day_is_not_a_night(self):
        # Fri -> Sun is the Friday and Saturday nights, not three days.
        self.assertEqual(stay_nights(FRI, SUN), [FRI, SAT])

    def test_same_day_counts_as_one_night(self):
        self.assertEqual(stay_nights(FRI, FRI), [FRI])

    def test_reversed_dates_do_not_produce_a_negative_stay(self):
        self.assertEqual(stay_nights(SUN, FRI), [SUN])

    def test_missing_dates_produce_no_nights(self):
        self.assertEqual(stay_nights(None, SUN), [])
        self.assertEqual(stay_nights(FRI, None), [])


class WeekendRateTests(TestCase):
    """Stays under three nights pay each night's own rate."""

    def test_a_single_weekday_night(self):
        # Monday night only.
        self.assertEqual(price_for_stay(make_hut(), MON, TUE), Decimal("1000.00"))

    def test_a_single_friday_night_is_a_weekend_night(self):
        self.assertEqual(price_for_stay(make_hut(), FRI, SAT), Decimal("1500.00"))

    def test_a_single_saturday_night_is_a_weekend_night(self):
        self.assertEqual(price_for_stay(make_hut(), SAT, SUN), Decimal("1500.00"))

    def test_a_sunday_night_is_a_weekday_night(self):
        # Sunday is a working day here -- only Fri and Sat are the weekend.
        self.assertEqual(price_for_stay(make_hut(), SUN, MON), Decimal("1000.00"))

    def test_friday_and_saturday_nights_are_both_weekend(self):
        # The specified case: 1500 + 1500.
        self.assertEqual(price_for_stay(make_hut(), FRI, SUN), Decimal("3000.00"))

    def test_a_mixed_two_night_stay_pays_each_night_its_own_rate(self):
        # Thursday night (weekday) + Friday night (weekend).
        thu = FRI - timedelta(days=1)
        self.assertEqual(price_for_stay(make_hut(), thu, SAT), Decimal("2500.00"))


class LongStayTests(TestCase):
    """Three nights or more drops the whole stay to the weekday rate."""

    def test_three_nights_over_a_weekend_are_all_weekday_rate(self):
        # The specified case: Fri, Sat, Sun nights -> 1000 x 3.
        self.assertEqual(price_for_stay(make_hut(), FRI, MON), Decimal("3000.00"))

    def test_the_third_night_is_effectively_free(self):
        two_weekend_nights = price_for_stay(make_hut(), FRI, SUN)
        three_nights = price_for_stay(make_hut(), FRI, MON)
        self.assertEqual(three_nights, two_weekend_nights)

    def test_a_longer_stay_stays_on_the_weekday_rate(self):
        # Fri, Sat, Sun, Mon nights.
        self.assertEqual(price_for_stay(make_hut(), FRI, TUE), Decimal("4000.00"))

    def test_three_pure_weekday_nights_are_unaffected(self):
        self.assertEqual(price_for_stay(make_hut(), SUN, WED), Decimal("3000.00"))

    def test_the_threshold_is_three_not_two(self):
        hut = make_hut()
        # Two nights spanning the weekend still pay weekend rates...
        self.assertEqual(price_for_stay(hut, FRI, SUN), Decimal("3000.00"))
        # ...and the discount only appears on the third.
        self.assertEqual(price_for_stay(hut, FRI, MON), Decimal("3000.00"))


class QuoteBreakdownTests(TestCase):
    def test_a_short_stay_reports_its_weekend_nights(self):
        q = quote(make_hut(), FRI, SUN)
        self.assertEqual(q["nights"], 2)
        self.assertEqual(q["weekend_nights"], 2)
        self.assertEqual(q["weekday_nights"], 0)
        self.assertFalse(q["long_stay"])
        self.assertEqual(q["total"], Decimal("3000.00"))

    def test_a_long_stay_is_billed_as_all_weekday_nights(self):
        q = quote(make_hut(), FRI, MON)
        self.assertEqual(q["nights"], 3)
        # Billed as weekday throughout even though two fell on the weekend.
        self.assertEqual(q["weekday_nights"], 3)
        self.assertEqual(q["weekend_nights"], 0)
        self.assertTrue(q["long_stay"])

    def test_the_breakdown_always_adds_up_to_the_total(self):
        for start, end in [(FRI, SAT), (FRI, SUN), (FRI, MON), (SUN, WED)]:
            q = quote(make_hut(), start, end)
            recomputed = (
                q["weekday_rate"] * q["weekday_nights"]
                + q["weekend_rate"] * q["weekend_nights"]
            )
            self.assertEqual(recomputed, q["total"], f"{start} -> {end}")

    def test_the_rates_are_carried_even_on_an_empty_quote(self):
        q = quote(make_hut(), None, None)
        self.assertEqual(q["total"], Decimal("0.00"))
        self.assertEqual(q["weekday_rate"], Decimal("1000.00"))


class MissingDataTests(TestCase):
    """A hut with no prices set must read as free, never crash the booking."""

    def test_a_hut_with_no_prices_is_zero(self):
        hut = Hut(title="t", description="d", size="small")
        self.assertEqual(price_for_stay(hut, FRI, MON), Decimal("0.00"))

    def test_no_hut_is_zero(self):
        self.assertEqual(price_for_stay(None, FRI, MON), Decimal("0.00"))

    def test_null_prices_are_treated_as_zero(self):
        hut = make_hut()
        hut.weekend_price = None
        self.assertEqual(price_for_stay(hut, FRI, SAT), Decimal("0.00"))


class BookingDateSignalTests(TestCase):
    """The stay total must be stamped onto BookingDate the moment it is created.

    BookingDate.total_price is what the payment-time recompute and the
    my-bookings screens read, so if the signal and the rule disagree the
    customer is charged one figure and shown another.
    """

    def make_booking_date(self, date_from, date_to, weekday="600.00", weekend="770.00"):
        hut = Hut.objects.create(
            title="Wahad Hut", description="d", size="small",
            weekday_price=Decimal(weekday), weekend_price=Decimal(weekend),
        )
        booking = Booking.objects.create(
            hut=hut, status="pending", persons_max_num=2, kids_max_num=0,
            guest_name="G", guest_email="g@example.invalid",
        )
        return BookingDate.objects.create(
            booking=booking, date_from=date_from, date_to=date_to,
        )

    def test_a_weekend_stay_is_stamped_at_the_weekend_rate(self):
        bd = self.make_booking_date(FRI, SUN)
        bd.refresh_from_db()
        self.assertEqual(bd.total_price, Decimal("1540.00"))  # 770 x 2

    def test_a_three_night_stay_is_stamped_at_the_weekday_rate(self):
        bd = self.make_booking_date(FRI, MON)
        bd.refresh_from_db()
        self.assertEqual(bd.total_price, Decimal("1800.00"))  # 600 x 3

    def test_the_stored_total_is_the_whole_stay_not_a_nightly_rate(self):
        # Guards the double-multiplication bug: the booking/extension
        # serializers used to multiply this figure by the night count again.
        bd = self.make_booking_date(FRI, MON)
        bd.refresh_from_db()
        self.assertEqual(bd.total_price, price_for_stay(bd.booking.hut, FRI, MON))

    def test_a_hut_with_no_rates_does_not_crash_the_booking(self):
        bd = self.make_booking_date(FRI, MON, weekday="0", weekend="0")
        bd.refresh_from_db()
        self.assertEqual(bd.total_price, Decimal("0.00"))


class InvoiceLineTests(TestCase):
    """Invoice lines must be arithmetically honest.

    products/daftra.py reconciles the sum of quantity x unit_price against
    what was actually charged and bills any gap as a discount, so a blended
    nightly rate that does not divide evenly would surface as a phantom
    discount on the customer's invoice.
    """

    def build_order(self, date_from, date_to):
        from .serializers import BookingDetailsAdminSerializer

        hut = Hut.objects.create(
            title="Wahad Hut", title_ar="كوخ وهاد", description="d", size="small",
            weekday_price=Decimal("600.00"), weekend_price=Decimal("770.00"),
        )
        booking = Booking.objects.create(
            hut=hut, status="paid", persons_max_num=2, kids_max_num=0,
            guest_name="G", guest_email="g@example.invalid",
        )
        BookingDate.objects.create(
            booking=booking, date_from=date_from, date_to=date_to,
        )
        data = BookingDetailsAdminSerializer(booking).data
        return [row for row in data["main_order"] if row["type"] == "hut"]

    def test_a_mixed_stay_splits_into_a_weekday_and_a_weekend_line(self):
        # Thursday night (weekday) + Friday night (weekend) = 2 nights, so
        # the long-stay rate does not apply and the rates differ.
        thu = FRI - timedelta(days=1)
        lines = self.build_order(thu, SAT)
        self.assertEqual(len(lines), 2)
        by_qty = {line["quantity"]: line for line in lines}
        self.assertEqual(len(by_qty), 1, "both lines are 1 night")

    def test_a_long_stay_is_a_single_line_at_one_rate(self):
        lines = self.build_order(FRI, MON)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 3)
        self.assertEqual(Decimal(lines[0]["price"]), Decimal("600.00"))

    def test_every_line_multiplies_out_exactly(self):
        for start, end in [(FRI, SAT), (FRI, SUN), (FRI, MON), (SUN, WED)]:
            for line in self.build_order(start, end):
                self.assertEqual(
                    Decimal(line["price"]) * line["quantity"],
                    Decimal(line["total_price"]),
                    f"{start} -> {end}: {line['title']}",
                )

    def test_the_lines_add_up_to_the_stay_total(self):
        for start, end in [(FRI, SAT), (FRI, SUN), (FRI, MON), (SUN, WED)]:
            lines = self.build_order(start, end)
            billed = sum(Decimal(line["total_price"]) for line in lines)
            hut = Hut.objects.filter(title="Wahad Hut").last()
            self.assertEqual(billed, price_for_stay(hut, start, end), f"{start}->{end}")

    def test_the_line_titles_name_which_nights_they_cover(self):
        lines = self.build_order(FRI, SUN)
        self.assertIn("Weekend nights", lines[0]["title"])
        self.assertIn("نهاية الأسبوع", lines[0]["title_ar"])


class DashboardRateSaveTests(TestCase):
    """The dashboard's pricing step must actually persist the rates.

    It previously collected and validated both figures, then left them out of
    the request body -- and there was no column to store them in anyway, so
    every hut kept whatever price its seed data had written. That is why the
    live site showed the same 5 SAR for every hut.
    """

    def setUp(self):
        from rest_framework.test import APIClient

        self.hut = Hut.objects.create(
            title="Malath Hut", description="d", size="meduim",
            weekday_price=Decimal("900.00"), weekend_price=Decimal("1100.00"),
        )
        self.admin = get_user_model().objects.create_user(
            email="rates-admin@example.invalid", password="pw-not-a-real-secret",
            role="admin", is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.url = f"/api/products/huts/available-dates/{self.hut.pk}/"

    def payload(self, **overrides):
        body = {
            "weekday_price": "950.00",
            "weekend_price": "1180.00",
            "available_dates": [{"date_from": "2026-01-01", "date_to": "2026-12-31"}],
            "promocodes": [],
        }
        body.update(overrides)
        return body

    def test_posting_rates_persists_them_on_the_hut(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.hut.refresh_from_db()
        self.assertEqual(self.hut.weekday_price, Decimal("950.00"))
        self.assertEqual(self.hut.weekend_price, Decimal("1180.00"))

    def test_the_saved_rates_come_back_in_the_response(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(Decimal(str(response.data["weekday_price"])), Decimal("950.00"))
        self.assertEqual(Decimal(str(response.data["weekend_price"])), Decimal("1180.00"))

    def test_a_price_sent_on_a_date_range_is_ignored(self):
        # Older dashboard builds still send this; ranges are availability only.
        body = self.payload(available_dates=[
            {"date_from": "2026-01-01", "date_to": "2026-12-31", "price": "5.00"}
        ])
        response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(AvailableDateRanges.objects.get(huts=self.hut).price)

    def test_a_negative_rate_is_refused(self):
        response = self.client.post(
            self.url, self.payload(weekday_price="-1.00"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.hut.refresh_from_db()
        self.assertEqual(self.hut.weekday_price, Decimal("900.00"), "must not persist")

    def test_omitting_the_rates_leaves_them_untouched(self):
        body = self.payload()
        del body["weekday_price"]
        del body["weekend_price"]
        response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.hut.refresh_from_db()
        self.assertEqual(self.hut.weekday_price, Decimal("900.00"))

    def test_a_saved_rate_immediately_changes_what_a_stay_costs(self):
        self.client.post(self.url, self.payload(), format="json")
        self.hut.refresh_from_db()
        # 2 weekend nights at the new 1180 rate.
        self.assertEqual(price_for_stay(self.hut, FRI, SUN), Decimal("2360.00"))


class PosterPriceTests(TestCase):
    """The three real huts, at the rates on the current price card."""

    CASES = [
        ("Wahad", "600.00", "770.00"),
        ("Malath", "900.00", "1100.00"),
        ("Qimma", "1450.00", "1650.00"),
    ]

    def test_a_weekend_break_charges_both_weekend_nights(self):
        for name, weekday, weekend in self.CASES:
            hut = make_hut(weekday, weekend)
            expected = Decimal(weekend) * 2
            self.assertEqual(price_for_stay(hut, FRI, SUN), expected, name)

    def test_three_nights_charge_the_weekday_rate_throughout(self):
        for name, weekday, weekend in self.CASES:
            hut = make_hut(weekday, weekend)
            expected = Decimal(weekday) * 3
            self.assertEqual(price_for_stay(hut, FRI, MON), expected, name)

    def test_the_long_stay_rule_is_always_a_discount(self):
        # The real invariant: a 3+ night stay never costs more than it would
        # if each night were charged at its own rate. (Not "3 nights cost the
        # same as 2" -- that equality is a coincidence of the 1000/1500
        # numbers the rule was illustrated with, and does not hold at the
        # rates actually in use.)
        for name, weekday, weekend in self.CASES:
            hut = make_hut(weekday, weekend)
            undiscounted = Decimal(weekend) * 2 + Decimal(weekday)  # Fri, Sat, Sun
            self.assertLess(
                price_for_stay(hut, FRI, MON),
                undiscounted,
                f"{name}: the 3-night rate must beat per-night pricing",
            )

    def test_at_the_real_rates_a_third_night_still_adds_to_the_bill(self):
        # Documents actual behaviour so it is not mistaken for a bug: at the
        # rates on the price card the third night is discounted, not free.
        # Wahad: Fri+Sat = 1540, Fri+Sat+Sun = 1800 (vs 2140 undiscounted).
        wahad = make_hut("600.00", "770.00")
        self.assertEqual(price_for_stay(wahad, FRI, SUN), Decimal("1540.00"))
        self.assertEqual(price_for_stay(wahad, FRI, MON), Decimal("1800.00"))

    def test_adding_a_night_never_makes_a_stay_cheaper(self):
        # A rate pair where the weekend price is more than 1.5x the weekday
        # price would make a 2-night weekend dearer than a 3-night stay,
        # so guests would game it by booking a night they do not want.
        # None of the real pairs do this; this asserts they stay that way.
        for name, weekday, weekend in self.CASES:
            hut = make_hut(weekday, weekend)
            self.assertLessEqual(
                price_for_stay(hut, FRI, SUN),
                price_for_stay(hut, FRI, MON),
                f"{name}: booking a 3rd night must not lower the total",
            )
