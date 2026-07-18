# Payment Gateway Integration Documentation

This directory contains the complete request code and response examples for the HyperPay (OPPWA) payment gateway integration used in production.

## Overview

Our backend integrates with **HyperPay (OPPWA)** payment gateway to process payments for bookings. The integration follows a server-to-server approach where:

1. **Create Checkout**: Backend creates a checkout session with HyperPay and receives a `checkoutId`
2. **Frontend Widget**: Frontend uses the `checkoutId` to load HyperPay's payment widget
3. **Verify Payment**: After payment completion, backend verifies the payment status using the `resourcePath` provided by HyperPay

## Files in this Directory

### Request Code Files (Python)

- **`create_checkout_request.py`**: Complete backend code that sends the request to HyperPay for creating a checkout session
- **`verify_payment_request.py`**: Complete backend code that sends the request to HyperPay for verifying payment status

### Response Files (JSON)

- **`create_checkout_response.json`**: Example responses from HyperPay when creating a checkout session (both success and error cases)
- **`verify_payment_response.json`**: Example responses from HyperPay when verifying payment status (success, failure, and error cases)

## Payment Gateway Details

### Production Configuration

- **Base URL**: `https://eu-prod.oppwa.com`
- **Authentication**: Bearer token in `Authorization` header
- **Entity ID**: Configured in Django settings (`OPPWA_ENTITY_ID`)
- **Access Token**: Configured in Django settings (`OPPWA_ACCESS_TOKEN`)

### API Endpoints

#### 1. Create Checkout Session

**Backend Endpoint**: `POST /api/payments/create-checkout/`

**HyperPay Endpoint**: `POST https://eu-prod.oppwa.com/v1/checkouts`

**Request Method**: `POST`

**Content-Type**: `application/x-www-form-urlencoded`

**Request Parameters** (form data):
- `entityId` (required): Entity ID from HyperPay
- `amount` (required): Payment amount in format "XX.00"
- `currency` (required): Currency code (default: "SAR")
- `paymentType` (required): Payment type (default: "DB" for Direct Debit)
- `merchantTransactionId` (required): Unique transaction ID
- `customer.email` (required): Customer email address
- `customer.givenName` (required): Customer first name
- `customer.surname` (required): Customer last name
- `billing.street1` (required): Billing street address
- `billing.city` (required): Billing city
- `billing.state` (required): Billing state
- `billing.country` (required): Billing country code (2 letters, e.g., "SA")
- `billing.postcode` (required): Billing postal code

**Response**: Returns a `checkoutId` that the frontend uses to load the payment widget.

#### 2. Verify Payment

**Backend Endpoint**: `GET /api/payments/verify-payment/?resourcePath=...`

**HyperPay Endpoint**: `GET https://eu-prod.oppwa.com{resourcePath}`

**Request Method**: `GET`

**Query Parameter**:
- `resourcePath` (required): Resource path from HyperPay redirect (e.g., "/v1/checkouts/{checkoutId}/payment")

**Response**: Returns payment verification data including result code, amount, currency, and payment status.

## Request Flow

### Create Checkout Flow

1. User initiates payment for a booking
2. Frontend sends `POST /api/payments/create-checkout/` with `booking_id`
3. Backend:
   - Validates booking and user permissions
   - Calculates payment amount
   - Prepares customer and billing data
   - Calls `HyperPayService.create_checkout()` with form data
   - Sends POST request to HyperPay with Bearer token authentication
4. HyperPay responds with `checkoutId`
5. Backend stores transaction in database
6. Backend returns `checkoutId` and payment widget URL to frontend

### Verify Payment Flow

1. User completes payment in HyperPay widget
2. HyperPay redirects to frontend with `resourcePath`
3. Frontend sends `GET /api/payments/verify-payment/?resourcePath=...`
4. Backend:
   - Calls `HyperPayService.verify_payment(resource_path)`
   - Sends GET request to HyperPay with Bearer token authentication
5. HyperPay responds with payment verification data
6. Backend:
   - Extracts result code and determines payment status
   - Updates payment transaction in database
   - Updates booking status if payment successful
7. Backend returns verification result to frontend

## Response Processing

### Create Checkout Response

The backend handles two response formats from HyperPay:

1. **JSON format**: Parses as JSON and extracts `id` or `checkoutId`
2. **Key=Value format**: Parses line by line (HyperPay standard format)

If successful, returns:
```python
{
    'success': True,
    'checkout_id': '8ac9a4cc9ae3df3d019b0c80be3d4f12_abc123def456',
    'response': {...},  # Parsed response dict
    'raw_response': '...'  # Full response text
}
```

### Verify Payment Response

The backend processes the JSON response and extracts:

- `result.code`: Payment result code (e.g., "000.000.000" for success)
- `amount`: Payment amount
- `currency`: Payment currency
- `merchantTransactionId`: Transaction ID

Payment status is determined by result code:
- `000.000.000` or `000.100.110`: Success
- `000.400.*`: Failed
- Other codes: Failed

## Error Handling

The backend includes comprehensive error handling:

- **Validation errors**: Missing required fields
- **Authentication errors**: Invalid or missing access token
- **HTTP errors**: Non-200 status codes from HyperPay
- **Timeout errors**: Request timeout after 30 seconds
- **Network errors**: Connection failures

All errors are logged and returned to the frontend with detailed error messages.

## Security Notes

- Access tokens and entity IDs are stored in Django settings (environment variables in production)
- All requests use HTTPS
- Bearer token authentication is used for all API requests
- Customer and billing data are validated before sending to HyperPay

## Testing

For testing, the backend supports a development mode that uses test credentials:
- Set `OPPWA_USE_DEV=True` in environment variables
- Uses test base URL: `https://eu-test.oppwa.com`
- Includes test mode parameters in checkout creation

## Support Information

If you need to contact HyperPay support, provide:

1. **Request Code**: See `create_checkout_request.py` and `verify_payment_request.py`
2. **Response Examples**: See `create_checkout_response.json` and `verify_payment_response.json`
3. **Configuration**: 
   - Base URL: `https://eu-prod.oppwa.com`
   - Entity ID: (from settings)
   - Request format: Form-encoded for checkout, GET for verification
   - Authentication: Bearer token

## Additional Notes

- All amounts are formatted with 2 decimal places (e.g., "100.00")
- Currency is always "SAR" (Saudi Riyal) in production
- Merchant transaction IDs are generated as `TXN_{16-char-hex}` format
- Timeout is set to 30 seconds for all requests
- The backend logs all requests and responses for debugging

