# Frontend

The frontend is the user-facing Seekr interface. It handles upload, authentication, lecture browsing, playback, notes, slide viewing, and search interactions.

## Stack

- Expo Router
- React Native Web
- TypeScript
- Zustand
- React Query
- Firebase Authentication

## Responsibilities

- user authentication
- lecture upload and status polling
- transcript and notes presentation
- search and Q&A interactions
- slide browsing and downloads
- responsive layout for web and mobile-friendly testing

## Local Run

From `frontend/`:

```bash
npm ci
npx expo start --web
```

Typical local URL:

- `http://localhost:8081`

## Environment Variables

Create `frontend/.env` and configure:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_FIREBASE_API_KEY=...
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=...
EXPO_PUBLIC_FIREBASE_PROJECT_ID=...
EXPO_PUBLIC_FIREBASE_APP_ID=...
```

For more detail, see [`../docs/local-development.md`](../docs/local-development.md).

## Frontend Checks

```bash
npm test -- --runInBand
npx tsc --noEmit
npm run reassure
```

For more detail, see:

- [`../docs/local-development.md`](../docs/local-development.md)
- [`../docs/testing.md`](../docs/testing.md)
