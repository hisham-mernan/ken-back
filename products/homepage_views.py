from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.utils.timezone import now

from products.models import Hut, Event, Services, HutRating
from products.serializers import HutListHomeSerializer, EventSerializer, ServiceSerializer, HutRatingSerializer
from content.models import AboutUs, FAQ
from content.serializers import AboutUsSerializer, FAQSerializer
from accounts.models import Partners
from accounts.serializers import PartnerSerializer


class HomepageDataAPIView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        cache_key = "homepage_combined_data"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
            response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
            return response

        today = now().date()

        # 1. Huts
        huts_qs = (
            Hut.objects
            .select_related('location')
            .prefetch_related('images', 'available_dates', 'promocode')
            .filter(is_active=True)
            .order_by('-created_at')[:3]
        )
        huts_data = HutListHomeSerializer(huts_qs, many=True, context={'request': request}).data

        # 2. Events
        events_qs = (
            Event.objects
            .select_related('location', 'supplier', 'hut')
            .prefetch_related('available_dates', 'event_note', 'event_include', 'event_include__icon')
            .filter(is_active=True, is_delete=False)
            .distinct()
            .order_by('-created_at')[:10]
        )
        events_data = EventSerializer(events_qs, many=True, context={'request': request}).data

        # 3. Services
        services_qs = (
            Services.objects
            .select_related('supplier', 'hut')
            .prefetch_related('available_dates')
            .filter(is_active=True, is_delete=False)
            .distinct()
            .order_by('-created_at')[:10]
        )
        services_data = ServiceSerializer(services_qs, many=True, context={'request': request}).data

        # 4. About Us
        about_obj = AboutUs.objects.order_by('-created_at').first()
        about_data = [AboutUsSerializer(about_obj, context={'request': request}).data] if about_obj else []

        # 5. FAQ
        faq_qs = FAQ.objects.all().order_by('-id')
        faq_data = FAQSerializer(faq_qs, many=True, context={'request': request}).data

        # 6. Testimonials
        testimonials_qs = HutRating.objects.filter(is_testmonail=True).order_by('-id')[:3]
        testimonials_data = HutRatingSerializer(testimonials_qs, many=True, context={'request': request}).data

        # 7. Partners
        partners_qs = Partners.objects.all().order_by('-id')
        partners_data = PartnerSerializer(partners_qs, many=True, context={'request': request}).data

        payload = {
            "huts": huts_data,
            "events": events_data,
            "services": services_data,
            "about_us": about_data,
            "faq": faq_data,
            "testimonials": testimonials_data,
            "partners": partners_data,
        }

        cache.set(cache_key, payload, 900)  # 15 minutes cache

        response = Response(payload, status=status.HTTP_200_OK)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response
