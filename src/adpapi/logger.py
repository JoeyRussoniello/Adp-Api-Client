"""Logging configuration for the ADP API client.

This module provides utilities for setting up and configuring logging
for the ADP API client, including file and console handlers.
"""

import logging


def configure_logging():
    logger = logging.getLogger("adpapi")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # File handler
    file_handler = logging.FileHandler("app.log", mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
