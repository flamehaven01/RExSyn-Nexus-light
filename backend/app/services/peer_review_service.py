import os
from typing import Dict, Any, Optional
import logging
import numpy as np
from redis import Redis

try:
    from src.peer_review.core import PeerReviewEngine
except Exception as e:  # pragma: no cover - light mode fallback
    logging.getLogger(__name__).warning("PeerReviewEngine unavailable (%s); using stub engine", e)

    class PeerReviewEngine:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def run(self, *_args, **_kwargs) -> dict:
            return {"posebusters_pass": 1.0, "dockq_v2": 0.0, "saxs_rchi2": 1.0}
from app.instrumentation.metrics import observe_peer_review
from app.services.mlflow_service import MLflowService
from app.services.md_refinement import MDRefinementService

# Lightweight smoke mode: skip heavy imports (torch/sentence_transformers) if requested
LIGHT_MODE = os.getenv("RSN_LIGHT_MODE") == "1"

def _stub_llm_drift():
    class _Stub:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
        def evaluate_intent_alignment(self, *_args, **_kwargs):
            return {"status": "stub", "drift": 0.0}
    return _Stub

def _stub_semantic_router():
    class _Stub:  # type: ignore
        def __init__(self, *args, **_kwargs):
            pass
        def route(self, *_args, **_kwargs):
            return "stub"
    return _Stub

def _stub_sampler():
    class _Stub:  # type: ignore
        def __init__(self, *args, **_kwargs):
            pass
        def generate_sampling_plan(self, *_args, **_kwargs):
            return {"regions": []}
    return _Stub

# Optional heavy dependencies: gracefully degrade if unavailable (or light mode)
if LIGHT_MODE:
    LLMDriftEvaluator = _stub_llm_drift()  # type: ignore
    SemanticRouter = _stub_semantic_router()  # type: ignore
    AdaptiveSampler = _stub_sampler()  # type: ignore
else:
    try:  # pragma: no cover - optional
        from src.peer_review.metrics.llm_drift import LLMDriftEvaluator
    except Exception as e:  # pragma: no cover - smoke fallback
        logging.getLogger(__name__).warning("LLMDriftEvaluator unavailable (%s); using no-op stub", e)
        LLMDriftEvaluator = _stub_llm_drift()  # type: ignore

    try:  # pragma: no cover - optional
        from src.rex.routing.semantic import SemanticRouter
    except Exception as e:  # pragma: no cover - smoke fallback
        logging.getLogger(__name__).warning("SemanticRouter unavailable (%s); using stub", e)
        SemanticRouter = _stub_semantic_router()  # type: ignore

    try:  # pragma: no cover - optional
        from src.rex.bio.sampling.adaptive import AdaptiveSampler
    except Exception as e:  # pragma: no cover - smoke fallback
        logging.getLogger(__name__).warning("AdaptiveSampler unavailable (%s); using stub", e)
        AdaptiveSampler = _stub_sampler()  # type: ignore

logger = logging.getLogger(__name__)

class PeerReviewService:
    """
    Peer review service with dependency injection support.

    All dependencies can be injected for testability and loose coupling.
    If not provided, default implementations are created.
    """

    def __init__(
        self,
        redis_url: str = "redis://rsn-redis:6379/0",
        redis_client: Optional[Redis] = None,
        peer_review_engine: Optional[PeerReviewEngine] = None,
        llm_drift_evaluator: Optional[LLMDriftEvaluator] = None,
        semantic_router: Optional[SemanticRouter] = None,
        adaptive_sampler: Optional[AdaptiveSampler] = None,
        md_service: Optional[MDRefinementService] = None,
        mlflow_service: Optional[MLflowService] = None
    ):
        """
        Initialize PeerReviewService with dependency injection.

        Args:
            redis_url: Redis connection URL (used if redis_client not provided)
            redis_client: Optional Redis client instance
            peer_review_engine: Optional PeerReviewEngine instance
            llm_drift_evaluator: Optional LLMDriftEvaluator instance
            semantic_router: Optional SemanticRouter instance
            adaptive_sampler: Optional AdaptiveSampler instance
            md_service: Optional MDRefinementService instance
            mlflow_service: Optional MLflowService instance
        """
        logger.info("Initializing PeerReviewService with DI pattern")

        # Initialize Redis (injected or create new)
        if redis_client is not None:
            self.redis = redis_client
            logger.info("Using injected Redis client")
        else:
            logger.info(f"Creating Redis client from URL: {redis_url}")
            try:
                self.redis = Redis.from_url(redis_url)
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

        # Initialize dependencies (injected or create new)
        self.engine = peer_review_engine or PeerReviewEngine()
        logger.info(f"PeerReviewEngine: {'injected' if peer_review_engine else 'created'}")

        self.llm_drift = llm_drift_evaluator or LLMDriftEvaluator(
            sample_rate=0.1,
            redis_client=self.redis
        )
        logger.info(f"LLMDriftEvaluator: {'injected' if llm_drift_evaluator else 'created'}")

        self.router = semantic_router or SemanticRouter(self.redis)
        logger.info(f"SemanticRouter: {'injected' if semantic_router else 'created'}")

        self.sampler = adaptive_sampler or AdaptiveSampler()
        logger.info(f"AdaptiveSampler: {'injected' if adaptive_sampler else 'created'}")

        self.md_service = md_service or MDRefinementService()
        logger.info(f"MDRefinementService: {'injected' if md_service else 'created'}")

        self.mlflow = mlflow_service or MLflowService()
        logger.info(f"MLflowService: {'injected' if mlflow_service else 'created'}")

        logger.info("PeerReviewService initialized successfully with all components")

    def run(
        self,
        job_id: str,
        scores: Dict[str, Any],
        meta: Dict[str, Any],
        plddt: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        logger.info(f"Starting peer review for job {job_id}")

        # 1. Semantic routing
        logger.info("Step 1: Semantic routing")
        try:
            plugin = self.router.route(meta.get("sequence", ""), meta)
            logger.info(f"Routed to plugin: {plugin}")
        except Exception as e:
            logger.error(f"Semantic routing failed: {e}")
            plugin = None

        # 2. Dual-layer drift
        logger.info("Step 2: Dual-layer drift evaluation")
        try:
            drift_result = self.llm_drift.evaluate_intent_alignment(
                {"scores": scores, "meta": meta},
                job_id
            )
            logger.info(f"Drift check completed: {drift_result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"Drift evaluation failed: {e}")
            drift_result = {"status": "error", "error": str(e)}

        # 3. pLDDT-aware sampling
        sampling_plan = None
        if plddt is not None:
            logger.info("Step 3: Generating pLDDT-aware sampling plan")
            try:
                sampling_plan = self.sampler.generate_sampling_plan(plddt)
                logger.info(f"Sampling plan generated with {len(sampling_plan.get('regions', []))} regions")
            except Exception as e:
                logger.error(f"Sampling plan generation failed: {e}")
        else:
            logger.info("Step 3: Skipping sampling plan (no pLDDT provided)")

        # 4. Standard peer review
        logger.info("Step 4: Running standard peer review")
        try:
            submission = {"scores": scores, "meta": meta}
            res = self.engine.score_aghi_human(submission)
            issues = self.engine.policy_check(submission)
            logger.info(f"Peer review completed with {len(issues)} issues found")
        except Exception as e:
            logger.error(f"Peer review failed: {e}")
            raise

        # 5. MD fallback
        confidence = scores.get("confidence", 1.0)
        saxs_mismatch = scores.get("saxs_mismatch_sigma", 0.0)
        md_result = None

        logger.info(f"Step 5: MD fallback check (confidence={confidence:.3f}, saxs_sigma={saxs_mismatch:.2f})")
        if self.md_service.should_trigger_md(confidence, saxs_mismatch):
            logger.info("MD refinement triggered")
            try:
                md_result = self.md_service.run_short_equilibration(
                    meta.get("structure_path", "/tmp/input.pdb"),
                    f"/tmp/refined_{job_id}.pdb"
                )
                if md_result.get("success"):
                    logger.info(f"MD refinement successful: {md_result['refined_pdb']}")
                else:
                    logger.warning(f"MD refinement failed: {md_result.get('error', 'unknown error')}")
            except Exception as e:
                logger.error(f"MD refinement exception: {e}")
                md_result = {"success": False, "error": str(e)}
        else:
            logger.info("MD refinement not needed")

        # 6. Certification
        logger.info("Step 6: Generating ethics certification")
        try:
            cert = self.engine.certify(job_id, res, "/tmp/ethics")
            self.mlflow.log_artifact(job_id, cert["cert_path"], artifact_path="ethics_trace")
            logger.info(f"Certification completed: {cert.get('cert_path', 'unknown')}")
        except Exception as e:
            logger.error(f"Certification failed: {e}")
            raise

        # 7. Metrics
        logger.info("Step 7: Recording metrics")
        try:
            observe_peer_review(scores, res)
            logger.info("Metrics recorded successfully")
        except Exception as e:
            logger.error(f"Metrics recording failed: {e}")

        logger.info(f"Peer review completed for job {job_id}")
        return {
            **res,
            "issues": issues,
            "drift_check": drift_result,
            "semantic_plugin": plugin,
            "sampling_plan": sampling_plan,
            "md_refinement": md_result,
            **cert
        }
