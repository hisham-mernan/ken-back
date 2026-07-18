from django.urls import path
from .views import *

urlpatterns = [
    # Story
    path('story/', StoryListCreateAPIView.as_view(), name='story-list-create'),
    path('story/<int:pk>/', StoryDetailAPIView.as_view(), name='story-detail'),

   
    path('faq/', FAQListCreateAPIView.as_view(), name='faq-list-create'),
    path('faq/<int:pk>/', FAQDetailAPIView.as_view(), name='faq-detail'),
    
    path('about-us/', AboutUsListCreateAPIView.as_view(), name='aboutus-list-create'),
    path('about-us/details/', AboutUsRetrieveUpdateAPIView.as_view(), name='aboutus-list-create'),
    
    
    
   
    path('terms-condations/', TermsAndCondationCreateAPIView.as_view()),
    path('terms-condation/<int:pk>/',  TermsAndCondationDetailAPIView.as_view(), ),
    
    path("ken/review/", WebStoreRatingCreateView.as_view(), name="store-rate"),
    path("ken/avg-rate/", MostRecentWebStoreAvgRateView.as_view(), name="store-latest-avg-rate"),
    
    
    path('our-service/', OurServiceListCreateView.as_view(), name='our-service-list-create'),
    path('our-service/<int:pk>/', OurServiceRetrieveUpdateDeleteView.as_view(), name='our-service-detail'),

    # SpecailAboutUs
    path('special-about-us/', SpecailAboutUsListCreateView.as_view(), name='special-about-us-list-create'),
    path('special-about-us/<int:pk>/', SpecailAboutUsRetrieveUpdateDeleteView.as_view(), name='special-about-us-detail'),


path('terms-titles/', TermsAndCindationsTitleListCreateView.as_view(), name='terms-title-list-create'),
path('terms-titles/details/', TermsAndCindationsTitleDetailView.as_view(), name='terms-title-detail'),

]


    



