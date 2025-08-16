
A step‑by‑step guide to build and deploy the **AI Dynamic Pricing & Demand Forecasting** project using **PostgreSQL + FastAPI (Python)** and **Next.js (TypeScript)**. Backend on **Railway**, frontend on **Vercel**.

---

## 0) Prerequisites & Local Setup

* [ ] Install **Python 3.11+**, **Node.js 18+**, **pnpm** or **npm**, **PostgreSQL 14+**
* [ ] Install **Git** and create a GitHub repo (public for portfolio)
* [ ] (Optional) Install **Docker** if you prefer containers
* [ ] Create a **virtualenv** for Python
* [ ] Create a local PostgreSQL DB `pricing_db`
* [ ] Create a `.env` file in `backend/` and `frontend/` (see examples below)

**Repo layout**

```
/ (monorepo)
  backend/              # FastAPI app + ML services + Alembic
  frontend/             # Next.js (TypeScript) UI
  ops/                  # DevOps helpers (Docker, CI, Makefiles)
  docs/                 # diagrams, notes (auto-generated if needed)
  README.md
```

**Backend .env example**

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pricing_db
CORS_ORIGINS=http://localhost:3000
ENV=dev
```

**Frontend .env.local example**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 1) Database & Migrations

* [ ] Apply the initial schema (ERD below)
* [ ] Initialize Alembic and generate migration
* [ ] Run `alembic upgrade head`

**Key tables**: `organizations`, `products`, `sales_daily`, `costs`, `model_runs`, `forecasts`, `elasticity_estimates`, `price_recommendations`.

**Indexes**: `(product_id, date)` on time-series tables.

---

## 2) Minimal API (FastAPI)

* [ ] `GET /health` → health check
* [ ] `POST /orgs`, `POST /products` → basic creation
* [ ] `POST /sales/bulk` → upsert daily sales rows
* [ ] Add CORS for Vercel/localhost

**Run locally**

```
uvicorn app.main:app --reload --port 8000
```

---

## 3) Elasticity & Price Optimization (ML v1)

* [ ] Implement rolling **price elasticity** estimator (log‑log OLS)
* [ ] Persist to `elasticity_estimates` with `model_runs`
* [ ] Implement **price optimization** (grid search)
* [ ] Persist to `price_recommendations`
* [ ] Expose endpoints:

  * `POST /ml/estimate-elasticity?product_id=&window_days=90`
  * `POST /ml/recommend-prices?product_id=&objective=revenue|profit&pmin=&pmax=`

---

## 4) Forecasting (ML v2)

* [ ] Engineer calendar/lag features (price, weekday, moving averages)
* [ ] Train per‑product model (LightGBM recommended) and predict `horizon` days
* [ ] Save to `forecasts` under a new `model_runs` entry
* [ ] Endpoint: `POST /ml/run-forecast?product_id=&horizon=30`

---

## 5) Frontend (Next.js on Vercel)

* [ ] Pages: `/` (overview), `/product/[id]` (detail)
* [ ] Charts: sales history, forecasts, suggested prices, revenue/profit curves
* [ ] Controls: date pickers, objective (revenue/profit), run ML buttons
* [ ] Data layer: React Query; forms for adding products and pasting sales rows

**Run locally**

```
pnpm dev  # or npm run dev
```

---

## 6) Deployment

**Railway (backend)**

* [ ] Create Railway Postgres → set `DATABASE_URL`
* [ ] Deploy FastAPI service; run `alembic upgrade head` on start
* [ ] Set `CORS_ORIGINS` to your Vercel URL

**Vercel (frontend)**

* [ ] Set `NEXT_PUBLIC_API_BASE_URL` to Railway public URL
* [ ] Deploy Next.js

---

## 7) Testing & QA

* [ ] Unit tests for services (elasticity, pricing, forecasting)
* [ ] API tests (pytest + httpx)
* [ ] E2E smoke: ingest → run ML → fetch recs → render charts
* [ ] Seed demo org/product & 6–12 months synthetic sales

---

## 8) Portfolio Finishing

* [ ] README with screenshots & live links
* [ ] Short Loom demo video
* [ ] Case study (problem → solution → ROI → tech)

---

### Makefile (optional)

```
make dev-api      # run FastAPI
make dev-web      # run Next.js
make migrate      # alembic upgrade head
make seed         # seed demo data
```

---