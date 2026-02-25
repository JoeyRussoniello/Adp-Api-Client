# Contributing to adpapi

Thank you for your interest in contributing! This guide covers how to set up the project locally, run tests, and submit changes.

## Table of Contents

- [Contributing to adpapi](#contributing-to-adpapi)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [Getting Started](#getting-started)
  - [Development Setup](#development-setup)
  - [Running Tests](#running-tests)
  - [Linting \& Type Checking](#linting--type-checking)
  - [Submitting Changes](#submitting-changes)
  - [Commit Messages](#commit-messages)
  - [Release Process](#release-process)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/Adp-Api-Client.git
   cd Adp-Api-Client
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/JoeyRussoniello/Adp-Api-Client.git
   ```

---

## Development Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for environment and dependency management.

```bash
# Install uv (if not already installed)
pip install uv

# Create the virtual environment and install all dev dependencies
uv sync --all-extras --dev
```

Copy `.env.example` to `.env` and populate your ADP credentials for integration tests.

---

## Running Tests

```bash
# Run the full test suite (unit tests only)
uv run pytest

# Run with coverage report
uv run pytest --cov=adpapi --cov-report=term-missing

# Run including integration tests (requires real ADP credentials in .env)
uv run pytest -m golden
```

> Integration tests marked `golden` are skipped by default in CI — they require valid ADP API credentials and certificates.

---

## Linting & Type Checking

```bash
# Lint and auto-fix with ruff
uv run ruff check src/ tests/ --fix

# Format with ruff
uv run ruff format src/ tests/

# Static type checking with mypy
uv run mypy
```

CI enforces that all of the above pass before merging.

---

## Submitting Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes, including tests for any new behaviour.
3. Ensure `pytest`, `ruff check`, and `mypy` all pass locally (CI will fail and PR will be rejected if any do not pass).
4. Push your branch and open a **Pull Request** against `main`.
5. Fill in the pull request template — describe what changed and why.

Please keep PRs focused: one logical change per PR makes review faster.

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix     | When to use                              |
|------------|------------------------------------------|
| `feat:`    | New feature                              |
| `fix:`     | Bug fix                                  |
| `docs:`    | Documentation only                       |
| `refactor:`| Code change that isn't a fix or feature  |
| `test:`    | Adding or updating tests                 |
| `chore:`   | Build process, tooling, or CI changes    |

Example:
```
feat: add retry logic for transient HTTP 5xx errors
```

---

## Release Process

Releases are maintained by the project owner. If you believe a release is warranted, open an issue or note it in your PR.

1. Update the version in `pyproject.toml`.
2. Add a section to `CHANGELOG.md` following the existing format.
3. Tag the commit: `git tag vX.Y.Z && git push --tags`.
4. GitHub Actions will build and publish to PyPI automatically (if configured).
