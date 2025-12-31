# RExSyn Nexus: Light vs Full Edition

**Last Updated**: 2025-12-31  
**Light Edition Version**: v0.1.0  
**Full Edition Version**: v1.2.0

## Quick Comparison

| Edition | Purpose | Target Users | Version |
|---------|---------|--------------|---------|
| **Light** | API evaluation, B2B demos, integration testing | Developers, sales engineers, POC teams | v0.1.0 |
| **Full** | Production science workloads, clinical research | Research labs, biotech, clinical institutions | v1.2.0 |

---

## Feature Matrix

### Core Features (NEW in v0.1.0)

| Feature | Light Edition | Full Edition |
|---------|---------------|--------------|
| **Omega Scorer** | [+] Lite (IxPx(1-Delta), S++ grading) | [+] Full LEDA Engine integration |
| **Scenario Engine** | [+] 4 modes (Perfect/Drift/Empathy/Random) | [+] ML-powered anomaly detection |
| **Demo Control** | [+] 100% deterministic outcomes | [+] Real-time adaptive scenarios |
| **Test Coverage** | [+] 14 tests (100% passing) | [+] 200+ tests with E2E coverage |

### Science & Computation

| Feature | Light | Full |
|---------|-------|------|
| AlphaFold3 Executor | [*] Scenario-based simulation | [+] GPU-accelerated (CUDA 12.x) |
| ESMFold Executor | [*] Scenario-based simulation | [+] Fast folding (8-16GB RAM) |
| RoseTTAFold | [*] Scenario-based simulation | [+] Alternative predictor |
| DockQ v2 Validation | [-] | [+] Complex quality |
| SAXS chi2 Validation | [-] | [+] X-ray fit |
| PoseBusters | [-] | [+] Ligand pose QC |
| GROMACS MD | [*] Placeholder simulation | [+] Energy minimization |
| Response Time | ~50ms (instant) | 30s-30min (real compute) |

**Legend**: [+] Fully functional | [*] Simulation/demo mode | [-] Not included

### Infrastructure

| Feature | Light | Full |
|---------|-------|------|
| Database | SQLite (local, demo-grade) | PostgreSQL 14+ (replicated) |
| Task Queue | [-] Sync only | [+] Redis + Celery workers |
| Storage | Local filesystem | [+] MinIO/S3 with versioning |
| Experiment Tracking | [-] | [+] MLflow with artifact storage |
| Orchestration | Docker (single container) | [+] Kubernetes + Helm charts |
| Autoscaling | [-] | [+] HPA-ready (CPU/GPU metrics) |

### Security & Governance

| Feature | Light | Full |
|---------|-------|------|
| JWT Auth | [+] Local JWKS (demo tokens) | [+] Remote JWKS (RS256/ES256) |
| RBAC | [+] 3 roles (Viewer/User/Admin) | [+] 7 roles + custom policies |
| Multi-Tenancy | [-] | [+] Org-level isolation + quotas |
| SIDRCE Gates | [*] Placeholder validation | [+] Full 7-stage pipeline |
| Audit Logs | [+] Basic (timestamp + user) | [+] Structured + retention policies |
| Drift Detection | [+] Scenario-based (v0.1.0) | [+] Real-time Prometheus monitoring |

---

## Decision Guide

### Choose Light Edition If:

- [+] Testing API integration patterns
- [+] Running B2B sales demonstrations with controlled scenarios
- [+] Evaluating platform before commitment
- [+] Building proof-of-concept (< 1 week timeline)
- [+] No GPU/HPC resources available
- [+] Rapid deployment requirement (< 5 min)
- [+] Learning Omega scoring concepts

**Perfect For**: Sales engineers, POC teams, API developers, evaluation period

### Choose Full Edition If:

- [+] Real structure prediction workloads (AlphaFold3, ESMFold)
- [+] Scientific validation required (DockQ, SAXS, PoseBusters)
- [+] MD refinement with GROMACS/OpenMM
- [+] Academic paper generation (PDF reports)
- [+] Enterprise infrastructure (K8s, S3, MLflow)
- [+] Compliance requirements (SIDRCE audit, HIPAA)
- [+] Production SLA (24/7 support)

**Perfect For**: Research labs, biotech R&D, clinical institutions, pharma enterprises

---

## Use Cases

### Research Lab (Academic)
**Scenario**: 10-20 predictions/week, publication outputs  
**Recommendation**: Full Edition  
**Infrastructure**: Single GPU server (A100 40GB) + PostgreSQL  
**Cost**: ~$500/month (cloud) or $15k one-time (on-prem)  
**Timeline**: 2 weeks setup to production

### Startup (Early Stage)
**Scenario**: API testing, 5 developers, POC for investors  
**Recommendation**: Light to Full (6 months)  
**Infrastructure**: Laptops to AWS EKS  
**Cost**: $0 (Light) to $2,000/month (Full on AWS)  
**Timeline**: Same-day Light setup to 1 month Full migration

### Pharma (Enterprise)
**Scenario**: 100+ scientists, HIPAA compliance, 1000s predictions  
**Recommendation**: Full Edition (on-prem)  
**Infrastructure**: Private K8s cluster, 10+ GPU nodes  
**Cost**: Enterprise agreement ($50k-200k/year)  
**Timeline**: 3-6 months custom deployment

### Sales Team (B2B Demos)
**Scenario**: Controlled demonstrations for prospects  
**Recommendation**: Light Edition with Scenario Engine  
**Infrastructure**: Laptop or demo server  
**Cost**: $0 (open source)  
**Timeline**: 5 minutes setup  
**Key Feature**: Deterministic Omega scenarios (PERFECT/DRIFT/EMPATHY_FAIL)

---

## Contact

**Light Edition Questions**: [GitHub Issues](https://github.com/flamehaven01/RExSyn-Nexus-light/issues)  
**Full Edition Inquiries**: info@flamehaven.space  
**B2B Demo Requests**: [Create Issue](https://github.com/flamehaven01/RExSyn-Nexus-light/issues/new)
