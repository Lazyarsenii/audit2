"""
Tests for Cost Estimator service.
"""
import pytest

from app.core.scoring.complexity import Complexity
from app.core.scoring.tech_debt import TechDebtScore
from app.services.cost_estimator import CostEstimator, ForwardEstimate, HistoricalEstimate


class TestCostEstimator:
    """Test cases for Cost Estimator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.estimator = CostEstimator()

    def test_forward_estimate_small_project(self):
        """Test forward estimate for small project."""
        complexity = Complexity.SMALL
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)  # Total = 10

        result = self.estimator.estimate_forward(complexity, tech_debt)

        assert isinstance(result, ForwardEstimate)
        assert result.complexity == "S"
        # Small project typical hours should be around 50 * 1.9 = 95
        assert 80 < result.hours_typical.total < 150

    def test_forward_estimate_xlarge_project(self):
        """Test forward estimate for XL project."""
        complexity = Complexity.XLARGE
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = self.estimator.estimate_forward(complexity, tech_debt)

        # XL project typical hours should be around 700 * 1.9 = 1330
        assert result.hours_typical.total > 1000

    def test_tech_debt_multiplier_increases_hours(self):
        """High tech debt should increase estimated hours."""
        complexity = Complexity.MEDIUM

        # Good tech debt
        good_debt = TechDebtScore(3, 3, 3, 3, 3)  # Total = 15
        result_good = self.estimator.estimate_forward(complexity, good_debt)

        # Bad tech debt
        bad_debt = TechDebtScore(0, 0, 1, 1, 1)  # Total = 3
        result_bad = self.estimator.estimate_forward(complexity, bad_debt)

        # Bad debt should result in more hours
        assert result_bad.hours_typical.total > result_good.hours_typical.total
        assert result_bad.tech_debt_multiplier > result_good.tech_debt_multiplier

    def test_cost_ranges_eu_ua(self):
        """Test that EU and UA cost ranges are calculated."""
        complexity = Complexity.MEDIUM
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = self.estimator.estimate_forward(complexity, tech_debt)

        # EU should be more expensive than UA
        assert result.cost_eu.min > result.cost_ua.min
        assert result.cost_eu.max > result.cost_ua.max

        # Currency should be correct
        assert result.cost_eu.currency == "EUR"
        assert result.cost_ua.currency == "USD"

    def test_activity_breakdown(self):
        """Test that activity breakdown is correct."""
        complexity = Complexity.MEDIUM
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = self.estimator.estimate_forward(complexity, tech_debt)

        typical = result.hours_typical

        # All activities should have hours
        assert typical.analysis > 0
        assert typical.design > 0
        assert typical.development > 0
        assert typical.qa > 0
        assert typical.documentation > 0

        # Total should equal sum
        expected_total = (
            typical.analysis +
            typical.design +
            typical.development +
            typical.qa +
            typical.documentation
        )
        assert abs(typical.total - expected_total) < 0.1

    def test_historical_estimate(self):
        """Test historical effort estimation."""
        structure_data = {
            "commits_total": 100,
            "authors_count": 3,
            "recent_commits": 20,
        }

        result = self.estimator.estimate_historical(structure_data)

        assert isinstance(result, HistoricalEstimate)
        assert result.active_days > 0
        assert result.estimated_hours_min > 0
        assert result.estimated_hours_max > result.estimated_hours_min
        assert result.confidence in ["low", "medium", "high"]
        assert len(result.note) > 0

    def test_historical_estimate_small_repo(self):
        """Test historical estimate for small repo has low confidence."""
        structure_data = {
            "commits_total": 10,
            "authors_count": 1,
            "recent_commits": 5,
        }

        result = self.estimator.estimate_historical(structure_data)

        assert result.confidence == "low"

    def test_forward_estimate_to_dict(self):
        """Test that forward estimate serializes correctly."""
        complexity = Complexity.SMALL
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = self.estimator.estimate_forward(complexity, tech_debt)
        data = result.to_dict()

        assert "hours" in data
        assert "cost" in data
        assert "complexity" in data
        assert "min" in data["hours"]
        assert "typical" in data["hours"]
        assert "max" in data["hours"]
        assert "eu" in data["cost"]
        assert "ua" in data["cost"]
