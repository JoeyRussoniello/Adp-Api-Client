# ADP API Client

A robust Python client for the ADP Workforce Now API with automatic token management, retry logic, and comprehensive error handling.

## Features

**Token Management**
- Automatic token acquisition with OAuth2 client credentials flow
- Automatic token refresh before expiration
- 5-minute buffer to prevent mid-request token expiration

**Resilience & Reliability**
- Exponential backoff retry strategy for transient failures
- Handles HTTP 429 (rate limiting), 500, 502, 503, 504 errors
- Configurable timeouts and page sizes
- Comprehensive error handling

**Security**
- Certificate-based authentication (mTLS)
- Masking support for sensitive PII data
- Proper session management and cleanup

**Data Operations**
- Flexible column selection via OData `$select`
- Automatic pagination with configurable page sizes
- Support for unmasked data retrieval when authorized

**Testing & Development**
- 42 comprehensive unit tests
- Full mock support for testing
- Context manager support for resource cleanup

## Installation

### Prerequisites
- Python 3.10 or higher
- ADP Workforce Now API credentials
- Client certificate and key files

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/trinity-property-consultants/API-Clients 
cd ADP
```

2. **Create a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install requests python-dotenv
```

4. **Configure credentials**
Create a `.env` file in the project root:

```env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
CERT_PATH=path/to/certificate.pem
KEY_PATH=path/to/adp.key
```

## Quick Start

```python
from client import AdpApiClient

# Initialize the client
client = AdpApiClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    cert_path="certificate.pem",
    key_path="adp.key"
)

# Fetch worker data with specific columns
workers = client.call_endpoint(
    endpoint="/hr/v2/workers",
    cols=[
        "workers/person/legalName",
        "workers/person/birthDate",
        "workers/workAssignments/reportsTo",
        "workers/businessCommunication/emails"
    ],
    masked=False  # Request unmasked PII (if authorized)
)

# Process the results
for response in workers:
    print(response)

# Use context manager for automatic cleanup
with AdpApiClient(...) as client:
    workers = client.call_endpoint(...)
```

## Configuration

### Environment Variables

```env
CLIENT_ID              # OAuth2 client ID
CLIENT_SECRET          # OAuth2 client secret
CERT_PATH             # Path to mTLS certificate (default: certificate.pem)
KEY_PATH              # Path to mTLS key (default: adp.key)
```

### Client Parameters

```python
AdpApiClient(
    client_id: str,           # Required: OAuth2 client ID
    client_secret: str,       # Required: OAuth2 client secret
    cert_path: str,           # Required: Path to certificate file
    key_path: str             # Required: Path to key file
)
```

### Endpoint Call Parameters

```python
client.call_endpoint(
    endpoint: str,            # Required: API endpoint (e.g., "/hr/v2/workers")
    cols: List[str],          # Required: Columns to retrieve (OData $select)
    masked: bool = True,      # Optional: Mask sensitive data (default: True)
    timeout: int = 30,        # Optional: Request timeout in seconds (default: 30)
    page_size: int = 100,     # Optional: Records per page, max 100 (default: 100)
    max_requests: int = None  # Optional: Max API calls (for testing)
)
```

## API Reference

### AdpApiClient

Main client class for interacting with the ADP API.

#### Methods

**`__init__(client_id, client_secret, cert_path, key_path)`**
- Initializes the client with credentials
- Validates certificate and key files exist
- Acquires initial OAuth2 token
- Raises: `ValueError`, `FileNotFoundError`

**`call_endpoint(endpoint, cols, masked=True, timeout=30, page_size=100, max_requests=None)`**
- Calls an ADP API endpoint with pagination support
- Returns: `List[Dict]` - List of API response objects
- Raises: `ValueError` for invalid endpoint format

**`_get_headers(masked=True)`**
- Generates request headers with Bearer token and masking preference
- Returns: `Dict[str, str]` - HTTP headers
- Automatically refreshes expired tokens

**`_ensure_valid_token(timeout=30)`**
- Checks token expiration and refreshes if needed
- Automatically called before each request

**`__enter__()` / `__exit__()`**
- Context manager support for automatic session cleanup
- Usage: `with AdpApiClient(...) as client:`

### ApiSession

Low-level HTTP session wrapper for ADP API requests.

#### Methods

**`get(url: str)`** - GET request
**`post(url: str, data: Optional[Any] = None)`** - POST request with optional JSON body
**`put(url: str, data: Optional[Any] = None)`** - PUT request with optional JSON body
**`delete(url: str)`** - DELETE request

#### Parameters

```python
ApiSession(
    session: requests.Session,
    cert: tuple[str, str],           # (cert_path, key_path)
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 30,
    data: Optional[Any] = None
)
```

## Usage Examples

### Basic Worker Retrieval

```python
from client import AdpApiClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize client
api = AdpApiClient(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    cert_path=os.getenv("CERT_PATH"),
    key_path=os.getenv("KEY_PATH")
)

# Get all workers
workers = api.call_endpoint(
    endpoint="/hr/v2/workers",
    cols=[
        "workers/person/legalName",
        "workers/person/birthDate",
        "workers/workAssignments/reportsTo"
    ]
)

print(f"Retrieved {len(workers)} worker records")
```

### Masked vs Unmasked Data

```python
# With masking (default) - PII is masked
workers_masked = api.call_endpoint(
    endpoint="/hr/v2/workers",
    cols=["workers/person/birthDate"],
    masked=True
)
# Output: {"workers": [{"person": {"birthDate": "0000-00-00"}}]}

# Without masking - Full PII (if authorized)
workers_unmasked = api.call_endpoint(
    endpoint="/hr/v2/workers",
    cols=["workers/person/birthDate"],
    masked=False
)
# Output: {"workers": [{"person": {"birthDate": "1990-05-15"}}]}
```

### Pagination Control

```python
# Request with custom page size and limit
workers = api.call_endpoint(
    endpoint="/hr/v2/workers",
    cols=["workers/person/legalName"],
    page_size=50,        # Fetch 50 records per request
    max_requests=10      # Stop after 10 API calls (500 records max)
)
```

### Context Manager (Recommended)

```python
# Automatic session cleanup
with AdpApiClient(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    cert_path=os.getenv("CERT_PATH"),
    key_path=os.getenv("KEY_PATH")
) as api:
    workers = api.call_endpoint(
        endpoint="/hr/v2/workers",
        cols=["workers/person/legalName"]
    )
# Session automatically closed here
```

### Error Handling

```python
import requests
from client import AdpApiClient

try:
    api = AdpApiClient(
        client_id="invalid_id",
        client_secret="invalid_secret",
        cert_path="cert.pem",
        key_path="key.key"
    )
except FileNotFoundError as e:
    print(f"Certificate not found: {e}")
except ValueError as e:
    print(f"Invalid credentials: {e}")
except requests.RequestException as e:
    print(f"Token request failed: {e}")

# Endpoint call errors
try:
    workers = api.call_endpoint(
        endpoint="invalid_endpoint",
        cols=["workers/person/legalName"]
    )
except ValueError as e:
    print(f"Invalid endpoint format: {e}")
except requests.RequestException as e:
    print(f"API request failed: {e}")
```

## Architecture

```
ADP API Client
├── client.py              # Main AdpApiClient class
│   ├── Token management
│   ├── Retry strategy
│   ├── Request headers
│   └── Endpoint calling
├── sessions.py            # ApiSession wrapper
│   ├── HTTP method routing
│   ├── Parameter handling
│   └── Error handling
├── logger.py              # Logging configuration
└── main.py                # Example usage
```

### Key Components

**AdpApiClient**
- OAuth2 token acquisition and refresh
- Automatic token expiration detection
- Request retry strategy
- Pagination support
- Header generation with masking control

**ApiSession**
- Low-level HTTP operations
- Certificate-based authentication
- Exception handling and logging
- Request parameter management

**Token Management**
- Tokens acquired via OAuth2 client credentials flow
- Automatic refresh with 5-minute expiration buffer
- Prevents mid-request token expiration

**Retry Strategy**
- Exponential backoff (3 retries, 0.5s factor)
- Retries on transient errors: 429, 500, 502, 503, 504
- Configurable via `_setup_retry_strategy()`

## Testing

### Run All Tests
```bash
python -m unittest discover tests/ -v
```

### Test Coverage
- **42 comprehensive unit tests** across all components
- Tests for initialization, token management, retries, error handling
- Mock-based testing with isolated dependencies
- ~0.26 second execution time

### Test Structure
```
tests/
├── test_client.py      # 26 tests for AdpApiClient
├── test_sessions.py    # 15 tests for ApiSession
├── test_logger.py      # 4 tests for logging
└── README.md           # Testing documentation
```

### Run Specific Tests
```bash
# Run specific test file
python -m unittest tests.test_client -v

# Run specific test class
python -m unittest tests.test_client.TestAdpApiClientInitialization -v

# Run specific test
python -m unittest tests.test_client.TestAdpApiClientInitialization.test_initialization_success -v
```

## Logging

Logging is configured in `logger.py` and outputs to both file and console.

### Configuration

```python
from logger import configure_logging

# Initialize logging
configure_logging()
```

### Log Output
- **File**: `app.log` (DEBUG level)
- **Console**: stdout (DEBUG level)
- **Format**: `%(asctime)s - %(levelname)s - %(message)s`

### Log Events
```
Token Acquired (expires in 3600s)
Retry strategy configured: 3 retries with 0.5s backoff
Request to /hr/v2/workers
End of pagination reached (204 No Content)
Session closed
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `FileNotFoundError` | Certificate/key file missing | Verify certificate and key paths |
| `ValueError: All credentials and paths must be provided` | Missing credentials | Check CLIENT_ID, CLIENT_SECRET, CERT_PATH, KEY_PATH |
| `ValueError: No access token in response` | Invalid credentials | Verify CLIENT_ID and CLIENT_SECRET |
| `ValueError: Incorrect Endpoint Received` | Invalid endpoint format | Use format: `/hr/v2/workers` or full URL |
| `requests.RequestException` | Network/API error | Check internet connection, API status |
| `requests.exceptions.HTTPError` | HTTP error (4xx, 5xx) | Check authorization, endpoint validity |

### Retry Behavior

The client automatically retries on transient errors:
- HTTP 429 (Rate Limiting)
- HTTP 500 (Internal Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

Retry strategy:
- Maximum 3 retries
- Exponential backoff: 0.5s, 1.0s, 1.5s
- Not retried: client errors (4xx), successful responses

## Best Practices

### 1. Use Context Managers
```python
# ✅ Good - Automatic cleanup
with AdpApiClient(...) as client:
    workers = client.call_endpoint(...)

# ❌ Avoid - Manual cleanup required
client = AdpApiClient(...)
workers = client.call_endpoint(...)
```

### 2. Request Unmasked Data Only When Needed
```python
# ✅ Good - Masked by default for security
workers = client.call_endpoint(endpoint, cols)

# ⚠️ Caution - Only use with proper authorization
workers = client.call_endpoint(endpoint, cols, masked=False)
```

### 3. Handle Errors Gracefully
```python
# ✅ Good - Comprehensive error handling
try:
    workers = client.call_endpoint(...)
except requests.RequestException as e:
    logger.error(f"API error: {e}")
except ValueError as e:
    logger.error(f"Invalid input: {e}")

# ❌ Avoid - Silent failures
try:
    workers = client.call_endpoint(...)
except:
    pass
```

### 4. Configure Appropriate Timeouts
```python
# ✅ Good - Sufficient timeout for large datasets
workers = client.call_endpoint(
    endpoint,
    cols,
    timeout=60,      # 60 seconds for large requests
    page_size=100    # Max page size
)

# ❌ Avoid - Too short timeout
workers = client.call_endpoint(endpoint, cols, timeout=5)
```

### 5. Store Credentials Securely
```python
# ✅ Good - Use environment variables
load_dotenv()
client = AdpApiClient(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    ...
)

# ❌ Avoid - Hardcoded credentials
client = AdpApiClient(
    client_id="actual_id",
    client_secret="actual_secret",
    ...
)
```

## Troubleshooting

### Token Acquisition Fails

**Error**: `Token request failed: 401 Unauthorized`

**Solutions**:
1. Verify CLIENT_ID and CLIENT_SECRET are correct
2. Check certificate and key files exist
3. Ensure certificate/key have proper permissions
4. Verify ADP API endpoint is accessible

### Birth Dates Show "0000-00-00"

**Cause**: Insufficient permissions to access unmasked data

**Solution**:
1. Check if your account has PII access permissions
2. Contact ADP administrator to grant unmasked data access
3. Verify `masked=False` parameter is working (see code review notes)

### Pagination Issues

**Error**: `Incorrect Endpoint Received`

**Solutions**:
1. Use proper endpoint format: `/hr/v2/workers` or `https://api.adp.com/hr/v2/workers`
2. Ensure columns are valid OData format: `workers/person/legalName`
3. Check page size is between 1-100

### Connection Timeouts

**Error**: `requests.exceptions.ConnectTimeout`

**Solutions**:
1. Increase timeout: `timeout=60`
2. Check internet connection
3. Verify ADP API service is operational
4. Check firewall/proxy settings

## Performance Considerations

### Pagination
- Default page size: 100 records
- Maximum page size: 100 records
- Adjust based on network speed and data size

### Timeouts
- Default: 30 seconds per request
- Increase for large datasets or slow connections
- Decrease for quick fail-fast behavior

### Retry Strategy
- Default: 3 retries with exponential backoff
- Customize via `_setup_retry_strategy(retries, backoff_factor)`

### Token Management
- Token refresh buffer: 5 minutes
- Reduces chance of mid-request expiration
- Automatic and transparent to caller

## Project Structure

```
ADP/
├── client.py              # Main API client
├── sessions.py            # HTTP session wrapper
├── logger.py              # Logging configuration
├── main.py                # Example usage script
├── proccessing.py         # Data processing utilities
├── worker_data.json       # Sample output
├── .env                   # Configuration (gitignored)
├── .gitignore
├── README.md              # This file
├── TESTING.md             # Testing documentation
├── requirements.txt       # Python dependencies
└── tests/
    ├── __init__.py
    ├── test_client.py     # Client tests
    ├── test_sessions.py   # Session tests
    ├── test_logger.py     # Logger tests
    ├── conftest.py        # Test configuration
    └── README.md          # Testing guide
```

## Development

### Install Development Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
python -m unittest discover tests/ -v
```

### Code Quality
- Type hints throughout
- Comprehensive docstrings
- Error handling at all integration points
- Logging at key operations

### Adding New Features
1. Create feature branch
2. Add tests first (TDD approach)
3. Implement feature
4. Run all tests
5. Update documentation
6. Submit pull request

## Limitations & Known Issues

### Masked Data
- When `masked=False`, birth dates may still show "0000-00-00" if permissions are insufficient
- Contact ADP to enable unmasked PII access

### API Limitations
- Maximum page size: 100 records
- Rate limiting: varies by ADP subscription
- Retry strategy: only retries transient (5xx) errors

### Token Lifecycle
- Token expiration buffer: fixed at 5 minutes
- No token invalidation on logout (handled by ADP)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Add/update tests
5. Run full test suite
6. Commit your changes (`git commit -m 'Add AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

## License

Internal use only. This client is designed for integration with ADP Workforce Now API.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test files for usage examples
3. Consult ADP Workforce Now API documentation
4. Contact your ADP administrator

## Related Documentation

- [TESTING.md](TESTING.md) - Comprehensive testing guide
- [Code Review Notes](./docs/code_review.md) - Architecture and design decisions
- ADP Workforce Now API Documentation: https://developer.adp.com/

## Changelog

### Version 1.0.0 (Current)
- ✅ OAuth2 client credentials authentication
- ✅ Automatic token management and refresh
- ✅ Exponential backoff retry strategy
- ✅ OData $select support for column selection
- ✅ Automatic pagination
- ✅ Masking support for sensitive data
- ✅ Comprehensive error handling
- ✅ Context manager support
- ✅ 42 comprehensive unit tests
- ✅ Full documentation and examples
