"""
Debug script to check order payment status and identify issues.

Usage:
    python manage.py shell < debug_order_payment.py
    OR
    python manage.py shell
    >>> exec(open('debug_order_payment.py').read())
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from decimal import Decimal
from products.models import Booking
from payments.models import PaymentTransaction
from django.utils import timezone

def debug_order_payment(order_id):
    """Debug a specific order's payment status."""
    
    print("\n" + "=" * 60)
    print(f"  DEBUGGING ORDER #{order_id}")
    print("=" * 60)
    
    try:
        booking = Booking.objects.get(id=order_id)
    except Booking.DoesNotExist:
        print(f"❌ ERROR: Order {order_id} not found")
        return
    
    print(f"\n📋 ORDER DETAILS:")
    print(f"   ID: {booking.id}")
    print(f"   Status: {booking.status}")
    print(f"   Is Paid: {booking.is_paid}")
    print(f"   Total Price: {booking.total_price}")
    print(f"   Paid: {booking.paid}")
    print(f"   Not Paid: {booking.not_paid}")
    print(f"   QR Code: {booking.qr_code}")
    print(f"   QR Generated: {booking.is_qr_genereated}")
    print(f"   QR Image: {'Yes' if booking.qr_code_image else 'No'}")
    print(f"   Created At: {booking.created_at}")
    
    # Check payment transactions
    print(f"\n💳 PAYMENT TRANSACTIONS:")
    transactions = PaymentTransaction.objects.filter(booking_id=order_id).order_by('-created_at')
    
    if not transactions.exists():
        print("   ❌ No payment transactions found for this order")
        print("   ⚠️  This means payment checkout was never created or booking_id was not set")
        return
    
    for idx, txn in enumerate(transactions, 1):
        print(f"\n   Transaction #{idx}:")
        print(f"   ID: {txn.id}")
        print(f"   Status: {txn.status}")
        print(f"   Amount: {txn.amount}")
        print(f"   Currency: {txn.currency}")
        print(f"   Checkout ID: {txn.checkout_id}")
        print(f"   Merchant TXN ID: {txn.merchant_transaction_id}")
        print(f"   Booking ID: {txn.booking_id}")
        print(f"   Created At: {txn.created_at}")
        print(f"   Verified At: {txn.verified_at}")
        print(f"   Resource Path: {txn.resource_path}")
        
        if txn.hyperpay_response:
            print(f"   HyperPay Response Keys: {list(txn.hyperpay_response.keys())}")
            
            # Show full response for debugging (truncated if too long)
            import json
            response_str = json.dumps(txn.hyperpay_response, indent=2, default=str)
            if len(response_str) > 1000:
                print(f"   Full Response (truncated):\n{response_str[:1000]}...")
            else:
                print(f"   Full Response:\n{response_str}")
            
            if 'result' in txn.hyperpay_response:
                result = txn.hyperpay_response.get('result')
                print(f"   Result Type: {type(result)}")
                print(f"   Result Value: {result}")
                if isinstance(result, dict):
                    print(f"   Result Dict Keys: {list(result.keys())}")
                    print(f"   Result Code: {result.get('code')}")
                    print(f"   Result Description: {result.get('description')}")
                elif isinstance(result, str):
                    print(f"   Result (string): {result}")
            
            # Check for result code in different possible locations
            if 'result' in txn.hyperpay_response:
                result = txn.hyperpay_response.get('result')
                if isinstance(result, str) and result.startswith('000'):
                    print(f"   ✅ Found result code in string format: {result}")
            
            # Also check if result code is at top level
            if 'code' in txn.hyperpay_response:
                print(f"   Result Code (top level): {txn.hyperpay_response.get('code')}")
            
            # Check card field for payment status
            if 'card' in txn.hyperpay_response:
                card = txn.hyperpay_response.get('card')
                print(f"   Card Info: {card}")
                if isinstance(card, dict):
                    print(f"   Card Keys: {list(card.keys())}")
            
            # Check paymentBrand field
            if 'paymentBrand' in txn.hyperpay_response:
                print(f"   Payment Brand: {txn.hyperpay_response.get('paymentBrand')}")
            
            # Check if there's a status field
            if 'status' in txn.hyperpay_response:
                print(f"   Status: {txn.hyperpay_response.get('status')}")
    
    # Analyze the issue
    print(f"\n🔍 ANALYSIS:")
    
    latest_txn = transactions.first()
    
    if latest_txn.status != 'success':
        print(f"   ❌ ISSUE: Latest transaction status is '{latest_txn.status}', not 'success'")
        print(f"   ⚠️  Payment verification may not have been called or payment failed")
    else:
        print(f"   ✅ Latest transaction status is 'success'")
    
    if booking.status != 'paid':
        print(f"   ❌ ISSUE: Booking status is '{booking.status}', not 'paid'")
        if booking.status == 'cancelled':
            print(f"   ⚠️  Booking was cancelled. This might prevent payment update.")
            print(f"   ⚠️  If payment was successful, booking should be restored to 'paid' status")
        if latest_txn.status == 'success':
            print(f"   ⚠️  Payment is successful but booking was not updated")
            print(f"   ⚠️  This suggests VerifyPaymentView did not update the booking")
    else:
        print(f"   ✅ Booking status is 'paid'")
    
    if booking.is_paid != True:
        print(f"   ❌ ISSUE: booking.is_paid is {booking.is_paid}, should be True")
    else:
        print(f"   ✅ booking.is_paid is True")
    
    if booking.paid != booking.total_price:
        print(f"   ❌ ISSUE: paid ({booking.paid}) != total_price ({booking.total_price})")
    else:
        print(f"   ✅ paid amount matches total_price")
    
    if booking.not_paid != Decimal('0.00'):
        print(f"   ❌ ISSUE: not_paid is {booking.not_paid}, should be 0.00")
    else:
        print(f"   ✅ not_paid is 0.00")
    
    if not booking.is_qr_genereated:
        print(f"   ❌ ISSUE: QR code was not generated")
    else:
        print(f"   ✅ QR code was generated")
    
    if not booking.qr_code_image:
        print(f"   ❌ ISSUE: QR code image was not saved")
    else:
        print(f"   ✅ QR code image exists")
    
    # Check if payment verification was called
    if latest_txn.status == 'success' and latest_txn.verified_at:
        print(f"\n   ✅ Payment verification was called at {latest_txn.verified_at}")
    elif latest_txn.status == 'success' and not latest_txn.verified_at:
        print(f"\n   ⚠️  Payment is successful but verified_at is not set")
        print(f"   ⚠️  This might indicate the transaction was manually updated")
    
    # Suggest fix
    print(f"\n🔧 SUGGESTED FIX:")
    
    if latest_txn.status == 'success' and booking.status != 'paid':
        print(f"   The payment transaction is successful but booking was not updated.")
        print(f"   This likely means VerifyPaymentView was not called or failed silently.")
        print(f"   \n   To fix manually, run:")
        print(f"   >>> from payments.views import VerifyPaymentView")
        print(f"   >>> from django.test import RequestFactory")
        print(f"   >>> from accounts.models import User")
        print(f"   >>> user = User.objects.get(id={booking.user.id})")
        print(f"   >>> factory = RequestFactory()")
        resource_path = latest_txn.resource_path or f"/v1/checkouts/{latest_txn.checkout_id}/payment"
        print(f"   >>> request = factory.get('/api/payments/verify-payment/', {{'resourcePath': '{resource_path}'}})")
        print(f"   >>> request.user = user")
        print(f"   >>> view = VerifyPaymentView.as_view()")
        print(f"   >>> response = view(request)")
        print(f"   \n   OR use the manual fix function below:")
        
        print(f"\n   Manual fix code:")
        print(f"   >>> manual_fix_order({order_id})")

def manual_fix_order(order_id):
    """Manually fix an order that has successful payment but wasn't updated."""
    
    print(f"\n🔧 MANUAL FIX FOR ORDER #{order_id}")
    print("=" * 60)
    
    try:
        booking = Booking.objects.get(id=order_id)
    except Booking.DoesNotExist:
        print(f"❌ ERROR: Order {order_id} not found")
        return False
    
    # Find payment transaction (check both success and pending with verified_at)
    transactions = PaymentTransaction.objects.filter(
        booking_id=order_id
    ).order_by('-created_at')
    
    if not transactions.exists():
        print(f"❌ ERROR: No payment transaction found for order {order_id}")
        return False
    
    # Prefer successful transactions, but also check pending ones that were verified
    latest_txn = transactions.filter(status='success').first()
    if not latest_txn:
        # Check for pending transactions that were verified (might be successful but status not updated)
        latest_txn = transactions.filter(status='pending', verified_at__isnull=False).first()
        if latest_txn:
            print(f"⚠️  WARNING: Found pending transaction that was verified. Checking if payment was successful...")
            # Check HyperPay response for result code
            if latest_txn.hyperpay_response:
                result = latest_txn.hyperpay_response.get('result')
                result_code = None
                if isinstance(result, dict):
                    result_code = result.get('code')
                elif isinstance(result, str):
                    result_code = result
                
                # Check result code first
                if result_code and str(result_code).startswith('000'):
                    print(f"✅ Payment was successful (result code: {result_code}), updating transaction status...")
                    latest_txn.status = 'success'
                    latest_txn.save()
                else:
                    # Fallback: Check for card info or paymentBrand as indicators of successful payment
                    has_card = latest_txn.hyperpay_response.get('card')
                    has_payment_brand = latest_txn.hyperpay_response.get('paymentBrand')
                    has_amount = latest_txn.hyperpay_response.get('amount')
                    
                    if (has_card or has_payment_brand) and has_amount and latest_txn.verified_at:
                        print(f"⚠️  No result code, but payment indicators present:")
                        print(f"   Card info: {'Yes' if has_card else 'No'}")
                        print(f"   Payment Brand: {has_payment_brand}")
                        print(f"   Amount: {has_amount}")
                        print(f"   Verified At: {latest_txn.verified_at}")
                        print(f"✅ Assuming payment was successful based on indicators, updating transaction status...")
                        latest_txn.status = 'success'
                        latest_txn.save()
                    else:
                        print(f"❌ Payment was not successful. Result code: {result_code}")
                        print(f"   Card: {has_card}, PaymentBrand: {has_payment_brand}, Amount: {has_amount}")
                        return False
    
    if not latest_txn:
        print(f"❌ ERROR: No successful payment transaction found for order {order_id}")
        return False
    print(f"✅ Found successful transaction: {latest_txn.id}")
    print(f"   Amount: {latest_txn.amount}")
    
    # Use the same logic as VerifyPaymentView
    from products.utils import generate_qr_code_image
    
    payment_amount = latest_txn.amount or Decimal('0.00')
    total_price = booking.total_price or Decimal('0.00')
    not_paid = booking.not_paid or Decimal('0.00')
    
    # Check if payment covers the full amount
    is_full_payment = (payment_amount >= not_paid and not_paid > 0) or (payment_amount >= total_price and total_price > 0)
    
    if is_full_payment:
        print(f"✅ Payment covers full amount, updating booking...")
        
        # Check if booking is cancelled
        if booking.status == 'cancelled':
            print(f"⚠️  WARNING: Booking is currently 'cancelled'. Changing to 'paid'...")
        
        booking.status = 'paid'
        booking.is_paid = True
        booking.paid = total_price
        booking.not_paid = Decimal('0.00')
        
        # Generate QR code if not already generated
        if not booking.is_qr_genereated or not booking.qr_code_image:
            try:
                qr_data = str(booking.id)
                qr_image = generate_qr_code_image(qr_data)
                booking.qr_code = qr_data
                booking.qr_code_image.save(f"booking_{booking.id}_qr.png", qr_image, save=False)
                booking.is_qr_genereated = True
                print(f"✅ QR code generated")
            except Exception as qr_error:
                print(f"❌ ERROR: Failed to generate QR code: {str(qr_error)}")
                import traceback
                traceback.print_exc()
        
        booking.save()
        booking.refresh_from_db()
        
        print(f"\n✅ Booking updated successfully:")
        print(f"   Status: {booking.status}")
        print(f"   Is Paid: {booking.is_paid}")
        print(f"   Paid: {booking.paid}")
        print(f"   Not Paid: {booking.not_paid}")
        print(f"   QR Generated: {booking.is_qr_genereated}")
        print(f"   QR Image: {'Yes' if booking.qr_code_image else 'No'}")
        
        return True
    else:
        print(f"⚠️  WARNING: Payment amount ({payment_amount}) doesn't cover full amount")
        print(f"   Total Price: {total_price}")
        print(f"   Not Paid: {not_paid}")
        return False

if __name__ == "__main__":
    import sys
    
    # Get order ID from command line argument or default to 125
    if len(sys.argv) > 1:
        try:
            order_id = int(sys.argv[1])
        except ValueError:
            print(f"❌ ERROR: Invalid order ID: {sys.argv[1]}")
            print("Usage: python debug_order_payment.py [order_id]")
            sys.exit(1)
    else:
        order_id = 125  # Default to order 125
    
    # Debug the specified order
    debug_order_payment(order_id)
    
    print("\n" + "=" * 60)
    print(f"  TO FIX MANUALLY, RUN:")
    print(f"  >>> manual_fix_order({order_id})")
    print("=" * 60)

