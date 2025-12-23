"""
Tests for Tech Debt scoring module.
"""
import pytest

from app.core.scoring.tech_debt import (
    calculate_tech_debt,
    TechDebtScore,
)


class TestTechDebtScoring:
    """Test cases for Tech Debt calculation."""

    def test_empty_metrics_default_scores(self):
        """Empty metrics should result in default scores."""
        static_metrics = {}
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        # With no data, scores should be relatively good (no evidence of problems)
        assert isinstance(result, TechDebtScore)
        assert 0 <= result.total <= 15

    def test_high_complexity_low_architecture_score(self):
        """Very large files should result in low architecture score."""
        static_metrics = {
            "max_file_lines": 1500,
            "max_function_lines": 200,
            "has_clear_layers": False,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.architecture == 0

    def test_good_architecture_high_score(self):
        """Well-structured code should score high on architecture."""
        static_metrics = {
            "max_file_lines": 200,
            "max_function_lines": 30,
            "has_clear_layers": True,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.architecture == 3

    def test_code_quality_with_high_duplication(self):
        """High duplication should result in low code quality score."""
        static_metrics = {
            "duplication_percent": 25,
            "cyclomatic_complexity_avg": 5,
            "code_smells_per_kloc": 5,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.code_quality == 0

    def test_testing_with_no_tests(self):
        """No tests should score 0."""
        static_metrics = {
            "test_files_count": 0,
            "files_count": 50,
            "test_coverage": None,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.testing == 0

    def test_testing_with_coverage(self):
        """Good test coverage should score high."""
        static_metrics = {
            "test_files_count": 20,
            "files_count": 50,
            "test_coverage": 75,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.testing == 3

    def test_infrastructure_no_ci(self):
        """No CI should score low on infrastructure."""
        static_metrics = {
            "has_ci": False,
            "has_dockerfile": False,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.infrastructure == 0

    def test_infrastructure_full_cicd(self):
        """Full CI/CD should score high."""
        static_metrics = {
            "has_ci": True,
            "ci_has_tests": True,
            "has_dockerfile": True,
            "has_deploy_config": True,
        }
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.infrastructure == 3

    def test_security_with_critical_findings(self):
        """Critical security findings should result in low security score."""
        static_metrics = {}
        semgrep_findings = [
            {"severity": "ERROR", "category": "security"},
            {"severity": "ERROR", "category": "security"},
            {"severity": "ERROR", "category": "security"},
            {"severity": "ERROR", "category": "security"},
            {"severity": "ERROR", "category": "security"},
            {"severity": "ERROR", "category": "security"},
        ]

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.security_deps == 0

    def test_security_no_findings(self):
        """No security findings should score high."""
        static_metrics = {}
        semgrep_findings = []

        result = calculate_tech_debt(static_metrics, semgrep_findings)

        assert result.security_deps == 3

    def test_tech_debt_score_total(self):
        """Test that total is calculated correctly."""
        score = TechDebtScore(
            architecture=2,
            code_quality=3,
            testing=1,
            infrastructure=2,
            security_deps=3,
        )

        assert score.total == 11
        assert score.to_dict()["total"] == 11
        assert score.to_dict()["max_possible"] == 15
