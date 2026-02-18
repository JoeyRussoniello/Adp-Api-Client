# How-To Guides

## Authenticate with the API

The ADP API Client uses OAuth 2.0 with certificate-based authentication:

```python
from adpapi.client import AdpApiClient, AdpCredentials

credentials = AdpCredentials(
    client_id = 'your_client_id',
    client_secret = 'your_client_secret',
    cert_path = 'path/to/cert.pem', # Optional
    key_path = 'path/to/adp.key' # Optional
)
client = AdpApiClient(credentials)
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

## Call a REST Endpoint with Path Parameters

Use `call_rest_endpoint` to call non-OData REST endpoints that contain path parameters:

```python
# Single value — fetch one worker
results = client.call_rest_endpoint(
    endpoint="/hr/v2/workers/{associateOID}",
    associateOID="G3349PRDL000001"
)

# List of values — batch fetch multiple workers in one call
results = client.call_rest_endpoint(
    endpoint="/hr/v2/workers/{associateOID}",
    associateOID=["G3349PRDL000001", "G3349PRDL000002"]
)
```

You can also pass query parameters and change the HTTP method:

```python
results = client.call_rest_endpoint(
    endpoint="/hr/v2/workers/{associateOID}/custom-fields",
    method="GET",
    masked=False,
    params={"$top": 10},
    associateOID="G3349PRDL000001"
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
