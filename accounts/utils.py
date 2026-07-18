from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from threading import Timer
from datetime import timedelta
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
import random
import logging

logger = logging.getLogger(__name__)


def send_email(recipient_email, subject, html_content):
    """
    Send an email. Returns True if sent successfully, False otherwise.
    Recipient is normalized (stripped, lowercased) to avoid SMTP issues.
    """
    if not recipient_email or not isinstance(recipient_email, str):
        logger.warning("send_email: missing or invalid recipient_email")
        return False
    recipient_email = recipient_email.strip().lower()
    if not recipient_email:
        logger.warning("send_email: empty recipient after strip")
        return False
    try:
        text_content = strip_tags(html_content)  # Fallback for non-HTML clients
        send_mail(
            subject,
            text_content,
            settings.EMAIL_HOST_USER,
            [recipient_email],
            fail_silently=False,
            html_message=html_content  # HTML content for the email
        )
        logger.info("Email sent successfully to %s (subject: %s)", recipient_email[:50], subject[:50])
        return True
    except Exception as e:
        logger.exception(
            "Failed to send email to %s (subject: %s): %s",
            recipient_email[:50], subject[:50], e
        )
        return False



def generate_otp():
    return random.randint(100000, 999999)


def clear_otp(user):
     
        user.otp_secret = ""
        user.save(update_fields=['otp_secret'])





def block_user_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user)
    for token in tokens:
        if not BlacklistedToken.objects.filter(token=token).exists():
            BlacklistedToken.objects.create(token=token)

def generate_jwt_token(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    refresh['email'] = user.email
    refresh['username'] = user.username
    # refresh['phone'] = str(user.phone) if user.phone else ""

    return str(refresh.access_token)
   
        
        
        

def delete_user_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user)
    tokens.delete()







import qrcode
from io import BytesIO
import base64
import requests

def generate_booking_qr_image(booking):
    qr = qrcode.make(str(booking.id))  
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode() # decode image as string

def send_qr_to_darevue(booking):
    darevue_url = "http://[YOUR-IP]:[PORT]/api/AcsDataApi/GetData"
    secret_key = "050e0dc1-deb8-4db4-9d88-9d5637d70b71"

    payload = {
        "Key": secret_key,
        "Type": "EditEmployee",
        "OperationType": "1",
        "Data": {
            "EmployeeCode": str(booking.user.id),
            "EmployeeName": booking.user.get_full_name(),
            "QRCode": str(booking.id),
            "EmpID": str(booking.qr_code)
        }
    }

    response = requests.post(darevue_url, json=payload, headers={"Content-Type": "application/json"})
    return response.json()




# utils/daftra.py
import requests
from django.conf import settings
from requests.exceptions import RequestException

class DaftraClient:
    def __init__(self):
        self.api_key = settings.DAFTRA_API_KEY
        self.base_url = settings.DAFTRA_BASE_URL
        self.headers = {
            'APIKEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def create_invoice(self, booking):
        # تحضير بيانات الفاتورة
        invoice_data = self._prepare_invoice_data(booking)
        
        try:
            response = requests.post(
                f"{self.base_url}/api2/invoices",
                headers=self.headers,
                json=invoice_data
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            print(f"Error creating Daftra invoice: {e}")
            raise

    def _prepare_invoice_data(self, booking):
        # تحويل بيانات الحجز إلى تنسيق Daftra
        client = booking.user
        dates = booking.dates.first()
        
        # العناصر الأساسية للفاتورة
        items = []
        
        # 1. سعر الكوخ
        if booking.hut:
            nights = (dates.date_to - dates.date_from).days
            items.append({
                "item": f"إيجار {booking.hut.name}",
                "description": f"من {dates.date_from} إلى {dates.date_to} ({nights} ليالي)",
                "unit_price": float(booking.hut.price),
                "quantity": nights,
                "product_id": None  # يمكنك إضافة ID المنتج إذا كان لديك
            })
        
        # 2. التذاكر والفعاليات
        for event in booking.events.all():
            items.append({
                "item": event.event.name,
                "description": f"تذكرة فعالية بتاريخ {event.date}",
                "unit_price": float(event.event.price),
                "quantity": event.quantity,
                "product_id": None
            })
        
        # 3. الخدمات
        for service in booking.services.all():
            items.append({
                "item": service.service.name,
                "description": f"خدمة بتاريخ {service.date}",
                "unit_price": float(service.service.price),
                "quantity": service.quantity,
                "product_id": None
            })
        
        # 4. العناصر الخاصة
        for item in booking.special_items.all():
            items.append({
                "item": item.item.name,
                "description": "عنصر خاص",
                "unit_price": float(item.item.price),
                "quantity": item.quantity,
                "product_id": None
            })
        
        # بيانات العميل
        client_data = {
            "business_name": client.get_full_name() or client.username,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "email": client.email,
            "phone1": client.phone if hasattr(client, 'phone') else "",
            "country_code": "SA"  # افتراضي للسعودية
        }
        
        # هيكل الفاتورة النهائي
        return {
            "Invoice": {
                "store_id": 1,  # يمكن تغييره حسب متجرك في Daftra
                "client_id": None,  # سيتم إنشاء عميل جديد إذا لم يتم التوفير
                "is_offline": True,
                "currency_code": "SAR",
                **client_data,
                "date": dates.date_from.isoformat(),
                "draft": "0",
                "notes": f"حجز رقم #{booking.id} - {booking.get_status_display()}",
                "html_notes": self._generate_html_notes(booking)
            },
            "InvoiceItem": items,
            "Payment": [{
                "payment_method": "manual_payment_17",  # مثال من API
                "amount": float(booking.paid) if booking.paid else 0,
                "date": booking.created_at.isoformat()
            }]
        }
    
    def _generate_html_notes(self, booking):
        # إنشاء ملاحظات HTML للفاتورة
        notes = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <h3>تفاصيل الحجز #{booking.id}</h3>
            <p>الحالة: {booking.get_status_display()}</p>
            <p>عدد الأشخاص: {booking.persons_max_num}</p>
            <p>عدد الأطفال: {booking.kids_max_num}</p>
            <p>المبلغ المدفوع: {booking.paid} ريال</p>
            <p>المبلغ المتبقي: {booking.not_paid} ريال</p>
        </div>
        """
        return notes