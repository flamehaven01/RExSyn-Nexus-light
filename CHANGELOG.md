# Changelog

## [0.0.4] - 2025-11-27
- Added CI/pytest coverage gate tuned for light profile (`--cov-fail-under=45`, API/core scope) to avoid failing on placeholder modules while still preventing drift.
- Bumped project version to 0.0.4; refreshed badges/logo and README CTA.
- Added issue templates (B2B demo request, full-edition feature) and stronger CTA/usage guidance in README.
- Kept light defaults (SQLite/demo secrets) while keeping coverage signal visible.

## [0.0.3] - 2025-11-27
- Added request size guard (`max_length=10000`) on sequences.
- Replaced `datetime.utcnow()` usage with timezone-aware timestamps where found (auth, storage, helpers).
- Rate limiting (slowapi 60/min) kept and wired into app state/handlers.
- Tests expanded (20 → 23 including placeholder integration); added integration placeholder test and length guard.
- CI installs from requirements.txt then editable package; pytest runs with coverage (`--cov=backend/app --cov-report=term-missing`).
- pytest-cov added to dev/requirements; coverage artifacts ignored in .gitignore.
- Documentation: CONTRIBUTING.md, CHANGELOG.md added.

## [0.0.2] - 2025-11-26
- Light profile stabilized (placeholder pipeline, SQLite default, local JWT).
- Static frontend served at `/frontend` (landing, API console, status/metrics, full edition preview).
- Added rate limiting (slowapi, default 60/min) and `/ui` redirect to landing.
- CI installs from requirements.txt then editable package; pytest smoke suite expanded.
- Docs updated (README, LOCAL_RUN, WIKI, inspection report).

## [0.0.1] - 2025-11-25
- Initial light demo profile setup.
