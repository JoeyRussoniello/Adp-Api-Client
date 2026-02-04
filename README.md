# adpapi
Minimal Python client for the ADP Workforce Now API using OAuth2 client credentials + mutual TLS (mTLS).

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

from adpapi.client import AdpApiClient
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

# Define your API Client
with AdpApiClient(
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    cert_path=os.getenv("CERT_PATH", "certificate.pem"),
    key_path=os.getenv("KEY_PATH", "adp.key"),
) as api:
    workers = api.call_endpoint(
        endpoint="/hr/v2/workers",
        cols=cols,
        masked=True,       # set False to request unmasked fields if your tenant allows it
        page_size=100,     # ADP max
        max_requests=1,    # increase/remove for full exports
    )

print(len(workers))
```

## Notes
- Uses OData-style pagination (`$top`, `$skip`, `$select`) and stops on HTTP 204 (No Content).
- `masked=False` requests `Accept: application/json;masked=false` (subject to tenant permissions).
- Logging writes DEBUG output to `app.log` and to the console.
