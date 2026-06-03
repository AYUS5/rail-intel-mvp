# Rail Intel Frontend

Next.js 14 UI for searching railway route intelligence and comparing hidden seat opportunities.

## Run

```powershell
copy .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

The backend should be running at `NEXT_PUBLIC_RAIL_INTEL_API_BASE_URL`, which defaults to `http://127.0.0.1:8000`.

## Checks

```powershell
npm run typecheck
npm run lint
npm run build
```

## Environment

- `NEXT_PUBLIC_RAIL_INTEL_API_BASE_URL`
- `NEXT_PUBLIC_RAIL_INTEL_REQUEST_TIMEOUT_MS`

