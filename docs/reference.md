# API Reference

## Credential Management

To use the `AdpApiClient` you first must configure your API credentials. These credentials are managed through an `AdpCredentials` object, which can be configured manually or from environment variables.

::: adpapi.client.AdpCredentials

## Client

The main entry point for interacting with the ADP API. Using a context manager is **recommended** so the HTTP session is always closed cleanly:

```python
from adpapi.client import AdpApiClient, AdpCredentials

credentials = AdpCredentials(
    client_id, client_secret, key_path, cert_path
)
with AdpApiClient(credentials) as api:
    api.call_endpoint(...)
    api.call_rest_endpoint(...)
```

The `AdpApiClient` surfaces two main entry points:

- `.call_endpoint()` — for paginated OData queries (lists, searches)
- `.call_rest_endpoint()` — for direct resource lookups by ID, with path parameter substitution

::: adpapi.client.AdpApiClient.call_endpoint

::: adpapi.client.AdpApiClient.call_rest_endpoint

## Filters

OData filter expressions for querying. Use `FilterExpression.field()` as the primary entry point:

```python
from adpapi.odata_filters import FilterExpression

# Recommended: use FilterExpression.field()
filter = FilterExpression.field('fieldName').eq('targetValue')

# Advanced: construct a Field directly for reuse
from adpapi.odata_filters import Field
field = Field('fieldName')
```

See full details on supported OData operations:
::: adpapi.odata_filters.Field


## Logging

Quick basic logging configuration with a rotating file handler and stream handling.

::: adpapi.logger.configure_logging
