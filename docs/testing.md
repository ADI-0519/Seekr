# Testing

## Testing Strategy

Seekr uses several complementary layers of validation:

- backend unit tests
- backend integration tests
- frontend unit and interaction tests
- frontend performance checks
- static analysis and formatting

Test-suite notes live alongside the tests themselves:

- [`../backend/tests/README.md`](../backend/tests/README.md)
- [`../frontend/__tests__/README.md`](../frontend/__tests__/README.md)

## Quick Checks

These are the most useful day-to-day commands while developing.

### Backend

```bash
cd backend
../.venv/bin/pytest -q -m "not integration"
../.venv/bin/mypy .
```

### Frontend

```bash
cd frontend
npm test -- --runInBand
npx tsc --noEmit
```

## Extended Checks

### Backend Integration Tests

```bash
cd backend
../.venv/bin/pytest -q -m integration
```

### Frontend Performance Checks

```bash
cd frontend
npm run reassure
```

### Repository Hooks And Formatting

```bash
./.venv/bin/pre-commit run --all-files
```

## Notes

- Integration tests expect the local infrastructure stack to be running.
- ML-heavy flows are more expensive to validate end-to-end, so focused smoke tests are useful alongside the automated suite.
- Coverage gates and stricter CI-only checks can be layered on top of these commands without making the local workflow heavier than necessary.
