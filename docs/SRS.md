
## Scope

Pricing optimization for multiple products across organizations using aggregated daily sales data.

## Functional Requirements

**Ingestion & Entities**

* \[F‑1] Create organization and products (SKU, name, currency)
* \[F‑2] Ingest daily sales: `date, units_sold, price` per product (bulk upsert)
* \[F‑3] (Optional) Ingest daily `unit_cost`

**Analytics & ML**

* \[F‑4] Estimate **price elasticity** per product over rolling window; store value & R²
* \[F‑5] Forecast **demand** per product for `horizon` days
* \[F‑6] Recommend **prices** for each target day maximizing **revenue** or **profit** within `pmin..pmax`

**Access & Delivery**

* \[F‑7] API endpoints to trigger ML runs and fetch results
* \[F‑8] Frontend dashboard with charts and controls
* \[F‑9] Export CSV of recommendations (frontend)

## Non‑Functional Requirements

* **Security**: CORS restricted; (optional) JWT for multi‑tenant auth
* **Performance**: P95 < 500ms on GET endpoints; background jobs for heavy ML
* **Reliability**: Idempotent `sales/bulk` upserts; migrations via Alembic
* **Observability**: request logs, structured logging, basic metrics
* **Portability**: Dockerfiles for backend/frontend; Railway/Vercel deploy

## Constraints & Assumptions

* Daily aggregate granularity; timezone UTC
* Constant elasticity model as v1; may not fit promo shocks perfectly
* Demo dataset size: up to \~1M sales rows total

## Acceptance Criteria (samples)

* **AC‑1**: When I POST valid `sales/bulk`, rows are upserted and retrievable via SQL and API
* **AC‑2**: Given last 90 days, `/ml/estimate-elasticity` produces an elasticity value and R² stored in DB
* **AC‑3**: `/ml/recommend-prices?objective=profit` returns `suggested_price`, `expected_units`, `expected_revenue`, `expected_profit` for each requested date
* **AC‑4**: Frontend renders history vs forecast vs price suggestions with tooltips and legends

## Out of Scope (v1)

* Real‑time streaming events; promos/coupons modeling; AB testing automation

---

