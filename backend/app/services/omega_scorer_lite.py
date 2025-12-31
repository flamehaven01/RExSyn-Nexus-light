"""
Omega Scorer Lite - Lightweight implementation for RExSyn-Nexus-Light
=====================================================================

Calculates Integrity (Iota), Resonance (Rho), and Stability (1-Delta) 
scores based on prediction metrics and user feedback, without requiring 
the full LEDA Engine infrastructure.

Algorithm:
    Integrity (I) = f(confidence_threshold, validation_success_rate)
    Resonance (P) = f(user_pain_metrics, workflow_completion_rate)  
    Stability (1-Delta) = f(consistency_across_runs, error_rate)
    
    Omega (Omega) = (I * P * (1-Delta))^(1/3)  # Geometric mean

Grade Boundaries (aligned with Full Edition):
    S++: >= 0.965
    S+:  >= 0.95
    S:   >= 0.93
    A:   >= 0.85
    B:   >= 0.75
    C:   >= 0.65
    D:   >= 0.50
    F:   <  0.50
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass
class OmegaComponents:
    """Individual components of Omega score."""
    integrity: float      # Iota (I): 0.0-1.0
    resonance: float      # Rho (P): 0.0-1.0  
    stability: float      # 1-Delta: 0.0-1.0
    omega: float          # Omega: Geometric mean of I, P, (1-Delta)
    grade: str            # S++, S+, S, A, B, C, D, F
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "integrity": round(self.integrity, 3),
            "resonance": round(self.resonance, 3),
            "stability": round(self.stability, 3),
            "omega": round(self.omega, 3),
            "grade": self.grade,
            "timestamp": self.timestamp.isoformat(),
        }


class OmegaScorerLite:
    """Lightweight Omega scoring for demo environments."""
    
    # Grade boundaries (aligned with Full Edition)
    GRADE_THRESHOLDS = {
        "S++": 0.965,
        "S+": 0.95,
        "S": 0.93,
        "A": 0.85,
        "B": 0.75,
        "C": 0.65,
        "D": 0.50,
        # Below 0.50 = F
    }
    
    def calculate(
        self,
        confidence_score: float,
        validation_passed: bool,
        pain_metrics: Optional[Dict[str, float]] = None,
        error_count: int = 0,
        consistency_score: float = 1.0,
    ) -> OmegaComponents:
        """
        Calculate Omega score from available metrics.
        
        Args:
            confidence_score: Prediction confidence (0.0-1.0)
            validation_passed: Whether validation checks passed
            pain_metrics: User pain metrics from empathy API
            error_count: Number of errors encountered
            consistency_score: Consistency across repeated runs (0.0-1.0)
        
        Returns:
            OmegaComponents with calculated scores
        """
        # 1. Integrity (I): Technical quality
        integrity = self._calculate_integrity(
            confidence_score, 
            validation_passed
        )
        
        # 2. Resonance (P): User experience quality
        resonance = self._calculate_resonance(pain_metrics)
        
        # 3. Stability (1-Delta): System reliability
        stability = self._calculate_stability(
            error_count, 
            consistency_score
        )
        
        # 4. Omega (Omega): Geometric mean
        omega = self._calculate_omega(integrity, resonance, stability)
        
        # 5. Grade assignment
        grade = self._assign_grade(omega)
        
        return OmegaComponents(
            integrity=integrity,
            resonance=resonance,
            stability=stability,
            omega=omega,
            grade=grade,
            timestamp=datetime.now(),
        )
    
    def _calculate_integrity(
        self, 
        confidence: float, 
        validation_passed: bool
    ) -> float:
        """
        Integrity = Technical correctness and validation success.
        
        Formula: I = confidence * validation_multiplier
        """
        validation_multiplier = 1.0 if validation_passed else 0.8
        return min(confidence * validation_multiplier, 1.0)
    
    def _calculate_resonance(
        self, 
        pain_metrics: Optional[Dict[str, float]]
    ) -> float:
        """
        Resonance = User experience quality (inverse of pain).
        
        Formula: P = 1 - (normalized_pain_score)
        """
        if not pain_metrics:
            return 0.95  # Default high resonance for demo
        
        # Normalize pain metrics (0-100 scale -> 0-1)
        rage_click = pain_metrics.get("rage_click_score", 0) / 100
        hesitation = min(pain_metrics.get("hesitation_rate", 0) / 10000, 1.0)
        abandonment = pain_metrics.get("abandonment_rate", 0) / 100
        
        # Average pain -> inverse for resonance
        avg_pain = (rage_click + hesitation + abandonment) / 3
        return max(1.0 - avg_pain, 0.0)
    
    def _calculate_stability(
        self, 
        error_count: int, 
        consistency: float
    ) -> float:
        """
        Stability = Reliability and consistency (1 - Delta).
        
        Formula: (1-Delta) = consistency * error_penalty
        """
        # Penalize errors exponentially
        error_penalty = math.exp(-error_count * 0.1)
        return min(consistency * error_penalty, 1.0)
    
    def _calculate_omega(
        self, 
        integrity: float, 
        resonance: float, 
        stability: float
    ) -> float:
        """
        Omega = Geometric mean of I, P, (1-Delta).
        
        Formula: Omega = (I * P * (1-Delta))^(1/3)
        """
        product = integrity * resonance * stability
        return math.pow(product, 1/3)
    
    def _assign_grade(self, omega: float) -> str:
        """Assign letter grade based on Omega score."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if omega >= threshold:
                return grade
        return "F"


# Singleton instance
omega_scorer = OmegaScorerLite()
