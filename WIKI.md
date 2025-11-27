# RExSyn Nexus Light – Wiki (Overview & Full Edition Preview)

## Purpose
- Light: Safe, demo-friendly edition with placeholder pipeline (no secrets, no external executors).
- Full: Production-grade edition with complete scientific pipeline, infra, and governance. Contact for access.

## Light Edition (Included)
- API: `/health`, `/predict` (placeholder), `/status`, `/result`.
- Data: simple Job/Result models, SQLite/in-memory ready.
- Runtime: FastAPI app skeleton, minimal env (`ALLOW_PLACEHOLDER_PIPELINE=1`, local JWKS).
- Tests: placeholder-level unit/smoke.
- Packaging: MIT license, basic Dockerfile/compose templates.
- Governance: Only a light checklist; full SIDRCE + Spicy 검수는 프로에서 실행.

## Full Edition (Available in Pro/B2B)
- Scientific Pipeline
  - Structure prediction executors (AlphaFold/ESM/etc.) wired to real CLI/compute.
  - Scientific validation: DockQ/SAXS/PoseBusters, metrics persisted and exported.
  - MD refinement pipeline (GROMACS), refined PDB artifacts.
  - Report generation (PDF/graphs) with artifact storage (MinIO/S3).
- Security & Auth
  - JWKS-based auth (RS256/ES256), RBAC/permissions, audit trails.
  - PII tools, org/user seeding, policy checks.
- Infra & Observability
  - Helm charts, secrets management, Redis/Celery workers, Postgres/MinIO/MLflow wiring.
  - Prometheus/Grafana metrics, alerting hooks.
  - CI/CD with quality gates, coverage, lint, drift checks (DFI-META/SIDRCE).
- Extensibility
  - External executor configuration (science CLI paths, storage endpoints).
  - Plug-in/add-on friendly architecture for B2B custom requirements.
 - Governance
   - Full SIDRCE + SpicyFileReview pipeline, red/amber gates, audit artifacts.

## How to Use the Light Edition
- Run locally with placeholders (no external tools), see `LOCAL_RUN.md`.
- Demo script in `README.md` calls predict→status→result with a demo token.
- No secrets needed; everything runs with safe defaults.

## How to Upgrade to Full
- Engage for B2B: we enable real executors, storage, auth, and deployment assets.
- We can tailor add-ons (custom science tools, reports, governance) while keeping the open skeleton compatible.***
