"""
Full request code for verifying payment status with HyperPay payment gateway.

This file contains the complete backend code that sends the request to HyperPay
for verifying payment status after the user completes payment.

Endpoint: GET /api/payments/verify-payment/?resourcePath=...
Payment Gateway: HyperPay (OPPWA)
Base URL: https://eu-prod.oppwa.com
"""

import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class HyperPayService:
    """Service class for HyperPay API interactions."""
    
    @staticmethod
    def get_base_url():
        """Get HyperPay base URL from settings."""
        return getattr(settings, 'OPPWA_BASE_URL', 'https://eu-prod.oppwa.com')
    
    @staticmethod
    def get_access_token():
        """Get HyperPay access token from settings."""
        token = getattr(settings, 'OPPWA_ACCESS_TOKEN', None)
        if not token:
            raise ValueError("OPPWA_ACCESS_TOKEN not configured in settings")
        return token
    
    @staticmethod
    def verify_payment(resource_path):
        """
        Verify payment status with HyperPay using resourcePath.
        
        This is the main function that sends the request to HyperPay
        to verify the payment status after the user completes payment.
        
        Args:
            resource_path (str): Resource path from HyperPay redirect
                Example: "/v1/checkouts/{checkoutId}/payment"
                This is provided by HyperPay after payment completion
                
        Returns:
            dict: Payment verification response from HyperPay containing:
                - success: Boolean indicating if request was successful
                - data: Full payment verification data from HyperPay
                - error: Error message if request failed
        """
        base_url = HyperPayService.get_base_url()
        access_token = HyperPayService.get_access_token()
        
        # Build verification URL
        # resourcePath already includes /v1/checkouts/...
        # Example: resource_path = "/v1/checkouts/8ac9a4cc9ae3df3d019b0c80be3d4f12_abc123/payment"
        verification_url = f"{base_url}{resource_path}"
        
        # Prepare headers with Bearer token authentication
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            # Send GET request to verify payment
            # This is the actual HTTP request sent to HyperPay
            response = requests.get(
                verification_url,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Log response for debugging
            logger.info(f"HyperPay payment verification response: {response.status_code}")
            
            # Check if request was successful
            if response.status_code == 200:
                try:
                    # HyperPay returns JSON response
                    response_data = response.json()
                    return {
                        'success': True,
                        'data': response_data
                    }
                except ValueError:
                    # If not JSON, return text
                    return {
                        'success': True,
                        'data': {'raw_response': response.text}
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'response_text': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error("HyperPay payment verification timeout")
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HyperPay payment verification error: {str(e)}")
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }


# Example usage from the view layer:
"""
The view layer (VerifyPaymentView) receives the resourcePath from the frontend
and calls this service:

resource_path = "/v1/checkouts/8ac9a4cc9ae3df3d019b0c80be3d4f12_abc123/payment"

result = HyperPayService.verify_payment(resource_path)

if result.get('success'):
    verification_data = result.get('data', {})
    # Process payment verification data
    # Extract result code, amount, currency, etc.
else:
    # Handle error
    error = result.get('error')
"""

