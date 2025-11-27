## Local Run (Light/Demo)

Placeholder-only pipeline. No external executors.

### Install
```powershell
pip install -e .[dev]
# 또는 pip install -r requirements.txt
```

### Env (PowerShell)
```powershell
$env:ALLOW_PLACEHOLDER_PIPELINE="1"
$env:RSN_JWKS_URL="local"
$env:RSN_SECRET_KEY="demo-secret"
$env:JWT_SECRET_KEY="demo-jwt"
$env:DATABASE_URL="sqlite:///D:/Sanctum/tmp/rsn-light.db"
$env:DB_URL=$env:DATABASE_URL
```

### Run
```powershell
cd D:\Sanctum\RExSyn-Nexus-light\backend
uvicorn app.main:app --port 8000
# 또는 (venv 활성화 후) D:\Sanctum\RExSyn-Nexus-light\run_light.ps1
```

### Health
```
curl http://127.0.0.1:8000/health
```

### Call (demo token from README)
```
curl -X POST http://127.0.0.1:8000/api/v1/predict ^
  -H "Authorization: Bearer <demo-token>" ^
  -H "Content-Type: application/json" ^
  --data '{"sequence":"ACDEFGHIKLMNPQRSTVWY","experiment_type":"protein_folding","method":"alphafold3"}'
```

### Tests
```powershell
pytest
```

### Notes
- Placeholder pipeline only; scientific executors/MinIO/MLflow/Celery are disabled.
- Full pipeline, SIDRCE/Spicy 풀 검수는 프로/엔터프라이즈 에디션에서 제공.
