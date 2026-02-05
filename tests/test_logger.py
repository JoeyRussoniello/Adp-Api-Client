import logging
from unittest.mock import patch

import pytest

from adpapi.logger import configure_logging


@pytest.fixture
def clean_logger():
    """Provide a clean logger with saved state for restoration."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    yield root_logger

    # Restore original state
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


class TestLoggingConfiguration:
    """Test logger configuration."""

    @patch("builtins.open", create=True)
    def test_configure_logging_basic(self, mock_open, clean_logger):
        """Test basic logging configuration adds handlers."""
        clean_logger.handlers = []

        configure_logging()

        assert len(clean_logger.handlers) > 0

    @patch("builtins.open", create=True)
    def test_configure_logging_file_handler(self, mock_open, clean_logger):
        """Test that file handler is configured."""
        clean_logger.handlers = []

        configure_logging()

        file_handlers = [
            h for h in clean_logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) > 0

    @patch("builtins.open", create=True)
    def test_configure_logging_console_handler(self, mock_open, clean_logger):
        """Test that console handler is configured."""
        clean_logger.handlers = []

        configure_logging()

        console_handlers = [
            h for h in clean_logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) > 0

    @patch("builtins.open", create=True)
    def test_configure_logging_debug_level(self, mock_open, clean_logger):
        """Test that logging level is set to DEBUG."""
        clean_logger.handlers = []

        configure_logging()

        assert clean_logger.level == logging.DEBUG
