# Swat Flood Early-Warning System — Architecture & Rebuild Plan

**Scope:** Backend + Web Portal + Mobile App (ML model excluded — already trained and frozen).
**Goal:** FYP-defense-grade *and* commercialization-ready. Elite OOP, clean architecture, and DSA used where it's genuinely load-bearing — not decorative.
**Owner:** Muhammad Muzzammil (backend, Next.js web, Flutter mobile). Teammate owns the ML model (XGBoost, done).

---

## 1. Guiding Principles

1. **Domain-first, framework-second.** Business rules (risk classification, escalation, alerting) live in plain Python/Dart classes with zero framework imports. FastAPI/Flutter widgets are delivery mechanisms, not the app.
2. **One backend, two clients.** Web and mobile never talk to each other or duplicate logic — everything flows through one versioned REST/WebSocket API.
3. **Config over hardcoding.** Zones (Kalam/Bahrain/Madyan/Mingora), thresholds, and escalation rules live in DB-backed config, not Python constants — this is what makes it commercializable to a *different* river basin later without a rewrite.
4. **Every DSA choice must earn its place.** Use a real data structure when it solves a real problem in this domain (see §4). No "add a linked list to look smart."
5. **Secrets never touch git.** Full stop — this is already broken in the current prototype and is priority #0.

---

## 2. Backend Architecture (FastAPI, Python)

### 2.1 Layered / Clean Architecture

```
backend/
├── src/
│   ├── domain/                  # Pure Python. No FastAPI, no SQLAlchemy imports.
│   │   ├── entities/            # SensorReading, Zone, RiskAssessment, Alert, User...
│   │   ├── value_objects/       # WaterLevel, RiskTier (enum), Coordinates, RainfallWindow
│   │   ├── services/            # RiskEngine, EscalationEngine, AlertDispatcher (interfaces)
│   │   └── exceptions/          # DomainError hierarchy
│   │
│   ├── application/              # Use cases — orchestrate domain + ports
│   │   ├── use_cases/           # IngestTelemetry, AssessZoneRisk, ModerateReport, IssueOverride
│   │   ├── ports/                # Abstract interfaces: WeatherProvider, NotificationSender, ZoneRepository
│   │   └── dto/                  # Request/response DTOs (framework-agnostic)
│   │
│   ├── infrastructure/           # Concrete implementations of ports
│   │   ├── db/                   # SQLAlchemy 2.0 async models, repositories, Alembic
│   │   ├── weather/               # OpenMeteoAdapter, OpenWeatherAdapter (implements WeatherProvider)
│   │   ├── cache/                 # Redis client, LRU wrapper
│   │   ├── notifications/         # FCMAdapter (implements NotificationSender)
│   │   └── auth/                  # JWT, password hashing (argon2)
│   │
│   └── interfaces/                # Delivery layer
│       ├── http/                  # FastAPI routers — thin, call use cases only
│       ├── websocket/             # Live risk-update channel
│       └── schemas/               # Pydantic request/response models
│
├── tests/
│   ├── unit/                      # domain + application, no DB/network
│   ├── integration/               # real Postgres (testcontainers), real Redis
│   └── contract/                  # API schema snapshot tests
├── alembic/
├── docker-compose.yml
└── pyproject.toml
```

**Why this matters for a viva:** you can point at `domain/services/risk_engine.py` and say "this has zero dependency on FastAPI or the database — it's independently unit-testable and portable." That's the actual definition of clean architecture, not just folder names.

### 2.2 Core domain model (replaces the current flat table dump)

- `Zone` (id, name, geometry [PostGIS], upstream_zone_id — self-referential, for escalation)
- `SensorReading` (zone_id, water_level, timestamp, source: real|test)
- `WeatherSnapshot` (zone_id, precipitation_mm, fetched_at, ttl)
- `RiskAssessment` (zone_id, tier: LOW|MEDIUM|HIGH|DANGER, probability, explanation, computed_at) — versioned, append-only, never mutated
- `Alert` (CAP-inspired: severity, certainty, urgency, area, headline, description, sent_at)
- `CommunityReport`, `ManualOverride`, `User`, `APIKey`, `AuditLogEntry`

Everything append-only where it represents a historical fact (readings, assessments, alerts). Nothing gets UPDATE'd except live state (inventory quantities, user profile).

### 2.3 Config-driven zones (commercialization hook)

Right now "Kalam/Bahrain/Madyan/Mingora" and their thresholds are hardcoded in `risk_engine.py`. Move to a `zones` + `zone_thresholds` table. This single change is what lets you say in your defense (and to any future buyer/NDMA pilot) *"this isn't a Swat-only script — it's a configurable early-warning platform we deployed for Swat."*

---

## 3. Web Portal (Next.js + TypeScript)

```
web/
├── app/                          # App Router
│   ├── (public)/dashboard/       # No auth: main dashboard, GIS map, zone detail, analytics
│   ├── (admin)/moderation/       # Auth-gated: reports, overrides, sensors, users
│   └── login/
├── features/                     # Feature-first (matches your existing preference)
│   ├── risk-dashboard/
│   │   ├── components/
│   │   ├── hooks/                # useZoneRisk (TanStack Query)
│   │   └── api/                  # typed fetch layer, generated from OpenAPI
│   ├── gis-map/
│   ├── community-reports/
│   ├── manual-override/
│   └── auth/
├── shared/
│   ├── ui/                       # shadcn/ui-based design system
│   ├── ws/                       # WebSocket client (live risk updates)
│   └── types/                    # generated from backend OpenAPI schema — single source of truth
```

Key upgrades vs. the current React/Vite prototype:
- **TypeScript strict**, types generated from the backend's OpenAPI spec (`openapi-typescript`) — no hand-maintained duplicate interfaces, no drift.
- **TanStack Query** for server state (cache invalidation, retries, background refetch) instead of manual `fetch` + `useState`.
- **WebSocket subscription** for live zone risk instead of polling.
- **Leaflet/MapLibre with PostGIS-backed geometry** for the GIS layer (matches your existing PostGIS familiarity).

---

## 4. Mobile App (Flutter) — clean architecture + real DSA use

```
lib/
├── core/
│   ├── network/                  # Dio client, interceptors (auth, retry, offline-queue)
│   ├── cache/                    # Hive/sqflite-backed offline cache
│   └── di/                       # get_it service locator
├── features/
│   ├── dashboard/
│   │   ├── data/                 # repository impl, DTOs
│   │   ├── domain/                # entities, repository interface, use cases
│   │   └── presentation/          # Riverpod/Bloc, widgets
│   ├── gis_map/
│   ├── zone_detail/
│   ├── alerts/
│   ├── community_reporting/
│   └── settings/
```

- **State management:** Riverpod (testable providers, no BuildContext-coupled singletons).
- **Offline-first:** repository pattern — UI never talks to Dio directly, always through a repository that decides cache vs. network.
- **Nearest-zone detection** uses a proper spatial structure (see §5) instead of a linear distance loop over 4 hardcoded zones — trivial now, matters the moment you add more zones/basins.

---

## 5. Where DSA is *actually* the right tool (not decoration)

| Problem in this domain | Data structure / algorithm | Why it's the real answer |
|---|---|---|
| Nearest-zone-to-user detection | Geospatial index (PostGIS GIST, or client-side k-d tree) | O(log n) nearest-neighbor instead of O(n) distance loop — matters once you're not hardcoded to 4 zones |
| Kalam-rain → Mingora-risk cascading escalation | Directed graph over `Zone.upstream_zone_id`, BFS/topological propagation | Escalation is genuinely a graph-traversal problem, not an if/else chain — and it generalizes to any river network shape |
| Alert dispatch under load (many zones escalate at once) | Priority queue keyed by severity | Danger-tier alerts must be processed and pushed before Low-tier ones |
| Weather API caching (avoid rate-limit/cost blowup) | TTL-based LRU cache (Redis with expiry, or `functools.lru_cache` equivalent) | Real cost/rate-limit constraint, not academic |
| Rainfall trend (7-day rolling window) | Fixed-size deque / ring buffer | O(1) push, natural fit for "last N readings" |
| API rate limiting per key | Token bucket / sliding-window counter (Redis) | Standard, correct approach — not a toy counter |
| Community report spam/duplicate detection | Simple content hashing + geo/time-bucket dedup | Prevents the same report being spammed 50x from one device |

Each of these is a natural, defensible answer to a real constraint — good material for a viva question like "why did you choose this structure here?"

---

## 6. Cross-cutting concerns (what makes it "industrial")

- **Security:** argon2 password hashing, JWT access + refresh tokens, RBAC via decorator/dependency, API-key rotation, secrets via `.env` + `.gitignore` (never committed), input validation at the schema boundary.
- **Migrations:** Alembic from day one — no more manual `DROP TABLE` on startup.
- **Testing:** unit tests on domain/application layers (fast, no DB), integration tests against a real Postgres via testcontainers, contract tests on the API schema.
- **CI/CD:** GitHub Actions — lint (ruff), type-check (mypy), test, build Docker image on every PR.
- **Observability:** structured logging (structlog), error tracking (Sentry free tier is fine), basic Prometheus metrics if time allows.
- **Containerization:** Docker Compose (Postgres + PostGIS, Redis, backend) — one-command local setup, and it's what a real deployment/pilot would need anyway.
- **CAP-inspired alert schema:** severity/certainty/urgency/area fields on `Alert` — signals you understand real emergency-alert standards, and costs almost nothing to adopt now vs. retrofitting later.

---

## 7. Build Sequence

1. **Domain layer** — entities, value objects, RiskEngine/EscalationEngine as pure classes with unit tests. Nothing else can start meaningfully before this is right.
2. **Infrastructure** — Postgres+PostGIS via Docker, SQLAlchemy models, Alembic, repositories implementing the ports.
3. **Application use cases** — wire domain + infrastructure (IngestTelemetry, AssessZoneRisk, IssueOverride, ModerateReport).
4. **HTTP interface** — FastAPI routers as thin adapters over use cases; WebSocket channel for live updates.
5. **Web portal** — dashboard + GIS map first (core value), then zone detail/SHAP panel, then admin pages.
6. **Mobile app** — home/map/zone-detail first, then alerts (FCM), then community reporting, then settings.
7. **Hardening pass** — tests, CI, Docker Compose, secrets audit, docs.

---

## 8. Immediate priority-0 items (before any new feature work)

- Rotate the OpenWeather API key and the hardcoded M2M API key — both were committed to source.
- Remove the `User.__table__.drop(...)` startup call before it's ever run against real data again.
- Decide Postgres (with PostGIS) as the actual database and drop the leftover SQLite file.
