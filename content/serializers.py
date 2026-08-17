from rest_framework import serializers
from django.conf import settings
from .models import *

class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = '__all__'

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'
        
        

class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = '__all__'
        
        
def absolute_media_url(file_field):
    """Absolute public URL for a FileField value, or None."""
    if not file_field:
        return None
    val = str(file_field.url) if hasattr(file_field, 'url') else str(file_field)
    if val.startswith("http://") or val.startswith("https://"):
        return val
    media_url = getattr(settings, 'MEDIA_URL', 'https://onzkkxvzuzkdcsckcxsp.supabase.co/storage/v1/object/public/media/')
    return media_url.rstrip('/') + '/' + val.lstrip('/')


class AbsoluteImageURLMixin:
    """Return `image` as an absolute URL while keeping the field writable.

    These serializers previously declared `image` as a SerializerMethodField,
    which DRF treats as read-only: an uploaded file was discarded without any
    error and the request still returned 200, so the admin dashboard reported
    a successful save while the image never changed. Building the URL in
    to_representation keeps the response identical but leaves the underlying
    ModelSerializer field writable.
    """

    image_field_name = "image"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data[self.image_field_name] = absolute_media_url(
            getattr(instance, self.image_field_name, None)
        )
        return data


class OurServiceSerializer(AbsoluteImageURLMixin, serializers.ModelSerializer):
    class Meta:
        model = OurService
        fields = '__all__'


class SpecailAboutUsSerializer(AbsoluteImageURLMixin, serializers.ModelSerializer):
    class Meta:
        model = SpecailAboutUs
        fields = '__all__'
        
        
        

class TermsAndCindationsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TermsAndCindations
        fields = [
            'id',
            'title', 'title_ar',
            'description', 'description_ar',
            'created_at',
        ]
        read_only_fields = ['id']
        
        

class TermsAndCindationsTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndCindationsTitle
        fields = ['id', 'title', 'title_ar']
        
        
        
        
        
        
class WebStoreRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebStoreRating
        fields = ["id", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]

    # Inject the current user automatically
    def create(self, validated_data):
        user = self.context["request"].user
        return WebStoreRating.objects.update_or_create(   # allows updating the same rating
          
            user=user,
            defaults={
                "rating": validated_data["rating"],
                "comment": validated_data.get("comment", "")
            }
        )[0]

class WebStoreAvgRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebStore
        fields = ["avg_rate"] 