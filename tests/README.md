# Test Documentation

## Overview
This test suite provides comprehensive coverage for the ADP API Client codebase.

## Test Structure

### `test_client.py`
Tests for the main `AdpApiClient` class:
- **TestAdpApiClientInitialization**: Client initialization, credential validation, file existence checks
- **TestTokenManagement**: Token acquisition, expiration checking, automatic refresh
- **TestRetryStrategy**: Retry strategy configuration and HTTP adapter setup
- **TestRequestHeaders**: Header generation with and without masking
- **TestContextManager**: Context manager functionality for proper resource cleanup
- **TestCallEndpoint**: Endpoint validation, page size limiting, pagination
- **TestErrorHandling**: Error scenarios including token failures and JSON parsing errors

### `test_sessions.py`
Tests for the `ApiSession` class:
- **TestApiSessionInitialization**: Session setup with default and custom values
- **TestApiSessionSetters**: Parameter and data setter methods
- **TestRequestMethod**: RequestMethod enum verification
- **TestGetRequestFunction**: Request function routing for different HTTP methods
- **TestRequest**: HTTP request execution with various configurations
- **TestHttpMethods**: HTTP method wrappers (GET, POST, PUT, DELETE)
- **TestRequestParameters**: Parameter passing and configuration

### `test_logger.py`
Tests for logging configuration:
- **TestLoggingConfiguration**: Logger setup, file and console handlers, logging level

## Running Tests

### Run all tests
```bash
python -m unittest discover tests/
# or
python tests/conftest.py
```

### Run specific test file
```bash
python -m unittest tests.test_client
python -m unittest tests.test_sessions
python -m unittest tests.test_logger
```

### Run specific test class
```bash
python -m unittest tests.test_client.TestAdpApiClientInitialization
```

### Run specific test
```bash
python -m unittest tests.test_client.TestAdpApiClientInitialization.test_initialization_success
```

### Run with verbose output
```bash
python -m unittest discover tests/ -v
```

## Test Coverage

- **Client Initialization**: Credential validation, file checks, token acquisition
- **Token Management**: Acquisition, expiration detection, automatic refresh
- **Retry Strategy**: Configuration and HTTP error handling
- **Request Headers**: Masking parameter handling, header generation
- **Context Manager**: Resource cleanup and proper shutdown
- **Endpoint Calling**: Validation, pagination, error handling
- **Session Management**: HTTP methods, parameter passing, error handling
- **Logging**: Configuration, handlers, logging levels

## Mocking Strategy

Tests use `unittest.mock` to:
- Mock file system operations (`os.path.exists`)
- Mock HTTP requests and responses
- Mock session and adapter behavior
- Isolate units for focused testing

## Key Test Patterns

1. **Fixture Setup**: Each test class has `setUp()` for common initialization
2. **Isolation**: External dependencies are mocked to ensure isolated testing
3. **Error Scenarios**: Tests cover both success and failure paths
4. **Parameter Validation**: Tests verify correct handling of various inputs
5. **Integration Points**: Tests verify proper parameter passing between components

## Adding New Tests

When adding new tests:
1. Add to appropriate test file based on component
2. Use descriptive test names following pattern: `test_[scenario]_[expected_outcome]`
3. Include docstring explaining what is being tested
4. Mock external dependencies
5. Clean up resources in `tearDown()` if needed
