"""
Test suite runner configuration for ADP API Client tests.

Run all tests:
    python -m pytest tests/
    or
    python -m unittest discover tests/

Run specific test file:
    python -m unittest tests.test_client
    python -m unittest tests.test_sessions
    python -m unittest tests.test_logger

Run specific test class:
    python -m unittest tests.test_client.TestAdpApiClientInitialization

Run specific test method:
    python -m unittest tests.test_client.TestAdpApiClientInitialization.test_initialization_success
"""

import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = loader.discover(".", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
