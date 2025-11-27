# Contributing to RExSyn Nexus Light

## Branches
- `main`/`master`: stable light profile.
- Feature branches: `feat/<short-desc>`.

## Setup
```
pip install -r requirements.txt
pip install -e .[dev]
```

## Run
```
./run_light.ps1   # with venv activated
# or
python -m uvicorn backend.app.main:app --port 8000
```

## Tests / CI
- Local: `pytest` (light smoke only).
- CI: GitHub Actions runs install + pytest on push/PR.

## Coding guidelines
- Keep light profile safe: placeholder pipeline, SQLite default, no secrets.
- Avoid adding heavy/production executors to light; use stubs/placeholders.
- New endpoints: document in README/LOCAL_RUN/WIKI and add a minimal test.
- Lint: ruff (optional, in dev extras).

## Static UI
- Served under `/frontend` from `frontend/stitch_bioai`.
- Landing/API console/Status/Full preview pages are in English; keep links working with backend defaults.

## Pull requests
- Describe scope, testing done, and any doc updates.
- For breaking changes, call out clearly and update CHANGELOG.md.
