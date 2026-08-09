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






class TermsAndCondationCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminForUnsafeMethods] 
    
    queryset = TermsAndCindations.objects.all().order_by('-id')
    serializer_class = TermsAndCindationsSerializer

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
            return Response({"detail": []}, status=status.HTTP_200_OK)
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