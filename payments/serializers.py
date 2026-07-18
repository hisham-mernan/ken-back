from rest_framework import serializers
from .models import PaymentTransaction


class CreateCheckoutSerializer(serializers.Serializer):
    """
    Serializer for creating checkout session.
    Only requires booking_id - all other data is fetched from the booking.
    """
    booking_id = serializers.IntegerField(
        required=True,
        help_text="Booking ID to create payment for"
    )
    
    def validate_booking_id(self, value):
        """Validate that booking exists and belongs to the user."""
        from products.models import Booking
        
        try:
            booking = Booking.objects.get(id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")
        
        return value


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentTransaction model.
    Used for displaying transaction details.
    """
    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'checkout_id',
            'merchant_transaction_id',
            'amount',
            'currency',
            'status',
            'created_at',
            'updated_at',
            'verified_at',
            'booking_id',
        ]
        read_only_fields = [
            'id',
            'checkout_id',
            'merchant_transaction_id',
            'status',
            'created_at',
            'updated_at',
            'verified_at',
        ]

