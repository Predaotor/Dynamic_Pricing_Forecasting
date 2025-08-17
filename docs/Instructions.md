# Instructions.md (Full SDLC, Detailed)

## Project: AI Dynamic Pricing & Demand Forecasting

A production-style system that ingests heterogeneous sales data, normalizes it, runs ML to forecast demand and estimate price elasticity, and recommends optimal prices to maximize revenue or profit. Backend: **FastAPI + PostgreSQL** on **Railway**. Frontend: **Next.js (TypeScript)** on **Vercel**. Includes **staging (RawSales) → ETL → canonical tables** and clear testing & deployment paths.

---

## Phase 0 — Prerequisites & Local Environment

### 0.1 Install Tooling

* Python **3.11+** (pyenv recommended)
* Node.js **18+** (nvm recommended)
* PostgreSQL **14+**
* Git + GitHub account
* Optional: Docker Desktop, Make, direnv

### 0.2 Repo Layout (Monorepo)

```
/ (monorepo)
  backend/                   # FastAPI, SQLAlchemy, Alembic, services
  frontend/                  # Next.js (TypeScript), UI
  etl/                       # ETL modules: extract/transform/load + mappings
  docs/                      # diagrams (.drawio), architecture notes
  ops/                       # Docker, k8s (optional), CI/CD scripts, Makefiles
  README.md
```

### 0.3 Environment Variables

Create `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pricing_db
CORS_ORIGINS=http://localhost:3000
ENV=dev
LOG_LEVEL=INFO
JWT_SECRET=dev-secret-change-me
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Note:** In Railway/Vercel, define these as project environment variables (never commit secrets).

### 0.4 Local DB Setup

* Create database: `createdb pricing_db`
* Enable extension (via migration): `uuid-ossp`

### 0.5 Run Services Locally

* Backend: `uvicorn app.main:app --reload --port 8000`
* Frontend: `pnpm dev` (or `npm run dev`)

---

## Phase 1 — Requirements (SRS) & Success Criteria

### 1.1 Functional Requirements

* **FR1** Ingest raw sales data in *any* column shape via upload endpoint; persist in `raw_sales` as JSONB.
* **FR2** Transform staged rows into canonical `sales` rows using client-specific mappings.
* **FR3** Maintain product catalog in `products` and link sales to products.
* **FR4** Estimate price elasticity per product on a rolling window; store in `elasticity_estimates`.
* **FR5** Forecast demand per product for a future horizon; store in `forecasts` with `model_runs` lineage.
* **FR6** Recommend prices to maximize revenue or profit; store in `suggested_prices`.
* **FR7** Provide REST API to trigger jobs and query results; paginate and filter by product/date.
* **FR8** Frontend dashboard for upload, controls, and charts.

### 1.2 Non‑Functional Requirements

* Security: CORS restricted; optional JWT multi-tenant auth; input validation with Pydantic.
* Performance: GET P95 < 500ms; background jobs for heavy computation.
* Reliability: Idempotent bulk inserts; transactional ETL; migrations via Alembic.
* Observability: structured logging, request IDs, basic metrics, error tracking.
* Portability: Dockerfiles; Railway/Vercel deploy.

### 1.3 Success Metrics

* Forecast MAPE < 25% on demo data.
* Elasticity R² > 0.4 for majority of products (demo target).
* Price recommendations demonstrate uplift vs. baseline (simulated report).

---

## Phase 2 — System Design (Data, API, ML, Frontend)

### 2.1 Database Schema (Canonical + Staging)

**Core tables:**

* `organizations (id, name, created_at)`
* `products (id, org_id, sku, name, currency, created_at)`
* `raw_sales (raw_id, uploaded_at, source, raw_json JSONB, status)`
* `sales (id, product_id, date, units_sold, price, revenue, created_at)`
* `costs (id, product_id, date, unit_cost, created_at)` *(optional for profit objective)*
* `model_runs (id, model_name, model_version, params JSONB, started_at, finished_at)`
* `elasticity_estimates (id, product_id, model_run_id, window_start, window_end, elasticity, r2, created_at)`
* `forecasts (id, product_id, model_run_id, target_date, predicted_units, created_at)`
* `suggested_prices (id, product_id, model_run_id, target_date, objective, suggested_price, expected_units, expected_revenue, expected_profit, created_at)`

**Indexes:**

* `sales(product_id, date)`
* `forecasts(product_id, target_date)`
* `suggested_prices(product_id, target_date)`

> Keep raw data immutable; use `status` lifecycle: `pending` → `processed` → `failed` with `error_message` (optional column) in `raw_sales`.

### 2.2 Data Contracts (Canonical)

* `sales` columns: `product_id: UUID`, `date: YYYY-MM-DD`, `units_sold: int>=0`, `price: decimal>=0`.
* `products` uniqueness: `(org_id, sku)`.

### 2.3 ETL Mapping Files (Per Client)

* Directory: `etl/mappings/` with one JSON/YAML per source.
* Example `client_A.json`:

```
{
  "productId": "product_id",
  "sold_qty": "units_sold",
  "priceUSD": "price",
  "saleDate": "date",
  "$defaults": {"currency": "USD"},
  "$coercions": {"date": "date", "units_sold": "int", "price": "float"},
  "$required": ["product_id", "units_sold", "price", "date"],
  "$id_fields": ["org_id", "sku"]
}
```

* **Mapping semantics:**

  * Key remaps (source→target),
  * `$defaults` fill missing targets,
  * `$coercions` enforce types (date/int/float/str),
  * `$required` enforces presence,
  * `$id_fields` define how to locate/create product records.

### 2.4 ETL Lifecycle & Error Handling

* **Extract:** Read `raw_sales` rows with `status='pending'` in FIFO batches.
* **Transform:**

  * Apply mapping; drop unexpected fields; attach `meta` for audit.
  * Validate: types, non-negatives, date ranges; deduplicate by `(product_id,date)`.
* **Load:**

  * Upsert `products` (by `(org_id, sku)`),
  * Upsert `sales` rows (unique `(product_id, date)`), transactional.
* **Finalize:** Set `status='processed'` or `status='failed'` with `error_message` and keep row for audit.

### 2.5 API Surface (Detailed)

**Public endpoints (v1):**

* `GET /health` → `{status:"ok", ts}`
* `POST /orgs` → create org
* `POST /products` → create product
* `POST /upload_raw_sales?source=client_A&org_id=<uuid>` → Body: CSV/JSON; stores **each row** in `raw_sales`
* `POST /run_etl?source=client_A&org_id=<uuid>&limit=5000` → Runs ETL on pending rows for that source
* `GET /sales?product_id=&from=&to=&limit=&offset=` → Paginated cleaned data
* `POST /ml/estimate-elasticity?product_id=&window_days=90` → writes to `elasticity_estimates`
* `POST /ml/run-forecast?product_id=&horizon=30` → writes to `forecasts`
* `POST /ml/recommend-prices?product_id=&objective=revenue|profit&pmin=&pmax=` → writes to `suggested_prices`
* `GET /products/{id}/forecasts?from=&to=`
* `GET /products/{id}/suggested-prices?from=&to=&objective=`

**Conventions:**

* All dates ISO-8601; responses in UTC.
* Pagination: `limit` (default 50, max 500), `offset`.
* Errors: JSON with `code`, `message`, optional `details`.

### 2.6 Security & Multi-Tenancy

* **Auth (optional for demo):** JWT with claims `{org_id, role}`.
* **Data isolation:** every write/read filtered by `org_id`.
* **CORS:** whitelist localhost + Vercel domain.

### 2.7 ML Design

* **Elasticity (log–log OLS):** `ln(q) = a + b ln(p)`; store `b` (expect negative) and `r²`.
* **Forecasting (LightGBM v1):**

  * Features: lags (1,7,14,28), MA (7,14,28), calendar (dow, month), price.
  * Train per-product; horizon prediction via recursive or direct multi-step.
  * Metrics: MAPE/SMAPE; store in `model_runs.params` or a `metrics` JSON.
* **Pricing:**

  * Assume demand curve `D(p) = D0 * (p/P0)^b` with baseline `(D0,P0)` from forecast/current price.
  * Objective revenue: maximize `R(p) = p * D(p)`.
  * Objective profit: `π(p) = (p-c) * D(p)` with `c` from `costs`.
  * Optimize by grid search over `[pmin, pmax]` or closed-form when applicable; store best `p*` and expectations.

### 2.8 Frontend (Next.js)

* **Pages:** `/` overview, `/product/[id]` detail.
* **Components:** Upload (drag & drop), Charts (Recharts), Tables (TanStack Table), Controls.
* **Data Layer:** React Query; optimistic updates for runs; toast notifications.
* **UX:** Clear status banners (ETL running, ML running), tooltips with definitions (elasticity, MAPE), CSV export.

---

## Phase 3 — Database & Migrations

### 3.1 Alembic Setup

* `alembic init alembic`
* Configure `sqlalchemy.url` (sync driver) and load `DATABASE_URL` via env in `env.py`.
* Autogenerate initial revision: `alembic revision -m "init schema" --autogenerate`
* Apply: `alembic upgrade head`

### 3.2 DDL Notes

* Use `NUMERIC(12,4)` for prices; `CHECK (>=0)`.
* Add unique constraints: `sales(product_id,date)`; `products(org_id,sku)`.
* Add helpful partial indexes later if needed.

---

## Phase 4 — ETL Implementation (Detailed)

### 4.1 Module Structure

```
etl/
  __init__.py
  extract.py        # read raw_sales by source/status
  mappings/
    client_A.json
    client_B.json
  transform.py      # apply mapping, validate, coerce, dedupe
  load.py           # upsert products, upsert sales (txn)
  runner.py         # orchestrate extract→transform→load; CLI
```

### 4.2 Extract (Pseudo-contract)

* Input: `source`, `org_id`, `limit`, `status='pending'`
* Output: iterable of `{raw_id, raw_json}` rows
* Side effect: none

### 4.3 Transform

* Inputs: row `raw_json`, mapping spec
* Steps:

  * Rename keys per mapping
  * Apply `$coercions` (date/int/float/str)
  * Validate `$required`
  * Normalize `price`/`units_sold` to non-negatives; skip/flag invalid
  * Produce canonical dict `{org_id, sku?, product_id?, date, units_sold, price}`
* Output: `ValidRow | Error(reason)`

### 4.4 Load (Transactional)

* For each `ValidRow`:

  * Resolve `product_id` by `(org_id, sku)`; create if missing
  * Upsert `sales` by `(product_id, date)` with `units_sold, price`
* Commit per batch (e.g., 500 rows). Mark raw rows `processed`; failures → `failed` with error.

### 4.5 API Wiring

* `POST /upload_raw_sales` (multipart CSV/JSON)

  * Parse file server-side into JSON rows
  * Insert each row into `raw_sales(status='pending')`
  * Return `{count_inserted}`
* `POST /run_etl`

  * Kicks `runner.py` (sync v1) over a batch
  * Return `{processed, failed}` with sample errors

### 4.6 Observability

* Add `X-Request-ID`; log ETL batch IDs, durations, counts.
* Expose `/metrics` (optional) for Prometheus if using.

---

## Phase 5 — ML Implementation

### 5.1 Elasticity Service

* Query last `window_days` of `sales` per product.
* Fit log–log OLS; store `elasticity` and `r2` with new `model_runs` row.
* Guardrails: if price variance < threshold or `r2 < 0.2`, flag `low_confidence` in params.

### 5.2 Forecasting Service

* Build feature frame from `sales` (lags, MAs, calendar, price).
* Train LightGBM; evaluate on last `k` days; record metrics.
* Predict horizon; write `forecasts` for each `target_date`.

### 5.3 Pricing Service

* For each forecasted date, compute demand curve using elasticity.
* Optimize price within `[pmin, pmax]` (defaults `[0.5*P0, 1.5*P0]`).
* Write `suggested_prices` including expected units/revenue/profit.

---

## Phase 6 — API (Detailed Contracts)

### 6.1 Health

`GET /health` → `200 {"status":"ok","ts":"..."}`

### 6.2 Upload Raw

`POST /upload_raw_sales?source=client_A&org_id=<uuid>`

* **Headers:** `Content-Type: multipart/form-data`
* **Body:** `file` (CSV/JSON)
* **Response:** `202 {"count":123, "status":"queued"}`

### 6.3 Run ETL

`POST /run_etl?source=client_A&org_id=<uuid>&limit=5000`

* **Response:** `200 {"processed":120, "failed":3, "errors":[{"raw_id":7,"message":"missing product_id"}]}`

### 6.4 Sales Query

`GET /sales?product_id=&from=&to=&limit=&offset=`

* **Response:** list of canonical rows

### 6.5 ML Endpoints

* `POST /ml/estimate-elasticity?product_id=&window_days=90`
* `POST /ml/run-forecast?product_id=&horizon=30`
* `POST /ml/recommend-prices?product_id=&objective=revenue|profit&pmin=&pmax=`

> **Note:** Long-running jobs can return `202 Accepted` and a `job_id`. v1 runs synchronously for simplicity.

---

## Phase 7 — Frontend (UX Details)

* **Upload page** with drag & drop; shows parsed row count, preview, and server response.
* **Products page** list with search; add product modal.
* **Product detail**:

  * Line chart: historical sales vs. forecast
  * Line/bar overlay: suggested price vs. expected revenue
  * Controls: objective switch (revenue/profit), pmin/pmax sliders, horizon selector
  * Actions: Run ETL / Run Forecast / Estimate Elasticity / Recommend Prices
* **Notifications:** toasts for job start/finish, errors outlined with row samples.
* **Exports:** CSV download for `suggested_prices`.

---

## Phase 8 — Testing & QA (Comprehensive)

### 8.1 Unit Tests

* ETL transform: mapping correctness, coercions, required fields, error cases.
* Elasticity: correct sign/scale for synthetic data; r² computation.
* Pricing: monotonicity checks; boundary behavior for pmin/pmax; profit objective with costs.

### 8.2 Integration Tests

* Upload → raw\_sales inserted → run\_etl → sales upserted; duplicates handled.
* End-to-end: seed → estimate elasticity → forecast → recommend → read back.

### 8.3 Data Quality Checks

* Non-negative `price`, `units_sold`.
* Date continuity by product (report gaps).
* Sane ranges (e.g., top 0.1% outliers flagged).

### 8.4 Performance

* Load 100k sales rows locally; ETL within N minutes; GET endpoints P95 < 500ms.

---

## Phase 9 — Deployment

### 9.1 Railway (Backend)

* Create Postgres + Service; set `DATABASE_URL`, `CORS_ORIGINS`, `ENV`, `JWT_SECRET`.
* Startup command: run migrations `alembic upgrade head` then `uvicorn`.
* Ensure port `8000` exposed; map to public URL.

### 9.2 Vercel (Frontend)

* Set `NEXT_PUBLIC_API_BASE_URL` to Railway public URL.
* Build: `pnpm build`, Output: static + serverless.

### 9.3 CI/CD (Optional but Recommended)

* GitHub Actions:

  * **backend:** lint, test, `alembic upgrade head`, deploy on main.
  * **frontend:** lint, typecheck, build, deploy on main.

---

## Phase 10 — Operations & Observability

* Structured logs (JSON) with `request_id`, `org_id`, `product_id` when applicable.
* Error monitoring (e.g., Sentry) for backend.
* Metrics (optional): request duration, ETL processed/failed counts, ML runtimes.

---

## Phase 11 — Portfolio Packaging

* README with **elevator pitch**, diagrams, tech stack, live demo links, quickstart commands.
* `/docs` with ERD and ETL workflow diagrams (draw\.io and PNG exports).
* Case study: **Problem → Approach → Architecture → Results → Business Impact**.
* Short demo video (Loom) showing upload → ETL → ML → recommendations.

---

## Makefile (Optional Convenience)

```
make dev-api        # run FastAPI locally
make dev-web        # run Next.js locally
make migrate        # alembic upgrade head
make seed           # seed demo data
make etl            # run ETL on pending rows
```

---

## Glossary

* **ETL**: Extract, Transform, Load — staging raw data then normalizing into canonical tables.
* **Elasticity**: %Δ in quantity per %Δ in price; negative numbers indicate demand falls as price rises.
* **MAPE/SMAPE**: forecasting accuracy metrics.
* **Horizon**: number of future periods predicted.

> This file is intentionally verbose so code-generation tools (like Cursor) can infer directory structure, endpoints, contracts, 