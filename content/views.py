from rest_framework import generics
from .models import *
from .serializers import*
from accounts.permissions import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework.views import APIView
from django.core.cache import cache

# ----- Story Views -----
class StoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = Story.objects.all().order_by('-id')
    serializer_class = StorySerializer

class StoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = Story.objects.all()
    serializer_class = StorySerializer

# ----- Our Vision -----

class FAQListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = FAQ.objects.all().order_by('-id')
    serializer_class = FAQSerializer

    def list(self, request, *args, **kwargs):
        cache_key = "content_faq_list"
        cached = cache.get(cache_key)
        if cached is not None:
            res = Response(cached)
        else:
            res = super().list(request, *args, **kwargs)
            cache.set(cache_key, res.data, 1800)
        res['Cache-Control'] = 'public, max-age=120, s-maxage=600, stale-while-revalidate=1200'
        return res

class FAQDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    
    
    
    
    
# class AboutUsListCreateAPIView(generics.ListCreateAPIView):
#     permission_classes = [IsAdminForUnsafeMethods]
#     serializer_class = AboutUsSerializer

#     def get_queryset(self):
#         return AboutUs.objects.order_by('-created_at')[:1]


# from rest_framework import status
# from rest_framework.response import Response

# class AboutUsRetrieveUpdateAPIView(generics.RetrieveUpdateDestroyAPIView):
#     permission_classes = [IsAdmin]
#     serializer_class = AboutUsSerializer

#     def get_object(self):
#         obj = AboutUs.objects.order_by('-created_at').first()
#         return obj  # can be None if no object

#     def get(self, request, *args, **kwargs):
#         obj = self.get_object()
#         if not obj:
#             return Response({"detail": "No AboutUs object found."}, status=status.HTTP_404_NOT_FOUND)
#         serializer = self.get_serializer(obj)
#         return Response(serializer.data)

#     def put(self, request, *args, **kwargs):
#         obj = self.get_object()
#         if not obj:
#             return Response({"detail": "No AboutUs object found."}, status=status.HTTP_404_NOT_FOUND)
#         serializer = self.get_serializer(obj, data=request.data, partial=False)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)

#     def patch(self, request, *args, **kwargs):
#         obj = self.get_object()
#         if not obj:
#             return Response({"detail": "No AboutUs object found."}, status=status.HTTP_404_NOT_FOUND)
#         serializer = self.get_serializer(obj, data=request.data, partial=True)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)

#     def delete(self, request, *args, **kwargs):
#         obj = self.get_object()
#         if not obj:
#             return Response({"detail": "No AboutUs object found."}, status=status.HTTP_404_NOT_FOUND)
#         obj.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)

    




from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

class AboutUsListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods]
    serializer_class = AboutUsSerializer

    def get_queryset(self):
        return AboutUs.objects.order_by('-created_at')[:1]

    def list(self, request, *args, **kwargs):
        cache_key = "content_about_us_list"
        cached = cache.get(cache_key)
        if cached is not None:
            res = Response(cached)
        else:
            res = super().list(request, *args, **kwargs)
            cache.set(cache_key, res.data, 1800)
        res['Cache-Control'] = 'public, max-age=120, s-maxage=600, stale-while-revalidate=1200'
        return res

    def create(self, request, *args, **kwargs):
        if AboutUs.objects.exists():
            return Response(
                {"detail": "An AboutUs object already exists. You can update it but cannot create another."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)


class AboutUsRetrieveUpdateAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AboutUsSerializer

    def get_object(self):
        obj = AboutUs.objects.order_by('-created_at').first()
        if not obj:
            raise ValidationError("No AboutUs object found.")
        return obj

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class OurServiceListCreateView(generics.ListCreateAPIView):
    queryset = OurService.objects.all()
    serializer_class = OurServiceSerializer
    permission_classes = [IsAdminForUnsafeMethods]

class OurServiceRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OurService.objects.all()
    serializer_class = OurServiceSerializer
    permission_classes = [IsAdmin]


# SPECIAL ABOUT US views
class SpecailAboutUsListCreateView(generics.ListCreateAPIView):
    queryset = SpecailAboutUs.objects.all()
    serializer_class = SpecailAboutUsSerializer
    permission_classes = [IsAdminForUnsafeMethods]

class SpecailAboutUsRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SpecailAboutUs.objects.all()
    serializer_class = SpecailAboutUsSerializer
    permission_classes = [IsAdmin]






def seed_terms_data():
    if not TermsAndCindationsTitle.objects.exists():
        TermsAndCindationsTitle.objects.create(
            title="General Terms and Conditions for Booking Ken Huts",
            title_ar="الشروط والأحكام العامة لحجز أكواخ كِن"
        )
    
    if not TermsAndCindations.objects.exists():
        terms_items = [
            (
                "Guest Responsibility for Damages and Losses",
                "مسؤولية الضيف عن التلفيات والخسائر",
                "The guest assumes full responsibility for any material damages or losses occurring inside the hut or its facilities during the stay, whether intentional or resulting from misuse or negligence. In the event of property damage, Ken Huts management reserves the right to claim appropriate compensation based on repair or replacement costs. If payment is refused, management reserves the right to take legal action through competent authorities.",
                "يتحمل الضيف كامل المسؤولية عن أي تلفيات أو خسائر مادية تحدث داخل الكوخ أو في مرافقه أثناء فترة الإقامة، سواء كانت متعمدة أو ناتجة عن سوء استخدام أو إهمال. في حال حدوث أي ضرر بالممتلكات، يحق لإدارة أكواخ كن المطالبة بالتعويض المناسب وفقاً لتكلفة الإصلاح أو الاستبدال. في حال رفض سداد التعويض، يحق للإدارة اتخاذ الإجراءات النظامية اللازمة عبر الجهات المختصة."
            ),
            (
                "Cancellation and Amendment Policy",
                "سياسة الإلغاء والتعديل",
                "Reservations can be cancelled with a full refund within (14) business days if cancelled 24 hours or more before check-in. If cancelled less than 24 hours before check-in, 50% of the total booking amount will be deducted. In case of a no-show without prior notice, the full booking value may be charged.",
                "يمكن إلغاء الحجز مع استرداد كامل المبلغ خلال (14) يوم عمل إذا تم الإلغاء قبل موعد الدخول بـ 24 ساعة أو أكثر. في حال تم الإلغاء قبل موعد الدخول بأقل من 24 ساعة، يتم خصم 50% من إجمالي مبلغ الحجز. في حال عدم الحضور دون إشعار مسبق، قد يتم احتساب قيمة الحجز كاملة."
            ),
            (
                "Adherence to Facility Usage",
                "الالتزام باستخدام المرافق",
                "Using the huts for any illegal activities or actions violating public order and morality is strictly prohibited. Moving furniture or changing electrical appliance locations without prior management approval is forbidden. Guests must maintain cleanliness, use facilities responsibly, and leave the hut in proper condition upon departure.",
                "يُمنع استخدام الأكواخ لأي أنشطة غير مشروعة أو مخالفة للأنظمة والآداب العامة. يُمنع نقل الأثاث أو تغيير مواقع الأجهزة الكهربائية دون موافقة مسبقة من الإدارة. يلتزم الضيوف بالحفاظ على نظافة المكان واستخدام المرافق بشكل مسؤول، وإعادة الكوخ بالحالة المناسبة عند المغادرة."
            ),
            (
                "Guest and Visitor Capacity",
                "عدد الضيوف والزوار",
                "Guests must adhere to the guest capacity specified in the reservation. If welcoming additional visitors is desired, prior coordination and approval from management is required. Management reserves the right to deny entry to any additional visitors exceeding the hut's maximum capacity.",
                "يجب الالتزام بعدد الضيوف المحدد في الحجز. في حال الرغبة باستقبال زوار إضافيين، يجب التنسيق المسبق مع الإدارة وأخذ الموافقة. تحتفظ الإدارة بحق رفض دخول أي عدد إضافي في حال تجاوز الطاقة الاستيعابية للكوخ."
            ),
            (
                "Quiet Hours and Privacy Respect",
                "الالتزام بالهدوء واحترام الخصوصية",
                "At Ken Huts, we strive to provide a quiet, comfortable environment for all guests. Please maintain an appropriate noise level and avoid disturbing others. Respect the privacy of fellow guests and surrounding properties.",
                "نحرص في أكواخ كن على توفير بيئة هادئة ومريحة لجميع الضيوف، لذا نرجو الالتزام بمستوى صوت مناسب وعدم إزعاج الآخرين. يُرجى احترام خصوصية الضيوف الآخرين والممتلكات المحيطة."
            ),
            (
                "Management Rights",
                "أحقية الإدارة",
                "Ken Huts management reserves the right to cancel any reservation if false information is provided or terms are violated. Management also holds the right to terminate a stay in the event of non-compliance with rules or property damage.",
                "تحتفظ إدارة أكواخ كن بالحق في إلغاء أي حجز في حال تقديم معلومات غير صحيحة أو مخالفة الشروط. كما يحق للإدارة إنهاء الإقامة في حال عدم الالتزام بالأنظمة أو الإضرار بالممتلكات."
            ),
            (
                "Personal Belongings Liability",
                "مسؤولية الممتلكات الشخصية",
                "Ken Huts management is not responsible for loss, theft, or damage to personal items inside or outside the huts during the stay. Guests are requested to safeguard their personal belongings.",
                "إدارة أكواخ كن غير مسؤولة عن ضياع أو سرقة أو تلف أي ممتلكات شخصية خاصة بالضيوف داخل الكوخ أو خارجه أثناء فترة الإقامة. نرجو من الجميع المحافظة على أمتعتهم الشخصية."
            )
        ]
        for title_en, title_ar, desc_en, desc_ar in terms_items:
            TermsAndCindations.objects.create(
                title=title_en,
                title_ar=title_ar,
                description=desc_en,
                description_ar=desc_ar
            )


class TermsAndCondationCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    serializer_class = TermsAndCindationsSerializer

    def get_queryset(self):
        if not TermsAndCindations.objects.exists():
            seed_terms_data()
        return TermsAndCindations.objects.all().order_by('id')

class TermsAndCondationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = TermsAndCindations.objects.all()
    serializer_class = TermsAndCindationsSerializer
    
    
    
    
    
class WebStoreRatingCreateView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
   
    queryset = WebStoreRating.objects.all()
    serializer_class = WebStoreRatingSerializer
    

# GET /api/stores/<store_id>/avg-rate/
class MostRecentWebStoreAvgRateView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        latest_store = WebStore.objects.order_by('-created_at').first()

        if latest_store is None:
            # Return a JSON object with avg_rate 0 and dummy id/created_at (optional)
            data = {
                
                "avg_rate": 0,
             
            }
            return Response(data)

        serializer = WebStoreAvgRateSerializer(latest_store)
        return Response(serializer.data)
    






class TermsAndCindationsTitleListCreateView(generics.GenericAPIView):
    permission_classes=[IsAdminForUnsafeMethods]
    serializer_class = TermsAndCindationsTitleSerializer

    def get(self, request, *args, **kwargs):
        last_obj = TermsAndCindationsTitle.objects.last()
        if not last_obj:
            seed_terms_data()
            last_obj = TermsAndCindationsTitle.objects.last()

        if not last_obj:
            last_obj = TermsAndCindationsTitle.objects.create(
                title="General Terms and Conditions for Booking Ken Huts",
                title_ar="الشروط والأحكام العامة لحجز أكواخ كِن"
            )

        serializer = self.get_serializer(last_obj)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class TermsAndCindationsTitleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TermsAndCindationsTitleSerializer
    queryset = TermsAndCindationsTitle.objects.all()

    def get_object(self):
        obj = TermsAndCindationsTitle.objects.last()
        if not obj:
            self.permission_denied(
                self.request, message="No record found"
            )
        return obj