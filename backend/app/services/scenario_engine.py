"""
Scenario Engine - Deterministic simulation for B2B demos
=========================================================

Provides controlled, repeatable outcomes for sales demonstrations.
Eliminates randomness to ensure consistent demo experiences.

Usage:
    from backend.app.services.scenario_engine import scenario_engine, Scenario
    
    outcome = scenario_engine.execute(Scenario.PERFECT)
    # Returns deterministic ScenarioOutcome with pre-defined metrics
"""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass
import random


class Scenario(str, Enum):
    """Available demo scenarios."""
    PERFECT = "perfect"              # All metrics excellent, deployment succeeds
    DRIFT_DETECTED = "drift_detected"  # Day-3 data shows drift, warning triggered
    EMPATHY_FAIL = "empathy_fail"    # High user pain, deployment blocked
    RANDOM = "random"                # Original behavior (for testing)


@dataclass
class ScenarioOutcome:
    """Predicted outcome for a scenario."""
    confidence_score: float
    validation_passed: bool
    pain_metrics: Dict[str, float]
    error_count: int
    consistency_score: float
    drift_detected: bool
    deployment_blocked: bool
    narrative: str  # Human-readable explanation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score": round(self.confidence_score, 3),
            "validation_passed": self.validation_passed,
            "pain_metrics": {
                k: round(v, 1) for k, v in self.pain_metrics.items()
            },
            "error_count": self.error_count,
            "consistency_score": round(self.consistency_score, 3),
            "drift_detected": self.drift_detected,
            "deployment_blocked": self.deployment_blocked,
            "narrative": self.narrative,
        }


class ScenarioEngine:
    """Generates deterministic outcomes for demo scenarios."""
    
    def execute(self, scenario: Scenario, day: int = 1) -> ScenarioOutcome:
        """
        Execute scenario and return controlled outcome.
        
        Args:
            scenario: Which scenario to run
            day: Simulation day (for drift detection)
        
        Returns:
            ScenarioOutcome with all metrics pre-determined
        """
        if scenario == Scenario.PERFECT:
            return self._scenario_perfect()
        elif scenario == Scenario.DRIFT_DETECTED:
            return self._scenario_drift(day)
        elif scenario == Scenario.EMPATHY_FAIL:
            return self._scenario_empathy_fail()
        else:  # RANDOM
            return self._scenario_random()
    
    def _scenario_perfect(self) -> ScenarioOutcome:
        """S++ grade scenario - everything excellent."""
        return ScenarioOutcome(
            confidence_score=0.98,
            validation_passed=True,
            pain_metrics={
                "rage_click_score": 2.0,
                "hesitation_rate": 800.0,
                "abandonment_rate": 5.0,
                "error_encounters": 0,
            },
            error_count=0,
            consistency_score=0.99,
            drift_detected=False,
            deployment_blocked=False,
            narrative="[PERFECT] All systems optimal. Omega=0.97 (S++). Deployment approved.",
        )
    
    def _scenario_drift(self, day: int) -> ScenarioOutcome:
        """Drift detection scenario - degrades on day 3."""
        if day >= 3:
            return ScenarioOutcome(
                confidence_score=0.72,  # Dropped from 0.95
                validation_passed=True,
                pain_metrics={
                    "rage_click_score": 25.0,  # Increased
                    "hesitation_rate": 6500.0,  # Increased
                    "abandonment_rate": 35.0,   # Increased
                    "error_encounters": 6,       # Increased
                },
                error_count=6,
                consistency_score=0.65,  # Dropped
                drift_detected=True,
                deployment_blocked=True,
                narrative=f"[DRIFT DETECTED] Day {day}: Metrics degraded. Omega=0.71 (C). Deployment blocked.",
            )
        else:
            return self._scenario_perfect()  # Days 1-2 are perfect
    
    def _scenario_empathy_fail(self) -> ScenarioOutcome:
        """High user pain scenario - blocked by empathy gate."""
        return ScenarioOutcome(
            confidence_score=0.92,  # Good technical score
            validation_passed=True,
            pain_metrics={
                "rage_click_score": 45.0,    # CRITICAL
                "hesitation_rate": 12000.0,  # CRITICAL
                "abandonment_rate": 65.0,    # CRITICAL
                "error_encounters": 15,      # CRITICAL
            },
            error_count=2,  # Backend errors low
            consistency_score=0.94,
            drift_detected=False,
            deployment_blocked=True,
            narrative="[EMPATHY GATE BLOCKED] High user pain detected. Omega=0.68 (D). Deployment blocked.",
        )
    
    def _scenario_random(self) -> ScenarioOutcome:
        """Original random behavior for testing."""
        return ScenarioOutcome(
            confidence_score=random.uniform(0.7, 0.95),
            validation_passed=random.choice([True, True, False]),
            pain_metrics={
                "rage_click_score": random.uniform(5.0, 30.0),
                "hesitation_rate": random.uniform(1000.0, 8000.0),
                "abandonment_rate": random.uniform(10.0, 40.0),
                "error_encounters": random.randint(0, 8),
            },
            error_count=random.randint(0, 5),
            consistency_score=random.uniform(0.8, 1.0),
            drift_detected=random.random() < 0.2,
            deployment_blocked=random.random() < 0.3,
            narrative="[RANDOM] Simulated with random values.",
        )


# Singleton instance
scenario_engine = ScenarioEngine()
