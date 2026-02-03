import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

from logger import configure_logging


class TestLoggingConfiguration(unittest.TestCase):
    """Test logger configuration."""

    def setUp(self):
        """Set up test fixtures."""
        # Get the root logger
        self.root_logger = logging.getLogger()
        # Store original handlers
        self.original_handlers = self.root_logger.handlers[:]

    def tearDown(self):
        """Clean up after tests."""
        # Restore original handlers
        self.root_logger.handlers = self.original_handlers

    @patch("builtins.open", create=True)
    def test_configure_logging_basic(self, mock_open):
        """Test basic logging configuration."""
        # Reset handlers
        self.root_logger.handlers = []
        
        configure_logging()

        # Check that logger is configured
        self.assertGreater(len(self.root_logger.handlers), 0)

    @patch("builtins.open", create=True)
    def test_configure_logging_file_handler(self, mock_open):
        """Test that file handler is configured."""
        # Reset handlers
        self.root_logger.handlers = []
        
        configure_logging()

        # Check for file handler
        file_handlers = [
            h for h in self.root_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        self.assertGreater(len(file_handlers), 0)

    @patch("builtins.open", create=True)
    def test_configure_logging_console_handler(self, mock_open):
        """Test that console handler is configured."""
        # Reset handlers
        self.root_logger.handlers = []
        
        configure_logging()

        # Check for console handler
        console_handlers = [
            h for h in self.root_logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        self.assertGreater(len(console_handlers), 0)

    @patch("builtins.open", create=True)
    def test_configure_logging_debug_level(self, mock_open):
        """Test that logging level is set to DEBUG."""
        # Reset handlers
        self.root_logger.handlers = []
        
        configure_logging()

        # Check that debug level is set
        self.assertEqual(self.root_logger.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
