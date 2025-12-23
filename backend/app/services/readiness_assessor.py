"""
Project Readiness Assessment Service.

Evaluates project readiness for formal evaluation and generates
actionable recommendations for improvements before acceptance.

Used at project START to establish baseline and expectations.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel
from app.core.scoring.complexity import Complexity

logger = logging.getLogger(__name__)


class ReadinessLevel(str, Enum):
    """Project readiness levels."""
    NOT_READY = "not_ready"           # < 40% - needs significant work
    NEEDS_WORK = "needs_work"         # 40-60% - some issues to address
    ALMOST_READY = "almost_ready"     # 60-80% - minor improvements needed
    READY = "ready"                   # 80-95% - ready for evaluation
    EXEMPLARY = "exemplary"           # 95%+ - exceeds expectations


class RecommendationPriority(str, Enum):
    """Recommendation priority levels."""
    BLOCKER = "blocker"       # Must fix before evaluation
    CRITICAL = "critical"     # Should fix, affects score significantly
    IMPORTANT = "important"   # Recommended, affects score
    OPTIONAL = "optional"     # Nice to have


@dataclass
class Recommendation:
    """Single improvement recommendation."""
    title: str
    description: str
    priority: RecommendationPriority
    category: str
    effort_hours: int
    impact_score: float  # 0-1, how much it improves readiness
    checklist: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "category": self.category,
            "effort_hours": self.effort_hours,
            "impact_score": round(self.impact_score, 2),
            "checklist": self.checklist,
        }


@dataclass
class ReadinessCheckResult:
    """Result of a single readiness check."""
    check_id: str
    name: str
    category: str
    passed: bool
    score: float  # 0-1
    weight: float  # importance weight
    details: str
    recommendation: Optional[Recommendation] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "category": self.category,
            "passed": self.passed,
            "score": round(self.score, 2),
            "weight": self.weight,
            "details": self.details,
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
        }


@dataclass
class ReadinessAssessment:
    """Complete readiness assessment result."""
    analysis_id: str
    repo_url: str

    # Overall
    readiness_level: ReadinessLevel
    readiness_score: float  # 0-100

    # By category
    category_scores: Dict[str, float]

    # Checks
    checks: List[ReadinessCheckResult]
    passed_checks: int
    failed_checks: int

    # Recommendations
    recommendations: List[Recommendation]
    blockers_count: int

    # Estimates
    estimated_fix_hours: int
    estimated_days_to_ready: int

    # Summary
    summary: str
    next_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "repo_url": self.repo_url,
            "readiness_level": self.readiness_level.value,
            "readiness_score": round(self.readiness_score, 1),
            "category_scores": {k: round(v, 1) for k, v in self.category_scores.items()},
            "checks": [c.to_dict() for c in self.checks],
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "blockers_count": self.blockers_count,
            "estimated_fix_hours": self.estimated_fix_hours,
            "estimated_days_to_ready": self.estimated_days_to_ready,
            "summary": self.summary,
            "next_steps": self.next_steps,
        }


class ReadinessAssessor:
    """
    Assesses project readiness for formal evaluation.

    Used workflow:
    1. Project submitted for evaluation
    2. Run readiness assessment
    3. Generate recommendations
    4. Team addresses blockers/critical issues
    5. Re-assess when ready
    6. Proceed to formal evaluation
    """

    # Readiness checks with weights
    CHECKS = [
        # Documentation (weight: 25%)
        {"id": "doc_readme", "name": "README exists and is comprehensive", "category": "documentation", "weight": 0.08},
        {"id": "doc_install", "name": "Installation instructions", "category": "documentation", "weight": 0.05},
        {"id": "doc_usage", "name": "Usage examples", "category": "documentation", "weight": 0.05},
        {"id": "doc_api", "name": "API documentation", "category": "documentation", "weight": 0.04},
        {"id": "doc_arch", "name": "Architecture documentation", "category": "documentation", "weight": 0.03},

        # Runability (weight: 25%)
        {"id": "run_deps", "name": "Dependencies declared", "category": "runability", "weight": 0.08},
        {"id": "run_docker", "name": "Docker configuration", "category": "runability", "weight": 0.07},
        {"id": "run_scripts", "name": "Build/run scripts", "category": "runability", "weight": 0.05},
        {"id": "run_env", "name": "Environment configuration", "category": "runability", "weight": 0.05},

        # Code Quality (weight: 20%)
        {"id": "qual_structure", "name": "Clear project structure", "category": "code_quality", "weight": 0.06},
        {"id": "qual_tests", "name": "Tests present", "category": "code_quality", "weight": 0.07},
        {"id": "qual_lint", "name": "Code style/linting", "category": "code_quality", "weight": 0.04},
        {"id": "qual_security", "name": "No critical security issues", "category": "code_quality", "weight": 0.03},

        # Infrastructure (weight: 15%)
        {"id": "infra_ci", "name": "CI/CD pipeline", "category": "infrastructure", "weight": 0.06},
        {"id": "infra_deploy", "name": "Deployment configuration", "category": "infrastructure", "weight": 0.05},
        {"id": "infra_monitoring", "name": "Logging/monitoring setup", "category": "infrastructure", "weight": 0.04},

        # History (weight: 15%)
        {"id": "hist_commits", "name": "Meaningful commit history", "category": "history", "weight": 0.05},
        {"id": "hist_versioning", "name": "Version management", "category": "history", "weight": 0.05},
        {"id": "hist_changelog", "name": "Changelog maintained", "category": "history", "weight": 0.05},
    ]

    def assess(
        self,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        product_level: ProductLevel,
        complexity: Complexity,
        structure_data: Dict[str, Any],
        static_metrics: Dict[str, Any],
    ) -> ReadinessAssessment:
        """
        Run full readiness assessment.

        Args:
            repo_health: Repo health scores
            tech_debt: Tech debt scores
            product_level: Product level classification
            complexity: Complexity classification
            structure_data: Raw structure data
            static_metrics: Raw static metrics

        Returns:
            ReadinessAssessment with checks, recommendations, and next steps
        """
        logger.info("Running readiness assessment...")

        # Run all checks
        checks = self._run_checks(repo_health, tech_debt, structure_data, static_metrics)

        # Calculate scores
        total_score = sum(c.score * c.weight for c in checks) * 100
        category_scores = self._calculate_category_scores(checks)

        # Determine level
        readiness_level = self._determine_level(total_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(checks, product_level, complexity)

        # Sort by priority
        priority_order = {
            RecommendationPriority.BLOCKER: 0,
            RecommendationPriority.CRITICAL: 1,
            RecommendationPriority.IMPORTANT: 2,
            RecommendationPriority.OPTIONAL: 3,
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        # Count stats
        passed = sum(1 for c in checks if c.passed)
        failed = len(checks) - passed
        blockers = sum(1 for r in recommendations if r.priority == RecommendationPriority.BLOCKER)

        # Estimate fix time
        fix_hours = sum(r.effort_hours for r in recommendations if r.priority in [
            RecommendationPriority.BLOCKER, RecommendationPriority.CRITICAL
        ])
        days_to_ready = max(1, fix_hours // 8)

        # Generate summary and next steps
        summary = self._generate_summary(readiness_level, total_score, blockers, product_level)
        next_steps = self._generate_next_steps(readiness_level, recommendations, blockers)

        return ReadinessAssessment(
            analysis_id=structure_data.get("analysis_id", ""),
            repo_url=structure_data.get("repo_url", ""),
            readiness_level=readiness_level,
            readiness_score=total_score,
            category_scores=category_scores,
            checks=checks,
            passed_checks=passed,
            failed_checks=failed,
            recommendations=recommendations,
            blockers_count=blockers,
            estimated_fix_hours=fix_hours,
            estimated_days_to_ready=days_to_ready,
            summary=summary,
            next_steps=next_steps,
        )

    def _run_checks(
        self,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        structure_data: Dict[str, Any],
        static_metrics: Dict[str, Any],
    ) -> List[ReadinessCheckResult]:
        """Run all readiness checks."""
        results = []

        for check in self.CHECKS:
            result = self._run_single_check(
                check, repo_health, tech_debt, structure_data, static_metrics
            )
            results.append(result)

        return results

    def _run_single_check(
        self,
        check: Dict[str, Any],
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        structure_data: Dict[str, Any],
        static_metrics: Dict[str, Any],
    ) -> ReadinessCheckResult:
        """Run a single readiness check."""
        check_id = check["id"]

        # Check logic based on ID
        if check_id == "doc_readme":
            has_readme = structure_data.get("has_readme", False)
            readme_size = structure_data.get("readme_size", 0)
            score = 1.0 if has_readme and readme_size > 500 else (0.5 if has_readme else 0)
            details = f"README: {'Yes' if has_readme else 'No'}, Size: {readme_size} bytes"

        elif check_id == "doc_install":
            score = 1.0 if structure_data.get("readme_has_install", False) else 0
            details = "Installation instructions " + ("found" if score else "missing")

        elif check_id == "doc_usage":
            score = 1.0 if structure_data.get("readme_has_usage", False) else 0
            details = "Usage examples " + ("found" if score else "missing")

        elif check_id == "doc_api":
            score = 1.0 if structure_data.get("has_api_docs", False) else 0
            details = "API documentation " + ("present" if score else "missing")

        elif check_id == "doc_arch":
            score = 1.0 if structure_data.get("has_architecture_docs", False) else 0
            details = "Architecture docs " + ("present" if score else "missing")

        elif check_id == "run_deps":
            score = 1.0 if structure_data.get("dependency_files") else 0
            details = "Dependencies " + ("declared" if score else "not found")

        elif check_id == "run_docker":
            has_docker = structure_data.get("has_dockerfile", False)
            has_compose = structure_data.get("has_docker_compose", False)
            score = 1.0 if has_docker and has_compose else (0.5 if has_docker or has_compose else 0)
            details = f"Dockerfile: {'Yes' if has_docker else 'No'}, Compose: {'Yes' if has_compose else 'No'}"

        elif check_id == "run_scripts":
            has_makefile = structure_data.get("has_makefile", False)
            has_run = structure_data.get("has_run_instructions", False)
            score = 1.0 if has_makefile or has_run else 0
            details = f"Makefile: {'Yes' if has_makefile else 'No'}, Run scripts: {'Yes' if has_run else 'No'}"

        elif check_id == "run_env":
            has_env = structure_data.get("has_env_example", False) or structure_data.get("has_config_dir", False)
            score = 1.0 if has_env else 0
            details = "Environment config " + ("found" if score else "missing")

        elif check_id == "qual_structure":
            score = repo_health.structure / 3.0
            details = f"Structure score: {repo_health.structure}/3"

        elif check_id == "qual_tests":
            test_count = static_metrics.get("test_files_count", 0)
            score = 1.0 if test_count > 5 else (0.5 if test_count > 0 else 0)
            details = f"Test files: {test_count}"

        elif check_id == "qual_lint":
            has_lint_config = structure_data.get("has_lint_config", False)
            score = 1.0 if has_lint_config else 0.5  # Default to partial if unknown
            details = "Linting " + ("configured" if has_lint_config else "not configured")

        elif check_id == "qual_security":
            sec_score = tech_debt.security_deps
            score = sec_score / 3.0
            details = f"Security score: {sec_score}/3"

        elif check_id == "infra_ci":
            has_ci = static_metrics.get("has_ci", False)
            score = 1.0 if has_ci else 0
            details = "CI/CD " + ("configured" if has_ci else "not found")

        elif check_id == "infra_deploy":
            has_deploy = static_metrics.get("has_deploy_config", False)
            score = 1.0 if has_deploy else 0
            details = "Deployment config " + ("found" if has_deploy else "missing")

        elif check_id == "infra_monitoring":
            score = 0.5  # Default partial - hard to detect
            details = "Monitoring setup needs manual verification"

        elif check_id == "hist_commits":
            commits = structure_data.get("commits_total", 0)
            score = 1.0 if commits > 50 else (0.5 if commits > 10 else 0)
            details = f"Commits: {commits}"

        elif check_id == "hist_versioning":
            has_version = structure_data.get("has_version_file", False)
            score = 1.0 if has_version else 0.5
            details = "Version file " + ("found" if has_version else "not found")

        elif check_id == "hist_changelog":
            has_changelog = structure_data.get("has_changelog", False)
            score = 1.0 if has_changelog else 0
            details = "Changelog " + ("present" if has_changelog else "missing")

        else:
            score = 0.5
            details = "Check not implemented"

        passed = score >= 0.7

        # Generate recommendation if not passed
        recommendation = None
        if not passed:
            recommendation = self._generate_check_recommendation(check_id, check, score)

        return ReadinessCheckResult(
            check_id=check_id,
            name=check["name"],
            category=check["category"],
            passed=passed,
            score=score,
            weight=check["weight"],
            details=details,
            recommendation=recommendation,
        )

    def _generate_check_recommendation(
        self,
        check_id: str,
        check: Dict[str, Any],
        score: float,
    ) -> Recommendation:
        """Generate recommendation for a failed check."""

        RECOMMENDATIONS = {
            "doc_readme": Recommendation(
                title="Create comprehensive README",
                description="Add a detailed README.md with project description, features, and screenshots",
                priority=RecommendationPriority.BLOCKER,
                category="documentation",
                effort_hours=4,
                impact_score=0.15,
                checklist=[
                    "Add project title and description",
                    "List key features",
                    "Add installation instructions",
                    "Include usage examples",
                    "Add contributing guidelines",
                ],
            ),
            "doc_install": Recommendation(
                title="Add installation instructions",
                description="Document step-by-step installation process",
                priority=RecommendationPriority.CRITICAL,
                category="documentation",
                effort_hours=2,
                impact_score=0.08,
                checklist=[
                    "List prerequisites",
                    "Add installation commands",
                    "Document environment setup",
                ],
            ),
            "doc_usage": Recommendation(
                title="Add usage examples",
                description="Provide code examples and common use cases",
                priority=RecommendationPriority.CRITICAL,
                category="documentation",
                effort_hours=3,
                impact_score=0.08,
                checklist=[
                    "Add basic usage example",
                    "Document common scenarios",
                    "Include configuration options",
                ],
            ),
            "doc_api": Recommendation(
                title="Create API documentation",
                description="Document all public APIs and endpoints",
                priority=RecommendationPriority.IMPORTANT,
                category="documentation",
                effort_hours=8,
                impact_score=0.06,
                checklist=[
                    "List all endpoints/functions",
                    "Document parameters and returns",
                    "Add request/response examples",
                ],
            ),
            "doc_arch": Recommendation(
                title="Add architecture documentation",
                description="Create high-level architecture diagrams and explanations",
                priority=RecommendationPriority.IMPORTANT,
                category="documentation",
                effort_hours=6,
                impact_score=0.05,
                checklist=[
                    "Create system diagram",
                    "Document component interactions",
                    "Explain data flow",
                ],
            ),
            "run_deps": Recommendation(
                title="Declare dependencies",
                description="Create requirements.txt, package.json, or equivalent",
                priority=RecommendationPriority.BLOCKER,
                category="runability",
                effort_hours=2,
                impact_score=0.12,
                checklist=[
                    "List all dependencies",
                    "Pin versions",
                    "Separate dev dependencies",
                ],
            ),
            "run_docker": Recommendation(
                title="Add Docker configuration",
                description="Create Dockerfile and docker-compose.yml for consistent environments",
                priority=RecommendationPriority.CRITICAL,
                category="runability",
                effort_hours=8,
                impact_score=0.10,
                checklist=[
                    "Create Dockerfile",
                    "Add docker-compose.yml",
                    "Configure environment variables",
                    "Test container build",
                ],
            ),
            "run_scripts": Recommendation(
                title="Add build/run scripts",
                description="Create Makefile or scripts for common operations",
                priority=RecommendationPriority.IMPORTANT,
                category="runability",
                effort_hours=4,
                impact_score=0.06,
                checklist=[
                    "Add build command",
                    "Add run command",
                    "Add test command",
                    "Add clean command",
                ],
            ),
            "run_env": Recommendation(
                title="Add environment configuration",
                description="Create .env.example and document environment variables",
                priority=RecommendationPriority.IMPORTANT,
                category="runability",
                effort_hours=2,
                impact_score=0.05,
                checklist=[
                    "Create .env.example",
                    "Document all variables",
                    "Add to .gitignore",
                ],
            ),
            "qual_structure": Recommendation(
                title="Improve project structure",
                description="Reorganize code into clear, logical directories",
                priority=RecommendationPriority.IMPORTANT,
                category="code_quality",
                effort_hours=8,
                impact_score=0.08,
                checklist=[
                    "Create src/ directory",
                    "Separate tests/",
                    "Add config/ for configuration",
                    "Create docs/ for documentation",
                ],
            ),
            "qual_tests": Recommendation(
                title="Add tests",
                description="Create unit and integration tests",
                priority=RecommendationPriority.CRITICAL,
                category="code_quality",
                effort_hours=16,
                impact_score=0.10,
                checklist=[
                    "Set up test framework",
                    "Add unit tests for core logic",
                    "Add integration tests",
                    "Configure test coverage",
                ],
            ),
            "qual_lint": Recommendation(
                title="Configure linting",
                description="Set up code style and linting tools",
                priority=RecommendationPriority.OPTIONAL,
                category="code_quality",
                effort_hours=2,
                impact_score=0.03,
                checklist=[
                    "Add linter config",
                    "Configure pre-commit hooks",
                    "Fix existing issues",
                ],
            ),
            "qual_security": Recommendation(
                title="Fix security issues",
                description="Address identified security vulnerabilities",
                priority=RecommendationPriority.BLOCKER,
                category="code_quality",
                effort_hours=8,
                impact_score=0.08,
                checklist=[
                    "Run security scanner",
                    "Update vulnerable dependencies",
                    "Fix code vulnerabilities",
                ],
            ),
            "infra_ci": Recommendation(
                title="Set up CI/CD pipeline",
                description="Configure automated testing and deployment",
                priority=RecommendationPriority.CRITICAL,
                category="infrastructure",
                effort_hours=8,
                impact_score=0.08,
                checklist=[
                    "Create CI config file",
                    "Add test stage",
                    "Add build stage",
                    "Configure notifications",
                ],
            ),
            "infra_deploy": Recommendation(
                title="Add deployment configuration",
                description="Create deployment scripts and documentation",
                priority=RecommendationPriority.IMPORTANT,
                category="infrastructure",
                effort_hours=6,
                impact_score=0.06,
                checklist=[
                    "Document deployment process",
                    "Create deployment scripts",
                    "Add environment configs",
                ],
            ),
            "infra_monitoring": Recommendation(
                title="Set up logging/monitoring",
                description="Configure application logging and monitoring",
                priority=RecommendationPriority.OPTIONAL,
                category="infrastructure",
                effort_hours=4,
                impact_score=0.04,
                checklist=[
                    "Add structured logging",
                    "Configure log levels",
                    "Set up health checks",
                ],
            ),
            "hist_commits": Recommendation(
                title="Improve commit history",
                description="Ensure meaningful, atomic commits",
                priority=RecommendationPriority.OPTIONAL,
                category="history",
                effort_hours=0,
                impact_score=0.02,
                checklist=[
                    "Use conventional commits",
                    "Make atomic changes",
                    "Write descriptive messages",
                ],
            ),
            "hist_versioning": Recommendation(
                title="Add version management",
                description="Implement semantic versioning",
                priority=RecommendationPriority.OPTIONAL,
                category="history",
                effort_hours=2,
                impact_score=0.03,
                checklist=[
                    "Create VERSION file",
                    "Use semantic versioning",
                    "Tag releases",
                ],
            ),
            "hist_changelog": Recommendation(
                title="Create CHANGELOG",
                description="Document changes between versions",
                priority=RecommendationPriority.OPTIONAL,
                category="history",
                effort_hours=2,
                impact_score=0.03,
                checklist=[
                    "Create CHANGELOG.md",
                    "Document past changes",
                    "Follow Keep a Changelog format",
                ],
            ),
        }

        return RECOMMENDATIONS.get(check_id, Recommendation(
            title=f"Address: {check['name']}",
            description="This check did not pass and needs attention",
            priority=RecommendationPriority.IMPORTANT,
            category=check["category"],
            effort_hours=4,
            impact_score=check["weight"],
            checklist=["Review and address the issue"],
        ))

    def _calculate_category_scores(self, checks: List[ReadinessCheckResult]) -> Dict[str, float]:
        """Calculate scores by category."""
        categories: Dict[str, List[float]] = {}

        for check in checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check.score * 100)

        return {cat: sum(scores) / len(scores) for cat, scores in categories.items()}

    def _determine_level(self, score: float) -> ReadinessLevel:
        """Determine readiness level from score."""
        if score >= 95:
            return ReadinessLevel.EXEMPLARY
        elif score >= 80:
            return ReadinessLevel.READY
        elif score >= 60:
            return ReadinessLevel.ALMOST_READY
        elif score >= 40:
            return ReadinessLevel.NEEDS_WORK
        else:
            return ReadinessLevel.NOT_READY

    def _generate_recommendations(
        self,
        checks: List[ReadinessCheckResult],
        product_level: ProductLevel,
        complexity: Complexity,
    ) -> List[Recommendation]:
        """Generate all recommendations from failed checks."""
        recommendations = []

        for check in checks:
            if check.recommendation:
                recommendations.append(check.recommendation)

        return recommendations

    def _generate_summary(
        self,
        level: ReadinessLevel,
        score: float,
        blockers: int,
        product_level: ProductLevel,
    ) -> str:
        """Generate human-readable summary."""
        summaries = {
            ReadinessLevel.NOT_READY: f"Project is NOT READY for evaluation (score: {score:.0f}%). "
                f"There are {blockers} blocking issues that must be resolved first. "
                f"Significant work is needed before formal assessment.",

            ReadinessLevel.NEEDS_WORK: f"Project NEEDS WORK before evaluation (score: {score:.0f}%). "
                f"Several important issues should be addressed. "
                f"Consider fixing critical items before proceeding.",

            ReadinessLevel.ALMOST_READY: f"Project is ALMOST READY (score: {score:.0f}%). "
                f"Minor improvements recommended but not blocking. "
                f"Can proceed to evaluation with noted caveats.",

            ReadinessLevel.READY: f"Project is READY for evaluation (score: {score:.0f}%). "
                f"All major criteria met. Ready for formal assessment as {product_level.value}.",

            ReadinessLevel.EXEMPLARY: f"Project is EXEMPLARY (score: {score:.0f}%). "
                f"Exceeds expectations. Ready for immediate evaluation as {product_level.value}.",
        }

        return summaries[level]

    def _generate_next_steps(
        self,
        level: ReadinessLevel,
        recommendations: List[Recommendation],
        blockers: int,
    ) -> List[str]:
        """Generate next steps based on assessment."""
        steps = []

        if blockers > 0:
            steps.append(f"1. Address {blockers} blocking issues before proceeding")

        critical = [r for r in recommendations if r.priority == RecommendationPriority.CRITICAL]
        if critical:
            steps.append(f"2. Fix {len(critical)} critical issues to improve score significantly")

        if level in [ReadinessLevel.READY, ReadinessLevel.EXEMPLARY]:
            steps.append("3. Schedule formal evaluation with assessment team")
            steps.append("4. Prepare acceptance documentation")
        elif level == ReadinessLevel.ALMOST_READY:
            steps.append("3. Consider addressing important recommendations")
            steps.append("4. Can proceed to evaluation with documented limitations")
        else:
            steps.append("3. Allocate resources for improvements")
            steps.append("4. Re-run assessment after fixes")

        return steps


# Singleton instance
readiness_assessor = ReadinessAssessor()
