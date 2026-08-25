from django.urls import path
from .views import *
from .homepage_views import HomepageDataAPIView

urlpatterns = [
    path('homepage/', HomepageDataAPIView.as_view(), name='homepage-combined'),
    # Hut
    path('huts-home/list/', HutListHomeAPIView.as_view(), name='hut-list-create'),
    path('huts-list/', HutListAPIView.as_view(), name='hut-list-create'),
    path('huts/<int:pk>/',  HutDetailView.as_view(), name='event-detail'),
    
    
    
    

    
    
    path('ken-items/hut/<int:hut_id>/',KenSpecialItemsListByHutIdView.as_view(), name='ken_items_by_hut'),
    
    
    path('events/',  EventListAPIView.as_view(), name='event-list-create'),
    path('events-details/web/<int:id>/',  EventRetrieveWebView.as_view(), name='event-list-create'),
    path('events/random/', RandomEventListAPIView.as_view(), name='random-events'),
   
    path('services/available-dates/<int:service_id>/', ServiceAvailableDatesUpdateView.as_view()),
    path('service-suppliers/list/', SupplierListView.as_view()),
    path('random-services/', RandomServiceListAPIView.as_view(), name='service-detail'),
    
     path('testmonial/',  HutRatingListAPIView.as_view(), name='service-detail'),
     path('rate/<int:booking_id>/', HutRatingCreateView.as_view()),
    
    path('booking/', BookingCreateView.as_view(), name='booking-create'),
    path('booking/update/<int:pk>/', BookingUpdateView.as_view(), name='booking-create'),
    path('booking/cancellation/<int:booking_id>/',CancelBookingView.as_view(), name='booking-create'),
    
    
    
    path('avliable/service/',  AvailableServiceView.as_view()),
    
    path('service-tickets/extra/', ServiceTicketCreateOrUpdateView.as_view(), name='service-ticket-create'),
    
    
     path('bookings/<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    # How a guest reaches their own booking: no account, so the token from the
    # confirmation email stands in for authentication.
    path('bookings/by-token/<uuid:access_token>/', BookingByTokenView.as_view(), name='booking-by-token'),
    path('bookings/<int:booking_id>/invoice.pdf', BookingInvoicePdfView.as_view(), name='booking-invoice-pdf'),
     path('bookings-qr/<int:pk>/',  BookingDetailForAminQrView.as_view(), name='booking-detail'),
     path('booking/paid/<int:pk>/', PaidBookingIfLastConfirmedView.as_view()),
     path('booking/payment-details/<int:pk>/',  PaidBookingIfLastConfirmedDetailsView.as_view()),
 
     path('bookings/upcoming/', UpcomingBookingsView.as_view(), name='upcoming-bookings'),
     path('bookings/past/', PastBookingsView.as_view(), name='past-bookings'),
    
    
    
     path("bookings/<int:booking_id>/add-extra-dates/", AddExtraBookingDateAPIView.as_view()),
     path("bookings-pay/<int:pk>/", BookingMarkPaidView.as_view(), name="booking-mark-paid"),
    # path("verfiy/qr/", AddExtraBookingDateAPIView.as_view()),
    ###########################################################################################
    #admin dashboard
    path("all-booking/",  BookingListView.as_view()),
    path('qr-logs/<int:booking_id>/', QrLogsByBookingView.as_view(), name='qr-logs-by-booking'),
    path('upcoming-admin/', RecentPaidBookingsView.as_view(), name='recent-paid-bookings'),
    path('admin/bookings-details/<int:id>/', BookingDetailsAdminListView.as_view(), name='booking-details-admin-list'),
    path('admin/refuse-cancellation/<int:booking_id>/', RefuseCancellationView.as_view(), name='booking-details-admin-list'),
    path('admin/refund/<int:booking_id>/',   RefundView.as_view(), name='booking-details-admin-list'),
    path('feedback-list/',   HutRatingListAllAPIView.as_view()),
    path('feedback/<int:pk>/', HutRatingDeleteView.as_view(), name='hut-rating-delete'),

    path('huts-details-admin/<int:pk>/',  HutDetailAdminDashBoardView.as_view(), name='event-detail'),
    path("huts/available-dates/<int:hut_id>/", HutDatesPromoUpdateView.as_view()),
    path('huts/', HutCreateView.as_view(), name='hut-list-create'),
    path("huts/admin-list/", HutListAdminAPIView.as_view()),
    path("huts/promocodes/<int:hut_id>/", PromoCodeListCreateView.as_view(), name="hut-promocode-list-create"),
    # Public: the booking form checks a typed code to show the discount before
    # the guest commits. Must stay above the <int:id> route only in spirit --
    # "validate" never matches an int, so ordering is not load-bearing here.
    path("promocodes/validate/", PromoCodeValidateView.as_view(), name="promocode-validate"),
    path("promocodes/<int:id>/", PromoCodeDetailView.as_view(), name="promocode-detail"),
    path('admin/huts/services-activities/<int:hut_id>/', HutServicesActivitiesBulkUpdateAPIView.as_view()),
    path('admin/import-ken-data/', ImportKenDataView.as_view()),
    path('hut-dropdown/', HutDropDownListView.as_view(), name='hut-dropdown'),

    
    
    path('events/available-dates/<int:event_id>/', EventAvailableDatesUpdateView.as_view()),
    path('events/add-list/', EventListCreateView.as_view(), name='hut-dropdown'),
    path('events/<int:id>/', EventRetrieveUpdateView.as_view(), name='event-retrieve-update'),
    path('events/list-dashboard/', EventDashboardListView.as_view(), name='event-retrieve-update'),
    path('events-include/<int:event_id>/', BulkUpdateEventDataAPIView.as_view()),
    
    path('services/', ServiceListCreateAPIView.as_view(), name='service-list-create'),
    path('services/<int:pk>/', ServiceRetrieveUpdateDestroyAPIView.as_view(), name='service-detail'),

    path('ken-items/', KenSpecialItemsListCreateView.as_view(), name='ken-items-list-create'),
    path('ken-items/<int:pk>/', KenSpecialItemsDetailView.as_view(), name='ken-items-detail'),
   
     path('icons/', IconListCreateAPIView.as_view(), name='icon-list-create'),
    
    # Analytics endpoints
    path('analytics/suppliers/', SupplierAnalyticsView.as_view(), name='supplier-analytics'),
    path('analytics/suppliers/<int:supplier_id>/', SupplierAnalyticsView.as_view(), name='supplier-analytics-detail'),
    path('analytics/summary/', AllSuppliersAnalyticsView.as_view(), name='all-suppliers-analytics'),
    path('supplier-analytics/', AdminSupplierAnalyticsAPIView.as_view(), name='supplier-analytics'),
    path('admin/analytics/', AdminAnalyticsView.as_view(), name='admin-analytics'),
    path('admin/revenue-chart/', YearlyRevenueChartAPIView.as_view(), name='monthly-revenue-chart'),
    path('analytics-recent-order/',   MostRecntOrderAnalyticsListView.as_view(), name='monthly-revenue-chart'),
    path('qrlogs-all/', QrLogsListAllView.as_view(), name='qrlogs-list'),

    
]