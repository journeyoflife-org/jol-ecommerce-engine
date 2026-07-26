# Contributing to JOL Commerce Engine

## Code of Conduct

All contributors must follow our security and compliance requirements. This is a payment processing system — security is non-negotiable.

## Development Setup

```bash
make dev          # Install all dependencies + pre-commit hooks
make run          # Start development server
make test         # Run all tests
make security     # Run security scanners
```

## Pull Request Process

1. Create a feature branch from `develop`
2. Write tests for all new functionality
3. Run `make lint && make typecheck && make test && make security`
4. Fill out the PR template completely
5. Request review from appropriate CODEOWNERS

## Critical Rules

### Payment Module Changes

Any PR touching `/payments/`, `/audit/`, or `/frontend/src/payment/` requires:
- Security team co-approval (enforced via CODEOWNERS)
- `payment-change.yml` issue filed
- Confirmation that no raw card data is processed server-side

### VAT Rate Changes

- Must update `country_rates.py` with effective dates
- Must add/update corresponding test files in `tests/tax/`
- Must update `docs/vat-matrix.md`

### Audit Log Changes

- Must maintain append-only semantics
- Must not introduce PII into log entries
- Must pass `test_audit_log_integrity.py`

## Testing Requirements

- Unit tests for new business logic
- Integration tests for API endpoints
- VAT tests for any tax calculation changes
- Security tests must always pass (`test_no_raw_card_data.py`)
- Minimum 85% code coverage

## Commit Messages

- Use conventional commits: `feat:`, `fix:`, `docs:`, `security:`, `test:`
- Reference issue numbers where applicable
- Never include secrets, tokens, or card data in commit messages
