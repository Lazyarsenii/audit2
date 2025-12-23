"""
Tests for Product Level classification module.
"""
import pytest

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import (
    classify_product_level,
    ProductLevel,
    get_product_level_description,
)


class TestProductLevelClassification:
    """Test cases for Product Level classification."""

    def test_rnd_spike_low_scores(self):
        """Very low scores should classify as R&D Spike."""
        repo_health = RepoHealthScore(
            documentation=0,
            structure=1,
            runability=0,
            commit_history=0,
        )
        tech_debt = TechDebtScore(
            architecture=0,
            code_quality=1,
            testing=0,
            infrastructure=0,
            security_deps=1,
        )
        structure_data = {}

        result = classify_product_level(repo_health, tech_debt, structure_data)

        assert result == ProductLevel.RND_SPIKE

    def test_prototype_moderate_scores(self):
        """Moderate scores should classify as Prototype."""
        repo_health = RepoHealthScore(
            documentation=1,
            structure=1,
            runability=1,
            commit_history=2,
        )
        tech_debt = TechDebtScore(
            architecture=1,
            code_quality=1,
            testing=1,
            infrastructure=1,
            security_deps=2,
        )
        structure_data = {}

        result = classify_product_level(repo_health, tech_debt, structure_data)

        assert result == ProductLevel.PROTOTYPE

    def test_internal_tool_decent_scores(self):
        """Decent scores with infrastructure should be Internal Tool."""
        repo_health = RepoHealthScore(
            documentation=2,
            structure=2,
            runability=2,
            commit_history=2,
        )
        tech_debt = TechDebtScore(
            architecture=2,
            code_quality=2,
            testing=1,
            infrastructure=2,
            security_deps=2,
        )
        structure_data = {}

        result = classify_product_level(repo_health, tech_debt, structure_data)

        assert result == ProductLevel.INTERNAL_TOOL

    def test_platform_module_good_architecture(self):
        """Good architecture and structure should be Platform Module."""
        repo_health = RepoHealthScore(
            documentation=2,
            structure=3,
            runability=2,
            commit_history=2,
        )
        tech_debt = TechDebtScore(
            architecture=3,
            code_quality=2,
            testing=2,
            infrastructure=2,
            security_deps=2,
        )
        structure_data = {}

        result = classify_product_level(repo_health, tech_debt, structure_data)

        assert result == ProductLevel.PLATFORM_MODULE

    def test_near_product_high_scores_with_polish(self):
        """High scores with version/docs signals should be Near-Product."""
        repo_health = RepoHealthScore(
            documentation=3,
            structure=3,
            runability=3,
            commit_history=3,
        )
        tech_debt = TechDebtScore(
            architecture=3,
            code_quality=3,
            testing=2,
            infrastructure=3,
            security_deps=3,
        )
        structure_data = {
            "has_version_file": True,
            "has_api_docs": True,
        }

        result = classify_product_level(repo_health, tech_debt, structure_data)

        assert result == ProductLevel.NEAR_PRODUCT

    def test_product_level_descriptions(self):
        """Test that all product levels have descriptions."""
        for level in ProductLevel:
            desc = get_product_level_description(level)
            assert desc is not None
            assert len(desc) > 10
