"""
HyperPay/OPPWA payment gateway service functions.
Handles server-to-server communication with HyperPay API.
"""
import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class HyperPayService:
    """Service class for HyperPay API interactions."""
    
    @staticmethod
    def get_base_url():
        """Get HyperPay base URL from settings."""
        return getattr(settings, 'OPPWA_BASE_URL', 'https://eu-prod.oppwa.com')
    
    @staticmethod
    def is_dev_mode():
        """Check if we're using dev/test credentials."""
        return getattr(settings, 'OPPWA_USE_DEV', False)
    
    @staticmethod
    def get_access_token():
        """Get HyperPay access token from settings."""
        token = getattr(settings, 'OPPWA_ACCESS_TOKEN', None)
        if not token:
            raise ValueError("OPPWA_ACCESS_TOKEN not configured in settings")
        return token
    
    @staticmethod
    def get_entity_id():
        """Get HyperPay entity ID from settings."""
        entity_id = getattr(settings, 'OPPWA_ENTITY_ID', None)
        if not entity_id:
            raise ValueError("OPPWA_ENTITY_ID not configured in settings")
        return entity_id
    
    @staticmethod
    def create_checkout(data):
        """
        Create checkout session with HyperPay.
        
        Args:
            data (dict): Checkout data including:
                - amount: Payment amount (e.g., "100.00")
                - currency: Currency code (default: "SAR")
                - merchantTransactionId: Unique transaction ID
                - customer data (email, name, billing info)
                
        Returns:
            dict: Response from HyperPay containing checkoutId
        """
        base_url = HyperPayService.get_base_url()
        access_token = HyperPayService.get_access_token()
        entity_id = HyperPayService.get_entity_id()
        
        # Build checkout URL
        checkout_url = f"{base_url}/v1/checkouts"
        
        # Prepare form data with mandatory fields
        form_data = {
            'entityId': entity_id,  # Required: Entity ID from HyperPay
            'amount': data.get('amount'),  # Required: Amount in format "XX.00"
            'currency': data.get('currency', 'SAR'),  # Required: Currency code
            'paymentType': 'DB',  # Required: Direct Debit payment type
            'merchantTransactionId': data.get('merchantTransactionId'),  # Required: Unique transaction ID
        }
        
        # Add test mode parameters only for dev/test environment
        if HyperPayService.is_dev_mode():
            form_data['testMode'] = 'EXTERNAL'  # Required: External test mode for 3DS testing
            form_data['customParameters[3DS2_enrolled]'] = 'true'
            form_data['customParameters[3DS2_flow]'] = 'challenge'
        
        # Add customer data (mandatory fields)
        # These are required by HyperPay for production transactions
        customer_email = data.get('customer_email')
        if not customer_email:
            raise ValueError("customer_email is required for payment transactions")
        form_data['customer.email'] = customer_email
        
        customer_given_name = data.get('customer_givenName')
        if not customer_given_name:
            raise ValueError("customer_givenName is required for payment transactions")
        form_data['customer.givenName'] = customer_given_name
        
        customer_surname = data.get('customer_surname')
        if not customer_surname:
            raise ValueError("customer_surname is required for payment transactions")
        form_data['customer.surname'] = customer_surname
        
        # Add billing data (mandatory fields)
        # These are required by HyperPay for production transactions
        billing_street1 = data.get('billing_street1')
        if not billing_street1:
            raise ValueError("billing_street1 is required for payment transactions")
        form_data['billing.street1'] = billing_street1
        
        billing_city = data.get('billing_city')
        if not billing_city:
            raise ValueError("billing_city is required for payment transactions")
        form_data['billing.city'] = billing_city
        
        billing_state = data.get('billing_state')
        if not billing_state:
            raise ValueError("billing_state is required for payment transactions")
        form_data['billing.state'] = billing_state
        
        billing_country = data.get('billing_country')
        if not billing_country:
            raise ValueError("billing_country is required for payment transactions")
        form_data['billing.country'] = billing_country
        
        billing_postcode = data.get('billing_postcode')
        if not billing_postcode:
            raise ValueError("billing_postcode is required for payment transactions")
        form_data['billing.postcode'] = billing_postcode
        
        # Prepare headers with Bearer token authentication
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            # Send POST request with form-encoded data
            response = requests.post(
                checkout_url,
                data=form_data,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Log response for debugging
            logger.info(f"HyperPay checkout creation response: {response.status_code}")
            logger.info(f"HyperPay response headers: {dict(response.headers)}")
            logger.info(f"HyperPay response text: {response.text[:500]}")  # First 500 chars for debugging
            
            # Check if request was successful
            if response.status_code == 200 or response.status_code == 201:
                response_text = response.text
                checkout_id = None
                response_dict = {}
                
                # Try to parse as JSON first
                try:
                    response_dict = response.json()
                    checkout_id = response_dict.get('id') or response_dict.get('checkoutId')
                    if not checkout_id:
                        # Sometimes nested in response data
                        if 'data' in response_dict and isinstance(response_dict['data'], dict):
                            checkout_id = response_dict['data'].get('id')
                except (ValueError, AttributeError):
                    # If not JSON, try parsing key=value format (HyperPay standard format)
                    for line in response_text.strip().split('\n'):
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            response_dict[key] = value
                            if key.lower() == 'id':
                                checkout_id = value
                
                # Extract checkout ID if still not found
                if not checkout_id:
                    checkout_id = response_dict.get('id') or response_dict.get('checkoutId')
                
                if checkout_id:
                    return {
                        'success': True,
                        'checkout_id': checkout_id,
                        'response': response_dict,
                        'raw_response': response_text
                    }
                else:
                    # Return detailed error with full response for debugging
                    logger.error(f"HyperPay response did not contain checkout ID. Full response: {response_text}")
                    return {
                        'success': False,
                        'error': 'No checkout ID in response',
                        'response': response_dict,
                        'raw_response': response_text,
                        'response_status': response.status_code
                    }
            else:
                logger.error(f"HyperPay returned error status {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'response_text': response.text,
                    'response_status': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error("HyperPay checkout creation timeout")
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HyperPay checkout creation error: {str(e)}")
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }
    
    @staticmethod
    def verify_payment(resource_path):
        """
        Verify payment status with HyperPay using resourcePath.
        
        Args:
            resource_path (str): Resource path from HyperPay redirect (e.g., "/v1/checkouts/{checkoutId}/payment")
            
        Returns:
            dict: Payment verification response from HyperPay
        """
        base_url = HyperPayService.get_base_url()
        access_token = HyperPayService.get_access_token()
        
        # Build verification URL
        # resourcePath already includes /v1/checkouts/...
        verification_url = f"{base_url}{resource_path}"
        
        # Prepare headers with Bearer token authentication
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        try:
            # Send GET request to verify payment
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

