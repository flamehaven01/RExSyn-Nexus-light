from typing import Dict, Any, Optional
from fastapi import APIRouter, Response
from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()

# Counters
PEER_TOTAL = Counter("rsn_peer_review_total", "Total peer-review evaluations")
PEER_PASS = Counter("rsn_peer_review_pass_total", "Peer-review passes")

# Gauges for gates
G_PB = Gauge("rsn_pb_pass_ratio", "PoseBusters pass ratio")
G_DOCKQ = Gauge("rsn_dockq_v2", "DockQ v2 score")
G_SAXS = Gauge("rsn_saxs_rchi2", "SAXS reduced chi-square")
G_SAXS_RES = Gauge("rsn_saxs_resolution_angstrom", "SAXS resolution (A)")
G_CORMAP = Gauge("rsn_cormap_p", "CorMap p-value")
G_OVE = Gauge("rsn_ove_prime", "OVE' ethics score")
G_DRIFT = Gauge("rsn_drift_value", "Drift value (PSI)")
G_DRIFT_LLM = Gauge("rsn_drift_llm", "LLM drift score")
G_LAMBDA = Gauge("rsn_risk_lambda_t", "Risk lambda_t")
G_EFFECT = Gauge("rsn_risk_effective", "Effective risk")
G_FTI = Gauge("kpi_fti_v2_gauge", "FTI consolidated gauge")

# Histograms
H_QUEUE = Histogram("rsn_gpu_queue_seconds", "GPU queue wait time")

@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def observe_peer_review(
    scores: Dict[str, Any],
    ethics: Optional[Dict[str, Any]] = None
) -> None:
    PEER_TOTAL.inc()

    pb = float(scores.get("posebusters_pass", 0.0))
    dockq = float(scores.get("dockq_v2", 0.0))
    saxs_r = float(scores.get("saxs_rchi2", 9.0))
    saxs_res = float(scores.get("saxs_resolution", 5.0))
    cormap = float(scores.get("cormap_p", 0.0))

    G_PB.set(pb)
    G_DOCKQ.set(dockq)
    G_SAXS.set(saxs_r)
    G_SAXS_RES.set(saxs_res)
    G_CORMAP.set(cormap)

    if ethics:
        ove = float(ethics.get("ove_prime", 0.0))
        drift = float(ethics.get("drift", 0.0))
        drift_llm = float(ethics.get("drift_llm", 0.0))

        G_OVE.set(ove)
        G_DRIFT.set(drift)
        G_DRIFT_LLM.set(drift_llm)

        # Resolution-dependent gate check
        if saxs_res < 3.0:
            threshold = 1.2
        elif saxs_res <= 8.0:
            threshold = 1.5
        else:
            threshold = 2.0

        passed = (
            pb >= 0.80 and
            dockq >= 0.40 and
            saxs_r <= threshold and
            cormap >= 0.05 and
            ove >= 0.85 and
            drift_llm < 0.03
        )

        if passed:
            PEER_PASS.inc()

def observe_risk(lambda_t: float = None, effective: float = None) -> None:
    if lambda_t is not None:
        G_LAMBDA.set(float(lambda_t))
    if effective is not None:
        G_EFFECT.set(float(effective))

def observe_fti(value: float) -> None:
    G_FTI.set(float(value))

def observe_gpu_queue(wait_seconds: float) -> None:
    H_QUEUE.observe(wait_seconds)
