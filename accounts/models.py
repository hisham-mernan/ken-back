from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
import random
from datetime import date
import string
import pyotp
from django.utils import timezone
from datetime import timedelta
from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email must be set')
       
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email,password=password,)
        user.role = 'admin'
        user.is_superuser = True
        user.is_staff = True
        user.is_verfied = True  # Superusers are automatically verified
        user.save(using=self._db)
        return user
    

    
def upload_path(instance, filename):
    return '/'.join(['uploads/profile', filename])

def partner(instance, filename):
    return '/'.join(['uploads/partner', filename])

def support(instance, filename):
    return '/'.join(['uploads/support', filename])
class User(AbstractUser):
    email = models.EmailField(unique=True)
    full_name=models.CharField(max_length=255,null=True,blank=True)
    role = models.CharField(max_length=200, choices=(("guest", "guest"),('supplier','supplier'),('admin','admin')))
    gender=models.CharField(max_length=50, choices=(("male", "male"),('female','female')),null=True,blank=True)
    is_active = models.BooleanField(default=True) 
    avatar = models.ImageField(null=True, blank=True, upload_to=upload_path) 
    breif=models.TextField(null=True,blank=True)
    address=models.TextField(null=True,blank=True)
    birth_date=models.DateField(null=True,blank=True)
    username = models.CharField(max_length=225, unique=False, null=True, blank=True)
    phone=models.CharField(max_length=16)
    id_num=models.IntegerField(max_length=15,null=True)
    is_verfied=models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=6, blank=True, null=True)
    created_at=models.DateField(auto_now_add=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    change_password_at = models.DateTimeField(null=True, blank=True)
    is_forget_pass=models.BooleanField(default=False)
    is_email_changed=models.BooleanField(default=False)
    email_temp=models.EmailField(null=True,blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    def calculate_age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
   
    def __str__(self):
        return f"{self.full_name} - {self.email}- {self.role}"








from django.db.models import Avg
class WebsiteRate(models.Model):
    average_value = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    @classmethod
    def update_average(cls):
      
        average = WebRating.objects.aggregate(Avg('value'))['value__avg'] or 0.00
        obj, created = cls.objects.get_or_create()  
        obj.average_value = round(average, 2)
        obj.save()

class WebRating(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    
    
    value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    content=models.TextField(null=True,blank=True)
    def save(self, *args, **kwargs):
      
        super().save(*args, **kwargs)
        
        
        WebsiteRate.update_average()
        


class Partners(models.Model):
    image = models.ImageField(upload_to=partner, null=True, blank=True)
    
    

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    


class Support(models.Model):
    full_name=models.CharField(null=True,blank=True, max_length=50)
    email=models.EmailField(null=True,blank=True, max_length=254)
    operation = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supports_operation',null=True,blank=True)
    content = models.TextField()
    attachment = models.FileField(upload_to=support, null=True, blank=True)
    is_replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_admin= models.BooleanField(default=False)

    def __str__(self):
        return self.email
    
    
    

class Notification(models.Model):
    TYPE_CHOCIES = [
        
       
        ("booking", "booking"),
        ("supplier_tickets", "supplier_tickets",),
        ("supplier_event_tickets", "supplier_event_tickets",),
        ("supplier_service_tickets", "supplier_service_tickets",),
        
        ("extra", "extra",),
        ("supplier_extra", "supplierextra",),
        
       
        ("support", "support"),
        ("booking_paid", "booking_paid"),
        ("need_refund", "need_refund"),
      
        
    
        
        
        
        
        
        
        
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    datetime = models.DateTimeField(auto_now_add=True)
    mark_as_read = models.BooleanField(default=False)
    message=models.TextField(null=True,blank=True)
    message_ar=models.TextField(null=True,blank=True)
    type=models.CharField(max_length=30, choices= TYPE_CHOCIES, null=True,blank=True)
   

    def __str__(self):
        return f"Report by {self.user} on {self.content_object}"
    