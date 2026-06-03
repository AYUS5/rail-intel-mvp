# Indian Railways Seat Availability Intelligence MVP

Backend-first MVP for discovering hidden confirmed-seat opportunities across train route segments.

This is not a ticket booking bot. It does not automate IRCTC login, captcha solving, OTP bypassing, or ticket purchasing. The system is designed as a travel intelligence platform for availability analysis, route optimization, monitoring, and human-readable recommendations.

## What It Does

- Searches trains for a source, destination, date, and class.
- Reads the ordered route for each train.
- Checks direct availability and relevant intermediate station pairs.
- Detects hidden segments such as `NDLS -> KOTA` or `MTJ -> MMCT` when `NDLS -> MMCT` is waitlisted.
- Scores opportunities by availability quality, route overlap, station mismatch, and estimated confirmation probability.
- Supports monitor creation and manual monitor checks.
- Provides an AI explanation interface with a deterministic template provider by default.

## Project Structure

```text
app/
  adapters/             external payload normalization into internal DTOs
  api_client/           reusable async HTTP client with retries and pooling
  api/                  FastAPI routes, dependencies, response mappers
  core/                 settings and logging
  db/                   async SQLAlchemy session setup
  models/               PostgreSQL SQLAlchemy models
  provider_clients/     external railway endpoint clients
  repositories/         provider, fallback, cache, monitor, and snapshot boundaries
  schemas/              Pydantic API contracts
  services/             route analysis, cache, snapshots, recommendations, AI, monitoring
  utils/                scoring helpers
  workers/              Celery app and async task entry points
docs/
  architecture.md       architecture and algorithm notes
  database_schema.sql   PostgreSQL schema
tests/                  focused tests for providers, caching, route analysis, scoring, and API
migrations/             SQL migration scripts
frontend/               Next.js route intelligence UI
```

## Architecture

The API layer stays thin. It validates requests, calls services, and maps domain objects to response schemas.

The route intelligence lives in `RouteAnalysisService`. It depends on `RailwayService`, which depends on `RailwayProviderInterface`. Providers are swappable through dependency injection:

- `MockRailwayProvider` for local deterministic data.
- `RealRailwayProvider` for sanctioned external APIs through provider-client and response-adapter layers.
- `CachedRailwayProvider` for Redis or memory caching.
- `FallbackRailwayProvider` for graceful degradation when the primary provider fails.

Real provider flow:

```text
RealRailwayProvider
  -> RailwayProviderClient
  -> AsyncHttpClient
  -> sanctioned external API

external response
  -> RailwayResponseAdapter
  -> TrainRoute / AvailabilitySnapshot
```

`AsyncHttpClient` uses `httpx.AsyncClient` with connection pooling, request logging, request ID propagation, timeout handling, retryable status handling, and exponential backoff.

The AI layer is also behind an interface. `TemplateExplanationProvider` is the default. `OpenAIExplanationProvider` can be enabled with environment variables, and a local model provider can later implement the same `summarize()` method.

## Hidden Segment Detection

For each train:

1. Locate source and destination on the ordered route.
2. Fetch direct availability.
3. Generate candidate station pairs within a bounded window around the requested route.
4. Skip the direct pair.
5. Prune pairs with no route overlap or weak overlap.
6. Fetch availability for the remaining pairs concurrently with timeout protection.
7. Score each pair for usefulness.
8. Return the strongest opportunities and recommendations.

The pruning window prevents route-wide pair explosion on long trains while preserving useful nearby and intermediate station options.

## Caching And Performance

`CachedRailwayProvider` caches train searches, train routes, availability queries, and station metadata. It uses versioned keys such as `railintel:v1:availability:{train}:{source}:{destination}:{date}:{class}`.

On a cache miss, the cache layer acquires a per-key single-flight lock before calling the upstream provider. This prevents duplicate external requests when multiple searches ask for the same segment at once.

Route analysis now batches candidate availability requests and fetches them with bounded `asyncio.gather()`. Concurrency and timeouts are controlled by:

- `ROUTE_AVAILABILITY_CONCURRENCY`
- `ROUTE_AVAILABILITY_TIMEOUT_SECONDS`

## Observability

The API middleware assigns or propagates `X-Request-ID` and returns it on every HTTP response. Structured logs include:

- API response time
- provider latency and retry attempts
- cache hit/miss/set events and in-process hit rate
- route-analysis duration
- candidate availability batch duration
- snapshot persistence and meaningful-change events

## Historical Snapshots

The `availability_snapshots` table stores append-only availability observations for future prediction work:

- `observed_at`
- `train_number`
- `source_station_code`
- `destination_station_code`
- `travel_date`
- `travel_class`
- `status`
- `available_count`
- `rac_count`
- `waitlist_count`
- `provider`

`AvailabilitySnapshotService` stores snapshots and marks meaningful changes such as status movement, WL movement, RAC movement, or seats becoming available.

Apply the standalone migration from `migrations/001_availability_snapshots.sql` if you are upgrading an existing database. Fresh Docker databases load `docs/database_schema.sql`.

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`.

## Run With Docker

```bash
copy .env.example .env  # optional overrides
docker compose up --build
```

API: `http://localhost:8000`

PostgreSQL and Redis are included. The SQL schema is mounted from `docs/database_schema.sql`.

## Frontend

The usable route-search UI lives in `frontend/`.

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. The frontend calls the backend at `NEXT_PUBLIC_RAIL_INTEL_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.

Frontend checks:

```bash
npm run typecheck
npm run lint
npm run build
```

## Main Endpoints

- `GET /api/v1/health`
- `POST /api/v1/search/trains`
- `POST /api/v1/search/hidden-segments`
- `POST /api/v1/monitors`
- `GET /api/v1/monitors`
- `GET /api/v1/monitors/{monitor_id}`
- `POST /api/v1/monitors/{monitor_id}/check`
- `DELETE /api/v1/monitors/{monitor_id}`

## Example Search Request

```json
{
  "source_station": "Delhi",
  "destination_station": "Mumbai",
  "travel_date": "2026-06-15",
  "travel_class": "3AC",
  "max_results": 5,
  "include_explanations": true
}
```

## Example Search Response Excerpt

```json
{
  "query": {
    "source_station": "DELHI",
    "destination_station": "MUMBAI",
    "travel_date": "2026-06-15",
    "travel_class": "3AC"
  },
  "results": [
    {
      "train": {
        "number": "12952",
        "name": "Mumbai Rajdhani Express"
      },
      "direct_availability": {
        "status": "WAITLIST",
        "waitlist_count": 120,
        "source_station_code": "NDLS",
        "destination_station_code": "MMCT"
      },
      "hidden_segments": [
        {
          "source": {"code": "MTJ", "name": "Mathura Junction"},
          "destination": {"code": "MMCT", "name": "Mumbai Central"},
          "availability": {"status": "AVAILABLE", "available_count": 9},
          "coverage_type": "LATER_BOARDING_TO_DESTINATION",
          "usefulness_score": 0.82
        }
      ],
      "explanation": "Direct ticket availability is weak for this train. Best intelligence signal: Mathura Junction to Mumbai Central, where confirmed seats are visible."
    }
  ]
}
```

## Example Monitor Request

```json
{
  "source_station": "Delhi",
  "destination_station": "Mumbai",
  "travel_date": "2026-06-15",
  "travel_class": "3AC",
  "train_number": "12952",
  "threshold_status": "RAC",
  "notification_target": "ops@example.com"
}
```

## Environment Variables

See `.env.example`.

Important switches:

- `RAILWAY_PROVIDER=mock`, `real`, or `real_with_mock_fallback`
- `REAL_PROVIDER_BASE_URL=...`
- `REAL_PROVIDER_SEARCH_PATH=/trains/search`
- `REAL_PROVIDER_ROUTE_PATH_TEMPLATE=/trains/{train_number}/route`
- `REAL_PROVIDER_AVAILABILITY_PATH=/availability`
- `REAL_PROVIDER_MAX_CONNECTIONS=100`
- `REAL_PROVIDER_MAX_KEEPALIVE_CONNECTIONS=20`
- `ENABLE_PROVIDER_CACHE=true`
- `CACHE_BACKEND=memory` or `redis`
- `AI_PROVIDER=template` or `openai`
- `OPENAI_API_KEY=...`
- `ROUTE_MAX_STATION_EXTENSION=2`
- `ROUTE_MIN_OVERLAP_RATIO=0.35`
- `ROUTE_AVAILABILITY_CONCURRENCY=12`
- `AVAILABILITY_CACHE_TTL_SECONDS=60`

## Worker Tasks

Celery tasks:

- `monitor_availability`
- `capture_monitor_snapshots`

Example enqueue:

```bash
celery -A app.workers.celery_app.celery_app call capture_monitor_snapshots --args='[{"source_station":"Delhi","destination_station":"Mumbai","travel_date":"2026-06-15","travel_class":"3AC","threshold_status":"RAC"}]'
```

Example beat schedule:

```python
celery_app.conf.beat_schedule = {
    "capture-monitored-routes-every-10-minutes": {
        "task": "capture_monitor_snapshots",
        "schedule": 600.0,
        "args": ({
            "source_station": "Delhi",
            "destination_station": "Mumbai",
            "travel_date": "2026-06-15",
            "travel_class": "3AC",
            "threshold_status": "RAC"
        },),
    }
}
```

## Prediction Foundation

No ML model is implemented yet. The codebase now includes interfaces for:

- `ConfirmationProbabilityPredictor`
- `WaitlistMovementModel`
- `QuotaBehaviorAnalyzer`
- `SeasonalTrendAnalyzer`

These are designed to consume historical snapshots when predictive modeling is added.

## Tests

```bash
pytest
```

## Phased Implementation Status

Phase 1 implemented:

- Project setup
- API structure
- Mock train search service
- Route graph logic
- Hidden segment detection

Phase 2 scaffolded:

- Recommendation scoring
- Monitoring service
- Redis and Celery setup
- Concurrent availability fetching
- Provider caching

Phase 3 scaffolded:

- AI explanation provider boundary
- Notification service boundary
- Dockerized production shape
- Historical snapshot storage
- Future prediction interfaces

## Safety Constraints

Future provider implementations must use compliant data sources such as sanctioned APIs, cached public datasets, partner feeds, or manual imports. Do not add logic that logs in to IRCTC, solves captchas, bypasses OTP, scrapes aggressively, or automates purchase flows.
