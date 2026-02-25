# Changelog

All notable changes to the `adpapi` package are documented in this file.

## [1.4.4] - 2026-02-25

### Added

- Automatic release configuration and example publish through `github/workflows/release.yml`  and trusted publishing

## [1.4.3] - 2026-02-25

### Fixed
- Resolved all mypy type-checking errors across the codebase
- Added `py.typed` marker for PEP 561 compliance
- Fixed `Optional` parameter types where `None` was never a valid input
- Improved type narrowing in OData filter parser (`_peek()` usage)
- Added runtime validation for missing environment variables in `AdpCredentials.from_env()`

### Added
- `types-requests` dev dependency for request stubs
- `[tool.mypy]` configuration in `pyproject.toml`

## [1.4.2] - 2026-02-24

### Fixed
- Resolved a bug that broke the context manager protocol

## [1.4.1] - 2026-02-24

### Added
- Parallelism / multithreading support — rewrote core for concurrent usage
- Test coverage for REST endpoints

### Changed
- Updated docs with parallelism instructions

## [1.4.0] - 2026-02-18

### Added
- Initial REST endpoint handler (`call_rest_endpoint`)

## [1.3.1] - 2026-02-09

### Fixed
- Improved logging on session failure
- Fixed typo

## [1.2.0] - 2026-02-06

### Breaking
- Moved credential management into its own object with helper environment variable loading
- Removed `python-dotenv` as a runtime dependency (moved to dev)

### Added
- `select` expression support in `call_endpoint`
- Tracking of headers on failed requests for debugging

### Changed
- Simplified main module
- Improved documentation and added initial use-case examples
- Added MkDocs dev dependencies for documentation generation

## [1.1.0] - 2026-02-05

### Breaking
- Renamed the `cols` parameter to `select` in `call_endpoint`

### Added
- OData filters helper module with `to_odata` conversion
- Filter integration in main module
- `cols` parameter is now optional (omit for a full data pull)

## [1.0.1] - 2026-02-05

### Changed
- Lazy header evaluation via `.get_headers()` in `ApiSession` to handle token refresh
- Moved token acquisition out of `__init__` for deferred authentication

### Added
- Automatic monofile generator and associated tooling
- Migrated test suite to pytest

## [1.0.0] - 2026-02-05

### Added
- Helper logging for masking/debugging

### Changed
- Restructured source into `src/` layout for PyPI packaging
- Updated project settings, documentation, and README

## [0.1.0] - 2026-02-04

### Added
- Initial release — transferred from mono-repo
- Began refactoring for PyPI distribution
