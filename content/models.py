from django.db import models

# Create your models here.


def story(instance, filetitle):
    return '/'.join(['uploads/content/story', filetitle])



def our_service(instance, filetitle):
    return '/'.join(['uploads/content/our_service', filetitle])



def special_about_us(instance, filetitle):
    return '/'.join(['uploads/content/special_about_us', filetitle])

def about_us(instance, filetitle):
    return '/'.join(['uploads/content/about_us', filetitle])
class Story (models.Model):
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    image = models.ImageField(upload_to=story, null=True, blank=True)
    
    
class AboutUs(models.Model):
    about_us= models.TextField()
    about_us_ar= models.TextField(null=True,blank=True)
    vission_ar= models.TextField(null=True,blank=True)
    vission= models.TextField(null=True,blank=True)
    mission_image = models.ImageField(upload_to=about_us, null=True, blank=True)
    mission_ar= models.TextField(null=True,blank=True)
    mission= models.TextField(null=True,blank=True)
    vision_image = models.ImageField(upload_to=about_us, null=True, blank=True)
    main_image= models.ImageField(upload_to=about_us, null=True, blank=True)
    created_at=models.DateField(auto_now_add=True,null=True, blank=True)
    
    
    
 

class FAQ(models.Model):
    question= models.TextField()
    question_ar = models.TextField(null=True,blank=True)
    answer= models.TextField()
    answer_ar = models.TextField(null=True,blank=True)
    
class TermsAndCindationsTitle(models.Model):
    title = models.CharField(max_length=500)
    title_ar = models.CharField(max_length=500,null=True,blank=True)
    
class TermsAndCindations(models.Model):
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    created_at=models.DateField( auto_now_add=True,null=True, blank=True)
    
    


# models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class WebStore(models.Model):
    
    avg_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
  # <‑‑ stored value
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"({self.avg_rate:.2f})"


class WebStoreRating(models.Model):
   
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webstore_ratings",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
       
        ordering = ("-created_at",)

    def __str__(self):
        return f" - {self.rating}by {self.user}"
    
    
    
    
    
class OurService(models.Model):
    description = models.TextField()
    description_ar = models.TextField(null=True,blank=True)
    image = models.ImageField(upload_to=our_service, null=True, blank=True)
    title = models.TextField(null=True,blank=True)
    title_ar = models.TextField(null=True,blank=True)
    
class SpecailAboutUs(models.Model):
    title = models.TextField()
    title_ar = models.TextField(null=True,blank=True)
    image = models.ImageField(upload_to=special_about_us, null=True, blank=True)

# ------------- automatic average update -------------
@receiver([post_save, post_delete], sender=WebStoreRating)
def update_global_average(sender, instance, **kwargs):
    avg = WebStoreRating.objects.aggregate(v=Avg("rating"))["v"] or 0
    avg_obj, _ = WebStore.objects.get_or_create(pk=1)
    avg_obj.avg_rate = round(avg, 2)
    avg_obj.save(update_fields=["avg_rate"])