# Changelog

All notable changes to RExSyn-Nexus-Light will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased - v0.1.0]

### Planned Features
See [UPGRADE_SPEC_v0.1.0.md](UPGRADE_SPEC_v0.1.0.md) for detailed specifications.

- **Omega Scorer Lite**: Geometric mean algorithm (I×P×(1-Δ)) with grade boundaries
- **Scenario Engine**: Deterministic simulation modes for B2B demos  
- **Visual Feedback**: Empathy gate alerts + Omega breakdown displays
- **Security Updates**: 8 dependency patches aligned with Full Edition
- **RBAC Testing**: Enhanced Viewer/User/Admin test coverage

---

## [0.0.5] - 2025-12-31

### Added - Comprehensive Planning & Documentation

#### Upgrade Specification (NEW)
- **UPGRADE_SPEC_v0.1.0.md**: 850+ line implementation guide for v0.1.0 release
  - Omega Scorer Lite algorithm design with code examples
  - Scenario Engine architecture (PERFECT, DRIFT_DETECTED, EMPATHY_FAIL, RANDOM modes)
  - Visual Feedback System specifications (CSS + JavaScript)
  - Security hardening roadmap with 8 dependency updates
  - 4-week implementation timeline with success metrics
  - File change summary and breaking changes analysis

#### Documentation Enhancements
- **README.md Overhaul**:
  - Version badge updated to v0.0.5 with architecture badge  
  - Enhanced overview highlighting v0.1.0 planning
  - Updated roadmap with clear v0.0.5 → v0.1.0 → v0.2.0 path
  - Clarified "planned" vs "active" feature status

- **CHANGELOG.md Structure**:
  - Added [Unreleased - v0.1.0] section for planned features
  - v0.0.5 focuses on documentation and planning (not implementation)
  - Clear distinction between current and future capabilities

#### Planned Security Updates (for v0.1.0)
- fastapi: 0.110 → 0.115 (security patches)
- uvicorn: 0.23 → 0.30 (performance improvements)
- pydantic: 2.6 → 2.9 (validation enhancements)
- sqlalchemy: 2.0 → 2.0.35 (SQL injection protection)
- python-jose: Add [cryptography] backend
- passlib: 1.7 → 1.7.4 (bcrypt timing attack fixes)
- prometheus-client: 0.19 → 0.21
- redis: 5.0 → 5.1 (connection pool fixes)

### Changed
- **Version**: 0.0.4 → 0.0.5 (documentation release)
- **Focus**: Implementation → Planning & Specification
- **Architecture Status**: "S++ certified" → "S++ planned" (pending v0.1.0 implementation)

### Migration from v0.0.4
**No breaking changes** - v0.0.5 is 100% backward compatible.

**What Changed:**
- Added comprehensive upgrade planning documentation
- No functional code changes (all v0.1.0 features are planned, not implemented)

### Next Steps
1. Review [UPGRADE_SPEC_v0.1.0.md](UPGRADE_SPEC_v0.1.0.md) for v0.1.0 implementation details
2. Implement Omega Scorer Lite (Week 1-2)
3. Implement Scenario Engine (Week 2-3)
4. Add Visual Feedback components (Week 3-4)
5. Apply security updates and testing (Week 4)

---

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
