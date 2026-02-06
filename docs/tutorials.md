# Getting Started

## Installation

Install the ADP API Client using pip or uv:

```bash
pip install adpapi
```

## Your First Request

Here's a simple example to get you started with the `call_endpoint` method:

```python
from adpapi.client import AdpApiClient

# Initialize the client
client = AdpApiClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    cert_path="/path/to/certificate.pem",
    key_path="/path/to/key.pem"
)

# Call an ADP endpoint
results = client.call_endpoint(
    endpoint="/hr/v2/workers",
    select=["workers/firstName", "lastName", "email"],
    masked=True
)
print(results)
```

### More about `call_endpoint`

The `call_endpoint` method is the primary way to interact with any registered ADP endpoint. You provide the endpoint path and optional parameters like `select` for specific fields and `filters` for querying results.


::: adpapi.client.AdpApiClient.call_endpoint


## Logging Configuration

::: adpapi.logger.configure_logging
