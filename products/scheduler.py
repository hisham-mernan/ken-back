from django.utils.timezone import now
from .models import Booking
from .utils import generate_qr_code_image  # This should return a Django File object (e.g., ContentFile)
import schedule
import time
from threading import Thread
# def generate_qr_for_booking(booking_id):
#     try:
#         booking = Booking.objects.get(pk=booking_id)
#         today = now().date()
#         print(f"[QR] Running QR generation for booking {booking.pk} on {today}")

#         has_today_date = booking.dates.filter(date_from=today).exists()
#         print(f"[QR] has_today_date: {has_today_date}")
#         print(f"[QR] status: {booking.status}")
#         print(f"[QR] qr_code exists: {bool(booking.qr_code)}")

#         if booking.status == "paid" and has_today_date and not booking.qr_code_image:
#             print("[QR] Generating QR...")
#             qr_data = str(booking.id)  # Use booking ID as QR data
#             qr_image = generate_qr_code_image(qr_data)
#             booking.qr_code = qr_data
#             booking.qr_code_image = qr_image
#             booking.save()
#             print(f"[QR] QR code generated for booking {booking.pk}")
#         else:
#             print("[QR] Conditions not met for QR generation")
#     except Booking.DoesNotExist:
#         print(f"[QR] Booking {booking_id} not found")


# def generate_qrs_for_today_bookings():
#     today = now().date()
#     print(f"[QR] Running batch QR generation for {today}")

#     bookings = Booking.objects.filter(
#         status="paid",
#         dates__date_from=today,
#         qr_code_image__isnull=True
#     ).distinct()

#     print(f"[QR] Found {bookings.count()} eligible bookings")

#     for booking in bookings:
#         print(f"[QR] Processing booking {booking.pk}")
#         qr_data = str(booking.id)  # Or any secure/encrypted ID
#         qr_image = generate_qr_code_image(qr_data)
#         booking.qr_code = qr_data
#         booking.qr_code_image = qr_image
#         booking.save()
#         print(f"[QR] QR code generated for booking {booking.pk}")

# from apscheduler.schedulers.background import BackgroundScheduler
# from datetime import datetime, time, timedelta


# scheduler = BackgroundScheduler()
# scheduler.start()

# def schedule_qr_generation(booking):
#     # Get earliest date_from
#     date_obj = booking.dates.order_by('date_from').first()
#     if not date_obj:
#         return

#     # Schedule for 8:20 AM on date_from
#     run_time = time(15, 4)
#     run_date = datetime.combine(date_obj.date_from, run_time)

#     scheduler.add_job(
#         # generate_qrs_for_today_bookings,
#         generate_qr_for_booking,
#         'date',
#         run_date=run_date,
#         args=[booking.id]
#     )
#     print(f"[QR Scheduler] Scheduled QR job for booking {booking.pk} on {run_date}")
##############################################################################


from django.template.loader import render_to_string
from django.conf import settings
from urllib.parse import urlparse
from accounts.utils import send_email 

def send_review_email(user, booking):
    html = render_to_string(
        "review.html",
        {
            "user": user,
            "booking": booking,
            "domain": urlparse(settings.FRONTEND_BASE_URL).netloc or "ken.mernantech.com",
        }
    )
    send_email(user.email, "We'd love your feedback!", html)
    print(f"[Email] Review reminder sent to {user.email} for booking {booking.id}")


from django.db.models import Max

def check_and_send_review_email(booking_id):
    try:
        booking = Booking.objects.select_related('user').prefetch_related('dates').get(pk=booking_id)
        latest_checkout = booking.dates.aggregate(max_to=Max('date_to'))['max_to']

        if not latest_checkout:
            print(f"[Review Email] Booking {booking_id} has no checkout date.")
            return

        if booking.status == "paid" and not booking.is_reviewed:
            if booking.user_id is None:
                # Reviews are written from an account, which a guest booking
                # does not have, so there is nothing for them to act on.
                print(f"[Review Email] Booking {booking_id} is a guest booking, skipping.")
                return
            send_review_email(booking.user, booking)
        else:
            print(f"[Review Email] Conditions not met for booking {booking_id}.")
    except Booking.DoesNotExist:
        print(f"[Review Email] Booking {booking_id} not found.")


def schedule_review_email(booking):
    from datetime import datetime, timedelta, time

    date_obj = booking.dates.aggregate(max_to=Max('date_to'))['max_to']
    print(date_obj )
    if not date_obj:
        return

    # Schedule 8:00 AM the day after checkout
    run_time = time(16, 0)
    run_date = datetime.combine(date_obj + timedelta(days=1), run_time)

    scheduler.add_job(
        check_and_send_review_email,
        'date',
        run_date=run_date,
        args=[booking.id]
    )
    print(f"[Review Scheduler] Scheduled review email for booking {booking.pk} on {run_date}")




######################################################





# def generate_qrs_for_today_bookings():
#     today = now().date()
#     print(f"[QR] Running batch QR generation for {today}")

#     # bookings = Booking.objects.filter(
#     #     status="paid",
#     #     dates__date_from=today,
#     #     qr_code_image__isnull=True
#     # ).distinct()
#     bookings = Booking.objects.filter(status="paid",
#     is_qr_genereated=False,
#     dates__date_from=today)

#     print(f"[QR] Found {bookings.count()} eligible bookings")

#     for booking in bookings:
#         print(f"[QR] Processing booking {booking.pk}")
#         qr_data = str(booking.id)  # Use booking ID or hash
#         qr_image = generate_qr_code_image(qr_data)
#         booking.qr_code = qr_data
#         booking.qr_code_image = qr_image
#         booking.is_qr_genereated=True
#         booking.save()
#         print(f"[QR] QR code generated for booking {booking.pk}")



# from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
# from django.utils.timezone import now

# scheduler = BackgroundScheduler()
# scheduler.start()

# # Schedule the QR generation to run every day at 08:00 AM
# trigger = CronTrigger(hour=20, minute=7)  # Adjust time as needed
# scheduler.add_job(generate_qrs_for_today_bookings, trigger)

# print("[QR Scheduler] Daily job scheduled for QR generation at 08:00 AM")





from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from django.utils.timezone import make_aware, now
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()
scheduler.start()


def generate_qr_for_booking(booking_id):
    """Run job to generate QR for a single booking"""
    from .models import Booking  # import here to avoid circular import

    booking = Booking.objects.get(id=booking_id)
    if booking.is_qr_genereated:
        print(f"[QR] Booking {booking.id} already has a QR")
        return

    print(f"[QR] Generating QR for booking {booking.id}")
    qr_data = str(booking.id)
    qr_image = generate_qr_code_image(qr_data)
    booking.qr_code = qr_data
    booking.qr_code_image = qr_image
    booking.is_qr_genereated = True
    booking.save()
    print(f"[QR] ✅ QR code generated for booking {booking.id}")


def schedule_qr_job(booking):
    date_obj = booking.dates.first()
    print(date_obj,"obj")
    if not date_obj:
        print(f"[QR Scheduler] Booking {booking.id} has no dates, skipped")
        return

    today = date_obj.date_from
    check_in_datetime = datetime.combine(today, booking.hut.check_in)

    check_in_datetime = make_aware(check_in_datetime)
    run_time = check_in_datetime - timedelta(hours=1)
    print(run_time,"run")
    print(now())

    if run_time > now():
        print("enter")
        scheduler.add_job(
            generate_qr_for_booking,
            trigger=DateTrigger(run_date=run_time),
            args=[booking.id],
            id=f"qr_job_{booking.id}",
            replace_existing=True,
        )
        print(f"[QR Scheduler] Booking {booking.id} scheduled at {run_time}")
    else:
        print(f"[QR Scheduler] Booking {booking.id} skipped (time passed)")

def schedule_all_today_bookings():
    """Loop all today bookings and schedule them individually"""
    from .models import Booking
    today = now().date()
    bookings = Booking.objects.filter(
        status="paid",
        is_qr_genereated=False,
        dates__date_from=today
    )

    print(f"[QR Scheduler] Found {bookings.count()} bookings for today")
    for booking in bookings:
        schedule_qr_job(booking)


# Run every midnight to schedule the day’s bookings
scheduler.add_job(schedule_all_today_bookings, CronTrigger(hour=0, minute=5))
print("[QR Scheduler] Daily scheduler initialized")
