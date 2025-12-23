"""
Calibration service for improving estimation accuracy.

Collects feedback, adjusts thresholds, and tracks accuracy over time.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class CalibrationSample:
    """A single calibration data point."""
    analysis_id: str
    timestamp: datetime

    # Predicted values
    predicted_hours: float
    predicted_cost_eu: float
    predicted_cost_ua: float
    predicted_level: str
    predicted_complexity: str

    # Actual values (from feedback)
    actual_hours: Optional[float] = None
    actual_cost: Optional[float] = None
    actual_level: Optional[str] = None

    # Calculated errors
    hours_error_pct: Optional[float] = None
    cost_error_pct: Optional[float] = None
    level_correct: Optional[bool] = None


@dataclass
class CalibrationStats:
    """Aggregated calibration statistics."""
    sample_count: int
    hours_mape: float  # Mean Absolute Percentage Error
    hours_bias: float  # Positive = overestimate, negative = underestimate
    cost_mape: float
    cost_bias: float
    level_accuracy: float
    confidence_interval: float  # Current ± range

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "hours": {
                "mape": round(self.hours_mape, 1),
                "bias": round(self.hours_bias, 1),
                "interpretation": self._interpret_bias(self.hours_bias),
            },
            "cost": {
                "mape": round(self.cost_mape, 1),
                "bias": round(self.cost_bias, 1),
            },
            "level_accuracy": round(self.level_accuracy * 100, 1),
            "confidence_interval_pct": round(self.confidence_interval, 0),
            "accuracy_label": self._accuracy_label(),
        }

    def _interpret_bias(self, bias: float) -> str:
        if bias > 10:
            return "consistently overestimates"
        elif bias < -10:
            return "consistently underestimates"
        else:
            return "well calibrated"

    def _accuracy_label(self) -> str:
        if self.hours_mape <= 15:
            return "excellent (±15%)"
        elif self.hours_mape <= 25:
            return "good (±25%)"
        elif self.hours_mape <= 40:
            return "acceptable (±40%)"
        else:
            return "needs calibration (>40%)"


class CalibrationService:
    """
    Service for calibrating cost estimates based on actual outcomes.

    How to improve accuracy:
    1. After project completion, submit actual hours/cost via add_feedback()
    2. Service calculates errors and adjusts multipliers
    3. New estimates use calibrated parameters

    Target: reduce ±30-50% to ±15-25%
    """

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("calibration_data.json")
        self.samples: List[CalibrationSample] = []
        self._load_data()

        # Calibration adjustments (learned from feedback)
        self.adjustments = {
            "hours_multiplier": 1.0,  # Applied to all hour estimates
            "complexity_adjustments": {  # Per-complexity corrections
                "S": 1.0,
                "M": 1.0,
                "L": 1.0,
                "XL": 1.0,
            },
            "tech_debt_adjustments": {},  # Per-debt-level corrections
        }

    def _load_data(self):
        """Load existing calibration data."""
        if self.data_path.exists():
            try:
                with open(self.data_path) as f:
                    data = json.load(f)
                    # Reconstruct samples from JSON
                    for s in data.get("samples", []):
                        self.samples.append(CalibrationSample(
                            analysis_id=s["analysis_id"],
                            timestamp=datetime.fromisoformat(s["timestamp"]),
                            predicted_hours=s["predicted_hours"],
                            predicted_cost_eu=s["predicted_cost_eu"],
                            predicted_cost_ua=s["predicted_cost_ua"],
                            predicted_level=s["predicted_level"],
                            predicted_complexity=s["predicted_complexity"],
                            actual_hours=s.get("actual_hours"),
                            actual_cost=s.get("actual_cost"),
                            actual_level=s.get("actual_level"),
                            hours_error_pct=s.get("hours_error_pct"),
                            cost_error_pct=s.get("cost_error_pct"),
                            level_correct=s.get("level_correct"),
                        ))
            except Exception as e:
                logger.warning(f"Failed to load calibration data: {e}")

    def _save_data(self):
        """Persist calibration data."""
        data = {
            "samples": [
                {
                    "analysis_id": s.analysis_id,
                    "timestamp": s.timestamp.isoformat(),
                    "predicted_hours": s.predicted_hours,
                    "predicted_cost_eu": s.predicted_cost_eu,
                    "predicted_cost_ua": s.predicted_cost_ua,
                    "predicted_level": s.predicted_level,
                    "predicted_complexity": s.predicted_complexity,
                    "actual_hours": s.actual_hours,
                    "actual_cost": s.actual_cost,
                    "actual_level": s.actual_level,
                    "hours_error_pct": s.hours_error_pct,
                    "cost_error_pct": s.cost_error_pct,
                    "level_correct": s.level_correct,
                }
                for s in self.samples
            ],
            "adjustments": self.adjustments,
        }
        with open(self.data_path, "w") as f:
            json.dump(data, f, indent=2)

    def record_prediction(
        self,
        analysis_id: str,
        predicted_hours: float,
        predicted_cost_eu: float,
        predicted_cost_ua: float,
        predicted_level: str,
        predicted_complexity: str,
    ):
        """Record a new prediction for later calibration."""
        sample = CalibrationSample(
            analysis_id=analysis_id,
            timestamp=datetime.now(timezone.utc),
            predicted_hours=predicted_hours,
            predicted_cost_eu=predicted_cost_eu,
            predicted_cost_ua=predicted_cost_ua,
            predicted_level=predicted_level,
            predicted_complexity=predicted_complexity,
        )
        self.samples.append(sample)
        self._save_data()

    def add_feedback(
        self,
        analysis_id: str,
        actual_hours: Optional[float] = None,
        actual_cost: Optional[float] = None,
        actual_level: Optional[str] = None,
    ):
        """
        Add actual outcome data for calibration.

        Call this after a project is completed to improve future estimates.
        """
        # Find the sample
        sample = next((s for s in self.samples if s.analysis_id == analysis_id), None)
        if not sample:
            logger.warning(f"No prediction found for analysis {analysis_id}")
            return

        # Update with actuals
        if actual_hours is not None:
            sample.actual_hours = actual_hours
            if sample.predicted_hours > 0:
                sample.hours_error_pct = (
                    (sample.predicted_hours - actual_hours) / actual_hours * 100
                )

        if actual_cost is not None:
            sample.actual_cost = actual_cost
            avg_predicted = (sample.predicted_cost_eu + sample.predicted_cost_ua) / 2
            if avg_predicted > 0:
                sample.cost_error_pct = (
                    (avg_predicted - actual_cost) / actual_cost * 100
                )

        if actual_level is not None:
            sample.actual_level = actual_level
            sample.level_correct = (sample.predicted_level == actual_level)

        self._save_data()
        self._recalculate_adjustments()

    def _recalculate_adjustments(self):
        """Recalculate calibration adjustments based on all feedback."""
        samples_with_hours = [s for s in self.samples if s.actual_hours is not None]

        if len(samples_with_hours) < 3:
            return  # Need at least 3 samples

        # Calculate overall hours adjustment
        ratios = [s.actual_hours / s.predicted_hours for s in samples_with_hours
                  if s.predicted_hours > 0]
        if ratios:
            self.adjustments["hours_multiplier"] = mean(ratios)

        # Calculate per-complexity adjustments
        for complexity in ["S", "M", "L", "XL"]:
            complexity_samples = [
                s for s in samples_with_hours
                if s.predicted_complexity == complexity and s.predicted_hours > 0
            ]
            if len(complexity_samples) >= 2:
                ratios = [s.actual_hours / s.predicted_hours for s in complexity_samples]
                self.adjustments["complexity_adjustments"][complexity] = mean(ratios)

        self._save_data()
        logger.info(f"Recalculated adjustments: {self.adjustments}")

    def get_calibrated_hours(
        self,
        raw_hours: float,
        complexity: str,
    ) -> float:
        """Apply calibration adjustments to raw hour estimate."""
        # Apply general multiplier
        adjusted = raw_hours * self.adjustments["hours_multiplier"]

        # Apply complexity-specific adjustment
        complexity_adj = self.adjustments["complexity_adjustments"].get(complexity, 1.0)
        adjusted *= complexity_adj

        return adjusted

    def get_stats(self) -> Optional[CalibrationStats]:
        """Get current calibration statistics."""
        samples_with_feedback = [
            s for s in self.samples
            if s.actual_hours is not None or s.actual_level is not None
        ]

        if not samples_with_feedback:
            return None

        # Hours MAPE
        hours_errors = [
            abs(s.hours_error_pct)
            for s in samples_with_feedback
            if s.hours_error_pct is not None
        ]
        hours_mape = mean(hours_errors) if hours_errors else 50.0

        # Hours bias
        hours_signed = [
            s.hours_error_pct
            for s in samples_with_feedback
            if s.hours_error_pct is not None
        ]
        hours_bias = mean(hours_signed) if hours_signed else 0.0

        # Cost MAPE
        cost_errors = [
            abs(s.cost_error_pct)
            for s in samples_with_feedback
            if s.cost_error_pct is not None
        ]
        cost_mape = mean(cost_errors) if cost_errors else 50.0
        cost_bias = mean([
            s.cost_error_pct for s in samples_with_feedback
            if s.cost_error_pct is not None
        ]) if cost_errors else 0.0

        # Level accuracy
        level_results = [
            s.level_correct
            for s in samples_with_feedback
            if s.level_correct is not None
        ]
        level_accuracy = (
            sum(level_results) / len(level_results)
            if level_results else 0.0
        )

        # Confidence interval (simplified: 1.96 * std for 95% CI)
        if len(hours_errors) >= 2:
            confidence_interval = 1.96 * stdev(hours_errors)
        else:
            confidence_interval = 50.0

        return CalibrationStats(
            sample_count=len(samples_with_feedback),
            hours_mape=hours_mape,
            hours_bias=hours_bias,
            cost_mape=cost_mape,
            cost_bias=cost_bias,
            level_accuracy=level_accuracy,
            confidence_interval=confidence_interval,
        )


# Singleton instance
calibration_service = CalibrationService(
    data_path=Path(__file__).parent.parent / "data" / "calibration.json"
)


# API integration example
"""
# After analysis is complete, record the prediction:
calibration_service.record_prediction(
    analysis_id="abc-123",
    predicted_hours=175,
    predicted_cost_eu=15000,
    predicted_cost_ua=9000,
    predicted_level="Internal Tool",
    predicted_complexity="M",
)

# Later, when project is done, add feedback:
calibration_service.add_feedback(
    analysis_id="abc-123",
    actual_hours=210,  # Was actually 210 hours
    actual_level="Internal Tool",  # Level was correct
)

# Future estimates automatically use calibrated values:
raw_estimate = 175
calibrated = calibration_service.get_calibrated_hours(raw_estimate, "M")
# calibrated might be 210 if historical data shows 20% underestimation
"""
