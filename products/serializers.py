from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import *
from datetime import datetime
from accounts .serializers import MiniUserSerializer
from .utils import *
from datetime import date
from django.utils import timezone
from django.db import transaction

class AvailableDateEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableDateEvent
        fields = '__all__'


class AvailableDateServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableDateService
        fields = '__all__'


  

class IconSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = ['id', 'image']
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
class EventIncludeSerializer(serializers.ModelSerializer):
    icon = IconSerializer(read_only=True)
    icon_id = serializers.PrimaryKeyRelatedField(queryset=Icon.objects.all(), source='icon', write_only=True)

    class Meta:
        model = EventInclude
        fields = ['id', 'icon', 'icon_id', 'description', 'description_ar']


class EventNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventNote
        fields = ['id', 'description', 'description_ar']


class HutActivitySerializer(serializers.ModelSerializer):
    

    class Meta:
        model = HutActivity
        fields = ['id', 'description', 'description_ar']

class HutMainServiceSerializer(serializers.ModelSerializer):
   
    icon = IconSerializer(read_only=True)
    

    class Meta:
        model = HutMainService
        fields = ['id',  'icon', 'description', 'description_ar', 'is_extra']
    

        


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'



        
        
        
        

class HutImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = HutImages
        fields = ['id', 'image']

    def get_image(self, obj):
        if not obj.image:
            return None
        val = str(obj.image)
        if val.startswith("http://") or val.startswith("https://"):
            return val
        try:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        except Exception:
            return f"/media/{val}"

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'





class AvailableDateRnageSerializer(serializers.ModelSerializer):
     huts = serializers.PrimaryKeyRelatedField(queryset=Hut.objects.all(),required=False)
     class Meta:
        model = AvailableDateRanges
        fields = ['id',"date_from","date_to","price","huts"]

class HutDropDownSerializer(serializers.ModelSerializer):
    
  
   

    class Meta:
        model = Hut
        fields = [
            'id',
            'title',
            'title_ar',
           
            'is_active',
            
        ]
    
class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ["id", "code", "percentage", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

class HutSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    promocode = PromoCodeSerializer(many=True, read_only=True)
    images = HutImageSerializer(many=True, read_only=True)
    main_image = serializers.SerializerMethodField()
    available_dates = serializers.SerializerMethodField()
    main_services = serializers.SerializerMethodField()
    extra_services = serializers.SerializerMethodField()
    activities = serializers.SerializerMethodField()
    lowest_price=serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Hut
        fields = '__all__'

    def get_main_image(self, obj):
        if not obj.main_image:
            return None
        val = str(obj.main_image)
        if val.startswith("http://") or val.startswith("https://"):
            return val
        try:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.main_image.url)
            return obj.main_image.url
        except Exception:
            return f"/media/{val}"

    def create(self, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            location = Location.objects.create(**location_data)
        else:
            location = None
        hut = Hut.objects.create(location=location, **validated_data)
        return hut

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)

        # Update nested Location fields
        if location_data:
            location = instance.location
            for attr, value in location_data.items():
                setattr(location, attr, value)
            location.save()

        # Update the Hut fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def get_available_dates(self, obj):
        if not hasattr(self, '_dates_cache'):
            self._dates_cache = {}
        if obj.id not in self._dates_cache:
            self._dates_cache[obj.id] = get_hut_available_dates(obj)
        return self._dates_cache[obj.id]

    def get_main_services(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'main_services' in obj._prefetched_objects_cache:
            services = [s for s in obj.main_services.all() if not s.is_extra]
        else:
            services = obj.main_services.filter(is_extra=False)
        return HutMainServiceSerializer(services, many=True, context=self.context).data

    def get_extra_services(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'main_services' in obj._prefetched_objects_cache:
            services = [s for s in obj.main_services.all() if s.is_extra]
        else:
            services = obj.main_services.filter(is_extra=True)
        return HutMainServiceSerializer(services, many=True, context=self.context).data

    def get_activities(self, obj):
        activities = obj.activities.all()
        return HutActivitySerializer(activities, many=True, context=self.context).data

    def get_lowest_price(self, obj):
        dates = self.get_available_dates(obj)
        if not dates:
            return None
        prices = [d['price'] for d in dates if 'price' in d]
        return min(prices) if prices else None

    def get_total_reviews(self, obj):
        if hasattr(obj, 'hutrating_count'):
            return obj.hutrating_count
        return obj.hutrating_set.count()



class HutAdminDetailsDashboardSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    images = HutImageSerializer(many=True, read_only=True)
    main_image = serializers.ImageField(required=False)
    available_dates = serializers.SerializerMethodField()
    main_services = serializers.SerializerMethodField()
    extra_services = serializers.SerializerMethodField()
    promocode = PromoCodeSerializer(many=True, read_only=True)  
    activities = serializers.SerializerMethodField()

    class Meta:
        model = Hut
        fields = '__all__'

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        if location_data:
            if instance.location:
                for attr, value in location_data.items():
                    setattr(instance.location, attr, value)
                instance.location.save()
            else:
                instance.location = Location.objects.create(**location_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    

    
    def get_available_dates(self, obj):
    # Query all related available_dates, assuming a related_name='available_dates'
      dates_qs = obj.available_dates.all()
    # Serialize them (assuming you have a serializer for AvailableDate model)
      serializer = AvailableDateRnageSerializer(dates_qs, many=True)
      return serializer.data
    def get_main_services(self, obj):
        services = obj.main_services.filter(is_extra=False)
        return HutMainServiceSerializer(services, many=True).data

    def get_extra_services(self, obj):
        services = obj.main_services.filter(is_extra=True)
        return HutMainServiceSerializer(services, many=True).data

    def get_activities(self, obj):
        activities = obj.activities.all()
        return HutActivitySerializer(activities, many=True).data



class KenSpecialItemsSerializer(serializers.ModelSerializer):
    huts = serializers.PrimaryKeyRelatedField(queryset=Hut.objects.all(), many=True, write_only=True)
    # supplier = serializers.CharField(source='supplier.full_name', read_only=True)
    # supplier_role = serializers.CharField(source='supplier.role', read_only=True)
    supplier = serializers.SerializerMethodField()
    supplier_role = serializers.SerializerMethodField()
    # 
    huts_details = HutDropDownSerializer(source='huts', many=True, read_only=True)
    
    class Meta:
        model = KenSpecialItems
        fields = '__all__'
        extra_fields = ['huts_details']  
    def get_supplier(self, obj):
        return obj.supplier.full_name if obj.supplier else None

    def get_supplier_role(self, obj):
        return obj.supplier.role if obj.supplier else None

    def create(self, validated_data):
        huts_data = validated_data.pop('huts', [])
        validated_data['is_active'] = True
        validated_data['is_delete'] = False
        ken_item = KenSpecialItems.objects.create(**validated_data)
        ken_item.huts.set(huts_data)  # 
        return ken_item

    def update(self, instance, validated_data):
        huts_data = validated_data.pop('huts', None)
        if huts_data is not None:
            instance.huts.set(huts_data)  # 
        for attr, value in validated_data.items():
           
            setattr(instance, attr, value)
        instance.save()
        
        return instance
    
        


class KenSpecialItemsListWebSerializer(serializers.ModelSerializer):
    
    
    
    class Meta:
        model = KenSpecialItems
        fields = '__all__'




class HutListHomeSerializer(serializers.ModelSerializer):
    
  
    main_image = serializers.ImageField(required=False)
    lowest_price=serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    

    class Meta:
        model = Hut
        fields = [
            'id',
            'title',
            'title_ar',
            'description',
            'description_ar',
           
            'size',
            'rate',
            'total_reviews',
            'created_at',
            'main_image',
            'location',
            'max_kids_num',
            'max_persons_num',
            'is_active',
            'lowest_price',
            
        ]
    def get_lowest_price(self, obj):
        dates = get_hut_available_dates(obj)
        if not dates:
            return None
        prices = [d['price'] for d in dates if 'price' in d]
        return min(prices) if prices else None
    
    def get_total_reviews(self, obj):
        if hasattr(obj, 'hutrating_count'):
            return obj.hutrating_count
        return obj.hutrating_set.count()





class HutListAdminSerializer(serializers.ModelSerializer):
    
  
    

    class Meta:
        model = Hut
        fields = [
            'id',
            'title',
            'title_ar',
            'description',
            'description_ar',
            'is_active',
            'size',
            'rate',
            'created_at',
            
           
        ]



class HutListSerializer(serializers.ModelSerializer):
    
    images = HutImageSerializer(many=True, read_only=True)
    main_image = serializers.ImageField(required=False)
    lowest_price=serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    
    

    class Meta:
        model = Hut
        fields = [
            'id',
            'title',
            'title_ar',
            'description',
            'description_ar',
           'is_active',
            'size',
            'rate',
            'total_reviews',
            'created_at',
            'images',
            'main_image',
            'location',
            'max_kids_num',
            'max_persons_num',
            "lowest_price",
            
        ]
    def get_lowest_price(self, obj):
        dates = get_hut_available_dates(obj)
        if not dates:
            return None
        prices = [d['price'] for d in dates if 'price' in d]
        return min(prices) if prices else None
    
    def get_total_reviews(self, obj):
        if hasattr(obj, 'hutrating_count'):
            return obj.hutrating_count
        return obj.hutrating_set.count()


class EventSerializer(serializers.ModelSerializer):
    location = LocationSerializer(required=False)
    available_dates = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    date = serializers.ListField(
        child=serializers.DateField(format="%Y-%m-%d"),
        write_only=True,
        required=False
    )
    supplier = serializers.CharField(source='supplier.full_name', read_only=True)
    notes = EventNoteSerializer(source='event_note', many=True, read_only=True)
    includes = EventIncludeSerializer(source='event_include', many=True, read_only=True)

    hut = HutDropDownSerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'title_ar', 'description', 'description_ar',
            'rate', 'created_at', 'image', 'supplier',
            'location', 'available_dates', 'date',
            'is_active', 'is_delete','hut',"notes","includes"
        ]

    def get_image(self, obj):
        if not obj.image:
            return None
        url = str(obj.image.url) if hasattr(obj.image, 'url') else str(obj.image)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)
        media_url = getattr(settings, 'MEDIA_URL', 'https://onzkkxvzuzkdcsckcxsp.supabase.co/storage/v1/object/public/media/')
        return media_url.rstrip('/') + '/' + url.lstrip('/')

    def get_available_dates(self, obj):
        today = date.today()
        next_date = obj.available_dates.filter(date__gte=today).order_by('date').first()
        if next_date:
            return {
                "id": next_date.id,
                "date": next_date.date,
                "price": next_date.price,
                "capacity": next_date.capacity,
                "max_purchasable_quantity": next_date.max_purchasable_quantity
            }
        return None




class EventAdminSerializer(serializers.ModelSerializer):
    location = LocationSerializer(required=False)
    available_dates = serializers.SerializerMethodField()
    date = serializers.ListField(
        child=serializers.DateField(format="%Y-%m-%d"),
        write_only=True,
        required=False
    )
    supplier = serializers.CharField(source='supplier.full_name', read_only=True)

    hut_id = serializers.PrimaryKeyRelatedField(
        source='hut',
        queryset=Hut.objects.all(),
        write_only=True,
        required=False
    )
    hut = HutDropDownSerializer(read_only=True)
    notes = EventNoteSerializer(source='event_note', many=True, read_only=True)
    includes = EventIncludeSerializer(source='event_include', many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'title_ar', 'description', 'description_ar',
            'rate', 'created_at', 'image', 'supplier',
            'location', 'available_dates', 'date',
            'is_active', 'is_delete',
            'hut_id', 'hut','notes','includes'
        ]

    def get_available_dates(self, obj):
     today = date.today()
     dates = obj.available_dates.filter(date__gte=today).order_by('date')

     return [
        {
            "id": d.id,
            "date": d.date,
            "price": d.price,
            "capacity": d.capacity,
            "max_purchasable_quantity": d.max_purchasable_quantity
        }
        for d in dates
    ] if dates.exists() else []

    def create(self, validated_data):
        location_data = validated_data.pop('location', None)
        dates_input = validated_data.pop('date', [])

        # Force is_active = True, is_delete = False
        validated_data['is_active'] = True
        validated_data['is_delete'] = False

        location = None
        if location_data:
            location = Location.objects.create(**location_data)

        event = Event.objects.create(location=location, **validated_data)

        # Get or create available dates
        if dates_input:
            date_objs = []
            for date in dates_input:
                obj, _ = AvailableDateEvent.objects.get_or_create(date=date)
                date_objs.append(obj)
            event.available_dates.set(date_objs)

        return event

    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', None)
        dates_input = validated_data.pop('available_dates_input', [])

        if location_data:
            for attr, value in location_data.items():
                setattr(instance.location, attr, value)
            instance.location.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if dates_input:
            date_objs = []
            for date in dates_input:
                obj, _ = AvailableDateEvent.objects.get_or_create(date=date)
                date_objs.append(obj)
            instance.available_dates.set(date_objs)

        return instance

    
    
    
    

class ServiceSerializer(serializers.ModelSerializer):
    # available_dates = AvailableDateSerializer(many=True, read_only=True)
    supplier = serializers.CharField(source='supplier.full_name', read_only=True)
    image = serializers.SerializerMethodField()
    hut_id = serializers.PrimaryKeyRelatedField(
        source='hut',
        queryset=Hut.objects.all(),
        write_only=True,
        required=False
    )
    hut = HutDropDownSerializer(read_only=True)
    available_dates = serializers.SerializerMethodField()
    date = serializers.ListField(
        child=serializers.DateField(format="%Y-%m-%d"),
        write_only=True,
        required=False
    )
    

    class Meta:
        model = Services
        fields = [
            'id', 'title', 'title_ar', 'description', 'description_ar','supplier',
            'capacity', 'available_dates', 'image','price',
            'min_purchasable_quantity', 'max_purchasable_quantity', 'date','hut_id','hut','is_active',"is_delete"
        ]
        read_only_fields = ['id', 'available_dates']

    def get_image(self, obj):
        if not obj.image:
            return None
        url = str(obj.image.url) if hasattr(obj.image, 'url') else str(obj.image)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)
        media_url = getattr(settings, 'MEDIA_URL', 'https://onzkkxvzuzkdcsckcxsp.supabase.co/storage/v1/object/public/media/')
        return media_url.rstrip('/') + '/' + url.lstrip('/')
    

    def create(self, validated_data):
        request = self.context.get('request')
        supplier = request.user  # Get the supplier from the request
        validated_data['is_active'] = True
        validated_data['is_delete'] = False

        dates_input = validated_data.pop('date', [])
        service = Services.objects.create(supplier=supplier, **validated_data)

        if dates_input:
            date_objs = []
            for date in dates_input:
                obj, _ = AvailableDateService.objects.get_or_create(date=date)
                date_objs.append(obj)
            service.available_dates.set(date_objs)

        return service

    def update(self, instance, validated_data):
        dates_input = validated_data.pop('date', [])
        

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if dates_input:
            date_objs = []
            for date in dates_input:
                obj, _ = AvailableDateService.objects.get_or_create(date=date)
                date_objs.append(obj)
            instance.available_dates.set(date_objs)

        return instance
    
    def get_available_dates(self, obj):
      today = date.today()
      next_date = obj.available_dates.filter(date__gte=today).order_by('date').first()

      if next_date:
        return {
            "id": next_date.id,
            "date": next_date.date,
            
        }




from rest_framework import serializers
from datetime import date

class ServiceSerializer(serializers.ModelSerializer):
    supplier = serializers.CharField(source='supplier.full_name', read_only=True)
    hut_id = serializers.PrimaryKeyRelatedField(
        source='hut',
        queryset=Hut.objects.all(),
        write_only=True,
        required=False
    )
    hut = HutDropDownSerializer(read_only=True)
    available_dates = serializers.SerializerMethodField()

    date = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_delete = serializers.BooleanField(required=False)

    class Meta:
        model = Services
        fields = [
            'id', 'title', 'title_ar', 'description', 'description_ar', 'supplier',
            'capacity', 'available_dates', 'image', 'price',
            'min_purchasable_quantity', 'max_purchasable_quantity',
            'date', 'hut_id', 'hut', 'is_active', "is_delete"
        ]
        read_only_fields = ['id', 'available_dates']
    def validate_date(self, value):
   
     if not value:
        return []

    # If it's a list (e.g. from getlist), flatten to a string
     if isinstance(value, list):
        raw_dates = []
        for v in value:
            raw_dates.extend([d.strip() for d in v.split(",") if d.strip()])
     else:
        raw_dates = [d.strip() for d in str(value).split(",") if d.strip()]

     if not raw_dates:
        raise serializers.ValidationError("❌ You must provide at least one valid date.")

     normalized = []
     for d in raw_dates:
        try:
            parsed_date = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            raise serializers.ValidationError(
                f"❌ Invalid date format: '{d}'. Use YYYY-MM-DD (e.g., 2025-10-30)."
            )

       

        normalized.append(parsed_date)

    # ✅ Prevent duplicates
     if len(normalized) != len(set(normalized)):
        raise serializers.ValidationError("❌ Duplicate dates are not allowed.")

     return normalized

    # def validate_date(self, value):
    #     if not value:
    #         return []

        
    #     if "," in value:
    #         date_list = [d.strip() for d in value.split(",") if d.strip()]
    #     else:
    #         date_list = [value.strip()]

        
    #     normalized = []
    #     for d in date_list:
    #         try:
    #             normalized.append(serializers.DateField().to_internal_value(d))
    #         except Exception:
    #             raise serializers.ValidationError(
    #                 f"Invalid date format: {d}. Use YYYY-MM-DD."
    #             )
    #     return normalized

    def create(self, validated_data):
        request = self.context.get('request')
        supplier = request.user
        validated_data['is_active'] = True
        validated_data['is_delete'] = False

        dates_input = validated_data.pop('date', [])
        print(dates_input,"der add")
        service = Services.objects.create(supplier=supplier, **validated_data)

        if dates_input:
            date_objs = []
            for d in dates_input:
                obj, _ = AvailableDateService.objects.get_or_create(date=d)
                date_objs.append(obj)
            service.available_dates.set(date_objs)

        return service

    def update(self, instance, validated_data):
        dates_input = validated_data.pop('date', [])
        print(dates_input,"ser date")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if dates_input:
            date_objs = []
            for d in dates_input:
                obj, _ = AvailableDateService.objects.get_or_create(date=d)
                date_objs.append(obj)
            instance.available_dates.set(date_objs)
        instance.save()

        return instance

    def get_available_dates(self, obj):
        today = date.today()
        next_date = obj.available_dates.filter(date__gte=today).order_by('date').first()
        if next_date:
            return {
                "id": next_date.id,
                "date": next_date.date,
            }
        return None



# class HutRatingSerializer(serializers.ModelSerializer):
#     user = MiniUserSerializer(read_only=True) 

#     class Meta:
#         model = HutRating
#         fields = ['id', 'user', 'hut', 'value', 'content', 'is_testmonail']
#         read_only_fields = ['id', 'user']
        
        
        
# serializers.py
from django.db.models import Max
from django.utils import timezone
from rest_framework import serializers
from .models import HutRating, Booking

class HutRatingSerializer(serializers.ModelSerializer):
    
    booking_id = serializers.IntegerField(write_only=True)  # <-- new field
    user       = MiniUserSerializer(read_only=True)
    hut        = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model  = HutRating
        fields = [
            'id', 'user', 'hut',          # read‑only
            'booking_id', 'value', 'content', 'is_testmonail'
        ]
        read_only_fields = ['id', 'user', 'hut']

    # ------------------------------------------------------------------ #
    # Core rule: user must own a PAID booking whose stay has ENDED
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        request_user = self.context['request'].user
        booking_id   = attrs.pop('booking_id')

        try:
            booking = (
                Booking.objects
                .select_related('hut')
                .prefetch_related('dates')
                .get(pk=booking_id, user=request_user)
            )
        except Booking.DoesNotExist:
            raise serializers.ValidationError('Booking not found.')

        if  booking.status !='paid':
            raise serializers.ValidationError('Booking is not paid yet.')
        if   booking.is_reviewed:
            raise serializers.ValidationError('You already rated this hut.')

        # latest date_to across all date ranges of the booking
        latest_checkout = (
            booking.dates.aggregate(max_to=Max('date_to'))['max_to']
        )

        if not latest_checkout:
            raise serializers.ValidationError('Booking has no dates attached.')

        if latest_checkout > timezone.localdate():
            raise serializers.ValidationError(
                f'You can rate this hut after {latest_checkout}.'
            )

        # # stop duplicate reviews for the same booking
        # if HutRating.objects.filter(user=request_user,
        #                             hut=booking.hut).exists():
        #     raise serializers.ValidationError('You already rated this hut.')

        # inject required fields
        attrs['hut']  = booking.hut
        attrs['user'] = request_user
        attrs['booking'] = booking 
        return attrs
    def create(self, validated_data):
        booking = validated_data.pop('booking')   # we stashed this in validate()
        with transaction.atomic():
            rating = HutRating.objects.create(**validated_data)
            booking.is_reviewed = True
            booking.save(update_fields=['is_reviewed'])
        return rating

class BookingDateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = BookingDate
        fields = ['id', 'date_from', 'date_to', 'is_extra', 'is_paid','total_price']


class EventTicketSerializer(serializers.ModelSerializer):
    
    date = serializers.PrimaryKeyRelatedField(
        queryset=AvailableDateEvent.objects.all(),
       
        write_only=True
    )
    
  
    
    class Meta:
        model = EventTicket
        fields = ['id', 'event', 'quantity', 'date', 'is_extra', 'is_paid']
    # def get_price_per_ticket(self, obj):
    #   date_obj = AvailableDateEvent.objects.filter(date=obj.date).first()
    #   return date_obj.price if date_obj else None

    def to_representation(self, instance):
     rep = super().to_representation(instance)
    
    # Get the actual related model instance from the related field
     available_date_event = AvailableDateEvent.objects.filter(date=instance.date).first()

     if available_date_event:
        rep['date'] = AvailableDateEventSerializer(available_date_event).data
     else:
        rep['date'] = instance.date  # fallback in case not found

     return rep
  
    

   

    def validate(self, data):
        if not data.get('event'):
            raise serializers.ValidationError("Event is required.")
        qty = data.get('quantity')

        min_qty = data['event'].min_purchasable_quantity
        max_qty = data['event'].max_purchasable_quantity

        if qty < min_qty or qty > max_qty:
            raise serializers.ValidationError(f"Quantity must be between {min_qty} and {max_qty}.")
        return data


class ServiceTicketMiniSerializer(serializers.ModelSerializer):
    # price = serializers.DecimalField(max_digits=10, decimal_places=2,read_only=True,source='service.price')
   
    price = serializers.DecimalField(
        source='service.price', max_digits=10, decimal_places=2, read_only=True
    )
    title = serializers.CharField(source='service.title', read_only=True)
    title_ar = serializers.CharField(source='service.title_ar', read_only=True)
    
    
    class Meta:
        model = ServiceTicket
        fields = ['id',  'quantity',  'is_extra', 'is_paid','price','title','title_ar']



class ServiceTicketSerializer(serializers.ModelSerializer):
    # price = serializers.DecimalField(max_digits=10, decimal_places=2,read_only=True,source='service.price')
    date = serializers.PrimaryKeyRelatedField(
        queryset=AvailableDateEvent.objects.all(),
       
        write_only=True
    )
    price = serializers.DecimalField(
        source='service.price', max_digits=10, decimal_places=2, read_only=True
    )
    booking_id = serializers.IntegerField(source='booking.id', read_only=True)
    
    
    class Meta:
        model = ServiceTicket
        fields = ['id', 'service', 'quantity', 'date', 'is_extra', 'is_paid','is_confirmed','price', 'booking_id']

    def validate(self, data):
        qty = data['quantity']
        if qty < data['service'].min_purchasable_quantity or qty > data['service'].max_purchasable_quantity:
            raise serializers.ValidationError("Quantity out of allowed range for this service.")
        return data
    def to_representation(self, instance):
     rep = super().to_representation(instance)
    
    # Get the actual related model instance from the related field
     available_date_event = AvailableDateService.objects.filter(date=instance.date).first()

     if available_date_event:
        rep['date'] = AvailableDateServiceSerializer(available_date_event).data
     else:
        rep['date'] = instance.date  # fallback in case not found

     return rep
    


class SpecialItemTicketForUpdandPastSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2,read_only=True,source='item.price')
   
    title_ar = serializers.CharField(read_only=True,source='item.title_ar')
    title = serializers.CharField(read_only=True,source='item.title')
    
    class Meta:
        model = SpecialItemTicket
        fields = ['id', 'item', 'quantity', 'is_extra', 'is_paid','price','title','title_ar']

class SpecialItemTicketSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2,read_only=True,source='item.price')
    
    class Meta:
        model = SpecialItemTicket
        fields = ['id', 'item', 'quantity', 'is_extra', 'is_paid','price']

    def validate(self, data):
        qty = data['quantity']
        if qty < data['item'].min_purchasable_quantity or qty > data['item'].max_purchasable_quantity:
            raise serializers.ValidationError("Quantity out of allowed range for this special item.")
        return data




  

class HutDetailsInBookingSerializer(serializers.ModelSerializer):
   
    # available_dates = serializers.SerializerMethodField()
   

    class Meta:
        model = Hut
        fields = ['id','max_persons_num','max_kids_num','check_in','check_out']
    # def get_available_dates(self, obj):
    #     today = date.today()
    #     valid_dates = obj.available_dates.filter(date_to__gte=today,date_from__gte=today)
    #     return AvailableDateRnageSerializer(valid_dates, many=True).data
    # def get_available_dates(self, obj):
    #     array=get_hut_available_dates(obj.id)
    #     print(array,'array')
    #     # today = date.today()
    #     # valid_dates = obj.available_dates.filter(date_to__gte=today,date_from__gte=today)
       
        
    #     # return AvailableDateRnageSerializer(valid_dates, many=True).data
    #     return array



class HutDetailsInBookingWithDateSerializer(serializers.ModelSerializer):
   
    available_dates = serializers.SerializerMethodField()
   

    class Meta:
        model = Hut
        fields = ['id','max_persons_num','max_kids_num','available_dates']
    # def get_available_dates(self, obj):
    #     today = date.today()
    #     valid_dates = obj.available_dates.filter(date_to__gte=today,date_from__gte=today)
    #     return AvailableDateRnageSerializer(valid_dates, many=True).data
    def get_available_dates(self, obj):
        array=get_hut_available_dates(obj.id)
        print(array,'array')
        # today = date.today()
        # valid_dates = obj.available_dates.filter(date_to__gte=today,date_from__gte=today)
       
        
        # return AvailableDateRnageSerializer(valid_dates, many=True).data
        return array



from django.utils.timezone import now
from django.db.models import Sum

class UpComingBookingSerializer(serializers.ModelSerializer):
    # dates = serializers.SerializerMethodField()
    
    extra_days = serializers.SerializerMethodField()
    check_in=serializers.SerializerMethodField()
    check_out=serializers.SerializerMethodField()
    hut = serializers.SerializerMethodField()
    available_dates = serializers.SerializerMethodField()
    # user = MiniUserSerializer(read_only=True)
    # hut_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='hut.price')
    # hut_details = HutDetailsInBookingSerializer(read_only=True, source='hut')
    # services = ServiceTicketSerializer(many=True, required=False)
    services = serializers.SerializerMethodField()
    extra_services = serializers.SerializerMethodField()
    # events = EventTicketSerializer(many=True, required=False)
     
    events_tickets_count = serializers.SerializerMethodField()
    # services_tickets_count = serializers.SerializerMethodField()
    # special_items_tickets_count = serializers.SerializerMethodField()
    booking_price = serializers.SerializerMethodField()
    extension_price = serializers.SerializerMethodField()


    class Meta:
        model = Booking
        fields = [
            'id', 'hut', 'available_dates', 'check_in','check_out', 'total_price', 'persons_max_num', 'kids_max_num',
            'paid', 'not_paid', 'created_at', 'status','is_paid',
             "services",'extra_days','extra_services','extension_price','booking_price',
            
            'events_tickets_count', 
            'qr_code_image', 'invoice_url'
        ]
        read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status', 'dates',]

    # def get_dates(self, obj):
    #     # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
    #     today = now().date()
    #     print(BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True))
    #     booking_date = BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True).order_by('date_from').first()
    #     print(booking_date )
    #     if booking_date:
    #         return BookingDateSerializer(booking_date).data
    #     return None
    def get_check_in(self, obj):
        # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
        today = now().date()
        print(BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True))
        booking_date = BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True).order_by('date_from').first()
      
        if booking_date:
            return booking_date.date_from
        return None
    def get_check_out(self, obj):
        # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
        today = now().date()
        print(BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True))
        booking_date = BookingDate.objects.filter(booking=obj,is_extra=False, is_paid=True).order_by('date_from').first()
      
        if booking_date:
            return booking_date.date_to
        return None

    def get_hut(self, obj):
        return obj.hut_id

    def get_available_dates(self, obj):
        if not obj.hut:
            return []
        return AvailableDateRnageSerializer(obj.hut.available_dates.all(), many=True).data


    def get_extra_days(self, obj):
        # All extra BookingDates that are paid
        extra_dates = obj.dates.filter(is_extra=True, is_paid=True).order_by('date_from')
        return BookingDateSerializer(extra_dates, many=True).data
    def get_extension_price(self, obj):
     total_extension_price = Decimal("0.00")
     extra_dates = obj.dates.filter(is_extra=True, is_paid=True)
     for d in extra_dates:
        if d.date_from and d.date_to and d.total_price:
            # Calculate number of nights (e.g. 26 - 29 → 3 nights)
            nights = (d.date_to - d.date_from).days
            if nights ==0:
             nights=1
            # If user paid per night, total_price is per night:
            total_extension_price += Decimal(d.total_price) * nights

    
     extra_services = obj.services.filter(is_extra=True, is_paid=True)
     for s in extra_services:
        if s.service and s.service.price:
            total_extension_price += Decimal(s.service.price) * s.quantity

     return total_extension_price
    def get_booking_price(self, obj):
     total_booking_price = Decimal("0.00")
     dates = obj.dates.filter(is_extra=False, is_paid=True)
     for d in dates:
        if d.date_from and d.date_to and d.total_price:
            # Calculate number of nights (e.g. 26 - 29 → 3 nights)
            nights = (d.date_to - d.date_from).days
          
            if nights ==0:
             nights=1
            
            # If user paid per night, total_price is per night:
            total_booking_price += Decimal(d.total_price) * nights

    
     services = obj.services.filter(is_extra=True, is_paid=True)
     for s in services:
        if s.service and s.service.price:
            total_booking_price += Decimal(s.service.price) * s.quantity
     events = obj.events.filter( is_paid=True)
     for s in events:
        if s.event :
            date=AvailableDateEvent.objects.filter(date=s.date).first()
            if date:
              total_booking_price += Decimal(date.price) * s.quantity
            total_booking_price += 0

     items = obj.special_items.filter( is_paid=True)
     for s in items:
        if s.item and s.item.price:
            total_booking_price += Decimal(s.item.price) * s.quantity
     return total_booking_price
    
    def get_extra_services(self, obj):
        # All extra BookingDates that are paid
        extra_service = obj.services.filter(is_extra=True, is_paid=True).order_by('-id')
        return ServiceTicketMiniSerializer(extra_service, many=True).data
    def get_services(self, obj):
        # All services that are paid
        # extra_service = obj.services.filter(is_extra=False, is_paid=True).order_by('-id')
        # return ServiceTicketSerializer(extra_service, many=True).data
        services = obj.services.filter(booking=obj,is_paid=True,is_extra=False)  # or filter() if needed
        service_data =  ServiceTicketMiniSerializer(services, many=True).data

        
        items = SpecialItemTicket.objects.filter(booking=obj,is_paid=True)  # 
        item_data = SpecialItemTicketForUpdandPastSerializer(items, many=True).data

        
        combined = list(service_data) + list(item_data)

        
        combined.sort(key=lambda x: x['id'], reverse=True)

        return combined


    def get_events_tickets_count(self, obj):
      return obj.events.filter(is_paid=True).aggregate(total=Sum('quantity'))['total'] or 0

    def get_services_tickets_count(self, obj):
      return obj.services.filter(is_paid=True).aggregate(total=Sum('quantity'))['total'] or 0

    def get_special_items_tickets_count(self, obj):
        # return obj.special_items.filter(is_paid=True).count()
        return obj.special_items.filter(is_paid=True).aggregate(total=Sum('quantity'))['total'] or 0














# class PastBookingSerializer(serializers.ModelSerializer):
#     dates = serializers.SerializerMethodField()
#     # extra_days = serializers.SerializerMethodField()
#     user = MiniUserSerializer(read_only=True)
#     hut_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='hut.price')
#     # hut_details = HutDetailsInBookingSerializer(read_only=True, source='hut')
#     # services = ServiceTicketSerializer(many=True, required=False)
     
#     events_tickets_count = serializers.SerializerMethodField()
#     services_tickets_count = serializers.SerializerMethodField()
#     special_items_tickets_count = serializers.SerializerMethodField()

#     class Meta:
#         model = Booking
#         fields = [
#             'id', 'user', 'hut','hut_price', 'total_price', 'persons_max_num', 'kids_max_num',
#             'paid', 'not_paid', 'created_at', 'status',
#             'dates',
            
#             'events_tickets_count', 'services_tickets_count', 'special_items_tickets_count',
#             'qr_code_image', 'invoice_url'
#         ]
#         read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status', 'dates', 'extra_days']

#     def get_dates(self, obj):
#         # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
#         today = now().date()
        
#         booking_date = BookingDate.objects.filter(booking=obj,
#     is_extra=False,
    
#     # date_to__lt=today   # 🔁 date is in the past (less than today)
# ).order_by('-date_to').first()
#         print(booking_date )
#         if booking_date:
#             return BookingDateSerializer(booking_date).data
#         return None

#     # def get_extra_days(self, obj):
#     #     # All extra BookingDates that are paid
#     #     extra_dates = obj.dates.filter(is_extra=True).order_by('date_from')
#     #     return BookingDateSerializer(extra_dates, many=True).data

#     def get_events_tickets_count(self, obj):
#         return obj.events.all().count()

#     def get_services_tickets_count(self, obj):
#         return obj.services.all().count()

#     def get_special_items_tickets_count(self, obj):
#         return obj.special_items.all().count()




class PastBookingSerializer(serializers.ModelSerializer):
    dates = serializers.SerializerMethodField()
    hut_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='hut.price')
    events_tickets_count = serializers.SerializerMethodField()
    services_tickets_count = serializers.SerializerMethodField()
    special_items_tickets_count = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'hut', 'total_price', 'persons_max_num', 'kids_max_num',
            'paid', 'not_paid', 'created_at', 'status',
    
            
            'events_tickets_count', 'services_tickets_count', 'special_items_tickets_count',
            'qr_code_image', 'invoice_url'
        ]
        read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status', 'dates', 'extra_days']

    def get_dates(self, obj):
        # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
        today = now().date()
        
        booking_date = BookingDate.objects.filter(booking=obj,
    is_extra=False,
    
    # date_to__lt=today   # 🔁 date is in the past (less than today)
).order_by('-date_to').first()
        print(booking_date )
        if booking_date:
            return BookingDateSerializer(booking_date).data
        return None

    # def get_extra_days(self, obj):
    #     # All extra BookingDates that are paid
    #     extra_dates = obj.dates.filter(is_extra=True).order_by('date_from')
    #     return BookingDateSerializer(extra_dates, many=True).data

    def get_events_tickets_count(self, obj):
        return obj.events.all().count()

    def get_services_tickets_count(self, obj):
        return obj.services.all().count()

    def get_special_items_tickets_count(self, obj):
        return obj.special_items.all().count()




class BookingForPaymnetSerializer(serializers.ModelSerializer):
    dates = serializers.SerializerMethodField()
    # extra_days = serializers.SerializerMethodField()
    # user = MiniUserSerializer(read_only=True)
    hut_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, source='hut.price')
    # hut_details = HutDetailsInBookingSerializer(read_only=True, source='hut')
    # services = ServiceTicketSerializer(many=True, required=False)
    promocode=PromoCodeSerializer(read_only=True)
    events_tickets_count = serializers.SerializerMethodField()
    services_tickets_count = serializers.SerializerMethodField()
    special_items_tickets_count = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',  'hut','hut_price', 'total_price', 'persons_max_num', 'kids_max_num',
            'paid', 'not_paid', 'created_at', 'status',
            'dates','promocode',
            
            'events_tickets_count', 'services_tickets_count', 'special_items_tickets_count',
            'qr_code_image', 'invoice_url'
        ]
        read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status', 'dates']

    def get_dates(self, obj):
        # Pick the BookingDate with is_extra=False, is_paid=True, closest upcoming
        today = now().date()
        
        booking_date = BookingDate.objects.filter(booking=obj,
    is_extra=False,
    
    # date_to__lt=today   # 🔁 date is in the past (less than today)
).order_by('-date_to').first()
        print(booking_date )
        if booking_date:
            return BookingDateSerializer(booking_date).data
        return None

    # def get_extra_days(self, obj):
    #     # All extra BookingDates that are paid
    #     extra_dates = obj.dates.filter(is_extra=True).order_by('date_from')
    #     return BookingDateSerializer(extra_dates, many=True).data

    def get_events_tickets_count(self, obj):
        return obj.events.all().count()

    def get_services_tickets_count(self, obj):
        return obj.services.all().count()

    def get_special_items_tickets_count(self, obj):
        return obj.special_items.all().count()













class SupplierListSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True) 
   

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'avatar', 'phone', 'address',
            'services'
        ]




class BookingAdminTableSerializer(serializers.ModelSerializer):
    # date = BookingDateSerializer(write_only=True)  
    date = serializers.SerializerMethodField(read_only=True) 
    # hut_title=serializers.CharField(source='hut.title')
    # hut_title_ar=serializers.CharField(source='hut.title_ar')
    # hut_title=serializers.CharField(source='hut.title')
    hut_title_ar=serializers.SerializerMethodField()
    hut_title=serializers.SerializerMethodField()


    is_scaned = serializers.CharField( read_only=True)
    
  
   
    is_valid = serializers.SerializerMethodField()
    has_extra_items = serializers.SerializerMethodField()
    

    class Meta:
        model = Booking
        fields = [
            'id','hut_title','hut_title_ar','is_valid', 'total_price', 
            'created_at', 'status',
            'date','qr_code_image','invoice_url','is_scaned','has_extra_items'
        ]
        read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status', 'dates']
   
    def get_date(self, obj):
     main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
     return main_date.date_from if main_date else None    
    def get_is_valid(self, obj):
        today = date.today()
        # Get the main (non-extra) date, or the first available one
        booking_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        if booking_date and booking_date.date_from == today and obj.status == 'paid':
            return True
        return False
    def get_has_extra_items(self, obj):
        return (
            obj.dates.filter(is_extra=True).exists() or
            obj.events.filter(is_extra=True).exists() or
            obj.services.filter(is_extra=True).exists() or
            obj.special_items.filter(is_extra=True).exists()
        )
    def get_hut_title(self, obj):
        return obj.hut.title if obj.hut else None

    def get_hut_title_ar(self, obj):
        return obj.hut.title_ar if obj.hut else None
    
    




# class BookingDetailsAdminSerializer(serializers.ModelSerializer):
#     # date = BookingDateSerializer(write_only=True)  
#     user = MiniUserSerializer(read_only=True)
#     hut_title=serializers.CharField(source='hut.title')
    
#     # hut = serializers.PrimaryKeyRelatedField(queryset=Hut.objects.all(), write_only=True)
#     # hut_details = HutDetailsInBookingSerializer(read_only=True, source='hut')
#     is_valid = serializers.SerializerMethodField()

#     class Meta:
#         model = Booking
#         fields = [
#             'id', 'is_valid', 'user',  'hut_title',
#             'total_price', 'persons_max_num', 'kids_max_num',
#             'paid', 'not_paid', 'created_at', 'status',
#              'qr_code_image', 'invoice_url', 'is_scaned',
            
#         ]
#         read_only_fields = ['total_price', 'paid', 'not_paid', 'created_at', 'status']

#     def get_is_valid(self, obj):
#         today = date.today()
#         booking_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
#         return booking_date and booking_date.date_from == today and obj.status == 'paid'

#     def to_representation(self, instance):
#         data = super().to_representation(instance)

#         # Inject services
#         for index, service in enumerate(instance.services.all(), start=1):
#             data[f"service_{index}"] = ServiceTicketSerializer(service).data

#         # Inject events
#         for index, event in enumerate(instance.events.all(), start=1):
#             data[f"event_{index}"] = EventTicketSerializer(event).data

#         # Inject dates
#         for index, booking_date in enumerate(instance.dates.all(), start=1):
#             data[f"date_{index}"] = BookingDateSerializer(booking_date).data

#         return data





from rest_framework import serializers
from datetime import date
from decimal import Decimal

class BookingOrderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    title_ar = serializers.CharField()
    type = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_paid = serializers.BooleanField()
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


# class BookingDetailsAdminSerializer(serializers.ModelSerializer):
#     user = MiniUserSerializer(read_only=True)
#     hut_title = serializers.CharField(source='hut.title', read_only=True)
#     is_valid = serializers.SerializerMethodField()
#     main_order = serializers.SerializerMethodField()
#     extra_order = serializers.SerializerMethodField()
#     date = serializers.SerializerMethodField()

#     class Meta:
#         model = Booking
#         fields = [
#             'id', 'is_valid', 'user', 'hut_title',
#             'total_price', 'persons_max_num', 'kids_max_num',
#             'paid', 'not_paid', 'created_at', 'status',
#             'qr_code_image', 'invoice_url', 'is_scaned',
#             'main_order', 'extra_order','date'
#         ]
#     def get_date(self, obj):
        
#         main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
#         return (
#             BookingDateSerializer(main_date).data if main_date else None
#         ) 


#     def get_is_valid(self, obj):
#         today = date.today()
#         booking_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
#         return booking_date and booking_date.date_from == today and obj.status == 'paid'

#     def get_main_order(self, obj):
#         return self._build_order(obj, is_extra=False)

#     def get_extra_order(self, obj):
#         return self._build_order(obj, is_extra=True)

#     def _build_order(self, obj, is_extra):
#         items = []

#         # Events
#         for item in obj.events.filter(is_extra=is_extra):
#             event = item.event
#             price = Decimal("0.00")
#             if event and event.available_dates.exists():
#                 price = event.available_dates.first().price or Decimal("0.00")
#             total_price = price * item.quantity
#             items.append({
#                 "id": item.id,
#                 "title": event.title if event else "",
#                 "title_ar": event.title_ar if event else "",
#                 "type": "event",
#                 "quantity": item.quantity,
#                 "price": price,
#                 "total_price": total_price,
#                 "is_paid": item.is_paid,
#             })

#         # Services
#         for item in obj.services.filter(is_extra=is_extra):
#             service = item.service
#             price = service.price or Decimal("0.00")
#             total_price = price * item.quantity
#             items.append({
#                 "id": item.id,
#                 "title": service.title if service else "",
#                 "title_ar": service.title_ar if service else "",
#                 "type": "service",
#                 "quantity": item.quantity,
#                 "price": price,
#                 "total_price": total_price,
#                 "is_paid": item.is_paid,
#             })

#         # Special Items
#         for item in obj.special_items.filter(is_extra=is_extra):
#             special_item = item.item
#             price = special_item.price or Decimal("0.00")
#             total_price = price * item.quantity
#             items.append({
#                 "id": item.id,
#                 "title": special_item.title if special_item else "",
#                 "title_ar": special_item.title_ar if special_item else "",
#                 "type": "special_item",
#                 "quantity": item.quantity,
#                 "price": price,
#                 "total_price": total_price,
#                 "is_paid": item.is_paid,
#             })

#         # Dates / Huts
#         for booking_date in obj.dates.filter(is_extra=is_extra):
#             hut_date = AvailableDateRanges.objects.filter(
#                 huts=obj.hut,
#                 date_from__lte=booking_date.date_to,
#                 date_to__gte=booking_date.date_from
#             ).first()
#             nights = (booking_date.date_to - booking_date.date_from).days
#             if nights ==0:
#                 nights=1
                
#             print(hut_date.price,'gg')
#             price = hut_date.price or Decimal("0.00")
#             per_night = price / nights if nights else price
#             items.append({
#                 "id": booking_date.id,
#                 "title": obj.hut.title if obj.hut else "",
#                 "title_ar": obj.hut.title_ar if obj.hut else "",
#                 "type": "hut",
#                 "quantity": nights,
#                 "price": round(per_night, 2),
#                 "total_price": price,
#                 "is_paid": booking_date.is_paid,
#                 "date_from": booking_date.date_from,
#                 "date_to": booking_date.date_to,
#             })

#         return BookingOrderItemSerializer(items, many=True).data




from rest_framework import serializers
from .models import *
from datetime import timedelta


class BookingDateInputSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class EventTicketInputSerializer(serializers.Serializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    quantity = serializers.IntegerField()
    date = serializers.PrimaryKeyRelatedField(queryset=AvailableDateEvent.objects.all())


class ServiceTicketInputSerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Services.objects.all())
    quantity = serializers.IntegerField()
    date = serializers.PrimaryKeyRelatedField(queryset=AvailableDateService.objects.all())
    # available_date_service = serializers.PrimaryKeyRelatedField(queryset=AvailableDateService.objects.all())


class SpecialItemTicketInputSerializer(serializers.Serializer):
    item = serializers.PrimaryKeyRelatedField(queryset=KenSpecialItems.objects.all())
    quantity = serializers.IntegerField()


class BookingSerializer(serializers.ModelSerializer):
    date = BookingDateInputSerializer(write_only=True)
    events = EventTicketInputSerializer(many=True, write_only=True, required=False)
    services = ServiceTicketInputSerializer(many=True, write_only=True, required=False)
    hut = serializers.PrimaryKeyRelatedField(queryset=Hut.objects.all(), write_only=True)
    special_items = SpecialItemTicketInputSerializer(many=True, write_only=True, required=False)
    user=MiniUserSerializer(read_only=True)
    hut_details = HutDetailsInBookingWithDateSerializer(read_only=True, source='hut')
    is_valid = serializers.SerializerMethodField()
    dates = serializers.SerializerMethodField(read_only=True) 
    promocode = serializers.CharField(write_only=True, required=False, allow_blank=True)
    promocode_obj = PromoCodeSerializer(read_only=True, source='promocode')
    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'hut', 'persons_max_num', 'kids_max_num','status','created_at','is_valid',"dates",
            'date', 'events', 'services', 'special_items','hut_details','total_price','paid','not_paid','promocode','promocode_obj',
        ]

    def validate(self, data):
        hut = data.get('hut')
        promocode_value = data.get('promocode')

        # Promo code validation
        if promocode_value:
            try:
                promo = PromoCode.objects.get(code=promocode_value)
            except PromoCode.DoesNotExist:
                raise serializers.ValidationError({"promocode": "Invalid promo code."})

            if not promo.is_active:
                raise serializers.ValidationError({"promocode": "Promo code is not active."})

            if promo not in hut.promocode.all():
              raise serializers.ValidationError({"promocode": "Promo code not valid for this hut."})

            # store promo object for use in create/update
            self._validated_promo = promo


        date_data = data.get('date')
        date_from = date_data['date_from']
        date_to = date_data['date_to']

        # 1. Hut capacity check
        if hut:
            if data['persons_max_num'] > (hut.max_persons_num or 0):
                raise serializers.ValidationError("Exceeds maximum persons allowed for this hut.")
            if data['kids_max_num'] > (hut.max_kids_num or 0):
                raise serializers.ValidationError("Exceeds maximum kids allowed for this hut.")

        # 2. Hut date range check
        valid, invalid_date = is_hut_available(hut.id, date_from, date_to,self.instance)
      
        if not valid:
            raise serializers.ValidationError(f"Hut not available on {invalid_date}")

        # 3. Event capacity & date validity
        for event_data in data.get('events', []):
            event = event_data['event']
            date_obj = event_data['date']
            if not event.available_dates.filter(id=date_obj.id).exists():
                raise serializers.ValidationError(f"Event '{event}' not available on selected date.")
            if date_obj.capacity is not None and event_data['quantity'] > date_obj.capacity:
                raise serializers.ValidationError(f"Event '{event}' exceeds capacity on {date_obj.date}.")

        # 4. Service capacity & date validity
        for service_data in data.get('services', []):
            service = service_data['service']
            date_obj = service_data['date']
            if not service.available_dates.filter(id=date_obj.id).exists():
                raise serializers.ValidationError(f"Service '{service}' not available on selected date.")
            if service.capacity is not None and service_data['quantity'] > service.capacity:
                raise serializers.ValidationError(f"Service '{service}' exceeds capacity on {date_obj.date}.")

        return data
    def get_is_valid(self, obj):
        today = date.today()
        # Get the main (non-extra) date, or the first available one
        booking_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        if booking_date and booking_date.date_from == today and obj.status == 'paid':
            return True
        return False
    def get_dates(self, obj):
        main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        return BookingDateSerializer(main_date).data if main_date else None
    # def get_dates(self, obj):
        
    #     main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
    #     # print( BookingDateSerializer(main_date).data,'llllllll' )
        
    
    #     return (
    #         BookingDateSerializer(main_date).data if main_date else None
    #     ) 

    def create(self, validated_data):
        user = validated_data['user']
        hut = validated_data['hut']
        persons = validated_data['persons_max_num']
        kids = validated_data['kids_max_num']
        date_data = validated_data.pop('date')
        events_data = validated_data.pop('events', [])
        services_data = validated_data.pop('services', [])
        items_data = validated_data.pop('special_items', [])
        promocode_value = validated_data.pop('promocode', None)
        promo = getattr(self, "_validated_promo", None)
       


        booking = Booking.objects.create(
            user=user,
            hut=hut,
            persons_max_num=persons,
            kids_max_num=kids
        )
        if promo:
            booking.promocode = promo
            booking.save()

        # Booking Date
        BookingDate.objects.create(
            booking=booking,
            date_from=date_data['date_from'],
            date_to=date_data['date_to']
        )

        total_price = 0

        # Events
        for event in events_data:
            event_obj = event['event']
            quantity = event['quantity']
            date = event['date']
            print(date)
            date_instance = event_obj.available_dates.filter(id=event['date'].id).first()
            print(date_instance,"ins")
            if not date_instance:
                raise ValueError("No available date found for this event")
            EventTicket.objects.create(
                booking=booking,
                event=event_obj,
                quantity=quantity,
                date=date_instance.date 
            )
            subtotal = (date.price or 0) * quantity
            # if date.precentage:
            #     subtotal -= subtotal * (date.precentage / 100)
            total_price += subtotal
            print(total_price,'event')

        # Services
        for service in services_data:
            service_obj = service['service']
            quantity = service['quantity']
            date = service['date']
            
            

            ServiceTicket.objects.create(
                booking=booking,
                service=service_obj,
                quantity=quantity,
                date=date.date 
            )
            subtotal = (service_obj.price or 0) * quantity
            # if date.precentage:
            #     subtotal -= subtotal * (date.precentage / 100)
            total_price += subtotal
            print(total_price,'service')

        # Special Items
        for item in items_data:
            item_obj = item['item']
            quantity = item['quantity']
            SpecialItemTicket.objects.create(
                booking=booking,
                item=item_obj,
                quantity=quantity
            )
            subtotal = (item_obj.price or 0) * quantity
            total_price += subtotal
            print(total_price,'kenitem')

        # Hut price from range
        date_from = date_data['date_from']
        date_to = date_data['date_to']
        current_date = date_from
        hut_price=0
        if date_data:
             date_from = date_data['date_from']
             date_to = date_data['date_to']
             nights = (date_to - date_from).days
             if nights == 0:
              nights = 1  # minimum 1 night if same day

   
             hut_range = AvailableDateRanges.objects.filter(huts=hut,date_from__lte=date_from,date_to__gte=date_to).first()

             if hut_range:
                nightly_price = hut_range.price or 0
                total_price += nightly_price * nights
                print(total_price, "total price by night")
# Loop until the day before date_to
        # while current_date <= date_to:
        #   hut_range = AvailableDateRanges.objects.filter(huts=hut,
        #        date_from__lte=current_date,
        #          date_to__gte=current_date ).first()
        #   print(hut_range,'hutrangeff')
          
        #   if hut_range:
        #    daily_price = hut_range.price or 0

        #    total_price += daily_price
        #    hut_price+=daily_price
        #   current_date += timedelta(days=1)
        #
        # print(hut_price,"hutprice")
        if promo:
           discount = (Decimal(promo.percentage) / Decimal("100")) * total_price
           total_price -= discount
           print(total_price, "after discount")
        
        # total_price+=hut_price
        booking.total_price = total_price
        booking.not_paid = total_price
        print(total_price)
        booking.save()

        return booking
    def update(self, instance, validated_data):
     hut = validated_data.get('hut', instance.hut)
     persons = validated_data.get('persons_max_num', instance.persons_max_num)
     kids = validated_data.get('kids_max_num', instance.kids_max_num)
     date_data = validated_data.pop('date', None)
     events_data = validated_data.pop('events', [])
     services_data = validated_data.pop('services', [])
     items_data = validated_data.pop('special_items', [])
     promocode_value = validated_data.pop('promocode', None)
     promo = getattr(self, "_validated_promo", None)

     instance.hut = hut
     instance.persons_max_num = persons
     instance.kids_max_num = kids
    #  instance.status = validated_data.get('status', instance.status)
     instance.save()

    # Update booking date
     if date_data:
        BookingDate.objects.filter(booking=instance, is_extra=False).delete()
        BookingDate.objects.create(
            booking=instance,
            date_from=date_data['date_from'],
            date_to=date_data['date_to']
        )

     total_price = 0

    # Update events
     instance.events.all().delete()
     for event in events_data:
        event_obj = event['event']
        quantity = event['quantity']
        date = event['date']
        EventTicket.objects.create(
            booking=instance,
            event=event_obj,
            quantity=quantity,
            date=date.date
        )
        subtotal = (date.price or 0) * quantity
        total_price += subtotal
        print(total_price,"event updaye")

    # Update services
     instance.services.all().delete()
     for service in services_data:
        service_obj = service['service']
        quantity = service['quantity']
        date = service['date']
        ServiceTicket.objects.create(
            booking=instance,
            service=service_obj,
            quantity=quantity,
            date=date.date
        )
        subtotal = (date.price or 0) * quantity
        total_price += subtotal
        print(total_price,"service updaye")


    # Update special items
     instance.special_items.all().delete()
     for item in items_data:
        item_obj = item['item']
        quantity = item['quantity']
        SpecialItemTicket.objects.create(
            booking=instance,
            item=item_obj,
            quantity=quantity
        )
        subtotal = (item_obj.price or 0) * quantity
        total_price += subtotal
        print(total_price,"iemens updaye")

     # Hut price (once, not inside the loop)
     if date_data:
         date_from = date_data['date_from']
         date_to = date_data['date_to']
         nights = (date_to - date_from).days
         if nights == 0:
             nights = 1  # minimum 1 night if same day
         hut_range = AvailableDateRanges.objects.filter(huts=hut, date_from__lte=date_from, date_to__gte=date_to).first()
         if hut_range:
             nightly_price = hut_range.price or 0
             total_price += nightly_price * nights
             print(total_price, "total price by night")

     if instance.promocode:
         discount = (Decimal(instance.promocode.percentage) / Decimal("100")) * total_price
         total_price -= discount
         print(total_price, "after discount")

     instance.total_price = total_price
     instance.not_paid = total_price
     instance.save()

     return instance

    def to_representation(self, instance):
        """Override to return nested read serializers on the same fields."""
        rep = super().to_representation(instance)

        # Replace 'events' with serialized EventTicketSerializer data
        rep['events'] = EventTicketSerializer(instance.events.all(), many=True).data
        rep['services'] = ServiceTicketSerializer(instance.services.all(), many=True).data
        rep['special_items'] = SpecialItemTicketSerializer(instance.special_items.all(), many=True).data
        rep['promocode'] = PromoCodeSerializer(instance.promocode).data if instance.promocode else None

   
        

        return rep
    










      
class EventBulkDataSerializer(serializers.Serializer):
    includes = EventIncludeSerializer(many=True)
    notes = EventNoteSerializer(many=True)


class HutActivityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HutActivity
        fields = ['description', 'description_ar']


class HutMainServiceCreateSerializer(serializers.ModelSerializer):
    icon_id = serializers.PrimaryKeyRelatedField(queryset=Icon.objects.all(), source='icon')

    class Meta:
        model = HutMainService
        fields = ['icon_id', 'description', 'description_ar', 'is_extra']
class HutServicesActivitiesBulkSerializer(serializers.Serializer):
    activities = HutActivityCreateSerializer(many=True)
    services = HutMainServiceCreateSerializer(many=True)










class BookingDetailsAdminSerializer(serializers.ModelSerializer):
    promocode = PromoCodeSerializer(read_only=True)

    user = MiniUserSerializer(read_only=True)
    hut_title = serializers.CharField(source='hut.title', read_only=True)
    is_valid = serializers.SerializerMethodField()
    main_order = serializers.SerializerMethodField()
    extra_order = serializers.SerializerMethodField()
    sub_total = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    qr_logs = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'is_valid', 'user', 'hut_title',
            'total_price', 'sub_total', 'persons_max_num', 'kids_max_num',
            'paid', 'not_paid', 'created_at', 'status',
            'qr_code_image', 'invoice_url', 'is_scaned',
            'main_order', 'extra_order', 'date','qr_logs','promocode'
        ]
    def get_qr_logs(self, obj):
        logs = QrLogs.objects.filter(booking=obj).order_by('-created_at')
        return QrLogsSerializer(logs, many=True).data

    def get_date(self, obj):
        main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        return BookingDateSerializer(main_date).data if main_date else None

    def get_is_valid(self, obj):
        today = date.today()
        booking_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        return booking_date and booking_date.date_from == today and obj.status == 'paid'

    def get_main_order(self, obj):
        return self._build_order(obj, is_extra=False)

    def get_extra_order(self, obj):
        return self._build_order(obj, is_extra=True)

    def get_sub_total(self, obj):
        """Sum of all line items (main_order + extra_order) for verification."""
        main = self.get_main_order(obj)
        extra = self.get_extra_order(obj)
        return sum(Decimal(str(item["total_price"])) for item in main + extra)

    def _build_order(self, obj, is_extra):
        request = self.context.get('request')
        user = request.user if request else None
        is_supplier = getattr(user, 'role', None) == 'supplier'

        items = []

        # Events
        event_qs = obj.events.filter(is_extra=is_extra)
        if is_supplier:
            event_qs = event_qs.filter(event__supplier=user)
        #     event_qs = event_qs.filter(event__supplier=user)
        # event_qs = event_qs.all()
        # print(event_qs,'lppll')
        
        # for item in event_qs:
        #     event = item.event
        #     print("jj")
        #     print(items,"kkjjrrf")
        #     price = Decimal("0.00")
        #     if event and event.available_dates.exists():
        #         price = event.available_dates.first().price or Decimal("0.00")
        #     total_price = price * item.quantity
        #     items.append({
        #         "id": item.id,
        #         "title": event.title if event else "",
        #         "title_ar": event.title_ar if event else "",
        #         "type": "event",
        #         "quantity": item.quantity,
        #         "price": price,
        #         "total_price": total_price,
        #         "is_paid": item.is_paid,
        #     })
        for item in event_qs:
          event = item.event
          price = Decimal("0.00")

          # Get price from this event's available date for the ticket date (filter by event to avoid wrong price)
          if event:
            date_price_obj = AvailableDateEvent.objects.filter(events=event, date=item.date).first()
            if date_price_obj and date_price_obj.price is not None:
              price = date_price_obj.price
            elif event.available_dates.exists():
              # Fallback: first available date price if exact date not found
              first_date = event.available_dates.first()
              if first_date and first_date.price is not None:
                price = first_date.price

          total_price = price * item.quantity

          items.append({
            "id": item.id,
            "title": event.title if event else "",
            "title_ar": event.title_ar if event else "",
            "type": "event",
            "quantity": item.quantity,
            "price": price,
            "total_price": total_price,
            "is_paid": item.is_paid,
        })

        # Services
        service_qs = obj.services.filter(is_extra=is_extra)
        if is_supplier:
            service_qs = service_qs.filter(service__supplier=user)
        for item in service_qs:
            service = item.service
            price = service.price or Decimal("0.00")
            total_price = price * item.quantity
            items.append({
                "id": item.id,
                "title": service.title if service else "",
                "title_ar": service.title_ar if service else "",
                "type": "service",
                "quantity": item.quantity,
                "price": price,
                "total_price": total_price,
                "is_paid": item.is_paid,
            })

        # Special Items (admin only)
        if not is_supplier:
            for item in obj.special_items.filter(is_extra=is_extra):
                special_item = item.item
                price = special_item.price or Decimal("0.00")
                total_price = price * item.quantity
                items.append({
                    "id": item.id,
                    "title": special_item.title if special_item else "",
                    "title_ar": special_item.title_ar if special_item else "",
                    "type": "special_item",
                    "quantity": item.quantity,
                    "price": price,
                    "total_price": total_price,
                    "is_paid": item.is_paid,
                })

            # Dates / Huts
            for booking_date in obj.dates.filter(is_extra=is_extra):
                hut_date = AvailableDateRanges.objects.filter(
                    huts=obj.hut,
                    date_from__lte=booking_date.date_to,
                    date_to__gte=booking_date.date_from
                ).first()
                # print(hut_date.price,'dattte hutt')
                nights = (booking_date.date_to - booking_date.date_from).days
                nights = nights if nights > 0 else 1
                price = hut_date.price or Decimal("0.00") if hut_date else Decimal("0.00")
                per_night = price / nights if nights else price
                items.append({
                    "id": booking_date.id,
                    "title": obj.hut.title if obj.hut else "",
                    "title_ar": obj.hut.title_ar if obj.hut else "",
                    "type": "hut",
                    "quantity": nights,
                    "price": hut_date.price if hut_date and hut_date.price is not None else Decimal("0.00"),
                    "total_price": price*nights,
                    "is_paid": booking_date.is_paid,
                    "date_from": booking_date.date_from,
                    "date_to": booking_date.date_to,
                })

        return BookingOrderItemSerializer(items, many=True).data







class BookingUpcominAdminSerializer(serializers.ModelSerializer):
    user = MiniUserSerializer(read_only=True)
    hut_title = serializers.CharField(source='hut.title', read_only=True)
    hut_title_ar = serializers.CharField(source='hut.title_ar', read_only=True)
    
    
    date = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',  'user', 'hut_title','hut_title_ar',
             'date'
        ]

    def get_date(self, obj):
        main_date = obj.dates.filter(is_extra=False).first() or obj.dates.first()
        return BookingDateSerializer(main_date).data if main_date else None
    
    





class QrLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QrLogs
        fields = ['id',  'status', 'created_at']





#for testing payment not real
class BookingPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "status", "is_paid", "paid", "not_paid"]
        read_only_fields = ["id", "status", "is_paid", "paid", "not_paid"]