"""
Tests for Scenario Engine
==========================

Validates deterministic scenario execution and outcome consistency.
"""

import pytest
from backend.app.services.scenario_engine import scenario_engine, Scenario, ScenarioOutcome


def test_perfect_scenario():
    """Test PERFECT scenario produces S++ grade outcomes."""
    outcome = scenario_engine.execute(Scenario.PERFECT)
    
    assert outcome.confidence_score > 0.95
    assert outcome.validation_passed is True
    assert outcome.pain_metrics["rage_click_score"] < 5.0
    assert outcome.error_count == 0
    assert outcome.drift_detected is False
    assert outcome.deployment_blocked is False
    assert "PERFECT" in outcome.narrative


def test_drift_scenario_day1():
    """Test DRIFT_DETECTED scenario on Day 1 (should be perfect)."""
    outcome = scenario_engine.execute(Scenario.DRIFT_DETECTED, day=1)
    
    assert outcome.confidence_score > 0.95
    assert outcome.drift_detected is False
    assert outcome.deployment_blocked is False


def test_drift_scenario_day3():
    """Test DRIFT_DETECTED scenario on Day 3 (should degrade)."""
    outcome = scenario_engine.execute(Scenario.DRIFT_DETECTED, day=3)
    
    assert outcome.confidence_score < 0.80  # Degraded
    assert outcome.drift_detected is True
    assert outcome.deployment_blocked is True
    assert "DRIFT DETECTED" in outcome.narrative
    assert outcome.pain_metrics["rage_click_score"] > 20.0


def test_empathy_fail_scenario():
    """Test EMPATHY_FAIL scenario produces high pain metrics."""
    outcome = scenario_engine.execute(Scenario.EMPATHY_FAIL)
    
    assert outcome.confidence_score > 0.90  # Technical quality still good
    assert outcome.pain_metrics["rage_click_score"] > 40.0
    assert outcome.pain_metrics["hesitation_rate"] > 10000.0
    assert outcome.pain_metrics["abandonment_rate"] > 60.0
    assert outcome.deployment_blocked is True
    assert "EMPATHY GATE BLOCKED" in outcome.narrative


def test_random_scenario_variability():
    """Test RANDOM scenario produces different results."""
    outcomes = [scenario_engine.execute(Scenario.RANDOM) for _ in range(10)]
    
    # Check that at least some variation exists
    confidence_scores = [o.confidence_score for o in outcomes]
    assert len(set(confidence_scores)) > 1, "Random scenario should produce varied results"


def test_scenario_determinism():
    """Test that non-RANDOM scenarios are deterministic."""
    outcome1 = scenario_engine.execute(Scenario.PERFECT)
    outcome2 = scenario_engine.execute(Scenario.PERFECT)
    
    assert outcome1.confidence_score == outcome2.confidence_score
    assert outcome1.pain_metrics == outcome2.pain_metrics
    assert outcome1.narrative == outcome2.narrative


def test_to_dict_serialization():
    """Test ScenarioOutcome serialization."""
    outcome = scenario_engine.execute(Scenario.PERFECT)
    data = outcome.to_dict()
    
    assert "confidence_score" in data
    assert "pain_metrics" in data
    assert "deployment_blocked" in data
    assert "narrative" in data
    assert isinstance(data["confidence_score"], float)
    assert isinstance(data["deployment_blocked"], bool)


def test_all_scenarios_executable():
    """Test that all scenarios can be executed without errors."""
    for scenario in Scenario:
        outcome = scenario_engine.execute(scenario, day=1)
        assert isinstance(outcome, ScenarioOutcome)
        assert outcome.narrative is not None
        assert len(outcome.pain_metrics) == 4
