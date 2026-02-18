# API Reference

## Credential Management

To use the `AdpApiClient` you first must configure your API credentials. These credentials are managed through an `AdpCredentials` object, which can be configured manually or from environment variables.

::: adpapi.client.AdpCredentials

## Client

The main entry point for interacting with the ADP API. Can be createdly manually, or **using context management**

```python
from adpapi.client import AdpApiClient, AdpCredentials

credentials = AdpCredentials(
    client_id, client_secret, key_path, cert_path
)
with AdpApiClient(credentials) as api:
    api.call_endpoint(...)
```

The `AdpApiClient` surfaces two main entry points:

- `.call_endpoint()` — for paginated OData queries
- `.call_rest_endpoint()` — for direct REST API calls with path parameter substitution

::: adpapi.client.AdpApiClient.call_endpoint

::: adpapi.client.AdpApiClient.call_rest_endpoint

## Filters

OData filter expressions for querying. Fields can be creating manually, or by using the `FilterExpression` constructor

```python
from adpapi.odata_filters import FilterExpression, Field

# Option 1 Construct Using FilterExpression
filter = FilterExpression.field('fieldName').eq('targetValue')

# Option 2: Construct using the Field class directly
field = Field('fieldName')
```

See More information on what OData Operations are supported using `Field`
::: adpapi.odata_filters.Field


## Logging

Quick basic logging configuration with a rotating file handler and stream handling.

::: adpapi.logger.configure_logging
