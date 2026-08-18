"""
HyperPay payment gateway API views.
Backend-only integration following the guide specifications.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from decimal import Decimal
import uuid
import logging

from .models import PaymentTransaction
from .serializers import CreateCheckoutSerializer, PaymentTransactionSerializer
from .services import HyperPayService

logger = logging.getLogger(__name__)

# Share of the total taken when a guest chooses to pay part now.
DEPOSIT_FRACTION = Decimal("0.5")


class CreateCheckoutView(generics.CreateAPIView):
    """
    Create checkout session with HyperPay.
    
    POST /api/payments/create-checkout/
    
    Creates a checkout session via server-to-server request to HyperPay.
    Returns checkoutId for frontend widget integration.
    """
    # Open, because a guest has no account to authenticate with. Ownership is
    # then checked explicitly in create(): the account for a normal booking, or
    # the booking's access token for a guest one.
    permission_classes = [AllowAny]
    serializer_class = CreateCheckoutSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        booking_id = validated_data.get('booking_id')
        
        # Fetch booking from database
        from products.models import (
            Booking,
            BookingDate,
            EventTicket,
            ServiceTicket,
            SpecialItemTicket,
            AvailableDateEvent,
        )
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Authorise the payment. A booking that belongs to an account is only
        # payable by that account. A guest booking has no account, so its own
        # access token is the credential -- compared in full, and only ever
        # accepted for guest bookings, so a leaked token cannot unlock someone
        # else's record.
        if booking.user_id:
            if not request.user.is_authenticated or booking.user_id != request.user.id:
                return Response(
                    {'error': 'You do not have permission to pay for this booking.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            from products.utils import booking_token_matches
            if not booking_token_matches(request.data.get('access_token'), booking.access_token):
                return Response(
                    {'error': 'You do not have permission to pay for this booking.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Recalculate booking totals on demand if they are zero
        # Prices are stored primarily on BookingDate.total_price and tickets,
        # so bookings created before the new pricing flow may have total_price=0.
        if booking.total_price is None or booking.total_price <= 0:
            total = Decimal("0.00")

            # Hut price from booking dates (BookingDate.total_price already holds full range price)
            for bd in booking.dates.all():
                if bd.total_price:
                    total += Decimal(bd.total_price)

            # Events: use AvailableDateEvent price * quantity
            for et in booking.events.all():
                available_date = AvailableDateEvent.objects.filter(date=et.date).first()
                price = Decimal(available_date.price if available_date and available_date.price is not None else 0)
                total += price * et.quantity

            # Services: use service.price * quantity
            for st in booking.services.all():
                price = Decimal(st.service.price or 0)
                total += price * st.quantity

            # Special items: item.price * quantity
            for sit in booking.special_items.all():
                price = Decimal(sit.item.price or 0)
                total += price * sit.quantity

            # Apply promo code if present
            if booking.promocode and booking.promocode.percentage:
                percentage = Decimal(booking.promocode.percentage)
                discount = (percentage / Decimal("100")) * total
                discount = min(discount, total)
                total -= discount

            # Persist recalculated totals once so other parts of the system see a correct value
            booking.total_price = total
            # If nothing has been paid yet, the entire amount is not_paid
            if not booking.paid:
                booking.paid = Decimal("0.00")
                booking.not_paid = total
            else:
                # In case of partial payments in future
                booking.not_paid = max(total - Decimal(booking.paid), Decimal("0.00"))
            booking.save(update_fields=["total_price", "paid", "not_paid"])
        
        # Check if HyperPay credentials are configured
        try:
            HyperPayService.get_access_token()
            HyperPayService.get_entity_id()
        except ValueError as e:
            logger.error(f"HyperPay configuration error: {str(e)}")
            return Response(
                {
                    'error': 'Payment gateway configuration error',
                    'details': str(e),
                    'message': 'Please configure OPPWA_ACCESS_TOKEN and OPPWA_ENTITY_ID in settings'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Generate merchant transaction ID
        merchant_transaction_id = f"TXN_{uuid.uuid4().hex[:16].upper()}"
        
        # Figure out how much is left to pay:
        # - prefer the unpaid balance if it's a positive number
        # - otherwise fall back to the booking total
        if getattr(booking, "not_paid", None) and Decimal(str(booking.not_paid)) > 0:
            amount = Decimal(str(booking.not_paid))
        else:
            amount = Decimal(str(booking.total_price or "0.00"))

        # "Pay 50% now" is only offered on the first payment. Once a deposit
        # has been taken, the remaining balance is always charged in full --
        # otherwise a booking could be part-paid indefinitely in ever smaller
        # instalments.
        if (
            str(request.data.get("payment_option") or "").lower() == "deposit"
            and not Decimal(str(booking.paid or "0.00")) > 0
        ):
            deposit = (amount * DEPOSIT_FRACTION).quantize(Decimal("0.01"))
            if deposit > 0:
                amount = deposit

        amount_formatted = f"{amount:.2f}"
        
        # Customer details come from the account when there is one, and from
        # the guest_* fields collected at checkout when there is not.
        user = booking.user
        customer_email = booking.contact_email or ''
        customer_name = booking.contact_name or ''
        
        # Split full_name into given name and surname
        # Ensure both are provided (mandatory fields)
        name_parts = customer_name.split(' ', 1) if customer_name else ['', '']
        customer_given_name = name_parts[0].strip() if len(name_parts) > 0 and name_parts[0].strip() else 'Customer'
        customer_surname = name_parts[1].strip() if len(name_parts) > 1 and name_parts[1].strip() else 'Name'
        
        # Prepare billing address from user address if available
        billing_address = (user.address if user else '') or ''
        address_parts = billing_address.split(',') if billing_address else []
        
        # Prepare data for HyperPay service with all mandatory fields
        checkout_data = {
            'amount': amount_formatted,
            'currency': 'SAR',  # Default currency
            'merchantTransactionId': merchant_transaction_id,
            'customer_email': customer_email,
            'customer_givenName': customer_given_name,
            'customer_surname': customer_surname,
        }
        
        # Add billing information (all mandatory fields must be provided)
        # billing.street1 (mandatory)
        if len(address_parts) >= 1 and address_parts[0].strip():
            checkout_data['billing_street1'] = address_parts[0].strip()
        else:
            checkout_data['billing_street1'] = 'Not Provided'  # Default if not available
        
        # billing.city (mandatory)
        if len(address_parts) >= 2 and address_parts[1].strip():
            checkout_data['billing_city'] = address_parts[1].strip()
        else:
            checkout_data['billing_city'] = 'Riyadh'  # Default to Riyadh if not available
        
        # billing.state (mandatory)
        if len(address_parts) >= 4 and address_parts[3].strip():
            checkout_data['billing_state'] = address_parts[3].strip()
        else:
            checkout_data['billing_state'] = 'Riyadh'  # Default state for Saudi Arabia
        
        # billing.country (mandatory) - must be Alpha-2 code (2 letters)
        if len(address_parts) >= 3:
            country_code = address_parts[2].strip()[:2].upper()
            if len(country_code) == 2 and country_code.isalpha():
                checkout_data['billing_country'] = country_code
            else:
                checkout_data['billing_country'] = 'SA'  # Default to Saudi Arabia
        else:
            checkout_data['billing_country'] = 'SA'  # Default to Saudi Arabia
        
        # billing.postcode (mandatory)
        if len(address_parts) >= 5 and address_parts[4].strip():
            checkout_data['billing_postcode'] = address_parts[4].strip()
        else:
            checkout_data['billing_postcode'] = '11564'  # Default postcode for Saudi Arabia
        
        # Create checkout session with HyperPay
        try:
            result = HyperPayService.create_checkout(checkout_data)
        except ValueError as e:
            # Handle missing mandatory fields
            logger.error(f"Checkout creation validation error: {str(e)}")
            return Response(
                {
                    'error': 'Invalid payment data',
                    'details': str(e),
                    'message': 'Missing required fields for payment transaction'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not result.get('success'):
            logger.error(f"Checkout creation failed: {result.get('error')}")
            error_response = {
                'error': 'Failed to create checkout session',
                'details': result.get('error'),
            }
            
            # Include raw response in error for debugging if available
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
            
            # Include full response for debugging
            if 'raw_response' in result:
                error_response['hyperpay_response'] = result.get('raw_response')
            if 'response' in result:
                error_response['parsed_response'] = result.get('response')
                
            logger.error(f"No checkout ID found. Full result: {result}")
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Store transaction in database. A guest checkout has no account, so
        # the transaction is linked to the booking alone.
        payment_transaction = PaymentTransaction.objects.create(
            user=request.user if request.user.is_authenticated else None,
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
        
        # Return response including checkout ID and widget URL for frontend
        return Response(
            {
                'success': True,
                'checkout_id': checkout_id,
                'merchant_transaction_id': merchant_transaction_id,
                'id': checkout_id,  # For compatibility with frontend expectations
                'transaction_id': str(payment_transaction.id),
                'payment_widget_url': payment_widget_url,  # URL for loading paymentWidgets.js
            },
            status=status.HTTP_201_CREATED
        )


class VerifyPaymentView(generics.GenericAPIView):
    """
    Verify payment status with HyperPay.
    
    GET /api/payments/verify-payment/?resourcePath=...
    
    Verifies payment using resourcePath from HyperPay redirect.
    Updates payment status in database.
    """
    # HyperPay redirects the payer back here, and a guest carries no token on
    # that hop. The resourcePath issued by HyperPay is the credential: it is
    # unguessable and is verified server-to-server against them before
    # anything is marked paid.
    permission_classes = [AllowAny]
    
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
        # HyperPay response format may vary, but typically includes:
        # id, result, amount, currency, paymentType, etc.
        checkout_id = verification_data.get('id')
        
        # Extract result code - handle different response formats
        result_code = None
        result_obj = verification_data.get('result')
        
        if isinstance(result_obj, dict):
            # Result is a dict with 'code' key
            result_code = result_obj.get('code')
        elif isinstance(result_obj, str):
            # Result is a string (e.g., "000.000.000")
            result_code = result_obj
        elif result_obj is not None:
            # Try to convert to string
            result_code = str(result_obj)
        
        # Also check if code is at top level
        if not result_code:
            result_code = verification_data.get('code')
        
        amount = verification_data.get('amount')
        currency = verification_data.get('currency')
        merchant_transaction_id = verification_data.get('merchantTransactionId')
        
        # Log the result code for debugging
        logger.info(f"HyperPay verification result_code: {result_code}, result_obj type: {type(result_obj)}, result_obj: {result_obj}")
        
        # Determine payment status based on result code
        # HyperPay result codes: 000.000.000 = success
        payment_status = 'pending'
        if result_code:
            result_code_str = str(result_code)
            if result_code_str.startswith('000.000.000') or result_code_str.startswith('000.100.110'):
                payment_status = 'success'
            elif result_code_str.startswith('000.400'):
                payment_status = 'failed'
            elif result_code_str.startswith('000'):
                # Any other 000 code might be success, but be cautious
                # Check for known success patterns
                if any(pattern in result_code_str for pattern in ['000.000', '000.100']):
                    payment_status = 'success'
                else:
                    payment_status = 'failed'
            else:
                payment_status = 'failed'
        else:
            # No result code found - try to determine from other indicators
            logger.warning(f"No result code found in HyperPay response. Verification data keys: {list(verification_data.keys())}")
            
            # Fallback: Check if payment appears successful based on other fields
            # If we have card info and the resourcePath indicates payment was processed, assume success
            has_card_info = 'card' in verification_data and verification_data.get('card')
            has_payment_brand = 'paymentBrand' in verification_data and verification_data.get('paymentBrand')
            resource_path_has_payment = resource_path and '/payment' in resource_path
            
            # If we have card info and payment brand, and resourcePath includes /payment,
            # it likely means payment was processed (even if result code is missing)
            if has_card_info or (has_payment_brand and resource_path_has_payment):
                logger.info(
                    f"Payment appears successful based on card/paymentBrand presence. "
                    f"Card: {has_card_info}, PaymentBrand: {has_payment_brand}, ResourcePath: {resource_path}"
                )
                # Be cautious - only mark as success if we're confident
                # Check if amount matches and we have transaction details
                if amount and verification_data.get('id'):
                    payment_status = 'success'
                    logger.info(f"Marking payment as success based on presence of card/paymentBrand and transaction details")
                else:
                    logger.warning(f"Payment indicators present but missing amount or transaction ID - keeping as pending")
        
        # Find or create payment transaction
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
        
        # If transaction not found, create a new one
        if not payment_transaction:
            # Convert amount to Decimal (handle string, float, or Decimal)
            amount_decimal = Decimal(str(amount)) if amount else Decimal('0')
            
            # Try to find booking_id from user's recent pending bookings with matching amount
            # This is a fallback in case the transaction wasn't found
            booking_id = None
            if request.user.is_authenticated and amount_decimal > 0:
                from products.models import Booking
                try:
                    # Find a booking with matching unpaid amount
                    matching_booking = Booking.objects.filter(
                        user=request.user,
                        status__in=['pending', 'confirmed', 'partially_paid'],
                        not_paid=amount_decimal
                    ).order_by('-created_at').first()
                    
                    if matching_booking:
                        booking_id = matching_booking.id
                        logger.info(f"Found matching booking {booking_id} for transaction verification")
                except Exception as e:
                    logger.warning(f"Failed to find booking by amount: {str(e)}")
            
            payment_transaction = PaymentTransaction.objects.create(
                user=request.user if request.user.is_authenticated else None,
                checkout_id=checkout_id,
                merchant_transaction_id=merchant_transaction_id or f"TXN_{uuid.uuid4().hex[:16].upper()}",
                amount=amount_decimal,
                currency=currency or 'SAR',
                status=payment_status,
                resource_path=resource_path,
                hyperpay_response=verification_data,
                booking_id=booking_id,  # Set booking_id if found
            )
            
            if not booking_id:
                logger.warning(
                    f"Created new payment transaction {payment_transaction.id} without booking_id. "
                    f"Checkout ID: {checkout_id}, Merchant TXN ID: {merchant_transaction_id}"
                )
        else:
            # Update existing transaction
            payment_transaction.status = payment_status
            payment_transaction.resource_path = resource_path
            payment_transaction.hyperpay_response = verification_data
            payment_transaction.verified_at = timezone.now()
            
            # Validate amount and currency match
            if amount:
                expected_amount = Decimal(str(amount))  # Convert to Decimal for comparison
                if abs(payment_transaction.amount - expected_amount) > Decimal('0.01'):
                    logger.warning(
                        f"Amount mismatch for transaction {payment_transaction.merchant_transaction_id}: "
                        f"expected {expected_amount}, stored {payment_transaction.amount}"
                    )
            
            if currency and payment_transaction.currency != currency:
                logger.warning(
                    f"Currency mismatch for transaction {payment_transaction.merchant_transaction_id}: "
                    f"expected {currency}, stored {payment_transaction.currency}"
                )
            
            payment_transaction.save()
        
        # Update booking status to paid if payment is successful
        logger.info(
            f"Payment verification result: status={payment_status}, "
            f"transaction_id={payment_transaction.id}, "
            f"booking_id={payment_transaction.booking_id}, "
            f"amount={payment_transaction.amount}"
        )
        
        if payment_transaction.booking_id and payment_status == 'success':
            from products.models import Booking
            from products.utils import generate_qr_code_image
            try:
                booking = Booking.objects.get(id=payment_transaction.booking_id)
                logger.info(f"Found booking {booking.id} for payment update. Current status: {booking.status}")
                
                # Calculate payment amounts
                payment_amount = payment_transaction.amount or Decimal('0.00')
                total_price = booking.total_price or Decimal('0.00')
                not_paid = booking.not_paid or Decimal('0.00')
                
                # Check if this payment covers the remaining amount (or full amount)
                is_full_payment = (payment_amount >= not_paid and not_paid > 0) or (payment_amount >= total_price and total_price > 0)
                
                if is_full_payment:
                    # Full payment - mark as paid
                    booking.status = 'paid'
                    booking.is_paid = True
                    booking.paid = total_price  # Ensure paid equals total_price
                    booking.not_paid = Decimal('0.00')
                    
                    # Generate QR code immediately if not already generated
                    if not booking.is_qr_genereated or not booking.qr_code_image:
                        try:
                            qr_data = str(booking.id)
                            qr_image = generate_qr_code_image(qr_data)
                            booking.qr_code = qr_data
                            booking.qr_code_image.save(f"booking_{booking.id}_qr.png", qr_image, save=False)
                            booking.is_qr_genereated = True
                            logger.info(f"QR code generated for booking {booking.id}")
                        except Exception as qr_error:
                            logger.error(f"Failed to generate QR code for booking {booking.id}: {str(qr_error)}")
                    
                    logger.info(f"Booking {booking.id} marked as fully paid after payment verification")
                else:
                    # Partial payment - update amounts but don't mark as fully paid
                    new_paid = (booking.paid or Decimal('0.00')) + payment_amount
                    new_not_paid = max(total_price - new_paid, Decimal('0.00'))
                    booking.paid = new_paid
                    booking.not_paid = new_not_paid
                    # A deposit holds the dates but must not look like an
                    # unpaid confirmed booking: the 30-minute sweep cancels
                    # those, which would wipe out a booking that just paid.
                    if booking.status in ('pending', 'confirmed'):
                        booking.status = 'partially_paid'
                    logger.info(f"Booking {booking.id} received partial payment: {payment_amount} of {not_paid} remaining")
                
                booking.save()
                logger.info(
                    f"✅ Booking {booking.id} updated successfully: "
                    f"status={booking.status}, paid={booking.paid}, not_paid={booking.not_paid}, "
                    f"is_paid={booking.is_paid}, qr_generated={booking.is_qr_genereated}"
                )
            except Booking.DoesNotExist:
                logger.error(f"❌ Booking {payment_transaction.booking_id} not found when trying to update payment status")
        elif payment_status == 'success' and not payment_transaction.booking_id:
            logger.error(
                f"❌ Payment successful but booking_id is None. "
                f"Transaction ID: {payment_transaction.id}, "
                f"Checkout ID: {payment_transaction.checkout_id}, "
                f"Merchant TXN ID: {payment_transaction.merchant_transaction_id}"
            )
        elif payment_transaction.booking_id and payment_status != 'success':
            logger.warning(
                f"⚠️  Payment status is '{payment_status}' (not 'success') for booking {payment_transaction.booking_id}. "
                f"Result code: {verification_data.get('result', {}).get('code') if isinstance(verification_data.get('result'), dict) else 'N/A'}"
            )
        
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

