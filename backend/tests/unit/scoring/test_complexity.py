"""
Tests for Complexity scoring module.
"""
import pytest

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.complexity import (
    calculate_complexity,
    Complexity,
    get_complexity_description,
    get_base_hours,
)


class TestComplexityScoring:
    """Test cases for Complexity calculation."""

    def test_small_project(self):
        """Small LOC should result in Small complexity."""
        static_metrics = {
            "total_loc": 3000,
            "files_count": 20,
            "external_deps_count": 5,
        }
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        assert result == Complexity.SMALL

    def test_medium_project(self):
        """Medium LOC should result in Medium complexity."""
        static_metrics = {
            "total_loc": 20000,
            "files_count": 100,
            "external_deps_count": 15,
        }
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        assert result == Complexity.MEDIUM

    def test_large_project(self):
        """Large LOC should result in Large complexity."""
        static_metrics = {
            "total_loc": 80000,
            "files_count": 400,
            "external_deps_count": 25,
        }
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        assert result == Complexity.LARGE

    def test_xlarge_project(self):
        """Very large LOC should result in XLarge complexity."""
        static_metrics = {
            "total_loc": 150000,
            "files_count": 800,
            "external_deps_count": 50,
        }
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        assert result == Complexity.XLARGE

    def test_tech_debt_bumps_complexity(self):
        """High tech debt should bump complexity up."""
        static_metrics = {
            "total_loc": 5000,  # Would be Small normally
            "files_count": 30,
            "external_deps_count": 10,
        }
        repo_health = RepoHealthScore(1, 1, 1, 1)
        tech_debt = TechDebtScore(0, 1, 0, 1, 1)  # Total = 3 (very high debt)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        # Should be bumped from Small to Medium
        assert result == Complexity.MEDIUM

    def test_many_deps_bumps_complexity(self):
        """Many external dependencies should bump complexity."""
        static_metrics = {
            "total_loc": 5000,  # Would be Small normally
            "files_count": 30,
            "external_deps_count": 50,  # Many deps
        }
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)

        result = calculate_complexity(static_metrics, repo_health, tech_debt)

        assert result == Complexity.MEDIUM

    def test_complexity_descriptions(self):
        """Test that all complexity levels have descriptions."""
        for level in Complexity:
            desc = get_complexity_description(level)
            assert desc is not None
            assert len(desc) > 5

    def test_base_hours_per_complexity(self):
        """Test base hours are defined for all complexity levels."""
        for level in Complexity:
            hours = get_base_hours(level)
            assert "min" in hours
            assert "typical" in hours
            assert "max" in hours
            assert hours["min"] < hours["typical"] < hours["max"]
