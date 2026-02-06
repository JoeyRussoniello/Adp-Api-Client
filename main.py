"""
Example: Export worker data from the ADP Workforce Now API to JSON.

This script demonstrates a minimal end-to-end workflow using the `adpapi` package:

1) Load credentials/paths from environment variables (optionally via a `.env` file).
2) Create an authenticated `AdpApiClient`.
3) Call an endpoint with a list of desired fields.
4) Write the returned worker payload to `worker_data.json`.

Environment variables
---------------------
Required:
- CLIENT_ID:     ADP API client ID.
- CLIENT_SECRET: ADP API client secret.

Optional:
- CERT_PATH: Path to the client certificate PEM file.
             Default: "certificate.pem"
- KEY_PATH:  Path to the client private key file.
             Default: "adp.key"

Output
------
- worker_data.json: Pretty-printed JSON containing the API response.

Notes
-----
- `desired_cols` uses ADP field paths. Your tenant permissions and the `masked`
  flag determine whether sensitive fields (e.g., birthDate) are returned.
- For large tenants, consider pagination / `max_requests=None` and writing
  output incrementally to avoid holding everything in memory.
"""

import json
import logging
import time

from dotenv import load_dotenv

from adpapi.client import AdpApiClient, AdpCredentials
from adpapi.logger import configure_logging
from adpapi.odata_filters import FilterExpression

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Fetch worker data from ADP and write it to a local JSON file.

    Steps:
    - Configure application logging.
    - Load environment variables (including optional `.env`).
    - Instantiate an `AdpApiClient` using mutual TLS credentials.
    - Call the `/hr/v2/workers` endpoint requesting a set of fields.
    - Write the API response to `worker_data.json`.
    """
    # Initialize logging once at process start (handlers/formatters live in adpapi.logger)
    configure_logging()

    # Load variables from a `.env` file (if present) into the process environment.
    # This does not override already-exported environment variables by default.
    load_dotenv()
    credentials = AdpCredentials.from_env()

    # Define which fields to request from ADP and which endpoint to call.
    # These are ADP field paths; adjust them depending on your use case and permissions.
    desired_cols = [
        "workers/associateOID",
        "workers/person/legalName",
        "workers/businessCommunication/emails",
        "workers/person/birthDate",
        "workers/workerDates/originalHireDate",
        "workers/workAssignments/reportsTo",
    ]
    endpoint = "/hr/v2/worrs"

    # Filter for just active employees
    filters = FilterExpression.field(
        "workers.workAssignments.assignmentStatus.statusCode.codeValue"
    ).eq("A")
    # Use the client as a context manager so any underlying session/resources are cleaned up.

    with AdpApiClient(credentials) as api:
        start_time = time.perf_counter()
        # Call the endpoint and return worker data.
        # `masked=False` requests unmasked fields when your ADP permissions allow it.
        # `max_requests=1` is a safety guard for examples; remove/adjust for full exports.
        workers = api.call_endpoint(
            endpoint,
            masked=True,
            page_size=10,
            max_requests=1,
            # select=desired_cols,
            filters=filters,
        )

        elapsed = time.perf_counter() - start_time
        logger.debug("Processed worker export in %.2f seconds.", elapsed)

    # Persist the returned JSON response locally for inspection / downstream processing.
    file_path = "worker_data.json"
    with open(file_path, mode="w", encoding="utf-8") as file:
        json.dump(workers, file, indent=2)
    logger.info("Wrote worker data to %s", file_path)


if __name__ == "__main__":
    main()
