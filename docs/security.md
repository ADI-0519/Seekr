# Security

Seekr is a lecture search engine and follows a small set of practical security rules for code, configuration, and disclosure.

## General Principles

- Do not commit secrets, credentials, private keys, or API tokens.
- Use environment variables or local `.env` files for configuration.
- Keep production credentials separate from development configuration.
- Prefer least-privilege configuration for storage, databases, and external services.
- Treat logs as potentially sensitive and avoid exposing tokens, signed URLs, or secret values.

## Secrets And Configuration

- Keep local secrets in untracked environment files.
- Do not hardcode API keys, service credentials, or private endpoints into source files.
- Rotate any credential immediately if it is exposed accidentally.
- Use separate credentials for development and deployment environments where possible.

## Safe Public Documentation

- Use placeholder values in README files and setup examples.
- Do not publish internal-only hostnames, personal machine IPs, or signed media URLs.
- Keep public deployment notes high-level unless there is a clear reason to expose more detail.

## Development Hygiene

- Review changes before committing, especially environment and config files.
- Avoid adding debug output that may expose sensitive data.
- Prefer authenticated and scoped API access over public unrestricted routes.
- Validate ownership and access boundaries when adding new data-access features.

## Dependencies

- Keep dependencies reasonably up to date.
- Treat new infrastructure or ML dependencies carefully, especially if they introduce networked services, model downloads, or executable binaries.

## Reporting

If you discover a security issue in Seekr, report it privately to the project team rather than opening a public issue with sensitive details.
