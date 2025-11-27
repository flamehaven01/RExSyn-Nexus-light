# RExSyn Nexus Light (Demo Profile)

Purpose: Safe, open demo profile with placeholders only. The full version includes real structure prediction, scientific validation, MD, report generation, and production deployment assets. Contact us for the full edition.

## What’s in this light profile
- Placeholder pipeline only (`ALLOW_PLACEHOLDER_PIPELINE=1`) for fast demos.
- External executors (DockQ/SAXS/PoseBusters), MinIO, MLflow, Celery/Redis are disabled.
- No secrets or production configs; SQLite is fine.

## Install (dev/demo)
```powershell
pip install -e .[dev]
```
또는
```powershell
pip install -r requirements.txt
```

## Quick Run (dev/demo)
```powershell
$env:ALLOW_PLACEHOLDER_PIPELINE="1"
$env:RSN_JWKS_URL="local"
$env:RSN_SECRET_KEY="demo-secret"
$env:JWT_SECRET_KEY="demo-jwt"
$env:DATABASE_URL="sqlite:///D:/Sanctum/tmp/rsn-light.db"
$env:DB_URL=$env:DATABASE_URL
cd backend
python -m uvicorn app.main:app --port 8000
# 또는 ./run_light.ps1 (venv 활성화 후 실행 시 자동으로 venv python 사용)
```
Use the demo token from the main README “LOCAL RUN” section.

### Health check
```
curl http://127.0.0.1:8000/health
```

### Tests (with coverage)
```
pytest --cov=backend/app --cov-report=term-missing
```

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
- SIDRCE + Spicy 검수 전 과정 포함(풀 버전에서만 수행).

## Wiki / Preview of Full Edition
- See `WIKI.md` for a side-by-side view (Light vs Full features) and how to upgrade to the pro/B2B edition.
