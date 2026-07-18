from django.contrib import admin
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'merchant_transaction_id',
        'checkout_id',
        'user',
        'amount',
        'currency',
        'status',
        'created_at',
        'verified_at',
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['merchant_transaction_id', 'checkout_id', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'verified_at', 'hyperpay_response']
    date_hierarchy = 'created_at'

