from django.db import models
from accounts .models import User,WebsiteRate
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.core.exceptions import ValidationError
import uuid
# Create your models here.
def icons(instance, filetitle):
    return '/'.join(['uploads/services/icons', filetitle])
def hut_image(instance, filetitle):
    return '/'.join(['uploads/services/hut_image', filetitle])
def event_image(instance, filetitle):
    return '/'.join(['uploads/services/event_image', filetitle])
def qr_image(instance, filetitle):
    return '/'.join(['uploads/services/qr', filetitle])
class AvailableDateEvent(models.Model):
    date = models.DateField(null=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # promo_code=models.CharField(max_length=255,null=True,blank=True)
    # precentage=models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    capacity=models.IntegerField(null=True,blank=True)
    min_purchasable_quantity = models.IntegerField(default=1, null=True, blank=True)
    max_purchasable_quantity = models.IntegerField(default=10, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    
    
    

    def __str__(self):
        return str(self.date)
    

class AvailableDateService(models.Model):
    date = models.DateField(null=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    # promo_code=models.CharField(max_length=255,null=True,blank=True)
    # precentage=models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    capacity=models.IntegerField(null=True,blank=True)
    min_purchasable_quantity = models.IntegerField(default=1, null=True, blank=True)
    max_purchasable_quantity = models.IntegerField(default=10, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    

    def __str__(self):
        return str(self.date)
    

    
    
class HutIncludes(models.Model):
    icon = models.ImageField(null=True, blank=True, upload_to=icons, max_length=500)
    hut = models.ForeignKey("Hut", on_delete=models.CASCADE, related_name="includes")
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)

    

class HutImages(models.Model):
    image = models.ImageField(upload_to=hut_image, null=True, blank=True, max_length=500)

   

class Location(models.Model):
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address=models.TextField(null=True, blank=True)
    address_ar=models.TextField(null=True, blank=True)
    # street = models.CharField(max_length=100, blank=True)
    # city = models.CharField(max_length=100, blank=True)
    # state = models.CharField(max_length=100, blank=True)
    # country = models.CharField(max_length=100, blank=True)

    # def save(self, *args, **kwargs):
    #     if self.latitude and self.longitude:
    #         print(self.latitude, self.longitude)
    #         try:
    #             self.street, self.city, self.state, self.country = get_location(self.latitude, self.longitude)
    #         except:
    #             print(f"none")
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"{self.street}, {self.city}, {self.state}, {self.country}"


class Note(models.Model):
    text = models.TextField()
    text_ar = models.TextField(null=True,blank=True)
    icon=models.ImageField(null=True, blank=True, upload_to=icons, max_length=500)
 

class PromoCode(models.Model):
    code=models.CharField(max_length=255,unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True) 
    percentage=models.IntegerField(default=0)
    
class Hut(models.Model):
    
    title = models.CharField(max_length=100)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    # price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=10, choices=(("small", "small"),('meduim','meduim'),('large','large')))
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    # includes = models.ManyToManyField(Includes, related_name='huts',null=True,blank=True)
    # available_dates = models.ManyToManyField(AvailableDate, related_name='huts')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    images=models.ManyToManyField(HutImages,null=True,blank=True)
    main_image= models.ImageField(upload_to=hut_image, null=True, blank=True, max_length=500)
    location=models.ForeignKey(Location, on_delete=models.CASCADE,null=True,blank=True)
    max_kids_num=models.IntegerField(null=True, blank=True,)
    bedrooms_num=models.IntegerField(null=True, blank=True,)
    bathrooms_num=models.IntegerField(null=True, blank=True,)
    max_persons_num=models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    check_in=models.TimeField(null=True,blank=True)
    check_out=models.TimeField(null=True,blank=True)
    macc_address=models.CharField(max_length=255,null=True, blank=True)
    promocode=models.ManyToManyField(PromoCode,null=True,blank=True)
    def __str__(self):
        return self.title




class AvailableDateRanges(models.Model):
    date_from = models.DateField(db_index=True)
    date_to= models.DateField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    promo_code=models.CharField(max_length=255,null=True,blank=True)
    precentage=models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    huts=models.ForeignKey(Hut, on_delete=models.CASCADE,related_name='available_dates')
    def __str__(self):
        return f"hut_id #{self.huts.id} date from {self.date_from} and date to {self.date_to}"



class Event(models.Model):
    supplier=models.ForeignKey(User, on_delete=models.CASCADE,related_name='events',null=True,blank=True)
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    # price = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    hut= models.ForeignKey(Hut, on_delete=models.CASCADE,null=True,blank=True)
    
    available_dates = models.ManyToManyField(AvailableDateEvent, related_name='events',null=True,blank=True)
    capacity=models.IntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    image = models.ImageField(upload_to=event_image, null=True, blank=True, max_length=500)
    location=models.ForeignKey(Location, on_delete=models.CASCADE,null=True,blank=True)
    min_purchasable_quantity = models.IntegerField(default=1, null=True, blank=True)
    max_purchasable_quantity = models.IntegerField(default=10, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    is_delete = models.BooleanField(default=False, db_index=True) 
    
    def __str__(self):
        return self.title


class KenSpecialItems(models.Model):
    supplier=models.ForeignKey(User, on_delete=models.CASCADE,related_name='ken_items',null=True,blank=True)
    image = models.ImageField(upload_to=event_image, null=True, blank=True, max_length=500)
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    # description = models.TextField()
    # description_ar = models.TextField(null=True,blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    capacity=models.IntegerField()
    huts=models.ManyToManyField(Hut,null=True,blank=True)
    min_purchasable_quantity = models.IntegerField(default=1, null=True, blank=True)
    max_purchasable_quantity = models.IntegerField(default=10, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    is_delete = models.BooleanField(default=False, db_index=True) 
    
    
    
    

class Services(models.Model):
    supplier=models.ForeignKey(User, on_delete=models.CASCADE,related_name='services')
    image = models.ImageField(upload_to=event_image, null=True, blank=True, max_length=500)
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    hut= models.ForeignKey(Hut, on_delete=models.CASCADE,null=True,blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    capacity=models.IntegerField()
    available_dates = models.ManyToManyField(AvailableDateService, related_name='services',null=True,blank=True)
    min_purchasable_quantity = models.IntegerField(default=1, null=True, blank=True)
    max_purchasable_quantity = models.IntegerField(default=10, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True) 
    is_delete = models.BooleanField(default=False, db_index=True) 
    
    
    
    
    
    
 
    
class HutRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    hut = models.ForeignKey(Hut, on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True)
    is_testmonail=models.BooleanField(default=True)
    

    def save(self, *args, **kwargs):
        # Save the rating
        super().save(*args, **kwargs)

        # Recalculate and update the hut's average rating
        avg_rating = HutRating.objects.filter(hut=self.hut).aggregate(avg=Avg('value'))['avg'] or 0.0
        self.hut.rate = round(avg_rating, 2)
        self.hut.save()
        
        
    


class Booking(models.Model):
    # Null for a guest booking made without an account. The guest_* fields below
    # carry the same details registration collects, and the contact_* properties
    # read from whichever source applies so callers do not have to branch.
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=255, null=True, blank=True)
    guest_email = models.EmailField(null=True, blank=True)
    guest_phone = models.CharField(max_length=16, null=True, blank=True)
    guest_id_num = models.CharField(max_length=15, null=True, blank=True)
    # Lets a guest reopen their booking and QR from the link in their email,
    # and authorises their payment calls. Unguessable and never reused.
    access_token = models.UUIDField(default=uuid.uuid4, editable=False,
                                    unique=True, null=True, blank=True,
                                    db_index=True)
    hut = models.ForeignKey(Hut, on_delete=models.SET_NULL, null=True, blank=True,related_name="bookings")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    persons_max_num = models.IntegerField()
    paid=models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True,blank=True)
    not_paid=models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True,blank=True)
    kids_max_num = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status=models.CharField(max_length=255, choices=(("pending", "pending"),('confirmed','confirmed'),('cancelled','cancelled'),('paid','paid'),('refuned','refuned')),default="pending", db_index=True)
    qr_code = models.CharField(max_length=255, blank=True, null=True, default=uuid.uuid4)
    qr_code_image = models.ImageField(upload_to=qr_image, null=True, blank=True)
    is_qr_genereated=models.BooleanField(default=False)
    is_paid=models.BooleanField(default=False)
    invoice_url = models.URLField(null=True, blank=True)
    is_reviewed=models.BooleanField(default=False)
    is_scaned=models.CharField(max_length=255, choices=(("not_started", "not_started"),('scaned','scaned'),('not_valid','not_valid')),default="not_started")
    promocode=models.ForeignKey(PromoCode,on_delete=models.SET_NULL,null=True,blank=True)
    @property
    def is_guest_booking(self):
        return self.user_id is None

    @property
    def contact_name(self):
        if self.user_id:
            return self.user.full_name or self.user.email
        return self.guest_name

    @property
    def contact_email(self):
        return self.user.email if self.user_id else self.guest_email

    @property
    def contact_phone(self):
        return self.user.phone if self.user_id else self.guest_phone

    @property
    def contact_id_num(self):
        return self.user.id_num if self.user_id else self.guest_id_num

    def __str__(self):
        who = self.user if self.user_id else f"guest {self.guest_email or '-'}"
        return f"Booking #{self.pk} by {who}"
    # def save(self, *args, **kwargs):
    #  from .utils import generate_qr_code_image
    #  import json

     
    #  if not self.qr_code_image and self.pk:
    #     qr_data = f"Booking ID: {self.pk}"
    #     # qr_data = json.dumps({"booking_id": self.pk,"hut": self.hut.macc_address if self.hut else None,})
    #     image_file = generate_qr_code_image(qr_data)
    #     self.qr_code_image.save(f"booking_{self.pk}_qr.png", image_file, save=False)
    #  super().save(*args, **kwargs)
class BookingDate(models.Model):
    booking = models.ForeignKey(Booking, related_name='dates', on_delete=models.CASCADE)
    date_from = models.DateField(db_index=True)
    date_to= models.DateField(db_index=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    is_extra=models.BooleanField(default=False)
    is_paid=models.BooleanField(default=False)
    is_confirmed=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    
    def __str__(self):
        return  f"id #{self.pk}  booking {self.booking}"
    

class EventTicket(models.Model):
    booking = models.ForeignKey(Booking, related_name='events', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    date = models.DateField()
    # data_fk=models.ForeignKey(AvailableDateEvent,on_delete=models.SET_NULL,null=True,blank=True)
    is_extra=models.BooleanField(default=False)
    is_paid=models.BooleanField(default=False)
    is_confirmed=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    
    def __str__(self):
        return  f"id #{self.pk}  booking {self.booking}"

    def clean(self):
        if self.quantity < self.event.min_purchasable_quantity or self.quantity > self.event.max_purchasable_quantity:
            raise ValidationError("quantity out of allowed range for this event.")

class ServiceTicket(models.Model):
    booking = models.ForeignKey(Booking, related_name='services', on_delete=models.CASCADE)
    service = models.ForeignKey(Services, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    date = models.DateField()
    is_extra=models.BooleanField(default=False)
    is_paid=models.BooleanField(default=False)
    is_confirmed=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    
    def __str__(self):
        return  f"id #{self.pk}  booking {self.booking}"
    

    def clean(self):
        if self.quantity < self.service.min_purchasable_quantity or self.quantity > self.service.max_purchasable_quantity:
            raise ValidationError("quantity out of allowed range for this service.")

class SpecialItemTicket(models.Model):
    booking = models.ForeignKey(Booking, related_name='special_items', on_delete=models.CASCADE)
    item = models.ForeignKey(KenSpecialItems, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_extra=models.BooleanField(default=False)
    is_paid=models.BooleanField(default=False)
    is_confirmed=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    
    def __str__(self):
        return  f"id #{self.pk}  booking {self.booking}"
    

    def clean(self):
        if self.quantity < self.item.min_purchasable_quantity or self.quantity > self.item.max_purchasable_quantity:
            raise ValidationError("quantity out of allowed range for this item.")




# models.py
class DaftraInvoice(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='daftra_invoice')
    invoice_number = models.CharField(max_length=100)
    invoice_url = models.URLField(blank=True, null=True)
    pdf_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} for Booking #{self.booking.id}"
    
    
    
    

class Icon(models.Model):
    image = models.ImageField(upload_to=icons, max_length=500)

    def __str__(self):
        return f"Icon {self.id}"



class HutActivity(models.Model):
    hut = models.ForeignKey(Hut, on_delete=models.CASCADE, related_name='activities')
    description = models.TextField()
    description_ar = models.TextField()

    def __str__(self):
        return self.description[:50]

class HutMainService(models.Model):
    hut = models.ForeignKey(Hut, on_delete=models.CASCADE, related_name='main_services')
    icon = models.ForeignKey(Icon, on_delete=models.CASCADE, related_name='hut_main_services')
    description = models.TextField()
    description_ar= models.TextField()
    is_extra = models.BooleanField(default=False)

    def __str__(self):
        return self.description[:50]


class EventInclude(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_include')
    icon = models.ForeignKey(Icon, on_delete=models.CASCADE, related_name='event_icon')
    description = models.TextField()
    description_ar = models.TextField()
    

    def __str__(self):
        return self.description[:50]
    
    
class EventNote(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_note')
    
    description = models.TextField()
    description_ar = models.TextField()
    

    def __str__(self):
        return self.description[:50]
    


class QrLogs(models.Model):
    booking= models.ForeignKey(Booking, on_delete=models.CASCADE)
    status=models.CharField(max_length=255,choices=(('check_in','check_in'),('check_out','check_out')))
    created_at=models.DateTimeField(null=True,blank=True)




