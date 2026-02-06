# How-To Guides

## Authenticate with the API

The ADP API Client uses OAuth 2.0 with certificate-based authentication:

```python
from adpapi.client import AdpApiClient

client = AdpApiClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    cert_path="path/to/cert.pem",
    key_path="path/to/key.pem"
)
```

## Filter Results with OData

Use the FilterExpression class to build complex OData queries with `call_endpoint`:

```python
from adpapi.odata_filters import FilterExpression

# Create filters and combine them
filter_expr = FilterExpression('targetField').eq('DesiredValue')  # Build your filter
results = client.call_endpoint(
    endpoint="/hr/v2/workers",
    filters=filter_expr
)
```

## Configure Logging

Set up application logging:

```python
from adpapi.logger import configure_logging

configure_logging()
```

## Manage Sessions

Understand how sessions are managed internally:

::: adpapi.sessions.RequestMethod

::: adpapi.sessions.ApiSession
