# Getting Started

## Installation

Install the ADP API Client using pip:

```bash
pip install adpapi
```

## Setting Up Credentials

ADP requires an OAuth 2.0 client ID/secret plus a mutual-TLS certificate and key file. The recommended approach is to load credentials from environment variables:

```bash
# .env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
CERT_PATH=certificate.pem   # optional, defaults to certificate.pem
KEY_PATH=adp.key            # optional, defaults to adp.key
```

```python
from dotenv import load_dotenv
from adpapi.client import AdpApiClient, AdpCredentials

load_dotenv()
credentials = AdpCredentials.from_env()
```

You can also pass credentials directly:

```python
credentials = AdpCredentials(
    client_id="your_client_id",
    client_secret="your_client_secret",
    cert_path="/path/to/certificate.pem",  # optional
    key_path="/path/to/adp.key",           # optional
)
```

## Your First Request

Use `AdpApiClient` as a context manager (recommended) so the underlying HTTP session is always closed cleanly:

```python
with AdpApiClient(credentials) as client:
    results = client.call_endpoint(
        endpoint="/hr/v2/workers",
        select=["workers/person/legalName/givenName", "workers/person/legalName/familyName1"],
        masked=True
    )
print(results)
```

`call_endpoint` automatically handles pagination — it keeps fetching pages until the API signals there are no more results, then returns all records as a flat `List[Dict]`.

## Fetching a Single Worker by ID

When you already have a specific resource ID, use `call_rest_endpoint` instead:

```python
with AdpApiClient(credentials) as client:
    results = client.call_rest_endpoint(
        endpoint="/hr/v2/workers/{associateOID}",
        associateOID="G3349PRDL000001"
    )
```

You can also pass a list of IDs to fetch multiple workers in a batch:

```python
with AdpApiClient(credentials) as client:
    results = client.call_rest_endpoint(
        endpoint="/hr/v2/workers/{associateOID}",
        associateOID=["G3349PRDL000001", "G3349PRDL000002", "G3349PRDL000003"]
    )
```

## Choosing the Right Method

| Scenario | Method |
|---|---|
| List/search records with OData filters or pagination | `call_endpoint` |
| Fetch a specific resource by ID | `call_rest_endpoint` |
| Batch-fetch several known IDs | `call_rest_endpoint` with a list |

## Next Steps

- **[How-To Guides](how-to-guides.md)** — filtering, logging, and other common tasks
- **[API Reference](reference.md)** — full parameter documentation
- **[Concepts](explanation.md)** — authentication flow, token lifecycle, and more

## Logging Configuration

::: adpapi.logger.configure_logging
