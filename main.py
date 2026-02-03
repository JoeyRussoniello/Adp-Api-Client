import json
import logging
import os
import time

from dotenv import load_dotenv

from client import AdpApiClient
from logger import configure_logging

logger = logging.getLogger(__name__)

def main():
    configure_logging()
    # Load Environment Variables
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    cert_path = os.getenv("CERT_PATH", "certificate.pem")
    key_path = os.getenv("KEY_PATH", "adp.key")

    # Get all workers
    desired_cols = [
        "workers/person/legalName",
        "workers/person/birthDate",
        "workers/workAssignments/reportsTo",
        "workers/associateOID",
        "workers/businessCommunication/emails",
    ]
    endpoint = "/hr/v2/workers"

    with AdpApiClient(client_id, client_secret, cert_path, key_path) as api:
        start_time = time.perf_counter()
        workers = api.call_endpoint(endpoint, desired_cols, masked=False, max_requests = 1)
        end_time = time.perf_counter()
        logger.debug(f"Processed all workers in {(end_time - start_time):.2f} seconds.")

    # Write to JSON
    file_path = "worker_data.json"
    with open(file_path, mode="w", encoding="utf-8") as file:
        logger.info(f"Wrote worker data to {file_path}")
        json.dump(workers, file, indent=2)


if __name__ == "__main__":
    main()
