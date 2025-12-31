"""
Tests for Omega Scorer Lite
============================

Validates Integrity, Resonance, Stability calculations and grade assignments.
"""

import pytest
from backend.app.services.omega_scorer_lite import omega_scorer, OmegaComponents


def test_perfect_scenario_omega():
    """Test S++ grade scenario with perfect metrics."""
    result = omega_scorer.calculate(
        confidence_score=0.98,
        validation_passed=True,
        pain_metrics={
            "rage_click_score": 2.0,
            "hesitation_rate": 800.0,
            "abandonment_rate": 5.0,
        },
        error_count=0,
        consistency_score=0.99,
    )
    
    assert result.integrity >= 0.95
    assert result.resonance >= 0.95
    assert result.stability >= 0.95
    assert result.omega >= 0.95
    assert result.grade in ["S++", "S+", "S"]


def test_empathy_fail_scenario():
    """Test scenario with high user pain (low resonance)."""
    result = omega_scorer.calculate(
        confidence_score=0.92,
        validation_passed=True,
        pain_metrics={
            "rage_click_score": 45.0,
            "hesitation_rate": 12000.0,
            "abandonment_rate": 65.0,
        },
        error_count=2,
        consistency_score=0.94,
    )
    
    assert result.integrity > 0.85  # Technical quality still good
    assert result.resonance < 0.70  # High pain = low resonance
    assert result.omega < 0.80      # Overall grade impacted
    assert result.grade in ["D", "C", "B"]


def test_drift_scenario():
    """Test scenario with errors and low consistency (low stability)."""
    result = omega_scorer.calculate(
        confidence_score=0.72,
        validation_passed=True,
        pain_metrics={
            "rage_click_score": 25.0,
            "hesitation_rate": 6500.0,
            "abandonment_rate": 35.0,
        },
        error_count=6,
        consistency_score=0.65,
    )
    
    assert result.stability < 0.70  # High error count = low stability
    assert result.omega < 0.75
    assert result.grade in ["C", "D", "F"]


def test_grade_boundaries():
    """Test grade assignment at exact thresholds."""
    test_cases = [
        (0.970, "S++"),
        (0.955, "S+"),
        (0.935, "S"),
        (0.875, "A"),
        (0.785, "B"),
        (0.675, "C"),
        (0.525, "D"),
        (0.425, "F"),
    ]
    
    for omega_value, expected_grade in test_cases:
        grade = omega_scorer._assign_grade(omega_value)
        assert grade == expected_grade, f"Omega {omega_value} should be grade {expected_grade}, got {grade}"


def test_validation_failure_penalty():
    """Test that validation failure reduces integrity."""
    result_passed = omega_scorer.calculate(
        confidence_score=0.90,
        validation_passed=True,
        error_count=0,
        consistency_score=1.0,
    )
    
    result_failed = omega_scorer.calculate(
        confidence_score=0.90,
        validation_passed=False,
        error_count=0,
        consistency_score=1.0,
    )
    
    assert result_failed.integrity < result_passed.integrity
    assert result_failed.omega < result_passed.omega


def test_to_dict_serialization():
    """Test OmegaComponents serialization."""
    result = omega_scorer.calculate(
        confidence_score=0.95,
        validation_passed=True,
    )
    
    data = result.to_dict()
    
    assert "integrity" in data
    assert "resonance" in data
    assert "stability" in data
    assert "omega" in data
    assert "grade" in data
    assert "timestamp" in data
    assert isinstance(data["integrity"], float)
    assert isinstance(data["grade"], str)
