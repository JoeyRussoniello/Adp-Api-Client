# How-To Guides

## Authenticate with the API

The recommended approach is to load credentials from environment variables (see [Getting Started](tutorials.md)):

```python
from dotenv import load_dotenv
from adpapi.client import AdpApiClient, AdpCredentials

load_dotenv()
credentials = AdpCredentials.from_env()
client = AdpApiClient(credentials)
```

You can also construct credentials manually if you prefer not to use environment variables:

```python
credentials = AdpCredentials(
    client_id='your_client_id',
    client_secret='your_client_secret',
    cert_path='path/to/cert.pem',  # optional
    key_path='path/to/adp.key'    # optional
)
client = AdpApiClient(credentials)
```

## Filter Results with OData

Use `FilterExpression.field()` to build type-safe OData filters to pass to `call_endpoint`:

```python
from adpapi.odata_filters import FilterExpression

# Simple equality filter
filter_expr = FilterExpression.field('workers/workAssignments/assignmentStatus/statusCode/codeValue').eq('Active')

results = client.call_endpoint(
    endpoint="/hr/v2/workers",
    filters=filter_expr
)
```

Combine multiple conditions with `&` (AND) and `|` (OR):

```python
active = FilterExpression.field('workers/workAssignments/assignmentStatus/statusCode/codeValue').eq('Active')
senior = FilterExpression.field('workers/workAssignments/seniorityDate').lt('2015-01-01')

results = client.call_endpoint(
    endpoint="/hr/v2/workers",
    filters=active & senior
)
```

You can also pass a raw OData string if you already have one:

```python
results = client.call_endpoint(
    endpoint="/hr/v2/workers",
    filters="workers/workAssignments/assignmentStatus/statusCode/codeValue eq 'Active'"
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

## Speed Up Batch Requests with Parallel Fetching

When calling `call_rest_endpoint` with a list of IDs, the default behaviour is sequential, one request at a time. For large batches this can be slow. Use the `max_workers` parameter to parallelize requests across multiple threads:

```python
aoid_list = get_aoids()  # e.g. a list of 50 associate OIDs

with AdpApiClient(credentials) as client:
    # Sequential (default) — ~44s for 50 workers
    results_slow = client.call_rest_endpoint(
        endpoint="/hr/v2/workers/{associateOID}",
        associateOID=aoid_list
    )

    # Parallel — ~8s for 50 workers with 10 threads (~5-10x faster)
    results_fast = client.call_rest_endpoint(
        endpoint="/hr/v2/workers/{associateOID}",
        max_workers=10,
        associateOID=aoid_list
    )
```

### Choosing `max_workers`

| `max_workers` | Behaviour |
|---|---|
| `1` (default) | Sequential — one request at a time |
| `5`–`10` | Good starting range for most workloads |
| `> 10` | Diminishing returns; may trigger API rate limits |

The token is refreshed once before the batch starts, so all threads share the same valid token, there is no risk of concurrent token refresh conflicts.

## Configure Logging

Enable logging to see token refresh events, pagination progress, and request errors:

```python
from adpapi.logger import configure_logging

configure_logging()  # logs to console and a rotating file by default
```

## Manage Sessions

`ApiSession` is used internally by `AdpApiClient` — you don't need to interact with it directly. It handles connection pooling, certificate attachment, and header generation on every request. See the [Concepts page](explanation.md) for more detail.
