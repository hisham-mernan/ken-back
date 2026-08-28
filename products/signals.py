from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import *
from .scheduler import  *
from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError
from .pricing import price_for_booking_date


@receiver([post_save, post_delete], sender=Hut)
@receiver([post_save, post_delete], sender=AvailableDateRanges)
@receiver([post_save, post_delete], sender=Event)
@receiver([post_save, post_delete], sender=AvailableDateEvent)
@receiver([post_save, post_delete], sender=Services)
@receiver([post_save, post_delete], sender=AvailableDateService)
@receiver([post_save, post_delete], sender=HutRating)
@receiver([post_save, post_delete], sender=Booking)
def invalidate_product_caches(sender, instance, **kwargs):
    cache.delete("hut_list_home")
    cache.delete("random_event_list")
    cache.delete("random_service_list")
    for i in range(1, 10):
        cache.delete(f"hut_list_page_{i}")
        cache.delete(f"event_list_page_{i}")
        cache.delete(f"hut_rating_list_{i}")
    cache.delete("hut_rating_list_all")

# def calculate_total(booking):
#     total = 0

#     for date in booking.dates.all():
#         hut_price = booking.hut.price if booking.hut else 0
#         delta = (date.date_to - date.date_from).days + 1
#         total += hut_price * delta

#     for et in booking.events.all():
#         total += et.event.price * et.quantity

#     for st in booking.services.all():
#         total += st.service.price * st.quantity

#     for si in booking.special_items.all():
#         total += si.item.price * si.quantity

#     booking.total_price = total
#     booking.not_paid = total
#     booking.save()




# The previous commented-out invoicing attempt lived here. It is gone: it
# carried a second hardcoded Daftra API key, pointed at a different
# subdomain than settings did, and has been superseded by products/daftra.py.
# ########################################################################################################################
# def calculate_total(booking):
#     paid = 0
#     not_paid = 0

#     # Booking Dates (Hut price calculation)
#     # for date in booking.dates.all():
#     #     if booking.hut:
#     #         delta = (date.date_to - date.date_from).days + 1
#     #         hut_total = booking.hut.price * delta
#     #         if date.is_paid:
#     #             paid += hut_total
#     #         else:
#     #             not_paid += hut_total

#     # Event Tickets
#     for et in booking.events.all():
#         line_total = et.event.price * et.quantity
#         if et.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # Service Tickets
#     for st in booking.services.all():
#         line_total = st.service.price * st.quantity
#         if st.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # Special Item Tickets
#     for si in booking.special_items.all():
#         line_total = si.item.price * si.quantity
#         if si.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # Save computed values
#     booking.paid = paid
#     booking.not_paid = not_paid
#     booking.total_price = paid + not_paid
#     booking.save()

# @receiver([post_save, post_delete], sender=EventTicket)
# @receiver([post_save, post_delete], sender=ServiceTicket)
# @receiver([post_save, post_delete], sender=SpecialItemTicket)
# def update_booking_total(sender, instance, **kwargs):
#     calculate_total(instance.booking)
    
    
    
    
    
    
    
# bookings/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Booking)
def mark_related_as_confirmed(sender, instance, **kwargs):
    if not instance.pk:
        return  

    old = Booking.objects.get(pk=instance.pk)
    if old.status != "confirmed" and instance.status == "confirmed":
       
        BookingDate.objects.filter(booking=instance).update(is_confirmed=True)
        EventTicket.objects.filter(booking=instance).update(is_confirmed=True)
        ServiceTicket.objects.filter(booking=instance).update(is_confirmed=True)
        SpecialItemTicket.objects.filter(booking=instance).update(is_confirmed=True)









from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Booking)
def mark_related_as_paid(sender, instance, **kwargs):
    if not instance.pk:
        return  

    old = Booking.objects.get(pk=instance.pk)
    if old.status != "paid" and instance.status == "paid":
        instance.is_paid=True
       
        BookingDate.objects.filter(booking=instance).update(is_paid=True)
        EventTicket.objects.filter(booking=instance).update(is_paid=True)
        ServiceTicket.objects.filter(booking=instance).update(is_paid=True)
        SpecialItemTicket.objects.filter(booking=instance).update(is_paid=True)
        if instance.paid != instance.total_price or instance.not_paid != 0:
            instance.paid = instance.total_price
            instance.not_paid = 0
         

            # Direct DB update to avoid recursion
            sender.objects.filter(pk=instance.pk).update(
                paid=instance.total_price,
                not_paid=0,
             
            )
        
        # Generate QR code immediately if not already generated
        if not instance.is_qr_genereated or not instance.qr_code_image:
            from .utils import generate_qr_code_image
            try:
                qr_data = str(instance.id)
                qr_image = generate_qr_code_image(qr_data)
                instance.qr_code = qr_data
                instance.qr_code_image.save(f"booking_{instance.id}_qr.png", qr_image, save=False)
                instance.is_qr_genereated = True
                sender.objects.filter(pk=instance.pk).update(
                    qr_code=qr_data,
                    is_qr_genereated=True,
                    qr_code_image=instance.qr_code_image.name
                )
                print(f"[Signal] QR code generated for booking {instance.id}")
            except Exception as qr_error:
                print(f"[Signal] Failed to generate QR code for booking {instance.id}: {str(qr_error)}")
        
        schedule_review_email(instance)

        # Notify kenluxuryreef@gmail.com when a new order is paid
        try:
            from django.template.loader import render_to_string
            from accounts.utils import send_email
            main_date = instance.dates.filter(is_extra=False).first()
            main_date_str = (
                f"{main_date.date_from} to {main_date.date_to}" if main_date else "—"
            )
            html = render_to_string(
                "new_order_notification.html",
                {"booking": instance, "main_date": main_date_str},
            )
            send_email("kenluxuryreef@gmail.com", "KEN - New Order Paid", html)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to send new order notification email: %s", e
            )

        # Invoice first, so the confirmation email can carry a link to it.
        # The balance payment is appended to the invoice raised at deposit
        # time, which is what flips it from 50% paid to fully paid.
        from .daftra import sync_booking_invoice
        just_paid = (instance.total_price or Decimal("0.00")) - (old.paid or Decimal("0.00"))
        sync_booking_invoice(instance, amount=just_paid)

        # Confirmation to whoever booked -- guest or account holder alike.
        # send_booking_confirmation swallows its own errors so a mail problem
        # cannot disturb a payment that has already gone through.
        from .utils import send_booking_confirmation
        send_booking_confirmation(instance)













from datetime import timedelta
from django.utils import timezone

from .utils import *
#  in cancellation
def cancel_unpaid_booking(booking):
    # 1. Return hut available dates
    # for date_obj in booking.dates.all():
    #     restore_available_ranges_to_hut(booking.hut, date_obj.date_from, date_obj.date_to)

    # 2. Restore event capacities
    for event_ticket in booking.events.all():
        event = event_ticket.event
        event.capacity += event_ticket.quantity
        event.save()

    # 3. Restore service capacities
    for service_ticket in booking.services.all():
        service = service_ticket.service
        service.capacity += service_ticket.quantity
        service.save()

    # 4. Restore item capacities
    for item_ticket in booking.special_items.all():
        item = item_ticket.item
        item.capacity += item_ticket.quantity
        item.save()

    # 5. Cancel booking
    booking.status = "cancelled"
    booking.save()







import threading
from django.db.models.signals import pre_save
from django.dispatch import receiver



# The hold used to be released by threading.Timer started inside this signal.
# It never worked: the timer was set to 5 minutes while the guest was promised
# 30, the process is frozen the moment the response is sent so it rarely fired
# at all, and it cancelled anything still marked "confirmed" without checking
# whether the money had arrived -- which would have cancelled a paid stay.
# Expiry now runs from `manage.py expire_unpaid_bookings` on a schedule.

@receiver(pre_save, sender=Booking)
def mark_related_as_confirmed(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Booking.objects.get(pk=instance.pk)
    except Booking.DoesNotExist:
        # New booking - no old status, ignore
        return

    if old.status != "confirmed" and instance.status == "confirmed":
       
        BookingDate.objects.filter(booking=instance).update(is_confirmed=True)
        EventTicket.objects.filter(booking=instance).update(is_confirmed=True)
        ServiceTicket.objects.filter(booking=instance).update(is_confirmed=True)
        SpecialItemTicket.objects.filter(booking=instance).update(is_confirmed=True)

        # Stamp when the hold started, so expiry has something to measure from.
        from django.utils import timezone

        instance.confirmed_at = timezone.now()












# delete for extra service if it not paid 



# services/signals.py

import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import ServiceTicket



# increase capity of service on delete
@receiver(post_delete, sender=ServiceTicket)
def restore_service_capacity_on_delete(sender, instance, **kwargs):
    try:
        service = instance.service
    except Exception:
        return  # service may already be deleted (e.g. user cascade)
    if service is None:
        return
    try:
        service.capacity += instance.quantity
        service.save()
    except Exception:
        pass  # avoid breaking cascade delete (e.g. when deleting user)





import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ServiceTicket

def delayed_service_tickets_delete(ticket_ids):
    from .models import ServiceTicket
    for ticket_id in ticket_ids:
        try:
            ticket = ServiceTicket.objects.get(pk=ticket_id)
        except ServiceTicket.DoesNotExist:
            continue

        if ticket.is_extra and ticket.is_confirmed and not ticket.is_paid:
            ticket.delete()

@receiver(post_save, sender=ServiceTicket)
def start_service_ticket_timer(sender, instance, created, **kwargs):
    if created and instance.is_extra and instance.is_confirmed and not instance.is_paid:
        # Gather all extra-confirmed unpaid tickets for the same booking
        ticket_ids = list(
            ServiceTicket.objects.filter(
                booking=instance.booking,
                is_extra=True,
                is_confirmed=True,
                is_paid=False
            ).values_list('id', flat=True)
        )

        # Start 30-minute timer (adjust as needed)
        timer = threading.Timer(3 * 60, delayed_service_tickets_delete, args=[ticket_ids])
        timer.daemon = True
        timer.start()











# ###################################################################################

# add etra days 

# @receiver(post_save, sender=BookingDate)
# def adjust_ranges_on_confirmed_or_paid(sender, instance, **kwargs):
#     if (instance.is_confirmed or instance.is_paid) and instance.is_extra:
#         adjust_available_ranges_after_booking(
#             instance.booking.hut,
#             instance.date_from,
#             instance.date_to
#         )

# @receiver(post_delete, sender=BookingDate)
# def restore_dates_on_delete(sender, instance, **kwargs):
#     if instance.is_extra and (instance.is_confirmed or instance.is_paid):
#         restore_available_ranges_to_hut(
#             instance.booking.hut,
#             instance.date_from,
#             instance.date_to
#         )
        
        
        

def delayed_booking_date_check(date_id):
    from .models import BookingDate
    try:
        date = BookingDate.objects.get(pk=date_id)
    except BookingDate.DoesNotExist:
        return

    if date.is_extra and date.is_confirmed and not date.is_paid:
        date.delete()
        
        



@receiver(post_save, sender=BookingDate)
def start_extra_date_timer(sender, instance, created, **kwargs):
    if instance.is_extra and instance.is_confirmed and not instance.is_paid:
        # Start timer for 30 minutes (1800 seconds)
        timer = threading.Timer(3 * 60, delayed_booking_date_check, args=[instance.pk])
        timer.daemon = True
        timer.start()





# ##########################################################################################


# order refund



def refund_booking(booking):
    # 1. Return hut available dates
    # for date_obj in booking.dates.all():
    #     restore_available_ranges_to_hut(booking.hut, date_obj.date_from, date_obj.date_to)

    # 2. Restore event capacities
    for event_ticket in booking.events.all():
        event = event_ticket.event
        event.capacity = (event.capacity or 0) + event_ticket.quantity
        event.save()

    # 3. Restore service capacities
    for service_ticket in booking.services.all():
        service = service_ticket.service
        service.capacity = (service.capacity or 0) + service_ticket.quantity
        service.save()

    # 4. Restore item capacities
    for item_ticket in booking.special_items.all():
        item = item_ticket.item
        item.capacity = (item.capacity or 0) + item_ticket.quantity
        item.save()

    # 5. Don't call booking.save() here to avoid recursion


from django.db.models.signals import pre_save
from django.dispatch import receiver
from threading import local
from .models import Booking  # adjust import as needed


_thread_locals = local()

@receiver(pre_save, sender=Booking)
def call_refund_on_status_change(sender, instance, **kwargs):
    # Prevent recursion
    if getattr(_thread_locals, 'processing_refund', False):
        return

    if not instance.pk:
        # New booking, nothing to compare
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # Check if status changed to 'refuned' (or fix typo to 'refunded' if you want)
    if old_instance.status != instance.status and instance.status == 'refuned':
        _thread_locals.processing_refund = True
        try:
            refund_booking(instance)
        finally:
            _thread_locals.processing_refund = False



#############################################################################################
# calcutlation 
# from decimal import Decimal
# from datetime import timedelta
# from django.core.exceptions import ValidationError

# def calculate_total(booking):
#     paid = Decimal('0.00')
#     not_paid = Decimal('0.00')

#     # ✅ Hut pricing based on AvailableDateRanges
#     for date in booking.dates.all():
#         # We need to track the current day we are processing
#         current_day = date.date_from
#         hut_total = Decimal('0.00')

#         # Iterate through all the days in this booking date range
#         while current_day < date.date_to:
#             # Find the range that applies to the current day
#             range_obj = AvailableDateRanges.objects.filter(
#                 huts=booking.hut,
#                 date_from__lte=current_day,
#                 date_to__gte=current_day
#             ).first()

#             if not range_obj or not range_obj.price:
#                 raise ValidationError(f"No valid price for night {current_day} for hut {booking.hut}")

#             # Add price for this day
#             hut_total += range_obj.price
#             current_day += timedelta(days=1)

#         # Add this to the total based on whether it’s paid or not
#         if date.is_paid:
#             paid += hut_total
#         else:
#             not_paid += hut_total

#     # ✅ Events
#     for et in booking.events.all():
#         price_obj = AvailableDate.objects.filter(events=et.event, date=et.date).first()
#         if not price_obj:
#             raise ValidationError(f"No pricing for event '{et.event.title}' on {et.date}")
#         line_total = price_obj.price * et.quantity

#         if et.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # ✅ Services
#     for st in booking.services.all():
#         price_obj = AvailableDate.objects.filter(services=st.service, date=st.date).first()
#         if not price_obj:
#             raise ValidationError(f"No pricing for service '{st.service.title}' on {st.date}")
#         line_total = price_obj.price * st.quantity

#         if st.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # ✅ Special Items (price is static)
#     for si in booking.special_items.all():
#         line_total = si.item.price * si.quantity
#         if si.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # Final save
#     booking.paid = paid
#     booking.not_paid = not_paid
#     booking.total_price = paid + not_paid
#     booking.save()
# def build_invoice_payload(booking):
#     items = []

#     # ✅ Hut
#     for date in booking.dates.all():
#         nights = (date.date_to - date.date_from).days + 1
#         description = f"From {date.date_from} to {date.date_to}"
#         if date.is_extra:
#             description += " (Extra Day)"
        
#         # Find the pricing range for this date
#         current_day = date.date_from
#         while current_day < date.date_to:
#             range_obj = AvailableDateRanges.objects.filter(
#                 huts=booking.hut,
#                 date_from__lte=current_day,
#                 date_to__gte=current_day
#             ).first()

#             if range_obj and range_obj.price:
#                 items.append({
#                     "item": f"Hut: {booking.hut.title}",
#                     "description": description,
#                     "unit_price": float(range_obj.price),
#                     "quantity": 1,  # Each night is treated separately
#                     "product_id": 1,
#                     "discount": 0
#                 })

#             current_day += timedelta(days=1)

#     # ✅ Events
#     for et in booking.events.all():
#         price_obj = AvailableDate.objects.filter(events=et.event, date=et.date).first()
#         if not price_obj:
#             continue

#         desc = et.event.description or ''
#         if et.is_extra:
#             desc += " (Extra)"
#         items.append({
#             "item": f"Event: {et.event.title}",
#             "description": desc,
#             "unit_price": float(price_obj.price),
#             "quantity": et.quantity,
#             "product_id": 2,
#             "discount": 0
#         })

#     # ✅ Services
#     for st in booking.services.all():
#         price_obj = AvailableDate.objects.filter(services=st.service, date=st.date).first()
#         if not price_obj:
#             continue

#         desc = st.service.description or ''
#         if st.is_extra:
#             desc += " (Extra)"
#         items.append({
#             "item": f"Service: {st.service.title}",
#             "description": desc,
#             "unit_price": float(price_obj.price),
#             "quantity": st.quantity,
#             "product_id": 3,
#             "discount": 0
#         })

#     # ✅ Special Items (price is static)
#     for si in booking.special_items.all():
#         desc = si.item.description or ''
#         if si.is_extra:
#             desc += " (Extra)"
#         items.append({
#             "item": f"Special Item: {si.item.title}",
#             "description": desc,
#             "unit_price": float(si.item.price),
#             "quantity": si.quantity,
#             "product_id": 4,
#             "discount": 0
#         })

#     return {
#         "Invoice": {
#             "store_id": 1,
#             "client_id": 1,
#             "currency_code": "USD",
#             "client_first_name": booking.user.full_name,
#             "client_last_name": booking.user.full_name,
#             "client_email": booking.user.email,
#             "client_address1": "Default Address",
#             "client_country_code": "US",
#             "date": str(booking.created_at.date()),
#             "draft": "0",
#             "notes": "Booking invoice for hut, events, services, and special items",
#             "invoice_layout_id": 2
#         },
#         "InvoiceItem": items,
#         "Payment": [
#             {
#                 "payment_method": "Cash",
#                 "amount": float(booking.paid or 0),
#                 "treasury_id": 1,
#                 "staff_id": 1,
#                 "date": str(booking.created_at)
#             }
#         ]
#     }



# @receiver([post_save, post_delete], sender=EventTicket)
# @receiver([post_save, post_delete], sender=ServiceTicket)
# @receiver([post_save, post_delete], sender=SpecialItemTicket)
# def update_booking_total(sender, instance, **kwargs):
#     calculate_total(instance.booking) 




# from decimal import Decimal
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.core.exceptions import ValidationError
# from datetime import timedelta
# from .models import (
#     Booking, EventTicket, ServiceTicket, SpecialItemTicket, BookingDate,
#     AvailableDateRanges, AvailableDate
# )

# # Function to calculate total
# def calculate_total(booking):
#     paid = Decimal('0.00')
#     not_paid = Decimal('0.00')

#     # ✅ Hut pricing based on AvailableDateRanges
#     for date in booking.dates.all():
#         current_day = date.date_from
#         hut_total = Decimal('0.00')

#         while current_day < date.date_to:
#             range_obj = AvailableDateRanges.objects.filter(
#                 huts=booking.hut,
#                 date_from__lte=current_day,
#                 date_to__gte=current_day
#             ).first()

#             # if not range_obj or not range_obj.price:
#             #     raise ValidationError(f"No valid price for night {current_day} for hut {booking.hut}")

#             hut_total += range_obj.price
#             print(hut_total,'hut_total')
#             current_day += timedelta(days=1)

#         if date.is_paid:
#             paid += hut_total
#             print(paid,'in hut paid')
#         else:
#             not_paid += hut_total
#             print(not_paid,'in hutnot paid')
            

#     # ✅ Events, Services, Special Items - Pricing as per available dates
#     for et in booking.events.all():
#         price_obj = AvailableDate.objects.filter(events=et.event, date=et.date).first()
#         # if not price_obj:
#         #     raise ValidationError(f"No pricing for event '{et.event.title}' on {et.date}")
#         line_total = price_obj.price * et.quantity
#         print(price_obj.price,'event')
#         print(et.quantity,'qntit')
#         print(line_total,'total in event')
        

#         if et.is_paid:
            
#             paid += line_total
#             print(paid,'event, paid')
#         else:
#             not_paid += line_total
#             print(not_paid,'event, notpaid')
            

#     for st in booking.services.all():
#         price_obj = AvailableDate.objects.filter(services=st.service, date=st.date).first()
#         # if not price_obj:
#         #     raise ValidationError(f"No pricing for service '{st.service.title}' on {st.date}")
#         line_total = price_obj.price * st.quantity
#         print(price_obj.price,'serice')
#         print(st.quantity,'qntit')
#         print(line_total,'total in service')
        

#         if st.is_paid:
#             paid += line_total
#             print(paid,'service paid')
#         else:
#             not_paid += line_total
#             print(not_paid,'service notpaid')
            

#     for si in booking.special_items.all():
#         line_total = si.item.price * si.quantity
#         if si.is_paid:
#             paid += line_total
#         else:
#             not_paid += line_total

#     # Final save
#     booking.paid = paid
#     booking.not_paid = not_paid
#     booking.total_price = paid + not_paid
#     booking.save()

# # Signal to handle updates when tickets, services, or special items are added or deleted
# @receiver([post_save, post_delete], sender=EventTicket)
# @receiver([post_save, post_delete], sender=ServiceTicket)
# @receiver([post_save, post_delete], sender=SpecialItemTicket)
# @receiver([post_save, post_delete], sender=BookingDate)
# def update_booking_total(sender, instance, **kwargs):
#     # Recalculate total for the booking
#     calculate_total(instance.booking)

#     # After recalculating the total, check if the booking is paid or not
#     booking = instance.booking

#     if booking.paid == booking.total_price:
#         booking.status = "paid"
#     else:
#         booking.status = "not_paid"

#     booking.save()

#     # Print or log the updated status and totals (optional)
#     print(f"Booking {booking.pk} - Paid: {booking.paid}, Not Paid: {booking.not_paid}, Total Price: {booking.total_price}, Status: {booking.status}")


###################################################################
#new flow 

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import EventTicket, AvailableDateEvent

@receiver(post_save, sender=EventTicket)
def decrease_event_capacity(sender, instance, created, **kwargs):
    if created:
        try:
            date_obj = AvailableDateEvent.objects.filter(date=instance.date).first()
            date_obj.capacity = max((date_obj.capacity or 0) - instance.quantity, 0)
            print(date_obj.capacity,'event capicty')
            date_obj.save()
        except AvailableDateEvent.DoesNotExist:
            pass

@receiver(post_delete, sender=EventTicket)
def restore_event_capacity(sender, instance, **kwargs):
    try:
        date_obj = AvailableDateEvent.objects.filter(date=instance.date).first()
        if date_obj is None:
            return
        date_obj.capacity = (date_obj.capacity or 0) + instance.quantity
        date_obj.save()
    except Exception:
        pass  # avoid breaking cascade delete (e.g. when deleting user)




from .models import ServiceTicket, AvailableDateService

@receiver(post_save, sender=ServiceTicket)
def decrease_service_capacity(sender, instance, created, **kwargs):
    if created:
        try:
            date_obj = AvailableDateService.objects.filter(date=instance.date).first()
            instance.service.capacity = max((instance.service.capacity or 0) - instance.quantity, 0)
            instance.save()
            date_obj.save()
        except AvailableDateService.DoesNotExist:
            pass

@receiver(post_delete, sender=ServiceTicket)
def restore_service_capacity(sender, instance, **kwargs):
    try:
        date_obj = AvailableDateService.objects.filter(date=instance.date).first()
        if date_obj is None:
            return
        date_obj.capacity = (date_obj.capacity or 0) + instance.quantity
        date_obj.save()
    except Exception:
        pass  # avoid breaking cascade delete (e.g. when deleting user)


#############################################################################
# from decimal import Decimal

#caculate total price of booking date ok 


@receiver(post_save, sender=BookingDate)
def calculate_total_price_on_booking_date_create(sender, instance, created, **kwargs):
    if not created:
        return  # only run on creation

    booking_date = instance

    # The stay total at the hut's weekday/weekend rates. This is already the
    # whole-range total, not a per-night figure -- see the note on
    # UpComingBookingSerializer.get_booking_price before multiplying it out.
    booking_date.total_price = price_for_booking_date(booking_date)
    booking_date.save(update_fields=["total_price"])











###############################################notifcation


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from .models import (
    Booking, BookingDate, EventTicket, ServiceTicket, SpecialItemTicket
)

from accounts.models import User,Support
from .models import Services, Event  # adjust if you use other module paths
from accounts.models import Notification


def notify_user(user, content_object, type, message, message_ar):
    content_type = ContentType.objects.get_for_model(content_object)
    Notification.objects.create(
        user=user,
        content_type=content_type,
        object_id=content_object.pk,
        type=type,
        message=message,
        message_ar=message_ar,
    )


def notify_admins(content_object, type, message, message_ar):
    admins = User.objects.filter(role='admin')
    for admin in admins:
        notify_user(admin, content_object, type, message, message_ar)

# Booking: New, Paid, Cancelled (Refund)
@receiver(post_save, sender=Booking)
def booking_notifications(sender, instance, created, **kwargs):
    if created:
        notify_admins(
            content_object=instance,
            type="booking",
            message="A new order has been added.",
            message_ar="تم إضافة حجز جديد."
        )
    else:
        if instance.status == "paid":
            notify_admins(
                content_object=instance,
                type="booking_paid",
                message="An order has been marked as paid.",
                message_ar="تم تأكيد دفع الحجز."
            )
        elif instance.status == "cancelled" and instance.is_paid:
            notify_admins(
                content_object=instance,
                type="need_refund",
                message="A cancelled paid order needs a refund.",
                message_ar="يوجد حجز مدفوع تم إلغاؤه ويحتاج إلى استرداد."
            )

# Extra Items (BookingDate, EventTicket, etc.)
def handle_extra_signal(instance):
    if instance.is_extra:
        notify_admins(
            content_object=instance,
            type="extra",
            message="An extra item was added to a booking.",
            message_ar="تمت إضافة عنصر إضافي إلى الحجز."
        )

@receiver(post_save, sender=BookingDate)
def extra_booking_date(sender, instance, created, **kwargs):
    if created:
        handle_extra_signal(instance)

@receiver(post_save, sender=EventTicket)
def event_ticket_signal(sender, instance, created, **kwargs):
    if created:
        # Notify admins if extra
        handle_extra_signal(instance)

        # Notify event supplier
        if instance.event and instance.event.supplier:
            notify_user(
                user=instance.event.supplier,
                content_object=instance,
                type="supplier_event_tickets",
                message="A new ticket has been created for your event.",
                message_ar="تم إنشاء تذكرة جديدة لفعاليتك."
            )

    if instance.is_paid and instance.event and instance.event.supplier:
        notify_user(
            user=instance.event.supplier,
            content_object=instance,
            type="booking_paid",
            message="A ticket has been paid for your event.",
            message_ar="تم دفع تذكرة لفعاليتك."
        )

@receiver(post_save, sender=ServiceTicket)
def service_ticket_signal(sender, instance, created, **kwargs):
    if created:
        # Notify admins if extra
        handle_extra_signal(instance)

        # Notify service supplier
        if instance.service and instance.service.supplier:
            notify_user(
                user=instance.service.supplier,
                content_object=instance,
                type="supplier_service_tickets",
                message="A new ticket has been created for your service.",
                message_ar="تم إنشاء تذكرة جديدة لخدمتك."
            )

    if instance.is_paid and instance.service and instance.service.supplier:
        notify_user(
            user=instance.service.supplier,
            content_object=instance,
            type="booking_paid",
            message="A ticket has been paid for your service.",
            message_ar="تم دفع تذكرة لخدمتك."
        )

@receiver(post_save, sender=SpecialItemTicket)
def extra_special_item(sender, instance, created, **kwargs):
    if created:
        handle_extra_signal(instance)

# Support with no operation → notify admin
# Support with operation.user → notify user
@receiver(post_save, sender=Support)
def support_added(sender, instance, created, **kwargs):
    if created:
        if instance.operation is None:
            notify_admins(
                content_object=instance,
                type="support",
                message="A new support request was added.",
                message_ar="تم إضافة طلب دعم جديد."
            )
        elif instance.operation  :
            notify_user(
                user=instance.operation,
                content_object=instance,
                type="support",
                message="Your support request has been received.",
                message_ar="تم استلام طلب الدعم الخاص بك."
            )


















# calculation in more accurate way 



from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    Booking, BookingDate, EventTicket, ServiceTicket,
    SpecialItemTicket, AvailableDateEvent
)


# def recalculate_booking_totals(booking: Booking):
#     print("hellllo we entered in signal neww")
#     total_price = Decimal("0.00")
#     paid_total = Decimal("0.00")
#     not_paid_total = Decimal("0.00")

#     # BookingDate calculation
#     for bd in booking.dates.all():
#         nights = (bd.date_to - bd.date_from).days
#         print(nights,"nights befor if")
#         if nights == 0:
#             nights = 1  # at least 1 night
#         print(nights,"after if ")
#         subtotal = Decimal(bd.total_price or 0) * nights
       
#         total_price += subtotal
#         print(total_price,"hut")
#         if bd.is_paid:
#             paid_total += subtotal
#         else:
#             not_paid_total += subtotal

#     # EventTicket calculation
#     for et in booking.events.all():
#         available_date = AvailableDateEvent.objects.filter(date=et.date).first()
#         event_price = Decimal(available_date.price if available_date else 0) * et.quantity
#         print(event_price,"event price alone")
#         total_price += event_price
#         print(total_price,"event add")

#         if et.is_paid:
#             paid_total += event_price
#         else:
#             not_paid_total += event_price

#     # ServiceTicket calculation
#     for st in booking.services.all():
#         service_price = Decimal(st.service.price or 0) * st.quantity
#         print(service_price,"service")
#         total_price += service_price
#         print(total_price,"service add")

#         if st.is_paid:
#             paid_total += service_price
#         else:
#             not_paid_total += service_price

#     # SpecialItemTicket calculation
#     for sit in booking.special_items.all():
#         item_price = Decimal(sit.item.price or 0) * sit.quantity
#         print(item_price,"item ")
#         total_price += item_price
#         print(total_price,"item add")
#         if sit.is_paid:
#             paid_total += item_price
#         else:
#             not_paid_total += item_price

#     #  Apply promo code discount if available
#     if booking.promocode and booking.promocode.percentage:
#         print("there is a promocoed")
#         percentage = Decimal(booking.promocode.percentage)
#         discount = (percentage / Decimal("100.0")) * total_price

#         # Make sure discount is not more than total
#         discount = min(discount, total_price)
#         print(discount,"discount")

#         total_price -= discount
#         print(total_price,"price after discount")

#         # Distribute discount proportionally to paid / not_paid
#         if total_price > 0:
#             paid_ratio = paid_total / (paid_total + not_paid_total) if (paid_total + not_paid_total) > 0 else Decimal("0")
#             not_paid_ratio = Decimal("1.0") - paid_ratio

#             paid_total = total_price * paid_ratio
#             not_paid_total = total_price * not_paid_ratio
#         else:
#             paid_total = Decimal("0.00")
#             not_paid_total = Decimal("0.00")

#     # Save the updated totals
#     booking.total_price = total_price
#     booking.paid = paid_total
#     booking.not_paid = not_paid_total
#     booking.save(update_fields=["total_price", "paid", "not_paid"])


# # Signals - recalc totals on any related model change
# @receiver([post_save, post_delete], sender=BookingDate)
# @receiver([post_save, post_delete], sender=EventTicket)
# @receiver([post_save, post_delete], sender=ServiceTicket)
# @receiver([post_save, post_delete], sender=SpecialItemTicket)
# def update_booking_totals(sender, instance, **kwargs):
#     booking = instance.booking
#     recalculate_booking_totals(booking)

















# from decimal import Decimal
# from django.db.models.signals import post_save, post_delete
# from django.db import transaction
# from django.dispatch import receiver
# from .models import (
#     Booking, BookingDate, EventTicket, ServiceTicket,
#     SpecialItemTicket, AvailableDateEvent
# )


# def recalculate_booking_totals(booking: Booking):
#     print("✅ Entered recalculation signal once.")
#     total_price = Decimal("0.00")
#     paid_total = Decimal("0.00")
#     not_paid_total = Decimal("0.00")

#     # --- BookingDate ---
#     for bd in booking.dates.all():
#         nights = (bd.date_to - bd.date_from).days or 1
#         print(nights,'night')
#         subtotal = Decimal(bd.total_price or 0) * nights
#         total_price += subtotal
#         print(total_price,"hut add")
#         if bd.is_paid:
#             paid_total += subtotal
#         else:
#             not_paid_total += subtotal

#     # --- Events ---
#     for et in booking.events.all():
#         available_date = AvailableDateEvent.objects.filter(date=et.date).first()
#         event_price = Decimal(available_date.price if available_date else 0) * et.quantity
#         print(event_price,'event only')
#         total_price += event_price
#         print(total_price,"event add")

#         if et.is_paid:
#             paid_total += event_price
#         else:
#             not_paid_total += event_price

#     # --- Services ---
#     for st in booking.services.all():
#         service_price = Decimal(st.service.price or 0) * st.quantity
#         print(service_price,'service only')
#         total_price += service_price
#         print(total_price,"service add")

#         if st.is_paid:
#             paid_total += service_price
#         else:
#             not_paid_total += service_price

#     # --- Special Items ---
#     for sit in booking.special_items.all():
#         item_price = Decimal(sit.item.price or 0) * sit.quantity
#         print(item_price,"item only")
#         total_price += item_price
#         print(total_price,"item add")

#         if sit.is_paid:
#             paid_total += item_price
#         else:
#             not_paid_total += item_price

#     # --- Promo Code ---
#     if booking.promocode and booking.promocode.percentage:
#         percentage = Decimal(booking.promocode.percentage)
#         discount = (percentage / Decimal("100.0")) * total_price
#         print(discount,"discount cal")
#         discount = min(discount, total_price)
#         print(discount,'after min')
#         total_price -= discount
#         print(total_price,"after discount")
        

#         if total_price > 0:
#             paid_ratio = paid_total / (paid_total + not_paid_total) if (paid_total + not_paid_total) > 0 else Decimal("0")
#             not_paid_ratio = Decimal("1.0") - paid_ratio
#             paid_total = total_price * paid_ratio
#             not_paid_total = total_price * not_paid_ratio
#         else:
#             paid_total = Decimal("0.00")
#             not_paid_total = Decimal("0.00")

#     # ✅ Save booking totals once
#     booking.total_price = total_price
#     booking.paid = paid_total
#     booking.not_paid = not_paid_total
#     booking.save(update_fields=["total_price", "paid", "not_paid"])


# # ✅ Run recalculation only once after all saves/deletes
# @receiver([post_save, post_delete], sender=BookingDate)
# @receiver([post_save, post_delete], sender=EventTicket)
# @receiver([post_save, post_delete], sender=ServiceTicket)
# @receiver([post_save, post_delete], sender=SpecialItemTicket)
# def update_booking_totals(sender, instance, **kwargs):
#     booking = instance.booking

#     # Schedule recalculation AFTER transaction commits (only once)
#     transaction.on_commit(lambda: recalculate_booking_totals(booking))


from django.db.models.signals import post_save


@receiver(pre_save, sender=Booking)
def flag_deposit_transition(sender, instance, **kwargs):
    """Notice a booking becoming partially_paid, ready for post_save to act.

    Split across pre_save and post_save on purpose: pre_save is the only place
    the previous status is still available, but the email must not go out until
    the row has actually committed -- otherwise a failed save would still tell
    the guest their deposit landed.
    """
    instance._deposit_just_taken = False
    if not instance.pk:
        return
    old = Booking.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    if old != "partially_paid" and instance.status == "partially_paid":
        instance._deposit_just_taken = True
        # The deposit email counts as the first contact, so the daily chase
        # starts a day later rather than possibly hours later.
        instance.last_reminder_at = timezone.now()


@receiver(post_save, sender=Booking)
def send_deposit_email(sender, instance, created, **kwargs):
    if not getattr(instance, "_deposit_just_taken", False):
        return
    instance._deposit_just_taken = False

    # Raise the invoice before the email so it can link to it. This is the
    # only invoice the booking gets; the balance payment is added to it later.
    from .daftra import sync_booking_invoice
    sync_booking_invoice(instance, amount=instance.paid)

    from .utils import send_deposit_confirmation
    send_deposit_confirmation(instance)


# --------------------------------------------------------- Google Calendar
#
# The dashboard calendar only exists inside the dashboard. These handlers
# mirror the same stays onto a shared Google Calendar so the desk sees them
# beside its own appointments. products/google_calendar.py swallows every
# error it meets, so nothing below can fail a booking.

from django.db import transaction

# The fields that change what the event says. A Booking is saved several times
# in a single checkout by the handlers above; without this the calendar would
# be rewritten on each of them for no change.
_CALENDAR_FIELDS = (
    "status", "paid", "not_paid", "total_price", "hut_id", "user_id",
    "persons_max_num", "kids_max_num", "guest_name", "guest_phone", "guest_email",
)


@receiver(pre_save, sender=Booking)
def remember_calendar_fields(sender, instance, **kwargs):
    """Snapshot the stored row so post_save can tell what actually changed.

    Skipped entirely when the integration is off, so a site with no calendar
    configured does not pay a query on every booking save for a feature it is
    not using.
    """
    from . import google_calendar

    if not google_calendar.is_enabled():
        return
    if not instance.pk:
        instance._calendar_before = None
        return
    instance._calendar_before = (
        Booking.objects.filter(pk=instance.pk).values(*_CALENDAR_FIELDS).first()
    )


@receiver(post_save, sender=Booking)
def push_booking_to_calendar(sender, instance, created, **kwargs):
    from . import google_calendar

    if not google_calendar.is_enabled():
        return

    before = getattr(instance, "_calendar_before", None)
    after = {field: getattr(instance, field) for field in _CALENDAR_FIELDS}
    if not created and before == after:
        return

    was_active = bool(before) and before["status"] in ACTIVE_BOOKING_STATUSES
    is_active = instance.status in ACTIVE_BOOKING_STATUSES
    if not (is_active or was_active):
        return

    # on_commit, so a checkout that rolls back never leaves an event behind for
    # a booking that does not exist.
    booking_pk = instance.pk

    def _push():
        booking = Booking.objects.filter(pk=booking_pk).select_related("hut").first()
        if booking is None:
            return
        if booking.status in ACTIVE_BOOKING_STATUSES:
            google_calendar.sync_booking(booking)
        else:
            google_calendar.remove_booking(booking)

    transaction.on_commit(_push)


@receiver([post_save, post_delete], sender=BookingDate)
def push_booking_dates_to_calendar(sender, instance, **kwargs):
    """Dates are what the event spans, so a change to them has to be pushed.

    On create the booking's own post_save runs before any BookingDate exists,
    so this is also what puts a brand new booking on the calendar.
    """
    from . import google_calendar

    if not google_calendar.is_enabled():
        return

    booking_pk = instance.booking_id
    if not booking_pk:
        return

    def _push():
        # Re-read rather than trusting the instance: the booking may have been
        # cascade-deleted with its dates, and an extra night added moments ago
        # has to be picked up from the database, not from this row.
        booking = Booking.objects.filter(pk=booking_pk).select_related("hut").first()
        if booking is None:
            return
        if booking.status in ACTIVE_BOOKING_STATUSES:
            google_calendar.sync_booking(booking)

    transaction.on_commit(_push)
