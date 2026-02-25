# adpapi
Minimal Python client for the ADP Workforce Now API using OAuth2 client credentials + mutual TLS (mTLS).

[![CI](https://github.com/JoeyRussoniello/Adp-Api-Client/actions/workflows/ci.yml/badge.svg)](https://github.com/JoeyRussoniello/Adp-Api-Client/actions/workflows/ci.yml)
[![Docs](https://github.com/JoeyRussoniello/Adp-Api-Client/actions/workflows/docs.yml/badge.svg)](https://github.com/JoeyRussoniello/Adp-Api-Client/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/adpapi)](https://pypi.org/project/adpapi/)
[![Python](https://img.shields.io/pypi/pyversions/adpapi)](https://pypi.org/project/adpapi/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://JoeyRussoniello.github.io/Adp-Api-Client/)

## Install
```bash
uv add adpapi
```

or 

```bash
pip install adpapi
```

## Configuration
Provide credentials via environment variables (or a `.env` file):
```env
CLIENT_ID=...
CLIENT_SECRET=...
CERT_PATH=certificate.pem
KEY_PATH=adp.key
```

## Quickstart
```python
import os
from dotenv import load_dotenv

from adpapi.client import AdpApiClient, AdpCredentials
from adpapi.logger import configure_logging

# Optional helper: Configure logger with file handlers and stream handling
configure_logging()
load_dotenv()

# Decide which OData columnns are required from your pull
cols = [
    "workers/person/legalName",
    "workers/person/birthDate",
    "workers/workAssignments/reportsTo",
    "workers/associateOID",
    "workers/businessCommunication/emails",
]

# Load API Credentials from environment
credentials = AdpCredentials.from_env()

# Define your API Client
with AdpApiClient(credentials) as api:
    workers = api.call_endpoint(
        endpoint="/hr/v2/workers",
        select=cols,
        masked=True,       # set False to request unmasked fields if your tenant allows it
        page_size=100,     # ADP max
        max_requests=1,    # increase/remove for full exports
    )
```

## Filtering with OData

Use `FilterExpression` to build OData `$filter` parameters. Pass filters to `call_endpoint()` using the `filters` parameter:

```python
from adpapi.odata_filters import FilterExpression

# Simple equality
filter1 = FilterExpression.field("workers.status").eq("Active")

# Combine conditions with logical operators
filter2 = (
    FilterExpression.field("workers.status").eq("Active")
    & FilterExpression.field("workers.hireDate").ge("2020-01-01")
)

# Multiple values (IN operator)
filter3 = FilterExpression.field("workers.status").isin(["Active", "OnLeave", "Pending"])

# String search
filter4 = FilterExpression.field("workers.person.legalName.familyName").contains("Smith")

# Pass to API call
workers = api.call_endpoint(
    endpoint="/hr/v2/workers",
    filters=filter2,
    select=cols,
    masked=True,
)
```

**Supported Operators:**
- Comparison: `eq`, `ne`, `gt`, `ge`, `lt`, `le`
- String functions: `contains()`, `startswith()`, `endswith()`
- Logical: `&` (and), `|` (or), `~` (not)
- IN operator: `isin([...])`

**Notes:**
- Field paths use dots in Python code (e.g., `workers.status`) but convert to forward slashes in OData syntax (`workers/status`)
- Not all operators are supported by all endpoints; check ADP API documentation
- You can also pass OData filter strings directly: `filters="workers/status eq 'Active'"`

## Notes
- Uses OData-style pagination (`$top`, `$skip`, `$select`) and stops on HTTP 204 (No Content).
- `masked=False` requests `Accept: application/json;masked=false` (subject to tenant permissions).
- Logging writes DEBUG output to `app.log` and to the console.

## `Monofile.ipynb`

For clients such as Microsoft Fabric, Azure Databricks, or other notebook-driven programming environments, running a single notebook with magic commands may be more efficient than creating a custom runtime with the `pip` version of the package. To allow for this, [`monofile.ipynb`](./monofile.ipynb) can simply be uploaded to the desired location and ran there. 

Import Syntax Changes to

```python
%run monofile.ipynb # Or whatever monofile has been renamed to in the notebook client

# Now, imports are no longer necessary and the top-level Api objects are exposed at top-level
configure_logging()
with AdpApiClient(...) as api:
    api.call_endpoint(...)
```