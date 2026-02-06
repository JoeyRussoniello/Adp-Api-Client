# ADP API Client Documentation

Welcome to the ADP API Client documentation. This project provides a Python client for interacting with the ADP Workforce Now API using OAuth 2.0 with certificate-based authentication.

## Quick Links

- **[Getting Started](tutorials.md)** - Start building with the ADP API Client
- **[How-To Guides](how-to-guides.md)** - Common tasks and patterns
- **[API Reference](reference.md)** - Complete API documentation
- **[Concepts](explanation.md)** - Understanding key concepts

## Key Features

- OAuth 2.0 client credentials authentication with certificate support
- Automatic token management and refresh
- Built-in retry logic and session management
- OData filter support for flexible queries
- Comprehensive logging for debugging

## Use Case

> Without the AdpApi module, handling paginated API responses from ADP and token generation is extremely verbose. 

Take, for example, the following code that handles exactly one request to the `/hr/v2/workers` endpoint, without pagination, token refreshing, or OData filtering

```python
import datetime
import json
import logging
import os
import time

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

DEFAULT_TIMEOUT = 30
BASE_URL = "https://api.adp.com"
ENDPOINT = "/hr/v2/workers"

url = BASE_URL + ENDPOINT

# Read required ADP OAuth client credentials from environment.

cert = (cert_path, key_path)

def get_token(timeout: int = DEFAULT_TIMEOUT) -> str:
    logger.debug("Requesting Token from ADP Accounts endpoint")
    
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    TOKEN_URL = "https://accounts.adp.com/auth/oauth/v2/token"
    try:
        response = requests.post(
            TOKEN_URL,
            data=token_payload,
            cert=cert,
            timeout=timeout,
        )
        
        response.raise_for_status()
        token_json = response.json()
        token = token_json.get("access_token")
        if not token:
            raise ValueError("No access token in response")

        # Track token expiration
        expires_in = token_json.get("expires_in", 3600)  # Default 1 hour
        logger.info(f"Token Acquired (expires in {expires_in}s)")
        return token
    except requests.RequestException as e:
        logger.error(f"Token request failed: {e}")
        raise

token = get_token()
params = {
    '$top': 1,
    '$skip': 0,
    '$select': 'workers/person/birthDate'
}
headers = {
    'Accept': 'application/json;masked=false',
    'Authorization': f'Bearer {token}' 
}

now = datetime.datetime.now()
timestamp = now.strftime('%m/%d/%Y - %H:%M:%S')
response = requests.get(
    url, params = params, headers = headers, cert = cert, timeout = DEFAULT_TIMEOUT
)

results = response.json()
```

The `adpapi` turns this whole chunk of code into a simple, readable OOP approach that automatically handles token acquisition and parameter generation:

```python
from dotenv import load_dotenv
from adpapi.client import AdpApiClient

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
cert_path = os.getenv("CERT_PATH", "certificate.pem")
key_path = os.getenv("KEY_PATH", "adp.key")
endpoint = 'hr/v2/workers

with AdpApiClient(client_id, client_secret, cert_path, key_path) as api:
    results = api.call_endpoint(endpoint, select = ['workers/person/birthDate'], page_size = 1, max_requests = 1)

print(results)
```