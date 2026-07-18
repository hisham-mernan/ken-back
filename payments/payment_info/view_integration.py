"""
View layer integration code showing how the services are called.

This file shows the complete view code that integrates with HyperPayService
to handle payment requests from the frontend.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
import uuid
import logging

from .models import PaymentTransaction
from .serializers import CreateCheckoutSerializer, PaymentTransactionSerializer
from .services import HyperPayService

logger = logging.getLogger(__name__)


class CreateCheckoutView(generics.CreateAPIView):
    """
    Create checkout session with HyperPay.
    
    POST /api/payments/create-checkout/
    
    Request Body:
    {
        "booking_id": 123
    }
    
    This view:
    1. Validates the booking exists and belongs to the user
    2. Calculates the payment amount
    3. Prepares customer and billing data
    4. Calls HyperPayService.create_checkout()
    5. Stores transaction in database
    6. Returns checkoutId to frontend
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCheckoutSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        booking_id = validated_data.get('booking_id')
        
        # Fetch booking from database
        from products.models import Booking
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify booking belongs to the authenticated user
        if booking.user != request.user:
            return Response(
                {'error': 'You do not have permission to pay for this booking.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate payment amount (recalculate if needed)
        if booking.total_price is None or booking.total_price <= 0:
            # Recalculate booking total
            total = Decimal("0.00")
            # ... (calculation logic)
            booking.total_price = total
            booking.save()
        
        # Get unpaid amount
        amount = booking.not_paid if booking.not_paid > Decimal("0.00") else booking.total_price
        
        if amount <= Decimal("0.00"):
            return Response(
                {'error': 'Invalid booking amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount_formatted = f"{amount:.2f}"
        
        # Get customer information from booking user
        user = booking.user
        customer_email = user.email
        customer_name = user.full_name or ''
        
        # Split name into given name and surname
        name_parts = customer_name.split(' ', 1) if customer_name else ['', '']
        customer_given_name = name_parts[0].strip() if name_parts[0].strip() else 'Customer'
        customer_surname = name_parts[1].strip() if len(name_parts) > 1 and name_parts[1].strip() else 'Name'
        
        # Prepare billing address
        billing_address = user.address or ''
        address_parts = billing_address.split(',') if billing_address else []
        
        # Generate merchant transaction ID
        merchant_transaction_id = f"TXN_{uuid.uuid4().hex[:16].upper()}"
        
        # Prepare data for HyperPay service
        checkout_data = {
            'amount': amount_formatted,
            'currency': 'SAR',
            'merchantTransactionId': merchant_transaction_id,
            'customer_email': customer_email,
            'customer_givenName': customer_given_name,
            'customer_surname': customer_surname,
            'billing_street1': address_parts[0].strip() if len(address_parts) >= 1 else 'Not Provided',
            'billing_city': address_parts[1].strip() if len(address_parts) >= 2 else 'Riyadh',
            'billing_state': address_parts[3].strip() if len(address_parts) >= 4 else 'Riyadh',
            'billing_country': 'SA',  # Default to Saudi Arabia
            'billing_postcode': address_parts[4].strip() if len(address_parts) >= 5 else '11564',
        }
        
        # Create checkout session with HyperPay
        try:
            result = HyperPayService.create_checkout(checkout_data)
        except ValueError as e:
            logger.error(f"Checkout creation validation error: {str(e)}")
            return Response(
                {
                    'error': 'Invalid payment data',
                    'details': str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not result.get('success'):
            logger.error(f"Checkout creation failed: {result.get('error')}")
            error_response = {
                'error': 'Failed to create checkout session',
                'details': result.get('error'),
            }
            
            # Include raw response in error for debugging
            if 'raw_response' in result:
                error_response['hyperpay_response'] = result.get('raw_response')
            if 'response' in result:
                error_response['parsed_response'] = result.get('response')
            if 'response_status' in result:
                error_response['http_status'] = result.get('response_status')
                
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        checkout_id = result.get('checkout_id')
        if not checkout_id:
            error_response = {
                'error': 'No checkout ID received from payment gateway',
                'details': result.get('error', 'Unknown error'),
            }
            
            if 'raw_response' in result:
                error_response['hyperpay_response'] = result.get('raw_response')
            if 'response' in result:
                error_response['parsed_response'] = result.get('response')
                
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Store transaction in database
        payment_transaction = PaymentTransaction.objects.create(
            user=request.user,
            checkout_id=checkout_id,
            merchant_transaction_id=merchant_transaction_id,
            amount=amount,
            currency='SAR',
            status='pending',
            booking_id=booking_id,
            hyperpay_response=result.get('response', {}),
        )
        
        # Get payment widget URL for frontend
        base_url = HyperPayService.get_base_url()
        payment_widget_url = f"{base_url}/v1/paymentWidgets.js?checkoutId={checkout_id}"
        
        # Return response to frontend
        return Response(
            {
                'success': True,
                'checkout_id': checkout_id,
                'merchant_transaction_id': merchant_transaction_id,
                'id': checkout_id,
                'transaction_id': str(payment_transaction.id),
                'payment_widget_url': payment_widget_url,
            },
            status=status.HTTP_201_CREATED
        )


class VerifyPaymentView(generics.GenericAPIView):
    """
    Verify payment status with HyperPay.
    
    GET /api/payments/verify-payment/?resourcePath=/v1/checkouts/{checkoutId}/payment
    
    This view:
    1. Receives resourcePath from frontend (provided by HyperPay after payment)
    2. Calls HyperPayService.verify_payment(resource_path)
    3. Processes payment verification response
    4. Updates payment transaction in database
    5. Updates booking status if payment successful
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        resource_path = request.query_params.get('resourcePath')
        
        if not resource_path:
            return Response(
                {'error': 'resourcePath query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify payment with HyperPay
        result = HyperPayService.verify_payment(resource_path)
        
        if not result.get('success'):
            logger.error(f"Payment verification failed: {result.get('error')}")
            return Response(
                {
                    'error': 'Failed to verify payment',
                    'details': result.get('error'),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        verification_data = result.get('data', {})
        
        # Extract payment details from HyperPay response
        checkout_id = verification_data.get('id')
        result_code = verification_data.get('result', {}).get('code') if isinstance(verification_data.get('result'), dict) else None
        amount = verification_data.get('amount')
        currency = verification_data.get('currency')
        merchant_transaction_id = verification_data.get('merchantTransactionId')
        
        # Determine payment status based on result code
        payment_status = 'pending'
        if result_code:
            if result_code.startswith('000.000.000') or result_code.startswith('000.100.110'):
                payment_status = 'success'
            elif result_code.startswith('000.400'):
                payment_status = 'failed'
            else:
                payment_status = 'failed'
        
        # Find or update payment transaction
        payment_transaction = None
        if checkout_id:
            try:
                payment_transaction = PaymentTransaction.objects.get(checkout_id=checkout_id)
            except PaymentTransaction.DoesNotExist:
                pass
        
        if not payment_transaction and merchant_transaction_id:
            try:
                payment_transaction = PaymentTransaction.objects.get(
                    merchant_transaction_id=merchant_transaction_id
                )
            except PaymentTransaction.DoesNotExist:
                pass
        
        # Create or update transaction
        if not payment_transaction:
            amount_decimal = Decimal(str(amount)) if amount else Decimal('0')
            payment_transaction = PaymentTransaction.objects.create(
                user=request.user,
                checkout_id=checkout_id,
                merchant_transaction_id=merchant_transaction_id or f"TXN_{uuid.uuid4().hex[:16].upper()}",
                amount=amount_decimal,
                currency=currency or 'SAR',
                status=payment_status,
                resource_path=resource_path,
                hyperpay_response=verification_data,
            )
        else:
            payment_transaction.status = payment_status
            payment_transaction.resource_path = resource_path
            payment_transaction.hyperpay_response = verification_data
            payment_transaction.verified_at = timezone.now()
            payment_transaction.save()
        
        # Update booking status if payment successful
        if payment_transaction.booking_id and payment_status == 'success':
            from products.models import Booking
            try:
                booking = Booking.objects.get(id=payment_transaction.booking_id)
                booking.status = 'paid'
                booking.is_paid = True
                if payment_transaction.amount:
                    booking.paid = payment_transaction.amount
                    booking.not_paid = booking.total_price - payment_transaction.amount
                booking.save()
            except Booking.DoesNotExist:
                logger.warning(f"Booking {payment_transaction.booking_id} not found")
        
        # Return verification response
        return Response(
            {
                'success': payment_status == 'success',
                'status': payment_status,
                'transaction': PaymentTransactionSerializer(payment_transaction).data,
                'verification_data': verification_data,
            },
            status=status.HTTP_200_OK
        )

