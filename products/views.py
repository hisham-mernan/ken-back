from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework import serializers
from .models import *
from .serializers import *
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from accounts .permissions import *
from accounts.models import User,WebsiteRate
from .models import *
from .serializers import HutSerializer
from datetime import datetime, timedelta, date
from rest_framework.pagination import PageNumberPagination
from datetime import date 
from rest_framework import generics
from django.utils.timezone import now
from django.conf import settings
from urllib.parse import urlparse
from .models import Hut
from .serializers import HutListHomeSerializer

from django.db.models import Q









class ThreePagePagination(PageNumberPagination):
    page_size = 3  # Number of items per page
    page_size_query_param = 'page_size'  # Optional: allow client to set page size
    max_page_size = 50  # Optional: upper limit on page size

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })







class TenPagePagination(PageNumberPagination):
    page_size = 10  # Number of items per page
    page_size_query_param = 'page_size'  # Optional: allow client to set page size
    max_page_size = 50  # Optional: upper limit on page size

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })



from django.core.cache import cache


class HutListAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods]
    serializer_class = HutListSerializer
    pagination_class=ThreePagePagination
    

    def get_queryset(self):
        today = now().date()
     
        return (
            Hut.objects
            .select_related('location')
            .prefetch_related('images', 'available_dates', 'promocode')
            .filter(
                Q(available_dates__date_from__lt=today) &
                Q(available_dates__date_to__gt=today), is_active=True
            )
            .distinct()
            .order_by('-created_at')[:3]
        )

    def list(self, request, *args, **kwargs):
        page = request.query_params.get('page', '1')
        cache_key = f"hut_list_page_{page}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 900)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response

class HutListHomeAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    serializer_class = HutListHomeSerializer

    def get_queryset(self):
        return (
            Hut.objects
            .select_related('location')
            .prefetch_related('images', 'available_dates', 'promocode')
            .filter(is_active=True)
            .order_by('-created_at')[:3]
        )

    def list(self, request, *args, **kwargs):
        cache_key = "hut_list_home"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 900)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response



   
class EventRetrieveWebView(generics.RetrieveAPIView):
    serializer_class = EventSerializer
    permission_classes = []  
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        return Event.objects.select_related('location', 'supplier', 'hut').prefetch_related('available_dates', 'event_note', 'event_include', 'event_include__icon').filter(is_delete=False)
  









class HutDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hut.objects.select_related('location').prefetch_related('images', 'available_dates', 'promocode', 'main_services', 'main_services__icon', 'activities')
    serializer_class = HutSerializer
    permission_classes = [IsAdminForUnsafeMethods] 
    def update(self, request, *args, **kwargs):
        """
        Make hut updates partial by default so fields like check_in/check_out
        are not required when editing.
        """
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class KenSpecialItemsListByHutIdView(generics.ListAPIView):
    serializer_class = KenSpecialItemsListWebSerializer
    pagination_class = TenPagePagination
    permission_classes = []

    def get_queryset(self):
        hut_id = self.kwargs.get('hut_id')  
        queryset = KenSpecialItems.objects.filter(is_delete=False, huts__id=hut_id,is_active=True)

        # Optional filter by is_active
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        # Optional search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(title_ar__icontains=search) |
                Q(huts__title__icontains=search) |
                Q(huts__title_ar__icontains=search)
            ).distinct()

        return queryset


class KenSpecialItemsDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = KenSpecialItems.objects.all()
    serializer_class = KenSpecialItemsSerializer
    permission_classes = [IsAdminOrSupplier] 
    def update(self, request, *args, **kwargs):
        user=request.user
        partial = True  
        instance = self.get_object()
        if hasattr(user, "role") and user.role == "supplier":
          if instance.supplier != user:
            return Response(
                {"detail": "You are not allowed to update this item."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def get_object(self):
     obj = super().get_object()
     user = self.request.user

     if hasattr(user, "role") and user.role == "supplier":
        if obj.supplier != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not allowed to view this item.")

     return obj

    
    
    
    
    
    
    

class EventListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    pagination_class=TenPagePagination
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.select_related('location', 'supplier', 'hut').prefetch_related('available_dates', 'event_note', 'event_include', 'event_include__icon').filter(
            is_active=True,
            is_delete=False
        ).distinct().order_by('-created_at')

    def list(self, request, *args, **kwargs):
        page = request.query_params.get('page', '1')
        cache_key = f"event_list_page_{page}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 900)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response


class RandomEventListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.select_related('location', 'supplier', 'hut').prefetch_related('available_dates', 'event_note', 'event_include', 'event_include__icon').filter(
            is_active=True,
            is_delete=False,
        ).distinct().order_by('-created_at')[:10]

    def list(self, request, *args, **kwargs):
        cache_key = "random_event_list"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 300)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response

# class EventRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAdminForUnsafeMethods] 
    
#     queryset = Event.objects.all()
#     serializer_class = EventSerializer
    
    
    
    
    
    
class ServiceListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrSupplier] 
    pagination_class = TenPagePagination
    serializer_class = ServiceSerializer

    def get_queryset(self):
        user = self.request.user
        print(user.role)
        if user.role=="supplier":
           queryset = Services.objects.filter(is_delete=False, supplier=user)

        else:
          queryset=Services.objects.filter(is_delete=False)

        # Filter by is_active if provided
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        # Search by title or title_ar
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(title_ar__icontains=search)|
                Q(hut__title__icontains=search) |
                Q(hut__title_ar__icontains=search) 
            )

        # Order by price if provided
        ordering = self.request.query_params.get('sort')
        if ordering == 'price':
            queryset = queryset.order_by('price')
        elif ordering == '-price':
            queryset = queryset.order_by('-price')
        else:
            queryset = queryset.order_by('-id')  # default ordering

        return queryset

    

# class ServiceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAdminOrSupplier] 
    
    
#     # queryset = Services.objects.all()
    
#     serializer_class = ServiceSerializer
#     def get_queryset(self):
#         user=self.request.user
#         return Services.objects.filter(supplier=user)
#     def update(self, request, *args, **kwargs):
#         partial = True  
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=partial)
#         serializer.is_valid(raise_exception=True)
#         self.perform_update(serializer)
#         return Response(serializer.data, status=status.HTTP_200_OK)
class ServiceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrSupplier]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role=="admin":
            return Services.objects.all()
        return Services.objects.filter(supplier=user)

    def update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()

        
        if request.user.role=="admin":
            allowed_fields = {"is_active", "is_delete"}
            data = {field: value for field, value in request.data.items() if field in allowed_fields}
        else:
            forbidden_fields = {"is_active", "is_delete"}
            data = {field: value for field, value in request.data.items() if field not in forbidden_fields}

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ServiceRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrSupplier]
    serializer_class = ServiceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Services.objects.all()
        return Services.objects.filter(supplier=user)

    def _build_update_data(self, request):
        """Build a mutable dict for the serializer from request.data, preserving list fields and applying role-based filter."""
        # Copy request.data into a mutable dict; handle both dict (JSON) and QueryDict (form)
        if hasattr(request.data, "get") and hasattr(request.data, "keys"):
            data = {}
            for key in request.data.keys():
                if key == "date" and hasattr(request.data, "getlist"):
                    val = request.data.getlist("date") or request.data.get("date")
                    if val is not None:
                        data[key] = val if isinstance(val, list) else [val]
                else:
                    data[key] = request.data.get(key)
        else:
            data = dict(request.data) if request.data else {}

        # Accept camelCase for admin-only fields (frontend may send isActive / isDelete)
        for api_key, payload_key in [("is_active", "isActive"), ("is_delete", "isDelete")]:
            if payload_key in data and api_key not in data:
                data[api_key] = data.pop(payload_key)

        # Normalize boolean-like values so serializer gets proper bools (avoids type errors)
        for key in ("is_active", "is_delete"):
            if key in data:
                v = data[key]
                if v is None:
                    data[key] = False
                elif isinstance(v, bool):
                    data[key] = v
                elif isinstance(v, str):
                    data[key] = v.strip().lower() in ("true", "1", "yes")
                else:
                    data[key] = bool(v)

        # ServiceSerializer uses CharField for date: normalize list to comma-separated string
        if "date" in data and isinstance(data["date"], list):
            data["date"] = ",".join(str(d) for d in data["date"]) if data["date"] else ""

        # Role-based field filter: suppliers cannot change is_active/is_delete; admin can update any field
        if request.user.role != "admin":
            data = {k: v for k, v in data.items() if k not in ("is_active", "is_delete")}
        return data

    def update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()
        data = self._build_update_data(request)

        # Grab date for view-level handling (optional, serializer also handles it)
        if hasattr(request.data, "getlist"):
            new_dates = request.data.getlist("date")
        else:
            raw = request.data.get("date")
            if raw is None:
                new_dates = []
            elif isinstance(raw, list):
                new_dates = raw
            else:
                new_dates = [raw] if raw else []

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Update available_dates if provided at top level
        if new_dates:
            from datetime import datetime as dt
            validated_dates = []
            for d in new_dates:
                try:
                    validated_dates.append(dt.strptime(str(d).strip(), "%Y-%m-%d").date())
                except (ValueError, TypeError):
                    raise serializers.ValidationError({"date": f"Invalid date format: {d}. Use YYYY-MM-DD"})
            instance.available_dates.clear()
            date_objs = []
            for d in validated_dates:
                obj, _ = AvailableDateService.objects.get_or_create(date=d)
                date_objs.append(obj)
            instance.available_dates.set(date_objs)
            instance.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

 
class RandomServiceListAPIView(generics.ListAPIView):
    permission_classes = [] 
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Services.objects.select_related('supplier', 'hut').prefetch_related('available_dates').filter(
            is_active=True, is_delete=False
        ).distinct().order_by('-id')[:10]

    def list(self, request, *args, **kwargs):
        cache_key = "random_service_list"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 300)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response
    
    
    


class HutRatingListAPIView(generics.ListAPIView):
    queryset = HutRating.objects.filter(is_testmonail=True).order_by('-id')
    serializer_class = HutRatingSerializer
    permission_classes = []

    def get_queryset(self):
        hut_id = self.request.query_params.get('hut')
        qs = super().get_queryset()
        if hut_id:
            qs = qs.filter(hut_id=hut_id)
        return qs[:3]  

    def list(self, request, *args, **kwargs):
        hut_id = request.query_params.get('hut', 'all')
        cache_key = f"hut_rating_list_{hut_id}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
        else:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, 900)
        response['Cache-Control'] = 'public, max-age=60, s-maxage=300, stale-while-revalidate=600'
        return response











# class BookingCreateView(generics.CreateAPIView):
    
#     queryset = Booking.objects.all()
#     serializer_class = BookingSerializer
#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)
        
     
class BookingCreateView(generics.CreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking_date = serializer.validated_data.get('date', None)
        if booking_date:
            date_from = booking_date.get('date_from')
            if not date_from:
                return Response({"detail": "Booking date 'date_from' is required."}, status=status.HTTP_400_BAD_REQUEST)

            # booking_month = date_from.month
            # booking_year = date_from.year

            # exists = Booking.objects.filter(
            #     user=user,
            #     dates__date_from__year=booking_year,
            #     dates__date_from__month=booking_month
            # ).exists()

            # if exists:
            #     return Response({"detail": "You can only have one booking per month."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "Booking date is required."}, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    def perform_create(self, serializer):
        # attaches the current user and then calls serializer.save()
        serializer.save(user=self.request.user)
      

class BookingUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        # Get booking before update to check current status
        booking = self.get_object()
        current_status = booking.status
        new_status = request.data.get("status")
        
        # Only check status change if status is provided AND it's different from current status
        if new_status and new_status != current_status:
            ok, msg = change_booking_status(booking, new_status)
            print(booking.id)

            if not ok:
                return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Proceed with regular update (allows updating other fields even if status is confirmed/paid)
        response = super().update(request, *args, **kwargs)
        
        # Refresh booking object after update
        booking.refresh_from_db()

        # If status change was successful, include message in response
        if new_status and new_status != current_status:
            response.data['status'] = booking.status
            response.data['status_message'] = msg

            if booking.status == "confirmed":
                response.data['message'] = "Your booking has been successfully confirmed."

        return response


 





    


# from django.utils.timezone import now
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from django.db.models import Count, Q
# from .models import Event, Services
# from .serializers import EventSerializer, ServiceSerializer
# from django.utils.dateparse import parse_date
# from datetime import timedelta

# def expand_date_range(start_date, end_date):
#     return [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
# class AvailableServiceView(APIView):
#     def post(self, request):
#         try:
#             date_from_str = request.data.get('date_from')
#             date_to_str = request.data.get('date_to')
#             if not date_from_str or not date_to_str:
#                 raise ValueError("Missing date range.")

#             date_from = parse_date(date_from_str)
#             date_to = parse_date(date_to_str)
#             if not date_from or not date_to:
#                 raise ValueError("Invalid date format.")
#             if date_from > date_to:
#                 raise ValueError("Start date must be before end date.")

#             today = now().date()
#             if date_from < today:
#                 raise ValueError("All dates must be in the future.")

#         except (KeyError, ValueError) as e:
#             return Response({"error": str(e)}, status=400)

#         date_list = expand_date_range(date_from, date_to)
#         print(date_list)
#         total_days = len(date_list)
#         print(total_days)

#         # Filter Events that have ALL the dates in available_dates
#         events = (Event.objects
#     .filter(available_dates__date__in=date_list, capacity__gt=0)
#     .distinct()
# )

#         # Same for Services
#         services = (
#     Services.objects
#     .filter(available_dates__date__in=date_list, capacity__gt=0)
#     .distinct()
# )
#         event_data = EventSerializer(events, many=True).data
#         service_data = ServiceSerializer(services, many=True).data

#         return Response({
#             "available_events": event_data,
#             "available_service": service_data
#         })

from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response




def expand_date_range(start, end):
    """Return a list of all dates from start → end inclusive."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


# class AvailableServiceView(APIView):
  
   
#     def post(self, request):
       
#         booking_id = request.data.get("booking_id")
#         if not booking_id:
#             return Response({"error": "booking_id is required."}, status=400)

#         booking = get_object_or_404(
#             Booking.objects.prefetch_related("dates"),
#             pk=booking_id
#         )
#         print(booking,"fff")
#         if not booking.dates.exists():
#             return Response({"error": "This booking has no date ranges."}, status=400)

        
#         # Build the full list of calendar days covered by *all* ranges
      
#         all_days = set()
#         for bd in booking.dates.all():
           
#             all_days.update(expand_date_range(bd.date_from, bd.date_to))

#         today = now().date()
#         print(all_days,"all days:")
#         if any(day < today for day in all_days):
#             return Response({"error": "All booking days must be today or later."}, status=400)

#         total_days = len(all_days)
#         if total_days == 0:
#             return Response({"error": "Empty date span."}, status=400)

    
#         date_filter = Q(available_dates__date__in=all_days)
#         print(date_filter,"data filter")

#         events = (
#             Event.objects
#             .filter(date_filter, capacity__gt=0)
#             # .annotate(match_days=Count("available_dates",
#             #                            filter=date_filter, distinct=True))
#             # # .filter(match_days=total_days)
#             .distinct()
#         )

#         services = (
#             Services.objects
#             .filter(date_filter, capacity__gt=0)
#             # .annotate(match_days=Count("available_dates",
#             #                            filter=date_filter, distinct=True))
#             # .filter(match_days=total_days)
#             .distinct()
#         )

     
#         return Response({
#             "available_events": EventSerializer(events, many=True).data,
#             "available_services": ServiceSerializer(services, many=True).data
#         })

from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.timezone import now
from datetime import timedelta

class AvailableServiceView(APIView):
    def post(self, request):
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required."}, status=400)

        booking = get_object_or_404(Booking.objects.prefetch_related("dates"), pk=booking_id)
        
        if not booking.dates.exists():
            return Response({"error": "This booking has no date ranges."}, status=400)

        all_days = set()
        for bd in booking.dates.all():
            # Ensure date_from <= date_to
            if bd.date_from > bd.date_to:
                continue
            all_days.update(self.expand_date_range(bd.date_from, bd.date_to))

        today = now().date()
        # Filter out past dates and only keep today and future dates
        future_days = {day for day in all_days if day >= today}
        
        if not future_days:
            return Response({"error": "No future booking days available. All booking days must be today or later."}, status=400)

        # Use future_days instead of all_days for the rest of the logic
        all_days = future_days

        # Filter available service dates
        service_dates = AvailableDateService.objects.filter(
            date__in=all_days,
            is_active=True
        )
       
        # Filter available event dates
        event_dates = AvailableDateEvent.objects.filter(
            date__in=all_days,
            capacity__gt=0,
            is_active=True
        )
       

        # Filter services/events by available dates
        services = Services.objects.filter(
            is_active=True,
            is_delete=False,
            hut=booking.hut,
            capacity__gt=0,
            available_dates__in=service_dates
        ).distinct()
        print(services)

        events = Event.objects.filter(
            is_active=True,
            is_delete=False,
            available_dates__in=event_dates
        ).distinct()

        return Response({
            "available_services": ServiceSerializer(services, many=True, context={"request": request}).data,
            "available_events": EventSerializer(events, many=True, context={"request": request}).data
        })

    def expand_date_range(self, start_date, end_date):
        """Utility to generate all dates between two dates (inclusive)."""
        if start_date > end_date:
            return []
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

# class AvailableServiceView(APIView):
#     def post(self, request):
#         booking_id = request.data.get("booking_id")
#         if not booking_id:
#             return Response({"error": "booking_id is required."}, status=400)

#         booking = get_object_or_404(Booking.objects.prefetch_related("dates"), pk=booking_id)
        
#         if not booking.dates.exists():
#             return Response({"error": "This booking has no date ranges."}, status=400)

#         all_days = set()
#         for bd in booking.dates.all():
#             all_days.update(self.expand_date_range(bd.date_from, bd.date_to))

#         today = now().date()
#         if any(day < today for day in all_days):
#             return Response({"error": "All booking days must be today or later."}, status=400)

#         if not all_days:
#             return Response({"error": "Empty date span."}, status=400)

#         date_filter = Q(available_dates__date__in=all_days)

#         events = (
#             Event.objects
#             .filter(date_filter, capacity__gt=0)
#             .distinct()
#         )

#         services = (
#             Services.objects
#             .filter(date_filter, capacity__gt=0)
#             .distinct()
#         )

#         return Response({
#             "available_events": EventSerializer(events, many=True).data,
#             "available_services": ServiceSerializer(services, many=True).data
#         })

#     def expand_date_range(self, start_date, end_date):
#         """Utility to generate all dates between two dates (inclusive)."""
#         return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]



class BookingDetailView(APIView):
    def get(self, request, pk):
        try:
            booking = Booking.objects.select_related('promocode').get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BookingSerializer(booking)
        data = serializer.data
        # Do not expose promo code to users
        data.pop('promocode', None)
        data.pop('promocode_obj', None)
        return Response(data, status=status.HTTP_200_OK)
    
    


    
# class BookingDetailForAminQrView(APIView):
#     permission_classes = [IsAdmin]

#     def get(self, request, pk):
#         is_scan = self.request.query_params.get("is_scan")

#         try:
#             booking = Booking.objects.get(pk=pk)
#         except Booking.DoesNotExist:
#             return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

#         today = date.today()
#         booking_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()

#         if is_scan:
#             if booking.is_scaned == 'scaned':
#                 # Already scanned — just return details
#                 serializer = BookingSerializer(booking)
#                 return Response(serializer.data, status=status.HTTP_200_OK)

#             if booking_date and booking_date.date_from == today and booking.status == 'paid':
#                 # Valid to scan now
#                 booking.is_scaned = 'scaned'
#                 booking.save()
#             else:
#                 # Only set 'not_valid' if it's never been scanned before
#                 if booking.is_scaned != 'scaned':
#                     booking.is_scaned = 'not_valid'
#                     booking.save()

#         serializer = BookingSerializer(booking)
#         return Response(serializer.data, status=status.HTTP_200_OK)  

from rest_framework import status
from datetime import date, datetime

class BookingDetailForAminQrView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        qr_status = request.data.get("status")  # Avoid shadowing 'status' module

        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        today = date.today()
        booking_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
        

        if (booking_date and booking_date.date_from == today and booking.status == 'paid')or booking.is_scaned == 'scaned':
            booking.is_scaned = 'scaned'
            booking.save()

            # Create QrLog
            QrLogs.objects.create(
                booking=booking,
                status=qr_status,
                created_at=datetime.now()
            )

            serializer = BookingSerializer(booking)
            return Response({"scaned "}, status=status.HTTP_200_OK)
        
        else:
            booking.is_scaned = 'not_valid'
            booking.save()
            return Response({"error": "Booking is not valid for scanning today."}, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
    
    

class UpcomingBookingsView(ListAPIView):
    serializer_class = UpComingBookingSerializer


    
    def get_queryset(self):
        today = now().date()
        return (
            Booking.objects
            .filter(user=self.request.user,
                    dates__date_to__gte=today,
                    status__in=['paid','cancelled'],is_paid=True)
            .distinct()
            .order_by('-created_at')[:1]  # still a queryset
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset:
            return Response({}, status=200)
        serializer = self.get_serializer(queryset[0])
        return Response(serializer.data)


class PastBookingsPagination(PageNumberPagination):
    page_size = 1  # adjust as you want
    page_size_query_param = 'page_size'
    max_page_size = 50
    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })

class PastBookingsView(ListAPIView):
    serializer_class = UpComingBookingSerializer
    pagination_class = PastBookingsPagination

    def get_queryset(self):
        today = now().date()
        # Filter bookings where the latest booking date (date_to) is before today
        return Booking.objects.filter(
            dates__date_to__lt=today,user=self.request.user,status__in=['paid','cancelled']
        ).distinct().order_by('-created_at')


# class SupplierListView(generics.ListAPIView):
#     serializer_class = SupplierListSerializer
#     pagination_class = PastBookingsPagination
#     permission_classes = [] 
    
    

#     def get_queryset(self):
#         return User.objects.filter(role='supplier', is_active=True)


# views.py
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# class SupplierListView(generics.ListAPIView):
    
#     serializer_class = SupplierListSerializer
#     pagination_class =  PastBookingsPagination
#     permission_classes = []

#     def get_queryset(self):
#         return User.objects.filter(role="supplier", is_active=True)

#     def list(self, request, *args, **kwargs):
#         # Get paginated suppliers list
#         suppliers_page = self.paginate_queryset(self.get_queryset())

#         if suppliers_page is None:
#             suppliers_page = self.get_queryset()

#         # Services pagination control
#         service_page_number = request.query_params.get("services_page", 1)
#         service_page_size = 4  # max 4 services per supplier

#         enriched_suppliers = []

#         for supplier in suppliers_page:
#             # 👇 Use the correct related_name for supplier.services
#             services_qs = supplier.services.all().order_by("-id")  # related_name='services'

#             # Paginate services manually
#             paginator = Paginator(services_qs, service_page_size)
#             try:
#                 services_page = paginator.page(service_page_number)
#             except (PageNotAnInteger, EmptyPage):
#                 services_page = paginator.page(1)

#             # Serialize supplier
#             supplier_data = SupplierListSerializer(supplier, context={"request": request}).data

#             # Add nested paginated services
#             supplier_data["services"] = {
#                 "count": paginator.count,
#                 "page": services_page.number,
#                 "num_pages": paginator.num_pages,
#                 "next": (
#                     f"{request.build_absolute_uri().split('?')[0]}?page={request.query_params.get('page', 1)}&services_page={services_page.next_page_number()}"
#                     if services_page.has_next() else None
#                 ),
#                 "previous": (
#                     f"{request.build_absolute_uri().split('?')[0]}?page={request.query_params.get('page', 1)}&services_page={services_page.previous_page_number()}"
#                     if services_page.has_previous() else None
#                 ),
#                 "results": ServiceSerializer(
#                     services_page.object_list, many=True, context={"request": request}
#                 ).data,
#             }

#             enriched_suppliers.append(supplier_data)

#         # Return final paginated supplier list
#         return self.get_paginated_response(enriched_suppliers)



from django.db.models import Count


class SupplierListView(generics.ListAPIView):
    serializer_class = SupplierListSerializer
    pagination_class = PastBookingsPagination
    permission_classes = []

    def get_queryset(self):
        # Only get suppliers that have at least one active, non-deleted service
        return User.objects.filter(
            role="supplier",
            is_active=True,
            services__is_active=True,
            services__is_delete=False
        ).annotate(
            service_count=Count('services', filter=Q(services__is_active=True, services__is_delete=False))
        ).filter(service_count__gt=0).distinct()

    def list(self, request, *args, **kwargs):
        suppliers_page = self.paginate_queryset(self.get_queryset())
        if suppliers_page is None:
            suppliers_page = self.get_queryset()

        service_page_number = request.query_params.get("services_page", 1)
        service_page_size = 4

        enriched_suppliers = []

        for supplier in suppliers_page:
            # ⚠️ Fix this filter: you meant is_delete=False not is_delete=True
            services_qs = supplier.services.filter(is_active=True, is_delete=False).order_by("-id")

            # ⛔️ Skip if no valid services
            if not services_qs.exists():
                continue

            paginator = Paginator(services_qs, service_page_size)
            try:
                services_page = paginator.page(service_page_number)
            except (PageNotAnInteger, EmptyPage):
                services_page = paginator.page(1)

            supplier_data = SupplierListSerializer(supplier, context={"request": request}).data
            supplier_data["services"] = {
                "count": paginator.count,
                "page": services_page.number,
                "num_pages": paginator.num_pages,
                "next": (
                    f"{request.build_absolute_uri().split('?')[0]}?page={request.query_params.get('page', 1)}&services_page={services_page.next_page_number()}"
                    if services_page.has_next() else None
                ),
                "previous": (
                    f"{request.build_absolute_uri().split('?')[0]}?page={request.query_params.get('page', 1)}&services_page={services_page.previous_page_number()}"
                    if services_page.has_previous() else None
                ),
                "results": ServiceSerializer(
                    services_page.object_list, many=True, context={"request": request}
                ).data,
            }

            enriched_suppliers.append(supplier_data)

        return self.get_paginated_response(enriched_suppliers)

from accounts.utils import generate_booking_qr_image, send_qr_to_darevue

class BookingQRCodeView(APIView):
  

    def get(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found"}, status=404)

        qr_image = generate_booking_qr_image(booking)
        return Response({
            "booking_id": booking.id,
            "qr_image_base64": qr_image
        })

class SendBookingToDarevueView(APIView):
   

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found"}, status=404)

        darevue_response = send_qr_to_darevue(booking)
        return Response({"darevue_response": darevue_response})






# views.py
from .models import DaftraInvoice
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def get_invoice_pdf(request, booking_id):
    try:
        invoice = DaftraInvoice.objects.get(booking_id=booking_id)
        return Response({
            'pdf_url': invoice.pdf_url,
            'invoice_url': invoice.invoice_url
        })
    except DaftraInvoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=404)
    
    
    
    
    
    

class ServiceTicketCreateOrUpdateView(APIView):
    def post(self, request):
        booking_id = request.data.get("booking")
        tickets_data = request.data.get("tickets")

        if not booking_id:
            return Response({"error": "Booking ID is required."}, status=400)

        if not isinstance(tickets_data, list):
            return Response({"error": "Expected a list of tickets."}, status=400)

        # Validate booking
        try:
            booking = Booking.objects.get(id=booking_id,user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Invalid booking ID."}, status=400)

        if booking.status not in ["paid", "confirmed"]:
            return Response({"error": "Booking must be paid or confirmed to add extra tickets."}, status=400)

        # Restore capacity from old tickets
        old_extra_tickets = ServiceTicket.objects.filter(booking=booking, is_extra=True)
        for ticket in old_extra_tickets:
            ticket.service.capacity += ticket.quantity
            ticket.service.save()
        old_extra_tickets.delete()

        response_data = []

        for data in tickets_data:
            data = data.copy()

            if str(data.get("is_extra")).lower() != "true":
                return Response({"error": "Only extra service tickets can be created here."}, status=400)

            if "is_paid" in data:
                return Response({"error": "You cannot manually set 'is_paid'."}, status=400)

            try:
                service = Services.objects.get(id=data.get("service"))
            except Services.DoesNotExist:
                return Response({"error": "Invalid service ID."}, status=400)

            quantity = int(data.get("quantity", 0))
            date_id = data.get("date")
            is_confirmed=data.get('is_confirmed',False)

            if not date_id:
                return Response({"error": "Date ID is required."}, status=400)

            # Get the AvailableDateService instance from the ID
            try:
                available_date_service = AvailableDateService.objects.get(id=date_id)
            except AvailableDateService.DoesNotExist:
                return Response({"error": f"Invalid date ID: {date_id}."}, status=400)

            # Extract the actual date from AvailableDateService
            ticket_date = available_date_service.date

            # Validate service ticket
            result = validate_service_ticket(service, quantity, ticket_date)
            if result == 0:
                return Response({"error": f"Service '{service.title}' exceeds capacity on {ticket_date}."}, status=400)
            elif result == 1:
                return Response({"error": f"Service '{service.title}' not available on {ticket_date}."}, status=400)

            # Subtract capacity for new ticket
            service.capacity -= quantity
            service.save()

            # Create new extra ticket
            ticket = ServiceTicket.objects.create(
                booking=booking,
                service=service,
                quantity=quantity,
                date=ticket_date,
                is_extra=True,
                is_confirmed=is_confirmed
                
            )

            response_data.append(ServiceTicketSerializer(ticket).data)

        return Response(response_data, status=201)






    
class CancelBookingView(APIView):
   

    def post(self, request,  booking_id,*args, **kwargs):
        

        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found or not yours"}, status=status.HTTP_404_NOT_FOUND)

        # Get earliest booking date (assumes Booking has related BookingDate objects)
        earliest_date_obj = booking.dates.order_by('date_from').first()
        if not earliest_date_obj:
            return Response({"error": "No booking dates found for this booking"}, status=status.HTTP_400_BAD_REQUEST)

        earliest_date = earliest_date_obj.date_from
        cutoff_date = earliest_date - timedelta(days=2)  # 2 days before earliest date

        today = date.today()

        if today > cutoff_date:
            return Response({"error": f"Cannot cancel booking less than 2 days before start date ({earliest_date})"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'cancelled'
        booking.save()

        return Response({"message": f"Booking #{booking.id} has been cancelled."}, status=status.HTTP_200_OK)


class AddExtraBookingDateAPIView(APIView):
    

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        date_from = request.data.get("date_from")
        date_to = request.data.get("date_to")
        confirmed=request.data.get("is_confirmed",False)

        if not date_from or not date_to:
            return Response({"error": "date_from and date_to are required"}, status=400)

        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

        if date_from > date_to:
            return Response({"error": "Invalid date range"}, status=400)

        # Ensure same month
        if date_from.month != date_to.month:
            return Response({"error": "Extra dates must be within the same month"}, status=400)

        # Ensure linking with existing booking
        existing_dates = list(booking.dates.all())
        if not existing_dates:
            return Response({"error": "No existing booking dates to link with"}, status=400)

        all_existing_days = []
        for d in existing_dates:
            all_existing_days += [
                d.date_from + timedelta(days=i) for i in range((d.date_to - d.date_from).days + 1)
            ]

        # Check adjacent
        previous_day = date_to + timedelta(days=1)
        next_day = date_from - timedelta(days=1)
        if previous_day not in all_existing_days and next_day not in all_existing_days:
            return Response({"error": "Extra dates must be directly adjacent to existing booking"}, status=400)

        # Check hut availability
        valid, invalid_date = is_hut_available(booking.hut.id, date_from, date_to)
        if not valid:
            return Response({"error": f"Date {invalid_date} is not available for this hut"}, status=400)

        # All checks passed: create the extra BookingDate
        BookingDate.objects.create(
            booking=booking,
            date_from=date_from,
            date_to=date_to,
            is_extra=True,
            is_confirmed=confirmed
        )

        return Response({"message": "Extra booking dates added successfully"}, status=201)
    
    
    
    



# @api_view(['POST'])
# def device_data_receiver(request):
#     data_type = request.data.get("Type")
#     qr_or_card_data = request.data.get("Data")

#     if data_type == "0":
#         # ده يعني Scan من QR
#         try:
#             booking = Booking.objects.get(id=qr_or_card_data)
#             if booking.status in ['paid']:
#                 # Send unlock signal to the hardware
#                 send_code_to_hardware("192.168.1.100", 8000, "0202F2AC000203E8B503")
#                 return Response({"status": "access granted"})
#             else:
#                 # Send reject signal
#                 send_code_to_hardware("192.168.1.100", 8000, "0202F2AD0001035F03")
#                 return Response({"status": "booking not valid"}, status=403)
#         except Booking.DoesNotExist:
#             # Send reject signal
#             send_code_to_hardware("192.168.1.100", 8000, "0202F2AD0001035F03")
#             return Response({"status": "booking not found"}, status=404)

#     elif data_type == "1":
#         # heart beat 
#         return Response({"status": "heartbeat received"}, status=200)

#     return Response({"status": "unknown type"}, status=400)




























from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils.timezone import now
from .models import Booking, BookingDate
from datetime import date

@api_view(['POST'])
def generate_today_qr_codes(request):
    today = date.today()
    # 1. دور على كل الـ Booking اللي تاريخ بدايته النهاردة
    today_bookings = Booking.objects.filter(
        status='paid',
        dates__date_from=today
    ).distinct()

    generated = []

    for booking in today_bookings:
        # لو بالفعل عنده qr_code، تجاهله
        if booking.qr_code and booking.qr_code_image:
            continue

        # 2. توليد QR value جديد
        qr_value = uuid.uuid4().hex.upper()
        qr_image = generate_qr_code_image(qr_value)

        # 3. حفظهم في الـ Booking
        booking.qr_code = qr_value
        booking.qr_code_image.save(f"{qr_value}.png", qr_image)
        booking.save()

        generated.append({
            "booking_id": booking.id,
            "qr_code": qr_value
        })

    return Response({
        "status": "done",
        "generated_count": len(generated),
        "bookings": generated
    })





class HutRatingCreateView(generics.CreateAPIView):
   
    serializer_class   = HutRatingSerializer
    

    # Pass booking_id into serializer's data if it came via the URL
    def get_serializer(self, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data'].copy()
            data['booking_id'] = self.kwargs['booking_id']
            kwargs['data'] = data
        return super().get_serializer(*args, **kwargs)
    
    
# #######################################################################



##########################################################################################################
#######################################################################################################
############################################################

# #########################################################admin dashboard 









class HutRatingListAllAPIView(generics.ListAPIView):
    serializer_class = HutRatingSerializer
    permission_classes = [IsAdmin]
    pagination_class = TenPagePagination

    def get_queryset(self):
        qs = HutRating.objects.select_related('user', 'hut').order_by('-id')

        hut_id = self.request.query_params.get('hut')
        search = self.request.query_params.get('search')

        if hut_id:
            qs = qs.filter(hut_id=hut_id)

        if search:
            qs = qs.filter(
                Q(user__full_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        return qs



from datetime import date
from django.template.loader import render_to_string
from accounts.utils import send_email 


class RefuseCancellationView(APIView):
    permission_classes = [IsAdmin]  # Only admin can access

    def post(self, request, booking_id, *args, **kwargs):
        reason = request.data.get('reason')

        if not reason:
            return Response({"error": "Reason is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != 'cancelled':
            return Response({"error": "Only cancelled bookings can be refused"}, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        booking.status = 'paid'
        booking.save()
        html = render_to_string(
        "cancellation_refuse.html",
        {
            "user": booking.user,
            "booking": booking,
            "reason":reason,
            "domain": urlparse(settings.FRONTEND_BASE_URL).netloc or "ken.mernantech.com",
        }
    )
        send_email(booking.user.email, "cancellation refuse!", html)

        
        
       
        return Response({"message": f"Cancellation for Booking #{booking.id} has been refused and status restored to paid."}, status=status.HTTP_200_OK)






class RefundView(APIView):
    permission_classes = [IsAdmin]  # Only admin can access

    def post(self, request, booking_id, *args, **kwargs):
       

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != 'cancelled':
            return Response({"error": "Only cancelled bookings can be refunded"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'refuned'
        booking.save()
        return Response({"message": f"Refund for Booking #{booking.id} "}, status=status.HTTP_200_OK)




# class AvailableDateRangeListCreateView(generics.GenericAPIView):
#     serializer_class = AvailableDateRnageSerializer

#     def post(self, request, *args, **kwargs):
#         hut_id = self.kwargs.get("hut_id")
#         try:
#             hut = Hut.objects.get(id=hut_id)
#         except Hut.DoesNotExist:
#             return Response({"detail": "Hut not found."}, status=status.HTTP_404_NOT_FOUND)

#         # Delete existing dates for this hut
#         AvailableDateRanges.objects.filter(huts=hut).delete()

#         # Create new ones
#         serializer = self.get_serializer(data=request.data, many=True)
#         serializer.is_valid(raise_exception=True)
#         for item in serializer.validated_data:
#             item['huts'] = hut  # Assign the hut manually

#         created_objects = [
#             AvailableDateRanges.objects.create(**item)
#             for item in serializer.validated_data
#         ]

#         return Response(self.get_serializer(created_objects, many=True).data, status=status.HTTP_201_CREATED)




class HutDatesPromoUpdateView(generics.GenericAPIView):
    serializer_class = AvailableDateRnageSerializer

    def post(self, request, *args, **kwargs):
        hut_id = self.kwargs.get("hut_id")
        try:
            hut = Hut.objects.get(id=hut_id)
        except Hut.DoesNotExist:
            return Response({"detail": "Hut not found."}, status=status.HTTP_404_NOT_FOUND)

        # ========================
        # 1️⃣ Handle Available Dates
        # ========================
        available_dates_data = request.data.get("available_dates", [])
        AvailableDateRanges.objects.filter(huts=hut).delete()

        date_serializer = AvailableDateRnageSerializer(data=available_dates_data, many=True)
        date_serializer.is_valid(raise_exception=True)

        created_dates = [
            AvailableDateRanges.objects.create(huts=hut, **item)
            for item in date_serializer.validated_data
        ]

        # ========================
        # 2️⃣ Handle Promo Codes
        # ========================
        promo_data = request.data.get("promocodes", [])
        existing_promos = hut.promocode.all()
        for promo in existing_promos: 
            promo.delete()
        # hut.promocode.clear()  

        promo_serializer = PromoCodeSerializer(data=promo_data, many=True)
        promo_serializer.is_valid(raise_exception=True)
        created_promos = [PromoCode.objects.create(**item) for item in promo_serializer.validated_data]
        hut.promocode.add(*created_promos)

        # ========================
        # ✅ Return Response
        # ========================
        return Response({
            "available_dates": AvailableDateRnageSerializer(created_dates, many=True).data,
            "promocodes": PromoCodeSerializer(created_promos, many=True).data
        }, status=status.HTTP_201_CREATED)

class HutListAdminAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = HutListAdminSerializer
    pagination_class = TenPagePagination

    def get_queryset(self):
        queryset = Hut.objects.all()

        # Search by title or title_ar
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(title_ar__icontains=search)
            )

        # Filter by size
        size = self.request.query_params.get('size')
        if size:
            queryset = queryset.filter(size=size)

        # Filter by is_active
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)

        return queryset



class BookingListView(generics.ListAPIView):
    serializer_class = BookingAdminTableSerializer
    pagination_class = TenPagePagination
    permission_classes=[IsAdminOrSupplier]

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related("hut").order_by("-created_at")

        if user.is_authenticated:
            if getattr(user, 'role', None) == 'supplier':
                # Filter bookings where any event or service belongs to the supplier
                queryset = queryset.filter(
                    Q(events__event__supplier=user) |
                    Q(services__service__supplier=user)
                ).distinct()
            

        # Admins get all bookings (or unauthenticated if allowed)
        # Optional: if you want to restrict unauthenticated users:
        # else:
        #     return Booking.objects.none()

        # Search by hut title
        hut_title = self.request.query_params.get('search')
        if hut_title:
            queryset = queryset.filter(hut__title__icontains=hut_title)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by is_scaned
        is_scaned = self.request.query_params.get('is_scaned')
        if is_scaned:
            queryset = queryset.filter(is_scaned=is_scaned)

        # Sorting by total_price (asc or desc)
        sort = self.request.query_params.get('sort')
        if sort == 'asc':
            queryset = queryset.order_by('total_price')
        elif sort == 'desc':
            queryset = queryset.order_by('-total_price')

        return queryset


class BookingDetailsAdminListView(generics.RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailsAdminSerializer
    permission_classes = [IsAdminOrSupplier]  # Add permissions as needed
    lookup_field = 'id'
    
    
    





from django.shortcuts import get_object_or_404

class EventAvailableDatesUpdateView(APIView):
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        data = request.data.get('dates', [])

        # Clear old dates
        event.available_dates.clear()

        # Delete all old dates (optional - only if you want to truly delete them from DB)
        AvailableDateEvent.objects.filter(events=event).delete()

        created_dates = []
        for date_data in data:
            serializer = AvailableDateEventSerializer(data=date_data)
            serializer.is_valid(raise_exception=True)
            date_obj = serializer.save()
            created_dates.append(date_obj)

        event.available_dates.set(created_dates)
        return Response({'detail': 'Dates updated successfully.'}, status=status.HTTP_200_OK)


class ServiceAvailableDatesUpdateView(APIView):
    def post(self, request, service_id):
        service = get_object_or_404(Services, id=service_id)
        data = request.data.get('dates', [])

        # Clear old dates
        service.available_dates.clear()

        # Delete old dates (optional)
        AvailableDateService.objects.filter(services=service).delete()

        created_dates = []
        for date_data in data:
            serializer = AvailableDateServiceSerializer(data=date_data)
            serializer.is_valid(raise_exception=True)
            date_obj = serializer.save()
            created_dates.append(date_obj)

        service.available_dates.set(created_dates)
        return Response({'detail': 'Dates updated successfully.'}, status=status.HTTP_200_OK)

    
class HutDropDownListView(generics.ListAPIView):
    permission_classes=[IsAdminOrSupplier]
    queryset = Hut.objects.filter(is_active=True)
    serializer_class = HutDropDownSerializer
    
    
    
    


class EventListCreateView(generics.ListCreateAPIView):
    permission_classes=[IsAdminOrSupplier]
    queryset = Event.objects.filter(is_delete=False)
    serializer_class = EventAdminSerializer
    

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)
        



class HutDetailAdminDashBoardView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hut.objects.all()
    serializer_class = HutAdminDetailsDashboardSerializer
    permission_classes = [IsAdmin] 

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        data = {}
        for key in request.data:
            val = request.data.get(key)
            if val is not None and not hasattr(val, 'read'):
                data[key] = val

        location_data = {}
        keys_to_remove = []
        for key, value in list(data.items()):
            if key.startswith("location."):
                loc_key = key.split("location.")[1]
                if value not in ("", "null", "undefined", None):
                    location_data[loc_key] = value
                keys_to_remove.append(key)

        for k in keys_to_remove:
            data.pop(k, None)

        if location_data:
            data["location"] = location_data

        if "main_image" in request.FILES:
            data["main_image"] = request.FILES["main_image"]

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        images_list = request.FILES.getlist("images")
        if images_list:
            for image_file in images_list:
                try:
                    hut_image = HutImages.objects.create(image=image_file)
                    instance.images.add(hut_image)
                except Exception as e:
                    print("Hut image save warning:", e)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)




from django.core.management import call_command

class ImportKenDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            call_command('import_ken_data')
            return Response({"status": "success", "message": "ken_data imported successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class HutCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminForUnsafeMethods]  # Your custom permission class

    def get(self, request, *args, **kwargs):
        try:
            queryset = Hut.objects.all().order_by('-id')
            serializer = HutSerializer(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        data = {}
        for key in request.data:
            val = request.data.get(key)
            if val is not None and not hasattr(val, 'read'):
                data[key] = val

        location_data = {}
        keys_to_remove = []
        for key, value in list(data.items()):
            if key.startswith("location."):
                loc_key = key.split("location.")[1]
                if value not in ("", "null", "undefined", None):
                    location_data[loc_key] = value
                keys_to_remove.append(key)

        for k in keys_to_remove:
            data.pop(k, None)

        if location_data:
            data["location"] = location_data
        elif "location" not in data:
            data["location"] = None

        if "main_image" in request.FILES:
            data["main_image"] = request.FILES["main_image"]

        try:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, "uploads/services/hut_image"), exist_ok=True)
        except Exception:
            pass

        serializer = HutSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            try:
                hut = serializer.save()
            except Exception as e:
                # If image saving failed during serializer.save() due to storage issues, save without image
                data.pop("main_image", None)
                serializer = HutSerializer(data=data, context={'request': request})
                serializer.is_valid(raise_exception=True)
                hut = serializer.save()

            # Handle multiple HutImages (images[])
            images_list = request.FILES.getlist("images")
            for image_file in images_list:
                try:
                    hut_image = HutImages.objects.create(image=image_file)
                    hut.images.add(hut_image)
                except Exception as e:
                    print("Hut image save warning:", e)

            return Response(HutSerializer(hut, context={'request': request}).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KenSpecialItemsListCreateView(generics.ListCreateAPIView):
    pagination_class=TenPagePagination
   
    serializer_class = KenSpecialItemsSerializer
    permission_classes = [IsAdminOrSupplier] 
    def get_queryset(self):
        queryset = KenSpecialItems.objects.filter(is_delete=False)
        user=self.request.user
        if hasattr(user, "role") and user.role == "supplier":
            queryset= queryset.filter(supplier=user)


      
        is_active = self.request.query_params.get('is_active')
        role = self.request.query_params.get('role')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)
        if role is not None:
            if role =='supplier':
                queryset=queryset.filter(supplier__role="supplier")
            else:
                queryset=queryset.exclude(supplier__role="supplier")
        
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(title_ar__icontains=search) |
                Q(huts__title__icontains=search) |
                Q(huts__title_ar__icontains=search)
            ).distinct()

        return queryset
    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)
    



   
   
class EventRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = EventAdminSerializer
    permission_classes = [IsAdminOrSupplier]  
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        return Event.objects.filter(is_delete=False)
    def update(self, request, *args, **kwargs):
        partial = True  
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class HutRatingDeleteView(generics.DestroyAPIView):
    queryset = HutRating.objects.all()
    serializer_class = HutRatingSerializer
    permission_classes = [IsAdmin]
    

class BulkUpdateEventDataAPIView(APIView):
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        serializer = EventBulkDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        includes_data = serializer.validated_data.get('includes', [])
        notes_data = serializer.validated_data.get('notes', [])

        # Delete existing data
        EventInclude.objects.filter(event=event).delete()
        EventNote.objects.filter(event=event).delete()

        # Create new includes
        for include_data in includes_data:
            icon = include_data.pop('icon')
            EventInclude.objects.create(event=event, icon=icon, **include_data)

        # Create new notes
        for note_data in notes_data:
            EventNote.objects.create(event=event, **note_data)

        return Response({"detail": "Event includes and notes updated."}, status=status.HTTP_200_OK)



class IconListCreateAPIView(generics.ListCreateAPIView):
    permission_classes=[IsAdminOrSupplier]
    queryset = Icon.objects.all()
    serializer_class = IconSerializer
    
    
    

from rest_framework import generics
from django.db.models import Q
from .models import Event
from .serializers import EventAdminSerializer


class EventDashboardListView(generics.ListAPIView):
    serializer_class = EventAdminSerializer
    pagination_class = TenPagePagination

    def get_queryset(self):
        user = self.request.user
        # is_admin_param = self.request.query_params.get('admin', 'false').lower()

        if user.role == 'admin':
            self.check_permissions(self.request)  # Manually check permission
           
            queryset = Event.objects.filter(is_delete=False)
        elif user.role=='supplier':
            
            
            queryset = Event.objects.filter(is_delete=False, supplier=user)
        else:
                self.permission_denied(self.request)
            

        # Filter by is_active
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(title_ar__icontains=search) |
                Q(hut__title__icontains=search) |
                Q(hut__title_ar__icontains=search) |
                (Q(supplier__full_name__icontains=search) if user.role == 'admin' else Q())
            ).distinct()

        return queryset

   
   

class HutServicesActivitiesBulkUpdateAPIView(APIView):
    permission_classes = [IsAdminForUnsafeMethods]

    def post(self, request, hut_id):
        hut = get_object_or_404(Hut, id=hut_id)

        serializer = HutServicesActivitiesBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delete existing
        hut.activities.all().delete()
        hut.main_services.all().delete()

        # Create activities
        activity_objs = [
            HutActivity(hut=hut, **activity_data)
            for activity_data in serializer.validated_data['activities']
        ]
        HutActivity.objects.bulk_create(activity_objs)

        # Create main services
        service_objs = [
            HutMainService(hut=hut, **service_data)
            for service_data in serializer.validated_data['services']
        ]
        HutMainService.objects.bulk_create(service_objs)

        return Response({"detail": "Hut services and activities updated successfully."}, status=status.HTTP_201_CREATED)
    
    
    
from django.db.models import OuterRef, Subquery

class RecentPaidBookingsView(generics.ListAPIView):
    serializer_class = BookingUpcominAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        today = now().date()
        # Subquery: earliest date_from for each booking (main date only)
        date_subquery = BookingDate.objects.filter(
            booking=OuterRef('pk'),
            is_extra=False
        ).order_by('-date_from').values('date_from')[:1]

        # Only upcoming: main booking end date (date_to) is today or in the future
        return (
            Booking.objects.filter(status='paid')
            .filter(dates__is_extra=False, dates__date_to__gte=today)
            .distinct()
            .annotate(latest_date_from=Subquery(date_subquery))
            .order_by('latest_date_from')[:10]
        )
        
        
        
class QrLogsByBookingView(ListAPIView):
    serializer_class = QrLogsSerializer
    permission_classes = [IsAdmin]  
    pagination_class=TenPagePagination

    def get_queryset(self):
        booking_id = self.kwargs.get('booking_id')
        return QrLogs.objects.filter(booking_id=booking_id).order_by('-created_at')

class QrLogsListAllView(generics.ListAPIView):
    permission_classes=[IsAdmin]
    pagination_class=TenPagePagination
    queryset = QrLogs.objects.all().order_by('-created_at')  # optional ordering
    serializer_class = QrLogsSerializer

class SupplierAnalyticsView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request, supplier_id=None):
        """
        Get analytics for a specific supplier or all suppliers
        """
        if supplier_id:
            # Get analytics for specific supplier
            try:
                supplier = User.objects.get(id=supplier_id, role='supplier')
                analytics = self._get_supplier_analytics(supplier)
                return Response(analytics, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Supplier not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get analytics for all suppliers
            suppliers = User.objects.filter(role='supplier')
            analytics_list = []
            
            for supplier in suppliers:
                analytics = self._get_supplier_analytics(supplier)
                analytics_list.append(analytics)
            
            return Response(analytics_list, status=status.HTTP_200_OK)
    
    def _get_supplier_analytics(self, supplier):
        """
        Calculate analytics for a specific supplier
        """
        # Count services for this supplier
        services_count = Services.objects.filter(
            supplier=supplier,
            is_delete=False
        ).count()
        
        # Count active events for this supplier
        active_events_count = Event.objects.filter(
            supplier=supplier,
            is_active=True,
            is_delete=False
        ).count()
        
        # Get all bookings that have services or events from this supplier
        supplier_services = Services.objects.filter(supplier=supplier)
        supplier_events = Event.objects.filter(supplier=supplier)
        
        # Get bookings with services from this supplier
        bookings_with_services = Booking.objects.filter(
            services__service__in=supplier_services
        ).distinct()
        
        # Get bookings with events from this supplier
        bookings_with_events = Booking.objects.filter(
            events__event__in=supplier_events
        ).distinct()
        
        # Get total unique bookings (union of both)
        total_bookings = (bookings_with_services | bookings_with_events).distinct()
        
        analytics = {
            'supplier_id': supplier.id,
            'supplier_name': supplier.full_name or supplier.email,
            'services_count': services_count,
            'active_events_count': active_events_count,
            'total_orders_count': total_bookings.count(),
            'orders_with_services_count': bookings_with_services.count(),
            'orders_with_events_count': bookings_with_events.count(),
        }
        
        return analytics


class AllSuppliersAnalyticsView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """
        Get summary analytics for all suppliers
        """
        suppliers = User.objects.filter(role='supplier')
        
        total_suppliers = suppliers.count()
        total_services = Services.objects.filter(is_delete=False).count()
        total_active_events = Event.objects.filter(is_active=True, is_delete=False).count()
        
        # Get all bookings with services or events
        all_bookings_with_services = Booking.objects.filter(
            services__isnull=False
        ).distinct()
        
        all_bookings_with_events = Booking.objects.filter(
            events__isnull=False
        ).distinct()
        
        total_orders = (all_bookings_with_services | all_bookings_with_events).distinct()
        
        summary = {
            'total_suppliers': total_suppliers,
            'total_services': total_services,
            'total_active_events': total_active_events,
            'total_orders': total_orders.count(),
            'orders_with_services': all_bookings_with_services.count(),
            'orders_with_events': all_bookings_with_events.count(),
        }
        
        return Response(summary, status=status.HTTP_200_OK)
    
    


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class AdminSupplierAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        supplier = request.user
        print(supplier.email)

        # Count services
        services_count = Services.objects.filter(supplier=supplier,is_active=True).count()

    
        active_events_count = Event.objects.filter(supplier=supplier, is_active=True).count()

        
        service_ticket_count = ServiceTicket.objects.filter(service__supplier=supplier).count()
        print(service_ticket_count,'kk')

        event_ticket_count = EventTicket.objects.filter(event__supplier=supplier).count()
        print(event_ticket_count,'event')
        
        
        orders_count=service_ticket_count+event_ticket_count
      

        return Response({
            "services_count": services_count,
            "events_count": active_events_count,
            "related_orders_count": orders_count
        })




from django.db.models import Sum
class AdminAnalyticsView(APIView):
    permission_classes = [IsAdmin]  # Only admin users can access

    def get(self, request):
        total_bookings = Booking.objects.count()
        total_revenue = Booking.objects.filter(status='paid').aggregate(total=Sum('paid'))['total'] or 0
        rate_obj = WebsiteRate.objects.first()
        average = rate_obj.average_value if rate_obj else 0.0
        return Response({
            "total_bookings": total_bookings,
            "total_revenue": float(total_revenue),
            "average_rating": float(average)
        })
        
        
        
        
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from datetime import datetime
import calendar
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from datetime import datetime
import calendar
class YearlyRevenueChartAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        year = datetime.today().year

        # Get paid bookings in the given year and group by month
        revenues = (
            Booking.objects.filter(status='paid', created_at__year=year)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total_revenue=Sum('paid'))
        )

        # Build a mapping: {7: 3300.0, 8: 22000.0, ...}
        revenue_dict = {
            item['month'].month: float(item['total_revenue']) for item in revenues
        }

        # Build months and revenue arrays
        months = [calendar.month_name[m] for m in range(1, 13)]
        revenues = [revenue_dict.get(m, 0.0) for m in range(1, 13)]

        return Response({
            "months": months,
            "revenues": revenues
        })
class MostRecntOrderAnalyticsListView(generics.ListAPIView):
    serializer_class = BookingAdminTableSerializer
    permission_classes = [IsAdminOrSupplier]
    pagination_class = None  # Disable pagination since we only want 7

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related('hut').all()

        if user.is_authenticated:
            if getattr(user, 'role', None) == 'supplier':
                # Filter bookings where any event or service belongs to the supplier
                queryset = queryset.filter(
                    Q(events__event__supplier=user) |
                    Q(services__service__supplier=user)
                ).distinct()

        # For admin, no filtering needed — all bookings returned

        # Return only the 7 most recent bookings by creation date
        return queryset.order_by('-created_at')[:3]
    
    
    
    
    
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer

class PaidBookingIfLastConfirmedView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer
   

    def get(self, request, pk):
        user = request.user

        try:
            booking = Booking.objects.get(id=pk, user=user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking is not found."}, status=status.HTTP_404_NOT_FOUND)

        # If booking is already paid
        if booking.status == "paid":
            return Response({"detail": "Booking is already paid."}, status=status.HTTP_200_OK)

        # Check if latest booking is confirmed
        latest_booking = Booking.objects.filter(user=user).order_by('-created_at').first()
        if latest_booking and latest_booking.status != "confirmed":
            return Response({"detail": "Cannot pay. Please confirm your latest booking first."}, status=status.HTTP_400_BAD_REQUEST)

       
        booking.status = "paid"
        booking.is_paid = True  
        booking.save()

        serializer = BookingSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)


   




class PaidBookingIfLastConfirmedDetailsView(generics.RetrieveAPIView):
    serializer_class = BookingForPaymnetSerializer
   

    def get(self, request, pk):
        user = request.user

        try:
            booking = Booking.objects.get(id=pk, user=user)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking is not found."}, status=status.HTTP_404_NOT_FOUND)

       
        

        serializer = BookingForPaymnetSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)


   












#for testing payment not real

class BookingMarkPaidView(generics.UpdateAPIView):
    queryset = Booking.objects.all()
    serializer_class=BookingPaymentSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        booking = self.get_object()

       
        if booking.user != request.user and not request.user.role=="admin":
            return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)

       
        booking.is_paid = True
        booking.status = "paid"
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)
    







class PromoCodeListCreateView(generics.ListCreateAPIView):
    serializer_class = PromoCodeSerializer

    def get_queryset(self):
        hut_id = self.kwargs["hut_id"]
        return PromoCode.objects.filter(hut__id=hut_id)

    def create(self, request, *args, **kwargs):
        hut_id = self.kwargs["hut_id"]
        try:
            hut = Hut.objects.get(id=hut_id)
        except Hut.DoesNotExist:
            return Response({"detail": "Hut not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promocode = serializer.save()

        # Attach the new promo code to hut
        hut.promocode.add(promocode)

        return Response(serializer.data, status=status.HTTP_201_CREATED)



class PromoCodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    lookup_field = "id"
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True  # ensure partial update
        return super().update(request, *args, **kwargs)


class PublicSeedKenDataView(APIView):
    permission_classes = []

    def get(self, request):
        import traceback
        from django.core.management import call_command
        from content.models import FAQ, AboutUs
        try:
            cache.clear()
            
            # Update date range prices and special item prices to 5.00 SAR
            AvailableDateRanges.objects.all().update(price=5.00)
            AvailableDateEvent.objects.all().update(price=5.00)
            AvailableDateService.objects.all().update(price=5.00)
            KenSpecialItems.objects.all().update(price=5.00)

            force = request.query_params.get('force') == 'true'
            if force or not Event.objects.filter(is_active=True).exists():
                call_command('seed_ken_data')

            # Ensure test accounts exist
            if not User.objects.filter(email='supplier1@kenluxuryreef.com').exists():
                u = User.objects.create(email='supplier1@kenluxuryreef.com', full_name='Red Sea Adventures', role='supplier', is_active=True, phone='+966500000001')
                u.set_password('supplier123')
                u.save()

            if not User.objects.filter(email='guest1@kenluxuryreef.com').exists():
                u = User.objects.create(email='guest1@kenluxuryreef.com', full_name='Guest One', role='user', is_active=True, phone='+966500000002')
                u.set_password('guest123')
                u.save()

            return Response({
                "status": "success",
                "message": "Database ready and verified!",
                "counts": {
                    "huts": Hut.objects.count(),
                    "events": Event.objects.count(),
                    "services": Services.objects.count(),
                    "faqs": FAQ.objects.count(),
                    "about_us": AboutUs.objects.count(),
                    "users": User.objects.count(),
                }
            })
        except Exception as e:
            error_details = traceback.format_exc()
            return Response({"status": "error", "message": str(e), "traceback": error_details}, status=500)