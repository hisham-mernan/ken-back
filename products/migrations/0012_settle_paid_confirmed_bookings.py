"""Label fully-paid bookings as paid.

Booking #16 carried its full 1000.00, had its QR issued, and was still marked
"confirmed" -- the status the desk reads as *awaiting payment*. Money had
arrived without the status following it, so a settled stay looked outstanding
on the calendar and in the book.

Written as a data migration rather than done through the API on purpose. The
API route runs the confirmed -> paid signal, which emails the guest a fresh
booking confirmation, emails the office a "new order paid" notice and syncs
another Daftra invoice. For a stay in the past that would mean confusing a
real customer and double-counting revenue to correct a label. `update()`
writes the column and fires nothing.

Deliberately expressed as a condition rather than a hardcoded id: if another
booking is in the same state, it has the same problem and the same fix.
"""
from django.db import migrations


def settle(apps, schema_editor):
    Booking = apps.get_model("products", "Booking")
    stuck = Booking.objects.filter(status="confirmed", paid__gt=0, not_paid__lte=0)
    for booking in stuck:
        print(f"  booking {booking.pk}: paid {booking.paid} of "
              f"{booking.total_price} -- confirmed -> paid")
    stuck.update(status="paid", is_paid=True)


def unsettle(apps, schema_editor):
    """Deliberately not reversible.

    Rolling a paid booking back to "confirmed" would put it in front of the
    expiry sweep, which cancels unpaid holds. There is no state worth
    returning to here.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0011_booking_confirmed_at"),
    ]

    operations = [
        migrations.RunPython(settle, unsettle),
    ]
