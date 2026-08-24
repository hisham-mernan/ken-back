"""Hut nightly pricing -- one rule, in one place.

Every path that needs the price of a stay calls quote() here: booking create,
booking update, the BookingDate signal, the admin/invoice order builder and
the payment-time recompute. Before this module each of those carried its own
copy of the date maths and they had drifted apart -- two of them looked for a
date range *containing* the whole stay while the others accepted any
*overlapping* range, so the same stay could be priced at zero on the booking
and non-zero on the invoice.

The rule
--------

* A stay is the nights in ``[date_from, date_to)``. Checkout day is not a
  night, and each night is named by the day it starts on. This is what the
  booking calendar already sends and what the site already charged: check in
  Friday and out Sunday is two nights, Friday's and Saturday's.
* Friday and Saturday nights are weekend nights. Everything else is a weekday
  night. (The Saudi weekend, as specified -- not the Sat/Sun default that
  Python's ``weekday()`` might tempt you into.)
* A stay of three nights or more is charged the weekday rate for *every*
  night, weekends included. Shorter stays pay each night's own rate.

So for a hut at 1000 weekday / 1500 weekend:

    check in Fri, out Mon  -> 3 nights (Fri, Sat, Sun) -> 3 x 1000 = 3000
    check in Fri, out Sun  -> 2 nights (Fri, Sat)      -> 1500 + 1500 = 3000

which is the intended shape: the third night is effectively free rather than
the stay getting more expensive.
"""
from datetime import timedelta
from decimal import Decimal

# Python's date.weekday(): Monday=0 ... Friday=4, Saturday=5, Sunday=6.
WEEKEND_WEEKDAYS = frozenset({4, 5})

# At or above this many nights the whole stay drops to the weekday rate.
MIN_NIGHTS_FOR_WEEKDAY_RATE = 3

ZERO = Decimal("0.00")


def _money(value):
    """A price as Decimal, treating None/blank as zero rather than exploding."""
    if value in (None, ""):
        return ZERO
    return value if isinstance(value, Decimal) else Decimal(str(value))


def is_weekend_night(day):
    """Is the night *starting* on this date a weekend night?"""
    return day.weekday() in WEEKEND_WEEKDAYS


def stay_nights(date_from, date_to):
    """The nights of a stay, each represented by the date it starts on.

    Half-open: checkout day is not a night. A same-day booking
    (``date_from == date_to``) counts as the single night of that day, which
    is how the old code behaved via its ``if nights == 0: nights = 1`` guard.
    """
    if not date_from or not date_to:
        return []
    if date_to <= date_from:
        return [date_from]
    span = (date_to - date_from).days
    return [date_from + timedelta(days=i) for i in range(span)]


def quote(hut, date_from, date_to):
    """Price a stay in one hut.

    Returns a dict rather than a bare total so invoice and order builders can
    show the breakdown without recomputing it (and getting a different
    answer):

        {
          "nights":          int,
          "weekday_nights":  int,
          "weekend_nights":  int,   # 0 when the long-stay rate applies
          "weekday_rate":    Decimal,
          "weekend_rate":    Decimal,
          "long_stay":       bool,  # True when 3+ nights forced the weekday rate
          "total":           Decimal,
        }

    ``weekday_nights``/``weekend_nights`` describe how the stay was *charged*,
    not the calendar -- on a long stay every night is a weekday night for
    billing purposes even if it fell on a Friday.
    """
    nights = stay_nights(date_from, date_to)
    weekday_rate = _money(getattr(hut, "weekday_price", None))
    weekend_rate = _money(getattr(hut, "weekend_price", None))

    empty = {
        "nights": 0,
        "weekday_nights": 0,
        "weekend_nights": 0,
        "weekday_rate": weekday_rate,
        "weekend_rate": weekend_rate,
        "long_stay": False,
        "total": ZERO,
    }
    if hut is None or not nights:
        return empty

    long_stay = len(nights) >= MIN_NIGHTS_FOR_WEEKDAY_RATE
    if long_stay:
        weekday_nights, weekend_nights = len(nights), 0
    else:
        weekend_nights = sum(1 for day in nights if is_weekend_night(day))
        weekday_nights = len(nights) - weekend_nights

    total = (weekday_rate * weekday_nights) + (weekend_rate * weekend_nights)

    return {
        "nights": len(nights),
        "weekday_nights": weekday_nights,
        "weekend_nights": weekend_nights,
        "weekday_rate": weekday_rate,
        "weekend_rate": weekend_rate,
        "long_stay": long_stay,
        "total": total,
    }


def lowest_rate(hut):
    """The cheaper of a hut's two rates, or None when neither is set.

    Keeps the long-standing ``lowest_price`` field meaningful as a "from"
    figure for anything that wants a single number. The site itself now shows
    both rates rather than this one.
    """
    rates = [
        rate
        for rate in (
            _money(getattr(hut, "weekday_price", None)),
            _money(getattr(hut, "weekend_price", None)),
        )
        if rate > 0
    ]
    return min(rates) if rates else None


def price_for_stay(hut, date_from, date_to):
    """Just the total, for the callers that do not need the breakdown."""
    return quote(hut, date_from, date_to)["total"]


def price_for_booking_date(booking_date):
    """Total for one BookingDate row, hut taken from its booking."""
    booking = getattr(booking_date, "booking", None)
    hut = getattr(booking, "hut", None) if booking else None
    return price_for_stay(hut, booking_date.date_from, booking_date.date_to)
