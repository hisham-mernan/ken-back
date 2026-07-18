from django.urls import path
from .views import *

urlpatterns = [
     
path('register/', UserRegistrationView.as_view(), name='register'),
path('login/', LoginApiView.as_view(), name='login'),
path('verfiy-otp/', VerifyOtpView.as_view(), name='verfy'),
path('resend-otp/', ResendOTPView.as_view(), name='resend'),
path('change-forget-password/', ChangeForgotPassword.as_view(), name='forget pass'),
path('user-info/', UserUpdateView.as_view(), name='user profile'),
path('partners/', PartnerListCreateAPIView.as_view(), name='partner-list-create'),
path('contact-us/', ContactUsListCreateView.as_view(), name='partner-list-create'),

path('supplier-dropdown/', SupplierListView.as_view(), name='partner-list-create'),

# #############################################################
path('user-list/', UserListAdminView.as_view()),

path('add-admin/', AddAdminView.as_view(),),
path('add-guest/', AddGuestView.as_view(),),
path('add-supplier/', AddUpplierView.as_view()),
path('user-details/<int:pk>/', UserDetailInAdminView.as_view()),
path('support/create/', SupportCreateView.as_view(), name='support-create'),
path('support/', SupportListView.as_view(), name='support-list'),
path('support/reply/', SupportReplyView.as_view(), name='support-reply'),
path('support/<int:pk>/', SupportDetailView.as_view(), name='support-detail'),



path('notifcation/', NotificationListView.as_view()),
 path('read-notifications/<int:pk>/',   MarkNotificationAsRead.as_view()),
path('count-notifications/',  GetNotificationCountView.as_view()),
path('notifications/mark-all-read/', MarkAllNotificationsAsRead.as_view(), name='mark-all-notifications-read'),













]
      
    
    
    
    
    
