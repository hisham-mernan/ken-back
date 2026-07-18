from django.urls import path
from .views import CreateCheckoutView, VerifyPaymentView

urlpatterns = [
    path('create-checkout/', CreateCheckoutView.as_view(), name='create-checkout'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
]

