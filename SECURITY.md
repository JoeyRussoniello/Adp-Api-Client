# Security Policy

## Supported Versions

Only the latest release on PyPI receives security fixes.

| Version | Supported |
|---------|-----------|
| Latest  | ✅        |
| Older   | ❌        |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security issue in `adpapi`, report it privately via GitHub's [Security Advisories](https://github.com/JoeyRussoniello/Adp-Api-Client/security/advisories/new) feature (under the **Security** tab of the repository).

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce (proof-of-concept if possible).
- Any suggested mitigation or fix.

You can expect an acknowledgement within **72 hours** and a resolution or status update within **14 days**.

## Scope

This library handles OAuth2 client credentials and mutual TLS (mTLS) connections with ADP. Particularly relevant areas include:

- Credential loading and storage (`AdpCredentials`)
- TLS certificate handling in `sessions.py`
- Token caching and refresh logic in `client.py`

Security contributions in these areas are especially appreciated.
