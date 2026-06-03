# Architecture

This MVP is a travel intelligence backend. It analyzes train routes and seat status signals; it does not automate IRCTC login, captcha solving, OTP flows, or ticket purchasing.

## Layers

- `app/api`: FastAPI routes, dependency wiring, and response mapping.
- `app/api_client`: reusable async HTTP client infrastructure with retries, pooling, request IDs, timeouts, and structured errors.
- `app/provider_clients`: external railway API client layer. It knows endpoint paths and query parameters, but not route-analysis rules.
- `app/adapters`: external payload normalization into internal DTOs.
- `app/schemas`: Pydantic request and response contracts.
- `app/services`: business use cases: railway lookup, route analysis, recommendations, monitoring, snapshots, notifications, caching, prediction interfaces, and AI explanations.
- `app/repositories`: provider and persistence boundaries. The MVP ships with deterministic mock data, a real HTTP provider adapter, a cache decorator, and a fallback provider.
- `app/models`: SQLAlchemy models for PostgreSQL.
- `app/workers`: Celery worker app and monitoring task entry points.
- `app/utils`: scoring and route-analysis helpers.

## Request Flow

1. API receives a search request with source, destination, date, and class.
2. `RailwayService` asks the configured `RailwayProviderInterface` for trains serving the requested station pair.
3. `RouteAnalysisService` locates the requested station indices on each train route.
4. The engine generates only route pairs inside a bounded station window around the user route.
5. It prunes pairs with insufficient overlap unless they preserve the source or destination boundary.
6. It fetches candidate availability concurrently with bounded `asyncio.gather()` calls and timeout protection.
7. `RecommendationService` ranks the best opportunities.
8. `AIExplanationService` creates a human-readable summary through a provider interface.

## Hidden Segment Algorithm

For each train:

1. Read ordered station stops.
2. Find the requested source and destination indices.
3. Compute direct route availability.
4. Build a candidate window from `source - extension` through `destination + extension`.
5. Generate candidate source-destination station pairs in that window.
6. Skip the direct pair.
7. Calculate overlap with the requested route.
8. Prune candidates with no overlap or weak overlap.
9. Fetch candidate availability concurrently with a semaphore limit.
10. Score by availability quality, confirmation probability, overlap, and station mismatch.
11. Return the highest-value segments.

This avoids a full route-wide pair explosion on long routes while still finding nearby quota and intermediate segment opportunities.

## Provider Abstraction

`RailwayProviderInterface` supports:

- `search_trains()`
- `get_train_route()`
- `get_availability()`

Provider implementations:

- `MockRailwayProvider`: deterministic local data for development and tests.
- `RealRailwayProvider`: generic HTTP adapter for sanctioned external railway data sources.
- `CachedRailwayProvider`: Redis or memory cache decorator.
- `FallbackRailwayProvider`: tries the primary provider and falls back to another provider when provider-specific failures occur.

Real provider flow:

```text
RealRailwayProvider
  -> RailwayProviderClient
  -> AsyncHttpClient
  -> external sanctioned API

external payload
  -> RailwayResponseAdapter
  -> TrainRoute / AvailabilitySnapshot
```

The HTTP client includes retry logic, exponential backoff, timeout handling, connection pooling, request ID propagation, provider latency logs, and structured errors. Vendor-specific response mapping should stay inside provider clients and adapters, not route analysis or recommendation services.

Endpoint paths are configurable:

- `REAL_PROVIDER_SEARCH_PATH`
- `REAL_PROVIDER_ROUTE_PATH_TEMPLATE`
- `REAL_PROVIDER_AVAILABILITY_PATH`

## Caching Flow

Cache keys use a versioned prefix:

- `railintel:v1:route:{train_number}`
- `railintel:v1:availability:{train}:{source}:{destination}:{date}:{class}`
- `railintel:v1:station:{station_code}`
- `railintel:v1:search:{source}:{destination}:{date}:{class}`

`CachedRailwayProvider` reads the cache first. On a miss, it acquires a per-key single-flight lock, rechecks the cache, calls the wrapped provider, writes the result with TTL, and releases the lock. This avoids duplicate upstream requests during concurrent searches.

Cache hit rate is tracked in-process and emitted in structured logs. Invalidation is explicit for availability through `invalidate_availability()`. Routes and station metadata are long-TTL caches and should be invalidated when route datasets are refreshed.

## Historical Snapshots

`availability_snapshots` is append-only time-series storage for prediction foundations. Each row stores:

- observation timestamp
- train number
- source and destination station code
- travel date and class
- availability status
- available, RAC, and waitlist counts
- provider name

`AvailabilitySnapshotService` stores snapshots and detects meaningful changes such as status movement, WL movement, RAC movement, or newly available seats.

## Workers

Celery tasks support monitor polling and snapshot capture:

- `monitor_availability`
- `capture_monitor_snapshots`

Both tasks use retry backoff and log snapshot/change counts. Production deployments should load monitors from PostgreSQL and dispatch notifications through a durable notification provider.

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

## Observability

The service logs:

- HTTP request duration through middleware.
- Search and per-train route analysis duration.
- Candidate availability batch duration and concurrency limit.
- Provider HTTP latency, retries, and failures.
- Cache hits, misses, writes, and read/write errors.
- Snapshot storage and meaningful change detection.
- Domain events emitted by monitoring workers.

Every inbound HTTP response includes `X-Request-ID`. The request ID is propagated through provider calls and logs using context variables. Logs use structured `extra` fields so they can be shipped to systems such as Loki, Datadog, CloudWatch, or OpenTelemetry collectors.

## Prediction Foundation

Prediction code is interface-only for now. Future implementations can plug into:

- `ConfirmationProbabilityPredictor`
- `WaitlistMovementModel`
- `QuotaBehaviorAnalyzer`
- `SeasonalTrendAnalyzer`

These interfaces consume current context plus historical snapshot data. No ML model is implemented yet.

## AI Provider Boundary

`AIExplanationService` depends on an `ExplanationProvider` interface. The default provider is template-based and deterministic. The OpenAI provider can be enabled with environment variables, and local model providers can later implement the same interface.
