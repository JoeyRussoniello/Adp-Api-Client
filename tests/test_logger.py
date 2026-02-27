import logging
from unittest.mock import MagicMock, patch

import pytest

from adpapi.logger import configure_logging


@pytest.fixture
def clean_logger():
    """Provide a clean adpapi logger with saved state for restoration."""
    adpapi_logger = logging.getLogger("adpapi")
    original_handlers = adpapi_logger.handlers[:]
    original_level = adpapi_logger.level

    adpapi_logger.handlers = []
    yield adpapi_logger

    # Restore original state
    adpapi_logger.handlers = original_handlers
    adpapi_logger.setLevel(original_level)


class TestLoggingConfiguration:
    """Test logger configuration."""

    @patch("logging.FileHandler", return_value=MagicMock(spec=logging.FileHandler))
    def test_configure_logging_basic(self, mock_file_handler, clean_logger):
        """Test basic logging configuration adds handlers."""
        configure_logging()

        assert len(clean_logger.handlers) > 0

    @patch("logging.FileHandler", return_value=MagicMock(spec=logging.FileHandler))
    def test_configure_logging_file_handler(self, mock_file_handler, clean_logger):
        """Test that file handler is configured."""
        configure_logging()

        assert mock_file_handler.return_value in clean_logger.handlers

    @patch("logging.FileHandler", return_value=MagicMock(spec=logging.FileHandler))
    def test_configure_logging_console_handler(self, mock_file_handler, clean_logger):
        """Test that console handler is configured."""
        configure_logging()

        console_handlers = [
            h for h in clean_logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) > 0

    @patch("logging.FileHandler", return_value=MagicMock(spec=logging.FileHandler))
    def test_configure_logging_debug_level(self, mock_file_handler, clean_logger):
        """Test that logging level is set to DEBUG."""
        configure_logging()

        assert clean_logger.level == logging.DEBUG

    @patch("logging.FileHandler", return_value=MagicMock(spec=logging.FileHandler))
    def test_root_logger_unaffected(self, mock_file_handler, clean_logger):
        """Test that the root logger is not modified by configure_logging."""
        root_logger = logging.getLogger()
        original_root_handlers = root_logger.handlers[:]
        original_root_level = root_logger.level

        configure_logging()

        assert root_logger.handlers == original_root_handlers
        assert root_logger.level == original_root_level
