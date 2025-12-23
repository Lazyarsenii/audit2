"""
Integration tests for the full analysis pipeline.
"""
import pytest

from app.core.scoring.repo_health import calculate_repo_health
from app.core.scoring.tech_debt import calculate_tech_debt
from app.core.scoring.product_level import classify_product_level, ProductLevel
from app.core.scoring.complexity import calculate_complexity, Complexity
from app.services.cost_estimator import cost_estimator
from app.services.task_generator import task_generator


class TestFullPipeline:
    """Integration tests for the complete analysis pipeline."""

    def test_healthy_repo_full_analysis(self, healthy_repo_data):
        """Test full pipeline for a healthy repository."""
        structure_data, static_metrics, semgrep_findings = healthy_repo_data

        # Step 1: Calculate Repo Health
        repo_health = calculate_repo_health(structure_data)
        assert repo_health.total >= 10  # Should be high

        # Step 2: Calculate Tech Debt
        tech_debt = calculate_tech_debt(static_metrics, semgrep_findings)
        assert tech_debt.total >= 12  # Should be low debt (high score)

        # Step 3: Classify Product Level
        product_level = classify_product_level(repo_health, tech_debt, structure_data)
        assert product_level in [ProductLevel.PLATFORM_MODULE, ProductLevel.NEAR_PRODUCT]

        # Step 4: Determine Complexity
        complexity = calculate_complexity(static_metrics, repo_health, tech_debt)
        assert complexity in [Complexity.MEDIUM, Complexity.LARGE]

        # Step 5: Estimate costs
        forward_estimate = cost_estimator.estimate_forward(complexity, tech_debt)
        historical_estimate = cost_estimator.estimate_historical(structure_data)

        # Verify estimates are reasonable
        assert forward_estimate.hours_typical.total > 100
        assert forward_estimate.cost_eu.min > 0
        assert forward_estimate.cost_ua.min > 0
        assert historical_estimate.estimated_hours_min > 0

        # Step 6: Generate tasks
        tasks = task_generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=semgrep_findings,
            structure_data=structure_data,
            product_level=product_level,
            complexity=complexity,
        )

        # Healthy repo should have few tasks
        assert len(tasks) < 10

    def test_unhealthy_repo_full_analysis(self, unhealthy_repo_data):
        """Test full pipeline for an unhealthy repository."""
        structure_data, static_metrics, semgrep_findings = unhealthy_repo_data

        # Step 1: Calculate Repo Health
        repo_health = calculate_repo_health(structure_data)
        assert repo_health.total <= 3  # Should be low

        # Step 2: Calculate Tech Debt
        tech_debt = calculate_tech_debt(static_metrics, semgrep_findings)
        assert tech_debt.total <= 5  # High debt (low score)

        # Step 3: Classify Product Level
        product_level = classify_product_level(repo_health, tech_debt, structure_data)
        assert product_level == ProductLevel.RND_SPIKE

        # Step 4: Determine Complexity
        complexity = calculate_complexity(static_metrics, repo_health, tech_debt)
        # Even small LOC should be bumped due to high debt
        assert complexity in [Complexity.SMALL, Complexity.MEDIUM]

        # Step 5: Estimate costs
        forward_estimate = cost_estimator.estimate_forward(complexity, tech_debt)
        historical_estimate = cost_estimator.estimate_historical(structure_data)

        # High debt should increase hours
        assert forward_estimate.tech_debt_multiplier > 1.2

        # Few commits = low historical estimate
        assert historical_estimate.confidence == "low"

        # Step 6: Generate tasks
        tasks = task_generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=semgrep_findings,
            structure_data=structure_data,
            product_level=product_level,
            complexity=complexity,
        )

        # Unhealthy repo should have many tasks
        assert len(tasks) >= 5

        # Should have P1 tasks
        p1_tasks = [t for t in tasks if t.priority.value == "P1"]
        assert len(p1_tasks) >= 2

        # Should have security tasks
        security_tasks = [t for t in tasks if t.category.value == "security"]
        assert len(security_tasks) >= 1

    def test_sample_repo_analysis(self, sample_structure_data, sample_static_metrics, sample_semgrep_findings):
        """Test analysis of a typical sample repository."""
        # Run full analysis
        repo_health = calculate_repo_health(sample_structure_data)
        tech_debt = calculate_tech_debt(sample_static_metrics, sample_semgrep_findings)
        product_level = classify_product_level(repo_health, tech_debt, sample_structure_data)
        complexity = calculate_complexity(sample_static_metrics, repo_health, tech_debt)

        # All results should be valid
        assert 0 <= repo_health.total <= 12
        assert 0 <= tech_debt.total <= 15
        assert product_level in ProductLevel
        assert complexity in Complexity

        # Generate costs and tasks
        forward = cost_estimator.estimate_forward(complexity, tech_debt)
        historical = cost_estimator.estimate_historical(sample_structure_data)
        tasks = task_generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=sample_semgrep_findings,
            structure_data=sample_structure_data,
            product_level=product_level,
            complexity=complexity,
        )

        # Verify all results are populated
        assert forward.hours_typical.total > 0
        assert forward.cost_eu.formatted
        assert forward.cost_ua.formatted
        assert historical.active_days > 0
        assert isinstance(tasks, list)

        # Verify serialization works
        repo_health_dict = repo_health.to_dict()
        tech_debt_dict = tech_debt.to_dict()
        forward_dict = forward.to_dict()
        historical_dict = historical.to_dict()

        assert "total" in repo_health_dict
        assert "total" in tech_debt_dict
        assert "hours" in forward_dict
        assert "cost" in forward_dict
        assert "hours" in historical_dict
