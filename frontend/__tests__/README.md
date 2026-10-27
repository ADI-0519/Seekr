# Frontend Tests

This directory contains the frontend test suite for Seekr.

## Coverage Areas

- screen rendering
- user interactions
- auth bootstrap behaviour
- API client behaviour
- state store behaviour
- player logic
- lightweight performance checks

## Common Commands

```bash
cd frontend
npm test -- --runInBand
npx tsc --noEmit
npm run reassure
```

For the broader testing guide, see [`../../docs/testing.md`](../../docs/testing.md).
