# /ARCHITECTURE.md

## High‑Level Components

* **Frontend (Vercel)**: Next.js + TS UI, React Query, Recharts, file‑free data entry
* **Backend (Railway)**: FastAPI REST, async SQLAlchemy, services for forecasting/elasticity/pricing
* **DB (Railway Postgres)**: normalized schema, indices for time‑series queries
* **Jobs**: On‑demand endpoints (v1). Optional scheduler (Railway cron) for nightly runs

### Component Diagram

```mermaid
flowchart LR
  subgraph Client
    U[Browser]
  end

  subgraph Vercel[Frontend — Next.js (TS)]
    FE[UI: Upload/Charts/Controls]
  end

  subgraph Railway[Backend — FastAPI]
    API[REST Endpoints]
    Svc[Services: Forecasting/Elasticity/Pricing]
    Jobs[Background Job Runner]
  end

  subgraph DB[(PostgreSQL)]
    T[(Tables: orgs, products, sales_daily, costs, forecasts, runs, elasticity, recs)]
  end

  U --> FE
  FE <---> API
  API --> DB
  Svc --> DB
  Jobs --> DB
```

### ERD (Database Schema)

```mermaid
erDiagram
  ORGANIZATIONS ||--o{ PRODUCTS : has
  PRODUCTS ||--o{ SALES_DAILY : has
  PRODUCTS ||--o{ COSTS : has
  PRODUCTS ||--o{ FORECASTS : has
  PRODUCTS ||--o{ ELASTICITY_ESTIMATES : has
  PRODUCTS ||--o{ PRICE_RECOMMENDATIONS : has
  MODEL_RUNS ||--o{ FORECASTS : produces
  MODEL_RUNS ||--o{ ELASTICITY_ESTIMATES : produces
  MODEL_RUNS ||--o{ PRICE_RECOMMENDATIONS : produces

  ORGANIZATIONS {
    uuid id PK
    text name
    timestamptz created_at
  }
  PRODUCTS {
    uuid id PK
    uuid org_id FK
    text sku
    text name
    text currency
    timestamptz created_at
  }
  SALES_DAILY {
    bigserial id PK
    uuid product_id FK
    date date
    int units_sold
    numeric price
    numeric revenue
    timestamptz created_at
  }
  COSTS {
    bigserial id PK
    uuid product_id FK
    date date
    numeric unit_cost
    timestamptz created_at
  }
  MODEL_RUNS {
    uuid id PK
    text model_name
    text model_version
    jsonb params
    timestamptz started_at
    timestamptz finished_at
  }
  FORECASTS {
    bigserial id PK
    uuid product_id FK
    uuid model_run_id FK
    date target_date
    numeric predicted_units
    timestamptz created_at
  }
  ELASTICITY_ESTIMATES {
    bigserial id PK
    uuid product_id FK
    uuid model_run_id FK
    date window_start
    date window_end
    numeric elasticity
    numeric r2
    timestamptz created_at
  }
  PRICE_RECOMMENDATIONS {
    bigserial id PK
    uuid product_id FK
    uuid model_run_id FK
    date target_date
    text objective
    numeric suggested_price
    numeric expected_units
    numeric expected_revenue
    numeric expected_profit
    timestamptz created_at
  }
```

### Sequence: Ingest → Recommend

```mermaid
sequenceDiagram
  participant User
  participant FE as Next.js (Vercel)
  participant API as FastAPI (Railway)
  participant DB as PostgreSQL
  User->>FE: Add product / paste sales
  FE->>API: POST /sales/bulk
  API->>DB: Upsert rows
  DB-->>API: OK
  API-->>FE: 200 Created
  FE->>API: POST /ml/run-forecast?horizon=30
  API->>DB: Insert model_runs(started)
  API->>DB: Insert forecasts
  API->>DB: Update model_runs(finished)
  FE->>API: POST /ml/estimate-elasticity?window_days=90
  API->>DB: Insert elasticity_estimates
  FE->>API: POST /ml/recommend-prices?objective=profit
  API->>DB: Insert price_recommendations
  FE->>API: GET /products/{id}/recommendations
  API->>DB: SELECT recs
  API-->>FE: JSON recs
```

---

## API Surface (v1)

| Method | Path                             | Description                                                                   |
| ------ | -------------------------------- | ----------------------------------------------------------------------------- |
| GET    | `/health`                        | Health check                                                                  |
| POST   | `/orgs`                          | Create organization                                                           |
| POST   | `/products`                      | Create product                                                                |
| POST   | `/sales/bulk`                    | Bulk upsert sales rows                                                        |
| POST   | `/ml/run-forecast`               | Train/predict demand; params: `product_id?`, `horizon`                        |
| POST   | `/ml/estimate-elasticity`        | Estimate elasticity over window                                               |
| POST   | `/ml/recommend-prices`           | Compute price suggestions; params: `objective`, `pmin`, `pmax`, `product_id?` |
| GET    | `/products/{id}/forecasts`       | List forecasts by date range                                                  |
| GET    | `/products/{id}/recommendations` | List price recommendations                                                    |

**Schemas:** JSON bodies follow Pydantic models; all dates ISO‑8601.

---

## Tech Choices

* **Python**: FastAPI, SQLAlchemy (async), Alembic, pandas, scikit‑learn, lightgbm
* **TypeScript**: Next.js, React Query, Recharts/TanStack Table, Tailwind CSS
* **DB**: PostgreSQL with sensible indices
* **Hosting**: Railway (API + DB), Vercel (UI)

---

## Risks & Mitigations

* **Sparse price variation → weak elasticity** → show R²/confidence, fallback to conservative pricing
* **Cold starts on Railway/Vercel** → keep ML in background jobs; cache results in DB
* **Schema drift** → enforce migrations; write DB tests

---

## Roadmap (8 weeks)

1. DB + Minimal API (week 1)
2. Elasticity + Pricing (week 2)
3. Forecasting (week 3)
4. Frontend MVP (week 4)
5. Deploy (week 5)
6. Testing/seed data (week 6)
7. Polish UX & docs (week 7)
8. Case study + demo video (week 8)

---

## Glossary

* **Elasticity**: % change in demand per % change in price
* **MAPE**: Mean Absolute Percentage Error (forecast metric)
* **Horizon**: number of future days to forecast
