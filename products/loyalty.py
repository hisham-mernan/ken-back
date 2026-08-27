"""Loyalty tiers, and the discount they earn.

A customer who keeps coming back moves up a tier and every later booking is
cheaper:

    3 stays -> bronze,  5% off
    5 stays -> silver, 10% off
    7 stays -> gold,   15% off

Two decisions worth knowing about, because both are easy to get wrong in a
way that costs money:

**Only bookings that were paid for count.** Anyone can create a booking; the
form is open to guests and nothing stops a browser making seven of them. If
unpaid bookings counted, a first-time visitor could hand themselves 15% off
in a couple of minutes. A booking counts once money has actually been taken
against it, and a cancelled or refunded stay stops counting.

**The booking being made never counts towards its own discount.** It has not
been paid for yet, so the count is of what came before it. In practice the
third paid stay earns bronze and the fourth is the first to be charged at it.

A guest has no account, so their history hangs off the phone number, matched
the way `phone_tail` matches it -- the same line typed three different ways is
one customer. A registered booking is counted by account *and* by the number
on it, so signing up does not reset the history built as a guest.

Nothing here is stored as a running total. The tier is derived from the
bookings themselves every time it is asked for, so it cannot drift away from
what the book actually says. What *is* recorded, on each booking, is the
discount that was applied to it and why -- otherwise a cheaper booking has no
explanation six months later.
"""
from decimal import Decimal

from django.db.models import Q

# Highest first: the first threshold met wins.
TIERS = (
    (7, "gold", 15),
    (5, "silver", 10),
    (3, "bronze", 5),
)

# Money has been taken against these. Anything else -- pending, confirmed but
# unpaid, cancelled, refunded -- does not move a customer up a tier.
QUALIFYING_STATUSES = ("paid", "partially_paid")


def _identity_filter(user_id=None, phone=None):
    """Bookings belonging to this customer, by account or by phone."""
    from .utils import phone_tail

    condition = Q()
    matched = False

    if user_id:
        condition |= Q(user_id=user_id)
        matched = True

    tail = phone_tail(phone)
    if tail:
        condition |= Q(guest_phone__endswith=tail) | Q(user__phone__endswith=tail)
        matched = True

    return condition if matched else None


def qualifying_count(user_id=None, phone=None, exclude_pk=None):
    """How many paid stays this customer has behind them."""
    from .models import Booking

    condition = _identity_filter(user_id, phone)
    if condition is None:
        return 0

    bookings = Booking.objects.filter(condition, status__in=QUALIFYING_STATUSES,
                                      paid__gt=0)
    if exclude_pk:
        bookings = bookings.exclude(pk=exclude_pk)
    return bookings.distinct().count()


def tier_for_count(count):
    for threshold, name, percent in TIERS:
        if count >= threshold:
            return name, percent
    return "", 0


def status(user_id=None, phone=None, exclude_pk=None):
    """The customer's standing, ready to show or to price with."""
    count = qualifying_count(user_id, phone, exclude_pk)
    name, percent = tier_for_count(count)

    nxt = ""
    remaining = 0
    for threshold, next_name, _ in reversed(TIERS):
        if count < threshold:
            nxt, remaining = next_name, threshold - count
            break

    return {
        "tier": name,
        "percent": percent,
        "stays": count,
        "next_tier": nxt,
        "stays_to_next": remaining,
    }


def resolve_discount(*, promo=None, user_id=None, phone=None, exclude_pk=None):
    """The single discount to charge this booking at, and why.

    A promo code and a loyalty tier are not added together: 15% off for being
    a gold customer plus 20% off a campaign code is 35% off, which no one
    intends. The better of the two is applied and the other is ignored, so a
    loyal customer is never worse off for having a code and vice versa.

    Returns ``(percent, source)`` where source is "" , "promocode" or
    "loyalty:<tier>".
    """
    promo_percent = int(promo.percentage or 0) if promo else 0
    standing = status(user_id=user_id, phone=phone, exclude_pk=exclude_pk)
    loyalty_percent = standing["percent"]

    if promo_percent >= loyalty_percent:
        return (promo_percent, "promocode" if promo_percent else "")
    return (loyalty_percent, f"loyalty:{standing['tier']}")


def apply_discount(total, percent):
    """The total after a whole-percentage discount."""
    if not percent:
        return total
    total = Decimal(str(total))
    return total - (Decimal(percent) / Decimal("100")) * total
