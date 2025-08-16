
## Elevator Pitch

Build a production‑like **AI Pricing & Demand** platform. It ingests daily sales into **PostgreSQL**, estimates **price elasticity**, forecasts future demand, and computes **optimal prices** to maximize **revenue** or **profit**. Backend is **FastAPI** (Railway), frontend is **Next.js** (Vercel).

## Objectives

* Demonstrate end‑to‑end ML system engineering (DB → ML → API → UI → cloud).
* Provide clear business value with interpretable metrics.
* Be recruiter‑friendly: live demo + clean code + docs.

## Success Metrics

* <200ms median response for read endpoints
* Forecast MAPE < 25% on holdout for demo data
* Elasticity R² > 0.4 on most products (demo target)
* One‑click "Recommend Prices" producing higher expected revenue vs baseline

## Users & Personas

* **Ops/Analyst**: uploads/maintains sales data, runs ML jobs
* **Pricing Manager**: explores charts, downloads recs

---