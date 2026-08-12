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
        
        
class OurServiceSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OurService
        fields = '__all__'

    def get_image(self, obj):
        if not obj.image:
            return None
        val = str(obj.image.url) if hasattr(obj.image, 'url') else str(obj.image)
        if val.startswith("http://") or val.startswith("https://"):
            return val
        media_url = getattr(settings, 'MEDIA_URL', 'https://onzkkxvzuzkdcsckcxsp.supabase.co/storage/v1/object/public/media/')
        return media_url.rstrip('/') + '/' + val.lstrip('/')

class SpecailAboutUsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SpecailAboutUs
        fields = '__all__'

    def get_image(self, obj):
        if not obj.image:
            return None
        val = str(obj.image.url) if hasattr(obj.image, 'url') else str(obj.image)
        if val.startswith("http://") or val.startswith("https://"):
            return val
        media_url = getattr(settings, 'MEDIA_URL', 'https://onzkkxvzuzkdcsckcxsp.supabase.co/storage/v1/object/public/media/')
        return media_url.rstrip('/') + '/' + val.lstrip('/')
        
        
        

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