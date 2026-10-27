# Contributing To Seekr

This repository is organised to keep feature work focused, reviewable, and safe to merge.

## Ground Rules

- Open a pull request for every meaningful change.
- Do not push directly to `main` or `develop`.
- Keep commits small, focused, and easy to review.
- Update documentation when behaviour, setup, or commands change.
- Never commit secrets, private keys, tokens, or personal environment details.

## Branching

- Create a feature or fix branch from the current shared branch.
- Use clear branch names that describe the work.
- Merge `develop` into your branch when needed instead of working against stale code for too long.

## Before Opening A Pull Request

- Run the checks relevant to your changes.
- Make sure the app still starts locally if you touched setup or runtime code.
- Re-read the diff and remove debug logs, temporary comments, and dead code.
- Confirm any new environment variables or setup steps are documented.

## Common Checks

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

For fuller local setup and testing notes, see:

- [`README.md`](README.md)
- [`docs/local-development.md`](docs/local-development.md)
- [`docs/testing.md`](docs/testing.md)

## Pull Request Expectations

- Explain what changed and why.
- Call out any tradeoffs, follow-ups, or known limitations.
- Keep the PR scope tight when possible.
- Wait for checks to pass before asking for final review.

## Documentation

If your change affects setup, runtime behaviour, architecture, or testing, update the relevant docs in:

- [`README.md`](README.md)
- [`docs/`](docs/)
- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)

## Questions And Larger Changes

For larger refactors or workflow changes, align on the approach early so implementation and review stay smooth.
