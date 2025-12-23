"""
Scoring Engine — converts raw metrics into scores.

This is the core logic layer that:
1. Takes standardized MetricSet from collectors
2. Applies scoring formulas
3. Calculates Repo Health, Tech Debt, Product Level, Complexity
4. Adds scored metrics back to MetricSet

Datadog analogy: This is like Datadog's metric processing pipeline
where raw metrics are transformed into actionable insights.
"""
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

from .schema import (
    MetricSet,
    MetricSource,
    MetricCategory,
    MetricNames,
)
from ..core.scoring.repo_health import RepoHealthScore
from ..core.scoring.tech_debt import TechDebtScore
from ..core.scoring.product_level import ProductLevel, classify_product_level
from ..core.scoring.complexity import Complexity, calculate_complexity
from ..services.cost_estimator import cost_estimator, ForwardEstimate, HistoricalEstimate
from ..services.cocomo_estimator import cocomo_estimator, CocomoEstimate
from ..services.task_generator import task_generator, GeneratedTask

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Complete scoring result."""
    repo_health: RepoHealthScore
    tech_debt: TechDebtScore
    product_level: ProductLevel
    complexity: Complexity
    forward_estimate: ForwardEstimate
    historical_estimate: HistoricalEstimate
    cocomo_estimate: CocomoEstimate  # COCOMO II based estimate (primary)
    tasks: list
    verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_health": self.repo_health.to_dict(),
            "tech_debt": self.tech_debt.to_dict(),
            "product_level": self.product_level.value,
            "complexity": self.complexity.value,
            # Primary estimate - COCOMO II (industry standard, ±20%)
            "cost_estimate": self.cocomo_estimate.to_dict(),
            # Legacy estimates (kept for backwards compatibility)
            "forward_estimate": self.forward_estimate.to_dict(),
            "historical_estimate": self.historical_estimate.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "verdict": self.verdict,
        }


class ScoringEngine:
    """
    Scoring engine that converts metrics to scores.

    Pipeline:
        MetricSet -> calculate_scores() -> ScoringResult
                                        -> adds scored metrics to MetricSet
    """

    def __init__(self):
        pass

    def calculate_scores(self, metrics: MetricSet, region_mode: str = "EU_UA") -> ScoringResult:
        """
        Calculate all scores from collected metrics.

        Args:
            metrics: MetricSet from collectors
            region_mode: Cost estimation region

        Returns:
            ScoringResult with all calculated scores
        """
        logger.info(f"[ScoringEngine] Calculating scores for {metrics.analysis_id}")

        # Convert metrics to structure_data format for existing scoring functions
        structure_data = self._metrics_to_structure_data(metrics)
        static_metrics = self._metrics_to_static_metrics(metrics)

        # Calculate Repo Health
        repo_health = self._calculate_repo_health(metrics)
        logger.info(f"  Repo Health: {repo_health.total}/12")

        # Calculate Tech Debt
        tech_debt = self._calculate_tech_debt(metrics, static_metrics)
        logger.info(f"  Tech Debt: {tech_debt.total}/15")

        # Classify Product Level
        product_level = classify_product_level(repo_health, tech_debt, structure_data)
        logger.info(f"  Product Level: {product_level.value}")

        # Calculate Complexity
        complexity = calculate_complexity(static_metrics, repo_health, tech_debt)
        logger.info(f"  Complexity: {complexity.value}")

        # Cost Estimation
        forward_estimate = cost_estimator.estimate_forward(complexity, tech_debt, region_mode)
        historical_estimate = cost_estimator.estimate_historical(structure_data)

        # COCOMO II Estimate (primary, industry-standard)
        cocomo_estimate = cocomo_estimator.estimate_from_metrics(
            static_metrics=static_metrics,
            tech_debt_total=tech_debt.total,
            repo_health_total=repo_health.total,
        )
        logger.info(
            f"  COCOMO II: {cocomo_estimate.hours_typical:.0f} hrs "
            f"(±20%: {cocomo_estimate.hours_min:.0f}-{cocomo_estimate.hours_max:.0f})"
        )

        # Generate Tasks
        tasks = task_generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],  # TODO: integrate semgrep collector
            structure_data=structure_data,
            product_level=product_level,
            complexity=complexity,
        )

        # Determine verdict
        verdict = self._determine_verdict(product_level, repo_health, tech_debt)

        # Add scored metrics back to MetricSet
        self._add_scored_metrics(metrics, repo_health, tech_debt, product_level, complexity)

        return ScoringResult(
            repo_health=repo_health,
            tech_debt=tech_debt,
            product_level=product_level,
            complexity=complexity,
            forward_estimate=forward_estimate,
            historical_estimate=historical_estimate,
            cocomo_estimate=cocomo_estimate,
            tasks=tasks,
            verdict=verdict,
        )

    def _metrics_to_structure_data(self, metrics: MetricSet) -> Dict[str, Any]:
        """Convert MetricSet to structure_data format for legacy scoring functions."""
        return {
            "has_readme": metrics.get_value(MetricNames.HAS_README, False),
            "readme_has_usage": metrics.get_value(MetricNames.README_HAS_USAGE, False),
            "readme_has_install": metrics.get_value(MetricNames.README_HAS_INSTALL, False),
            "has_docs_folder": metrics.get_value(MetricNames.HAS_DOCS_FOLDER, False),
            "has_architecture_docs": metrics.get_value(MetricNames.HAS_ARCHITECTURE_DOCS, False),
            "has_api_docs": metrics.get_value(MetricNames.HAS_API_DOCS, False),
            "has_changelog": metrics.get_value(MetricNames.HAS_CHANGELOG, False),
            "directory_structure": self._extract_directory_patterns(metrics),
            "dependency_files": ["requirements.txt"] if metrics.get_value(MetricNames.HAS_DEPS_FILE, False) else [],
            "has_dockerfile": metrics.get_value(MetricNames.HAS_DOCKERFILE, False),
            "has_docker_compose": metrics.get_value(MetricNames.HAS_DOCKER_COMPOSE, False),
            "has_run_instructions": metrics.get_value(MetricNames.HAS_RUN_INSTRUCTIONS, False),
            "commits_total": metrics.get_value(MetricNames.COMMITS_TOTAL, 0),
            "authors_count": metrics.get_value(MetricNames.AUTHORS_COUNT, 1),
            "recent_commits": metrics.get_value(MetricNames.COMMITS_RECENT, 0),
            "has_version_file": False,  # TODO: add version file detection
        }

    def _metrics_to_static_metrics(self, metrics: MetricSet) -> Dict[str, Any]:
        """Convert MetricSet to static_metrics format for legacy scoring functions."""
        return {
            "total_loc": metrics.get_value(MetricNames.LOC_TOTAL, 0),
            "files_count": metrics.get_value(MetricNames.FILES_TOTAL, 0),
            "test_files_count": metrics.get_value(MetricNames.TEST_FILES_COUNT, 0),
            "max_file_lines": 500,  # Default estimate
            "max_function_lines": 50,
            "has_clear_layers": metrics.get_value(MetricNames.HAS_SRC_DIR, False),
            "duplication_percent": 5,  # Default estimate
            "cyclomatic_complexity_avg": 10,
            "has_ci": metrics.get_value(MetricNames.HAS_CI, False),
            "ci_has_tests": metrics.get_value(MetricNames.CI_HAS_TESTS, False),
            "has_dockerfile": metrics.get_value(MetricNames.HAS_DOCKERFILE, False),
            "has_deploy_config": metrics.get_value(MetricNames.CI_HAS_DEPLOY, False),
            "test_coverage": self._estimate_coverage(metrics),
            "external_deps_count": 20,  # Default estimate
        }

    def _extract_directory_patterns(self, metrics: MetricSet) -> list:
        """Extract directory patterns from metrics."""
        patterns = []
        if metrics.get_value(MetricNames.HAS_SRC_DIR, False):
            patterns.append("src")
        if metrics.get_value(MetricNames.HAS_TESTS_DIR, False):
            patterns.append("tests")
        if metrics.get_value(MetricNames.HAS_DOCS_DIR, False):
            patterns.append("docs")
        if metrics.get_value(MetricNames.HAS_CONFIG_DIR, False):
            patterns.append("config")
        return patterns

    def _estimate_coverage(self, metrics: MetricSet) -> Optional[float]:
        """Get real coverage or estimate from metrics."""
        # First, try to get real coverage from CoverageCollector
        real_coverage = metrics.get_value(MetricNames.TEST_COVERAGE, None)
        if real_coverage is not None and real_coverage > 0:
            logger.debug(f"Using real coverage: {real_coverage}%")
            return real_coverage

        # Fall back to estimate based on test file ratio
        test_files = metrics.get_value(MetricNames.TEST_FILES_COUNT, 0)
        total_files = metrics.get_value(MetricNames.FILES_TOTAL, 1)

        if test_files == 0:
            return 0

        # Rough estimate based on test file ratio
        ratio = test_files / max(total_files, 1)
        if ratio > 0.2:
            return 60
        elif ratio > 0.1:
            return 40
        elif ratio > 0.05:
            return 20
        return 10

    def _calculate_repo_health(self, metrics: MetricSet) -> RepoHealthScore:
        """Calculate Repo Health scores from metrics."""

        # Documentation score (0-3)
        doc_score = 0
        if metrics.get_value(MetricNames.HAS_README, False):
            doc_score = 1
            if metrics.get_value(MetricNames.README_HAS_USAGE, False) and \
               metrics.get_value(MetricNames.README_HAS_INSTALL, False):
                doc_score = 2
            if metrics.get_value(MetricNames.HAS_DOCS_FOLDER, False) and \
               metrics.get_value(MetricNames.HAS_ARCHITECTURE_DOCS, False):
                doc_score = 3

        # Structure score (0-3)
        struct_score = metrics.get_value(MetricNames.STRUCTURE_SCORE, 0)
        struct_score = min(3, struct_score)

        # Runability score (0-3)
        run_score = 0
        if metrics.get_value(MetricNames.HAS_DEPS_FILE, False):
            run_score = 1
            if metrics.get_value(MetricNames.HAS_RUN_INSTRUCTIONS, False):
                run_score = 2
            if metrics.get_value(MetricNames.HAS_DOCKERFILE, False) and \
               metrics.get_value(MetricNames.HAS_DOCKER_COMPOSE, False):
                run_score = 3

        # History score (0-3)
        commits = metrics.get_value(MetricNames.COMMITS_TOTAL, 0)
        authors = metrics.get_value(MetricNames.AUTHORS_COUNT, 1)
        recent = metrics.get_value(MetricNames.COMMITS_RECENT, 0)

        if commits <= 5:
            history_score = 0
        elif commits <= 30:
            history_score = 1
        elif commits <= 200:
            history_score = 2 if not (authors >= 3 and recent >= 10) else 3
        else:
            history_score = 3

        return RepoHealthScore(
            documentation=doc_score,
            structure=struct_score,
            runability=run_score,
            commit_history=history_score,
        )

    def _calculate_tech_debt(self, metrics: MetricSet, static_metrics: Dict) -> TechDebtScore:
        """Calculate Tech Debt scores from metrics."""

        # Architecture score (0-3)
        arch_score = 2  # Default
        if metrics.get_value(MetricNames.HAS_SRC_DIR, False):
            arch_score = 3
        if static_metrics.get("max_file_lines", 0) > 1000:
            arch_score = max(0, arch_score - 2)

        # Code quality score (0-3)
        quality_score = 2  # Default
        duplication = static_metrics.get("duplication_percent", 5)
        if duplication > 15:
            quality_score = 0
        elif duplication > 10:
            quality_score = 1
        elif duplication < 5:
            quality_score = 3

        # Testing score (0-3)
        test_files = metrics.get_value(MetricNames.TEST_FILES_COUNT, 0)
        total_files = metrics.get_value(MetricNames.FILES_TOTAL, 1)
        coverage = self._estimate_coverage(metrics)

        if test_files == 0:
            test_score = 0
        elif coverage and coverage >= 60:
            test_score = 3
        elif coverage and coverage >= 20:
            test_score = 2
        else:
            test_score = 1

        # Infrastructure score (0-3)
        has_ci = metrics.get_value(MetricNames.HAS_CI, False)
        ci_has_tests = metrics.get_value(MetricNames.CI_HAS_TESTS, False)
        has_docker = metrics.get_value(MetricNames.HAS_DOCKERFILE, False)
        ci_has_deploy = metrics.get_value(MetricNames.CI_HAS_DEPLOY, False)

        if not has_ci and not has_docker:
            infra_score = 0
        elif has_docker and not has_ci:
            infra_score = 1
        elif has_ci and ci_has_tests:
            infra_score = 3 if ci_has_deploy else 2
        else:
            infra_score = 1

        # Security score (0-3) - based on actual security scan results
        security_score = self._calculate_security_score(metrics)

        return TechDebtScore(
            architecture=arch_score,
            code_quality=quality_score,
            testing=test_score,
            infrastructure=infra_score,
            security_deps=security_score,
        )

    def _calculate_security_score(self, metrics: MetricSet) -> int:
        """
        Calculate security score based on actual scan results.

        Score (0-3):
        - 3: No vulnerabilities or issues found
        - 2: Only low severity issues
        - 1: Medium severity issues or some vulnerabilities
        - 0: High/Critical issues or many vulnerabilities
        """
        # Get security metrics
        critical = metrics.get_value(MetricNames.SEMGREP_CRITICAL, 0)
        high = metrics.get_value(MetricNames.SEMGREP_HIGH, 0)
        medium = metrics.get_value(MetricNames.SEMGREP_MEDIUM, 0)
        low = metrics.get_value(MetricNames.SEMGREP_LOW, 0)
        vulnerabilities = metrics.get_value(MetricNames.DEPS_VULNERABILITIES, 0)
        has_secrets = metrics.get_value(MetricNames.HAS_SECRETS_IN_CODE, False)

        # Calculate score
        if critical > 0 or has_secrets:
            return 0
        elif high > 0 or vulnerabilities > 5:
            return 1
        elif medium > 2 or vulnerabilities > 0:
            return 2
        else:
            return 3

    def _determine_verdict(
        self,
        product_level: ProductLevel,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
    ) -> str:
        """Determine the final verdict."""
        if product_level == ProductLevel.NEAR_PRODUCT:
            return "Near-Product"
        elif product_level == ProductLevel.PLATFORM_MODULE:
            return "Platform Module Candidate"
        elif product_level == ProductLevel.INTERNAL_TOOL:
            return "Internal Tool"
        elif product_level == ProductLevel.PROTOTYPE:
            if repo_health.total >= 6 or tech_debt.total >= 6:
                return "R&D Prototype"
            return "Archive / Reference Only"
        else:
            return "Archive / Reference Only"

    def _add_scored_metrics(
        self,
        metrics: MetricSet,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        product_level: ProductLevel,
        complexity: Complexity,
    ) -> None:
        """Add calculated scores as metrics."""
        source = MetricSource.MANUAL  # Scored metrics

        # Repo Health scores
        metrics.add_gauge(MetricNames.SCORE_DOCUMENTATION, repo_health.documentation, source, MetricCategory.DOCUMENTATION)
        metrics.add_gauge(MetricNames.SCORE_STRUCTURE, repo_health.structure, source, MetricCategory.STRUCTURE)
        metrics.add_gauge(MetricNames.SCORE_RUNABILITY, repo_health.runability, source, MetricCategory.RUNABILITY)
        metrics.add_gauge(MetricNames.SCORE_HISTORY, repo_health.commit_history, source, MetricCategory.HISTORY)
        metrics.add_gauge(MetricNames.SCORE_REPO_HEALTH_TOTAL, repo_health.total, source, MetricCategory.DOCUMENTATION)

        # Tech Debt scores
        metrics.add_gauge(MetricNames.SCORE_ARCHITECTURE, tech_debt.architecture, source, MetricCategory.ARCHITECTURE)
        metrics.add_gauge(MetricNames.SCORE_CODE_QUALITY, tech_debt.code_quality, source, MetricCategory.CODE_QUALITY)
        metrics.add_gauge(MetricNames.SCORE_TESTING, tech_debt.testing, source, MetricCategory.TESTING)
        metrics.add_gauge(MetricNames.SCORE_INFRASTRUCTURE, tech_debt.infrastructure, source, MetricCategory.INFRASTRUCTURE)
        metrics.add_gauge(MetricNames.SCORE_SECURITY, tech_debt.security_deps, source, MetricCategory.SECURITY)
        metrics.add_gauge(MetricNames.SCORE_TECH_DEBT_TOTAL, tech_debt.total, source, MetricCategory.ARCHITECTURE)


# Singleton instance
scoring_engine = ScoringEngine()
