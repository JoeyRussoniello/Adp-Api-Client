"""Logging configuration for the ADP API client.

This module provides utilities for setting up and configuring logging
for the ADP API client, including file and console handlers.
"""

import logging


def configure_logging():
    logging.basicConfig(
        filename="app.log",
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(console_handler)
