from django.db import models
from accounts.models import User
import uuid


class PaymentTransaction(models.Model):
    """
    Model to store payment transaction details from HyperPay.
    Stores merchantTransactionId, checkoutId, amount, currency for verification.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_transactions')
    
    # HyperPay identifiers
    checkout_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="Checkout ID from HyperPay")
    merchant_transaction_id = models.CharField(max_length=255, unique=True, db_index=True, help_text="Unique transaction ID for this payment")
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Payment amount")
    currency = models.CharField(max_length=3, default='SAR', help_text="Payment currency")
    
    # Payment status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # HyperPay response data
    resource_path = models.TextField(null=True, blank=True, help_text="Resource path from HyperPay redirect")
    hyperpay_response = models.JSONField(null=True, blank=True, help_text="Full response from HyperPay")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When payment was verified")
    
    # Optional: Link to booking/order if applicable
    booking_id = models.IntegerField(null=True, blank=True, help_text="Related booking ID if applicable")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant_transaction_id']),
            models.Index(fields=['checkout_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment {self.merchant_transaction_id} - {self.status} - {self.amount} {self.currency}"

