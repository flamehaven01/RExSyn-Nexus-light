# RExSyn Nexus: Light vs Full Edition

## Quick Comparison

| Edition | Purpose | Target Users |
|---------|---------|--------------|
| **Light** | API evaluation, integration testing, rapid prototyping | Developers, small teams, evaluation |
| **Full** | Production science workloads, clinical research | Research labs, biotech, clinical institutions |

---

## Feature Matrix

### Science & Computation

| Feature | Light | Full |
|---------|-------|------|
| AlphaFold3 Executor | L Placeholder |  GPU-accelerated |
| ESMFold Executor | L Placeholder |  Fast folding |
| RoseTTAFold | L Placeholder |  Alternative predictor |
| DockQ v2 Validation | L |  Complex quality |
| SAXS Ç² Validation | L |  X-ray fit |
| PoseBusters | L |  Ligand pose QC |
| GROMACS MD | L |  Energy minimization |
| Response Time | ~50ms (instant) | 30s-30min (real) |

### Infrastructure

| Feature | Light | Full |
|---------|-------|------|
| Database | SQLite (local) | PostgreSQL (replicated) |
| Task Queue | L Sync only | Redis + Celery |
| Storage | Local FS | MinIO/S3 |
| Experiment Tracking | L | MLflow |
| Orchestration | Docker Compose | Kubernetes + Helm |
| Autoscaling | L | HPA-ready |

### Security & Governance

| Feature | Light | Full |
|---------|-------|------|
| JWT Auth |  Local JWKS |  Remote JWKS (RS256) |
| RBAC |  Basic |  Fine-grained |
| Multi-Tenancy | L |  Org-level isolation |
| SIDRCE Gates | L |  Quality/drift detection |
| Audit Logs | Basic |  Structured + retention |

### Reports & Monitoring

| Feature | Light | Full |
|---------|-------|------|
| JSON Responses |  |  |
| PDF Reports | L |  Academic-grade |
| Grafana Dashboards | L |  Pre-built |
| Alerting | L |  AlertManager |
| Distributed Tracing | L |  Jaeger |

---

## Decision Guide

### Choose Light Edition If:

-  Testing API integration patterns
-  Evaluating platform before commitment
-  Building proof-of-concept
-  No GPU/HPC resources
-  Rapid deployment (< 5 min)

### Choose Full Edition If:

-  Real structure prediction workloads
-  Scientific validation required
-  MD refinement needed
-  Academic paper generation
-  Enterprise infrastructure (K8s, S3)
-  Compliance (SIDRCE, audit trails)

---

## Use Cases

### Research Lab (Academic)
**Scenario:** 10-20 predictions/week, publication outputs
**Recommendation:** Full Edition
**Infrastructure:** Single GPU server + PostgreSQL
**Cost:** ~$500/month

### Startup (Early Stage)
**Scenario:** API testing, 5 developers
**Recommendation:** Light ’ Full (6 months)
**Infrastructure:** Laptops ’ AWS EKS
**Cost:** $0 ’ $2000/month

### Pharma (Enterprise)
**Scenario:** 100+ scientists, HIPAA, 1000s predictions
**Recommendation:** Full Edition (on-prem)
**Infrastructure:** Private K8s, GPU nodes
**Cost:** Enterprise agreement

### Teaching/Training
**Scenario:** 50 students, API learning
**Recommendation:** Light Edition
**Infrastructure:** Local or shared server
**Cost:** $0

---

## Upgrade Path

**Timeline:** 1-2 weeks with support

1. **Assessment** - Usage patterns, executor needs, infrastructure
2. **Preparation** - Provision K8s, PostgreSQL, Redis, MinIO
3. **Migration** - Export SQLite, configure executors, deploy Helm
4. **Validation** - Parallel testing, quality checks, benchmarks
5. **Cutover** - DNS switch, monitor 24-48h, decommission Light

---

## FAQ

**Can I run Light in production?**
Yes, for workflows without real predictions. Architecture is production-grade, outputs are placeholders.

**Does Full include Light features?**
Yes, Full is a superset. All APIs identical with added science capabilities.

**Can I mix Light and Full?**
Yes, use environment variables to toggle executor modes.

**What's the learning curve?**
Moderate. API surface identical, adds K8s/Helm complexity. Budget 1-2 weeks with support.

**Is there a trial?**
Yes, 30-day evaluation available.

---

## Contact

- **Email:** info@flamehaven.space
- **GitHub:** [Request B2B Demo](https://github.com/flamehaven01/RExSyn-Nexus-light/issues/new?labels=b2b-request)

**Last Updated:** 2025-11-28 | **Version:** 1.0.0
