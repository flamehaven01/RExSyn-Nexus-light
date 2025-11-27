# RExSyn Nexus Light (Demo Profile)

[![CI](https://img.shields.io/github/actions/workflow/status/flamehaven01/RExSyn-Nexus-light/ci.yml?branch=main&label=CI)](https://github.com/flamehaven01/RExSyn-Nexus-light/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-40%2B%25-blue)](https://github.com/flamehaven01/RExSyn-Nexus-light/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

![RExSyn Nexus Logo](frontend/assets/LOGO.png)

**Ethics-Certified BioAI Light Demo.** Star ⭐ / Fork 🍴 to support and try the API/UI quickly.  
**Why this exists (light edition):** Safe, open demo of RExSyn Nexus. Shows API surface, UI, rate limiting, and placeholder pipeline without exposing full production science stack (structure prediction, validation, MD, reports).  
**Want the full thing?** → The pro/B2B edition ships real executors, MinIO/S3, MLflow, Helm, and SIDRCE + Spicy governance. Open an issue or contact us to talk.

## Quick links
- ⭐ **Star/Fork**: https://github.com/flamehaven01/RExSyn-Nexus-light
- 🧭 **Live tour**: Open `frontend/landing/home/code.html` or `http://localhost:8000/ui` when the backend is running.
- 📕 **Wiki (Light vs Full)**: `WIKI.md`
- 🛠 **Local run**: `LOCAL_RUN.md`
- 📬 **Contact**: yun@flamehaven.ai
- 🏷️ **GitHub topics (set in repo settings):** `fastapi`, `bioai`, `demo`, `sidrce`, `light-edition`

## Features (Light)
- Placeholder pipeline only (`ALLOW_PLACEHOLDER_PIPELINE=1`) for fast demos.
- Auth + RBAC + rate limiting (slowapi) + request-size guard.
- SQLite default; no external brokers/storage/science executors required.
- Frontend tour: landing, API console, status/metrics, full-edition preview.
- CI with coverage gate on API/core (40% minimum) to prevent drift.

## What’s *not* in light (CTA)
- No real structure prediction / DockQ / SAXS / PoseBusters / MD / reports.
- No MinIO/S3, MLflow, Redis/Celery production stack.
- Full SIDRCE + Spicy governance only in pro/B2B edition.

## Getting Started (dev/demo)
Fast one-liner (after activating your venv):
```powershell
./run_light.ps1
```

Manual setup:
```powershell
pip install -e .[dev]
```
or
```powershell
pip install -r requirements.txt
```
```powershell
$env:ALLOW_PLACEHOLDER_PIPELINE="1"
$env:RSN_JWKS_URL="local"
$env:RSN_SECRET_KEY="demo-secret"
$env:JWT_SECRET_KEY="demo-jwt"
$env:DATABASE_URL="sqlite:///D:/Sanctum/tmp/rsn-light.db"
$env:DB_URL=$env:DATABASE_URL
cd backend
python -m uvicorn app.main:app --port 8000
# or ./run_light.ps1 (auto-uses venv python when activated)
```
Use the demo token from the main README “LOCAL RUN” section.

### Health check
```
curl http://127.0.0.1:8000/health
```

### Tests (with coverage)
```
pytest --cov=backend/app/api --cov=backend/app/core --cov-report=term-missing --cov-fail-under=45
```
CI enforces the same light-profile gate (45% on API/core). Placeholders in other services are outside the coverage target so contributors aren’t blocked.

## Usage
- Open `http://localhost:8000/ui` after starting the backend for the guided UI.
- Call `/api/v1/predict` with the demo token (see `LOCAL_RUN.md`) to get a fake job/result flow.
- Check `/health` and `/metrics` for liveness and Prometheus gauges.

## UI walkthrough (light)
- Landing (`/ui`): hero + CTA to API console and status/metrics.
- API Console: sample request payloads and curl snippets.
- Status/Monitoring: health + Prometheus metrics cards.
- Full-edition preview: highlights pro/B2B features; invite to contact.
*(Add screenshots/GIFs to `frontend/assets/` and link them here when available.)*

## Demo script (PowerShell)
```powershell
$token = "<demo-token>"
$body  = '{"sequence":"ACDEFGHIKLMNPQRSTVWY","experiment_type":"protein_folding","method":"alphafold3"}'
$port  = 8000

$resp = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:$port/api/v1/predict" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body $body

$job = $resp.job_id
Write-Host "job_id:" $job
Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/jobs/$job/status" `
  -Headers @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/v1/jobs/$job/result" `
  -Headers @{ Authorization = "Bearer $token" }
```

## Full edition (contact us)
- Real structure prediction executors, scientific validation (DockQ/SAXS/PoseBusters), MD refinement, report generation.
- Production-ready JWKS auth, MinIO/S3, MLflow, Helm/monitoring assets.
- Plug-in/add-on friendly architecture.
- SIDRCE + Spicy audits available in the full edition only.

## Request B2B demo
- Email: yun@flamehaven.ai
- Open an issue with the “Request B2B demo” template (Issues → New → B2B Demo Request).

## Made for labs/clinics/testing teams
- Quick eval of API + UI without heavy infra.
- Ethics-first defaults (rate limiting, size guard, placeholder-only data path).
- Clean upgrade path to pro/B2B edition when you need real science + governance.

## Contributing
- Fork → feature branch → PR. See `CONTRIBUTING.md`.
- We welcome issues/PRs for docs, UI polish, and light-profile tests. For full-stack features, let’s discuss first (they belong in the pro edition).

## Roadmap (Light)
- Improve CTA and UX polish on landing/API console.
- Keep adding smoke tests around `/predict` → `/status` → `/result`.
- Optional: raise the coverage gate as placeholders are replaced.

## Wiki / Preview of Full Edition
- See `WIKI.md` for a side-by-side view (Light vs Full features) and how to upgrade to the pro/B2B edition.
