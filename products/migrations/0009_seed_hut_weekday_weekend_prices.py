"""Seed the new weekday/weekend rates from the current price card.

Without this every hut would read as 0 SAR the moment the new fields ship,
because the old prices lived on AvailableDateRanges rows and are no longer
consulted. (Those rows are left alone -- they still say which dates are
bookable; only their price column stops being read.)

Rates come from the published price card:

    كوخ وهاد الصغير   Wahad     600 weekday /  770 weekend
    كوخ ملاذ الوسط    Malath    900 weekday / 1100 weekend
    كوخ قمة الكبير    Qimma    1450 weekday / 1650 weekend

Keyed on the hut's *name*, not its `size` column. The card labels the huts
small/medium/large, so size looks like the obvious key -- but the column does
not agree with those labels: Wahad, the small hut on the card, is stored as
'large'. Matching on size would have charged 1450 a night for the 600 hut.

A hut whose name matches none of the three is deliberately left at 0 rather
than guessed at. It then shows no price on the site until someone sets one in
the dashboard, which is the safe failure: no price is recoverable, a wrong
price is money.

Only huts still sitting at 0 are touched, so re-running this cannot stamp on
a rate an admin has since edited.
"""
from decimal import Decimal

from django.db import migrations

# Matched case-insensitively against title and title_ar, so "Wahad Hut" and
# "كوخ وهاد الصغير" both land on the same rates.
RATES_BY_NAME = {
    ("wahad", "وهاد"): (Decimal("600.00"), Decimal("770.00")),
    ("malath", "ملاذ"): (Decimal("900.00"), Decimal("1100.00")),
    ("qimma", "قمة"): (Decimal("1450.00"), Decimal("1650.00")),
}


def _rates_for(hut):
    haystack = f"{hut.title or ''} {hut.title_ar or ''}".lower()
    for names, rates in RATES_BY_NAME.items():
        if any(name in haystack for name in names):
            return rates
    return None


def seed_rates(apps, schema_editor):
    Hut = apps.get_model("products", "Hut")
    for hut in Hut.objects.filter(weekday_price=0, weekend_price=0):
        rates = _rates_for(hut)
        if not rates:
            continue
        hut.weekday_price, hut.weekend_price = rates
        hut.save(update_fields=["weekday_price", "weekend_price"])


def clear_rates(apps, schema_editor):
    # Reversing only undoes what this migration could have written; a rate
    # edited since is left as it is rather than being silently discarded.
    Hut = apps.get_model("products", "Hut")
    for hut in Hut.objects.all():
        rates = _rates_for(hut)
        if rates and (hut.weekday_price, hut.weekend_price) == rates:
            hut.weekday_price, hut.weekend_price = Decimal("0"), Decimal("0")
            hut.save(update_fields=["weekday_price", "weekend_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0008_hut_weekday_price_hut_weekend_price"),
    ]

    operations = [
        migrations.RunPython(seed_rates, clear_rates),
    ]
