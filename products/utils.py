

from datetime import timedelta
from django.core.exceptions import ValidationError
from .models import *
# def is_date_range_valid_for_hut(hut, date_from, date_to):
#     if date_from > date_to:
#         return False ,None

#     current_date = date_from
#     while current_date <= date_to:
#         if not AvailableDateRanges.objects.filter(
#             huts=hut,
#             date_from__lte=current_date,
#             date_to__gte=current_date
#         ).exists():
#             return False, current_date
#         current_date += timedelta(days=1)
    
#     return True, None



from datetime import timedelta
from decimal import Decimal
from .models import AvailableDateRanges, BookingDate, Booking

def is_date_range_valid_for_hut(hut, date_from, date_to):
    if date_from > date_to:
        return False, None

    current_date = date_from
    while current_date <= date_to:
        # Check if the hut is available on this date
        if not AvailableDateRanges.objects.filter(
            huts=hut,
            date_from__lte=current_date,
            date_to__gte=current_date
        ).exists():
            return False, current_date

        # Check if there's a conflicting booking on this date
        conflicting_booking = BookingDate.objects.filter(
            booking__hut=hut,
            booking__status__in=ACTIVE_BOOKING_STATUSES,
            date_from__lte=current_date,
            date_to__gte=current_date
        ).exists()

        if conflicting_booking:
            return False, current_date

        current_date += timedelta(days=1)

    return True, None

    
    
    





def adjust_available_ranges_after_booking(hut, booking_from, booking_to):
    
    matching_ranges = AvailableDateRanges.objects.filter(
        huts=hut,
        date_from__lte=booking_from,
        date_to__gte=booking_to
    )

    if not matching_ranges.exists():
        return False, "The booking range is not available anymore."

    matched_range = matching_ranges.first()

    original_from = matched_range.date_from
    original_to = matched_range.date_to

   
    matched_range.delete()

    # Create "before" split range
    if original_from < booking_from:
        AvailableDateRanges.objects.create(
            date_from=original_from,
            date_to=booking_from - timedelta(days=1),
            huts=hut
        )

    # Create "after" split range
    if booking_to < original_to:
        AvailableDateRanges.objects.create(
            date_from=booking_to + timedelta(days=1),
            date_to=original_to,
            huts=hut
        )

    return True, "Available ranges adjusted successfully."



def validate_event_ticket(event, quantity, date):
    if quantity < event.min_purchasable_quantity or quantity > event.max_purchasable_quantity:
         return 0
    
    if not event.available_dates.filter(date=date).exists():
         return 1

def validate_service_ticket(service, quantity, date):
    if quantity < service.min_purchasable_quantity or quantity > service.max_purchasable_quantity:
         return 0
    
    if not service.available_dates.filter(date=date).exists():
         return 1

def validate_item_ticket(item, quantity):
    if quantity < item.min_purchasable_quantity or quantity > item.max_purchasable_quantity:
        return 0
    
    
    
    
    
    

def restore_available_ranges_to_hut(hut, date_from, date_to):
   
        AvailableDateRanges.objects.create(
            date_from=date_from,
            date_to=date_to,
            huts=hut
        )
        
        
        
        
        
        
# def change_booking_status(booking, new_status):
#     print(booking.status)

#     if booking.status == 'confirmed' and new_status == 'confirmed':
#         print("kk")
#         return False, {"error": "Booking is already confirmed."}

#     if booking.status == 'paid' and new_status in ['confirmed', 'pending']:
#         return False, {"error": "Booking is already paid."}

#     if new_status != 'confirmed':
#         print("55")
#         return False, {"error": "it must be confirmed only"}
#         # booking.save()
#         # return True, {"success": f"Booking status updated to '{new_status}'."}

#     # Validation and reservation
#     date_obj = booking.dates.first()
#     if not date_obj:
#         return False, {"error": "Booking does not have any date range."}

#     hut = booking.hut
#     date_from = date_obj.date_from
#     date_to = date_obj.date_to

#     # Hut availability
#     is_valid, invalid_date = is_date_range_valid_for_hut(hut, date_from, date_to)
#     if not is_valid:
#         return False, {"error": f"The hut is not available from {date_from} to {date_to}."}

#     # Events
#     for event_ticket in booking.events.all():
#         event = event_ticket.event
#         qty = event_ticket.quantity
#         ticket_date = event_ticket.date

#         result = validate_event_ticket(event, qty, ticket_date)
#         if result == 0:
#             return False, {"error": f"Event '{event.title}' exceeds capacity."}
#         if result == 1:
#             return False, {"error": f"Event '{event.title}' not available on {ticket_date}."}

#         event.capacity -= qty
#         print(event.capacity )
#         event.save()

#     # Services
#     for service_ticket in booking.services.all():
#         service = service_ticket.service
#         qty = service_ticket.quantity
#         ticket_date = service_ticket.date

#         result = validate_service_ticket(service, qty, ticket_date)
#         if result == 0:
#             return False, {"error": f"Service '{service.title}' exceeds capacity on {ticket_date}."}
#         if result == 1:
#             return False, {"error": f"Service '{service.title}' not available on {ticket_date}."}

#         service.capacity -= qty
#         service.save()

   
#     for item_ticket in booking.special_items.all():
#         item = item_ticket.item
#         qty = item_ticket.quantity

#         if validate_item_ticket(item, qty) == 0:
#             return False, {"error": f"Item '{item.title}' exceeds available quantity."}

#         item.capacity -= qty
#         item.save()

    
#     ok, msg = adjust_available_ranges_after_booking(hut, date_from, date_to)
#     if not ok:
#         return False, {"error": msg}

#     # Confirm the booking
#     booking.status = 'confirmed'
#     booking.save()

#     return True, {
#         "success": "Booking confirmed successfully. Please pay within 30 minutes or the booking will be cancelled."
#     }



def expand_date_range(date_from, date_to):
    
    delta = (date_to - date_from).days
    return [date_from + timedelta(days=i) for i in range(delta + 1)]










import uuid
# utils.py
import qrcode
from io import BytesIO
from email.mime.image import MIMEImage
from django.core.files import File

def generate_qr_code_image(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return File(buffer, name="qr_code.png")





from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Booking
import socket

# 
UNLOCK_CODE = "0202F2AC000203E8B503"
REJECT_CODE = "0202F2AD0001035F03"

# tcp send code to hard ware
def send_code_to_hardware(ip, port, hex_code):
    try:
        command = bytes.fromhex(hex_code)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(command)
            response = s.recv(1024)
            return response.hex()
    except Exception as e:
        return str(e)












# ###########################################################new flow


from datetime import timedelta
from .models import Hut, BookingDate, Booking

def is_hut_available(hut_id, date_from, date_to,booking_obj):
    # Ensure valid date range
    if date_from > date_to:
        return False, "Invalid date range"

    # Get hut instance
    try:
        hut = Hut.objects.get(id=hut_id)
    except Hut.DoesNotExist:
        return False, "Hut does not exist"

    # Get all relevant bookings with status paid or confirmed
    bookings = Booking.objects.filter(
        hut=hut,
        status__in=ACTIVE_BOOKING_STATUSES
    )
    print(booking_obj,"kkoo")
    if booking_obj:
        print("enter")
        bookings = bookings.exclude(id=booking_obj.id)

    # Check for overlapping BookingDate entries
    for booking in bookings:
     
        for booking_date in booking.dates.all():


            if (
                date_from <= booking_date.date_to and
                date_to >= booking_date.date_from
            ):
                # Overlap found
                return False, f"Hut is booked from {booking_date.date_from} to {booking_date.date_to}"

    return True, None












from datetime import timedelta,timezone
from .models import Hut, AvailableDateRanges, Booking, BookingDate
from django.utils.timezone import now
def get_hut_available_dates(hut_or_id):
    if isinstance(hut_or_id, Hut):
        hut = hut_or_id
    else:
        try:
            hut = Hut.objects.get(id=hut_or_id)
        except Hut.DoesNotExist:
            return []

    # Step 1: Get all available date ranges in the future
    today = now().date()
    available_ranges = AvailableDateRanges.objects.filter(
        huts=hut,
        date_to__gte=today
    ).order_by("date_from")

    # Step 2: Get all booked date ranges (paid or confirmed)
    bookings = Booking.objects.filter(hut=hut, status__in=ACTIVE_BOOKING_STATUSES).prefetch_related('dates')
    booked_ranges = []
    for booking in bookings:
        for b_date in booking.dates.all():
            booked_ranges.append((b_date.date_from, b_date.date_to))

    # Step 3: Generate final available ranges by subtracting booked ranges
    final_ranges = []

    for avail in available_ranges:
        start = max(avail.date_from, today)  # skip past dates
        end = avail.date_to

        current_range = [(start, end)]

        for b_start, b_end in booked_ranges:
            new_ranges = []

            for r_start, r_end in current_range:
                if b_end < r_start or b_start > r_end:
                    # No overlap
                    new_ranges.append((r_start, r_end))
                else:
                    # Overlap exists, slice the range
                    if r_start < b_start:
                        new_ranges.append((r_start, b_start - timedelta(days=1)))
                    if b_end < r_end:
                        new_ranges.append((b_end + timedelta(days=1), r_end))

            current_range = new_ranges

        for r_start, r_end in current_range:
            if r_start <= r_end:
                final_ranges.append({
                    "date_from": r_start,
                    "date_to": r_end,
                    "price": avail.price,
                    # "promo_code": avail.promo_code,
                    # "percentage": avail.precentage
                })

    return final_ranges











        
def change_booking_status(booking, new_status):
    print(booking.status)
    print(booking.id)

    if booking.status == 'confirmed' and new_status == 'confirmed':
        print("kk")
        return False, {"error": "Booking is already confirmed."}

    if booking.status == 'paid' and new_status in ['confirmed', 'pending']:
        return False, {"error": "Booking is already paid."}

    if new_status != 'confirmed':
        print("55")
        return False, {"error": "it must be confirmed only"}
        # booking.save()
        # return True, {"success": f"Booking status updated to '{new_status}'."}

    # Validation and reservation
    date_obj = booking.dates.first()
    if not date_obj:
        return False, {"error": "Booking does not have any date range."}

    hut = booking.hut
    date_from = date_obj.date_from
    date_to = date_obj.date_to

    # Hut availability
    is_valid, invalid_date = is_hut_available(hut.id, date_from, date_to,booking)
    print(is_valid,"ttt")
    if not is_valid:
        return False, {"error": f"The hut is not available from {date_from} to {date_to}."}

    # Events
    for event_ticket in booking.events.all():
        event = event_ticket.event
        qty = event_ticket.quantity
        ticket_date = event_ticket.date
        event_date=AvailableDateEvent.objects.filter(date=ticket_date).first()
        print(ticket_date,"utils-eventdata")

        result = validate_event_ticket(event, qty, ticket_date)
        if result == 0:
            return False, {"error": f"Event '{event.title}' exceeds capacity."}
        if result == 1:
            return False, {"error": f"Event '{event.title}' not available on {ticket_date}."}

        event_date.capacity -= qty
        # print(event.capacity )
        event.save()

    # Services
    for service_ticket in booking.services.all():
        service = service_ticket.service
        qty = service_ticket.quantity
        ticket_date = service_ticket.date

        result = validate_service_ticket(service, qty, ticket_date)
        if result == 0:
            return False, {"error": f"Service '{service.title}' exceeds capacity on {ticket_date}."}
        if result == 1:
            return False, {"error": f"Service '{service.title}' not available on {ticket_date}."}

        service.capacity -= qty
        service.save()

   
    for item_ticket in booking.special_items.all():
        item = item_ticket.item
        qty = item_ticket.quantity

        if validate_item_ticket(item, qty) == 0:
            return False, {"error": f"Item '{item.title}' exceeds available quantity."}

        item.capacity -= qty
        item.save()

    
    # ok, msg = adjust_available_ranges_after_booking(hut, date_from, date_to)
    # if not ok:
    #     return False, {"error": msg}

    # Confirm the booking
    booking.status = 'confirmed'
    booking.save()

    return True, {
        "success": "Booking confirmed successfully. Please pay within 30 minutes or the booking will be cancelled."
    }


def attach_invoice_pdf(message, booking):
    """Attach the booking's invoice to an outgoing email.

    The customer's copy travels with the email rather than as a link, because
    Daftra's own invoice links redirect to a Daftra sign-in and a guest has no
    Daftra account. Never raises: a failed render must not stop a confirmation
    that a paying customer is waiting for.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        from .invoice_pdf import render_invoice_pdf

        message.attach(
            f"invoice-booking-{booking.pk}.pdf",
            render_invoice_pdf(booking),
            "application/pdf",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not attach invoice for booking %s: %s", booking.pk, exc)
        return False


def send_booking_confirmation(booking):
    """Email the booker their confirmation, booking details and QR code.

    Sent for every paid booking, whether it belongs to an account or was made
    as a guest. Guests also get a link back to their booking, since they have
    no account to sign into.

    Never raises. This runs off the back of a payment that has already
    succeeded, so a mail problem must not be able to disturb that.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from .map_preview import email_context as map_email_context

        recipient = (booking.contact_email or "").strip()
        if not recipient:
            logger.warning(
                "Booking %s has no contact email; confirmation not sent.", booking.pk
            )
            return False

        main_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        booking_link = (
            f"{base_url}/booking/{booking.access_token}"
            if booking.is_guest_booking and booking.access_token
            else f"{base_url}/my-booking"
        )

        context = {
            "booking": booking,
            "contact_name": booking.contact_name or "there",
            "main_date": main_date,
            "dates": booking.dates.all(),
            "hut": booking.hut,
            "is_guest": booking.is_guest_booking,
            "booking_link": booking_link,
            # Referenced by the template as an inline attachment, so the code
            # still shows when a client blocks remote images.
            "qr_cid": "booking_qr",
        }
        # Where to turn up: a map picture and a link to the place.
        context.update(map_email_context(booking.hut))
        html = render_to_string("booking_confirmation.html", context)

        message = EmailMultiAlternatives(
            subject=f"KEN - Booking #{booking.pk} confirmed",
            body=strip_tags(html),
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient],
        )
        message.attach_alternative(html, "text/html")

        attach_invoice_pdf(message, booking)
        attach_map_preview(message, booking)

        qr_bytes = _booking_qr_bytes(booking)
        if qr_bytes:
            image = MIMEImage(qr_bytes, _subtype="png")
            image.add_header("Content-ID", "<booking_qr>")
            image.add_header("Content-Disposition", "inline",
                             filename=f"booking_{booking.pk}_qr.png")
            message.attach(image)
            message.mixed_subtype = "related"

        message.send(fail_silently=False)
        logger.info("Booking confirmation sent to %s for booking %s",
                    recipient[:50], booking.pk)
        return True
    except Exception as exc:
        logger.exception(
            "Failed to send booking confirmation for booking %s: %s", booking.pk, exc
        )
        return False


def attach_map_preview(message, booking):
    """Attach the location picture inline, if one has been built for this hut.

    Mirrors the booking QR beside it: carried with the email rather than
    fetched, so a client that blocks remote images still shows it. Returns
    True when something was attached.
    """
    from .map_preview import preview_bytes

    data = preview_bytes(getattr(booking, "hut", None))
    if not data:
        return False
    image = MIMEImage(data, _subtype="png")
    image.add_header("Content-ID", "<booking_map>")
    image.add_header("Content-Disposition", "inline", filename="ken-location.png")
    message.attach(image)
    message.mixed_subtype = "related"
    return True


def _booking_qr_bytes(booking):
    """PNG bytes for the booking QR, regenerated rather than re-downloaded.

    The stored image lives in remote storage, so rebuilding it locally avoids
    a network round trip failing the email.
    """
    try:
        buffer = BytesIO()
        qrcode.make(str(booking.pk)).save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None



def booking_token_matches(supplied, expected):
    """Compare a caller-supplied booking access token against the stored one.

    Both sides are normalised to canonical UUID form first: '1234abcd...' and
    '1234-abcd-...' are the same token, and a client that sends the undashed
    form should not be turned away. Comparison stays constant-time so the
    endpoint cannot be used to guess a token a character at a time.
    """
    import secrets
    import uuid

    if not supplied or not expected:
        return False
    try:
        left = str(uuid.UUID(str(supplied).strip()))
    except (ValueError, AttributeError, TypeError):
        return False
    try:
        right = str(uuid.UUID(str(expected).strip()))
    except (ValueError, AttributeError, TypeError):
        return False
    return secrets.compare_digest(left, right)


def booking_payment_link(booking):
    """Where a booker goes to settle their balance.

    A guest has no account, so their link carries the booking's access token;
    an account holder is sent to their bookings list.
    """
    from django.conf import settings

    base = settings.FRONTEND_BASE_URL.rstrip("/")
    if booking.user_id is None and booking.access_token:
        return f"{base}/booking/{booking.access_token}"
    return f"{base}/my-booking"


def send_balance_reminder(booking, is_sample=False):
    """Email a reminder that a balance is still outstanding.

    Returns True when sent. Never raises: one bad address must not stop the
    rest of the run.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        recipient = (booking.contact_email or "").strip()
        if not recipient:
            logger.warning("Booking %s has no contact email; reminder skipped.", booking.pk)
            return False

        main_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
        html = render_to_string(
            "payment_reminder.html",
            {
                "booking": booking,
                "contact_name": booking.contact_name or "there",
                "main_date": main_date,
                "hut": booking.hut,
                "payment_link": booking_payment_link(booking),
                "amount_due": booking.not_paid,
                "amount_paid": booking.paid,
                # A sample is sent from a booking that is rolled back straight
                # after, so its link cannot resolve. Say so in the email rather
                # than let it look like a broken site.
                "is_sample": is_sample,
            },
        )
        message = EmailMultiAlternatives(
            subject=(f"[TEST] KEN - sample balance reminder"
                     if is_sample else
                     f"KEN - Balance due for booking #{booking.pk}"),
            body=strip_tags(html),
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient],
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        logger.info("Balance reminder sent to %s for booking %s", recipient[:50], booking.pk)
        return True
    except Exception as exc:
        logger.exception("Failed to send balance reminder for booking %s: %s", booking.pk, exc)
        return False


def send_deposit_confirmation(booking):
    """Confirm a deposit: the dates are held, but the balance is still owed.

    Sent the moment a booking becomes partially_paid, so the guest is not left
    wondering what their money bought until the first daily reminder arrives.
    Deliberately does NOT carry the QR -- that is issued on full payment.

    Never raises: the payment has already succeeded by this point.
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from .map_preview import email_context as map_email_context

        recipient = (booking.contact_email or "").strip()
        if not recipient:
            logger.warning("Booking %s has no contact email; deposit note not sent.", booking.pk)
            return False

        main_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
        html = render_to_string(
            "deposit_confirmation.html",
            {
                "booking": booking,
                "contact_name": booking.contact_name or "there",
                "main_date": main_date,
                "hut": booking.hut,
                "payment_link": booking_payment_link(booking),
                "amount_paid": booking.paid,
                "amount_due": booking.not_paid,
                **map_email_context(booking.hut),
                },
        )
        message = EmailMultiAlternatives(
            subject=f"KEN - Deposit received for booking #{booking.pk}",
            body=strip_tags(html),
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient],
        )
        message.attach_alternative(html, "text/html")
        attach_invoice_pdf(message, booking)
        attach_map_preview(message, booking)
        message.send(fail_silently=False)
        logger.info("Deposit confirmation sent to %s for booking %s", recipient[:50], booking.pk)
        return True
    except Exception as exc:
        logger.exception("Failed to send deposit confirmation for booking %s: %s", booking.pk, exc)
        return False
