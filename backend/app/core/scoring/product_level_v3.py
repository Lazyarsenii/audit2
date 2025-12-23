"""
Product Level Classification v3 — Extended Maturity Model.

Classifies repositories into detailed maturity stages:

Development Stages:
- R&D Spike          → Experiment, throwaway code
- Proof of Concept   → Technical feasibility demo
- Prototype          → Working concept, not production-ready
- MVP                → Minimum viable product, core features only

Product Stages:
- Alpha              → Feature complete, internal testing
- Beta               → External testing, stabilization
- Release Candidate  → Final testing before release
- Production Ready   → Ready for release

Maintenance Stages:
- Active Development → Actively maintained and improved
- Maintenance Mode   → Bug fixes only
- Legacy             → No active development
- Deprecated         → Scheduled for removal

Also classifies by type:
- Library/SDK
- CLI Tool
- Web Service/API
- Desktop App
- Mobile App
- Data Pipeline
- ML/AI Model
- Infrastructure
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from .repo_health import RepoHealthScore
from .tech_debt import TechDebtScore

logger = logging.getLogger(__name__)


class DevelopmentStage(str, Enum):
    """Development lifecycle stages."""
    RND_SPIKE = "R&D Spike"
    PROOF_OF_CONCEPT = "Proof of Concept"
    PROTOTYPE = "Prototype"
    MVP = "MVP"
    ALPHA = "Alpha"
    BETA = "Beta"
    RELEASE_CANDIDATE = "Release Candidate"
    PRODUCTION = "Production Ready"


class MaintenanceStatus(str, Enum):
    """Maintenance status."""
    ACTIVE = "Active Development"
    MAINTENANCE = "Maintenance Mode"
    LEGACY = "Legacy"
    DEPRECATED = "Deprecated"
    ARCHIVED = "Archived"


class ProjectType(str, Enum):
    """Project type classification."""
    LIBRARY = "Library/SDK"
    CLI = "CLI Tool"
    WEB_SERVICE = "Web Service/API"
    WEB_APP = "Web Application"
    DESKTOP_APP = "Desktop Application"
    MOBILE_APP = "Mobile Application"
    DATA_PIPELINE = "Data Pipeline"
    ML_MODEL = "ML/AI Model"
    INFRASTRUCTURE = "Infrastructure/DevOps"
    MONOREPO = "Monorepo"
    UNKNOWN = "Unknown"


class ReadinessLevel(str, Enum):
    """Business readiness level."""
    NOT_READY = "Not Ready"
    INTERNAL_ONLY = "Internal Use Only"
    PARTNER_READY = "Partner Ready"
    MARKET_READY = "Market Ready"
    ENTERPRISE_READY = "Enterprise Ready"


@dataclass
class ClassificationSignals:
    """Signals used for classification."""
    # Structure signals
    has_readme: bool = False
    has_docs: bool = False
    has_api_docs: bool = False
    has_architecture_docs: bool = False
    has_changelog: bool = False
    has_contributing: bool = False
    has_license: bool = False
    has_version: bool = False

    # Code signals
    has_tests: bool = False
    has_ci: bool = False
    has_cd: bool = False
    has_docker: bool = False
    has_kubernetes: bool = False
    has_monitoring: bool = False
    has_logging: bool = False

    # Quality signals
    test_coverage: float = 0.0
    code_quality_score: int = 0
    security_score: int = 0

    # Activity signals
    commits_total: int = 0
    commits_recent: int = 0  # Last 30 days
    authors_count: int = 0
    days_since_last_commit: int = 0

    # Size signals
    loc_total: int = 0
    files_total: int = 0

    # Type signals (detected patterns)
    has_setup_py: bool = False
    has_package_json: bool = False
    has_cargo_toml: bool = False
    has_go_mod: bool = False
    has_main_py: bool = False
    has_cli_commands: bool = False
    has_web_framework: bool = False
    has_api_endpoints: bool = False
    has_ml_libs: bool = False
    has_terraform: bool = False
    has_helm: bool = False


@dataclass
class ProductClassification:
    """Complete product classification result."""
    # Primary classification
    stage: DevelopmentStage
    stage_confidence: float  # 0.0-1.0

    # Secondary classifications
    maintenance_status: MaintenanceStatus
    project_type: ProjectType
    readiness_level: ReadinessLevel

    # Scores used
    repo_health_score: int
    tech_debt_score: int

    # Detailed breakdown
    signals: ClassificationSignals

    # Reasoning
    stage_reasons: List[str] = field(default_factory=list)
    next_stage_requirements: List[str] = field(default_factory=list)

    # Metadata
    version: str = "3.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "stage_confidence": round(self.stage_confidence, 2),
            "maintenance_status": self.maintenance_status.value,
            "project_type": self.project_type.value,
            "readiness_level": self.readiness_level.value,
            "scores": {
                "repo_health": self.repo_health_score,
                "tech_debt": self.tech_debt_score,
            },
            "stage_reasons": self.stage_reasons,
            "next_stage_requirements": self.next_stage_requirements,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        return f"""
Stage: {self.stage.value} ({self.stage_confidence*100:.0f}% confidence)
Type: {self.project_type.value}
Status: {self.maintenance_status.value}
Readiness: {self.readiness_level.value}

Why {self.stage.value}:
{chr(10).join(f'  • {r}' for r in self.stage_reasons[:5])}

To reach next stage:
{chr(10).join(f'  • {r}' for r in self.next_stage_requirements[:5])}
"""


class ProductClassifier:
    """
    Extended product classifier with detailed stage detection.

    Classification Matrix:

    ┌────────────────┬────────┬────────┬─────────────────────────────────┐
    │ Stage          │ Health │ Debt   │ Key Requirements                │
    ├────────────────┼────────┼────────┼─────────────────────────────────┤
    │ R&D Spike      │ 0-2    │ 0-3    │ Just code, no docs/tests        │
    │ PoC            │ 2-4    │ 3-5    │ Basic readme, works             │
    │ Prototype      │ 4-6    │ 5-7    │ Some docs, some tests           │
    │ MVP            │ 5-7    │ 6-9    │ Core features, deployable       │
    │ Alpha          │ 7-9    │ 8-11   │ Feature complete, CI            │
    │ Beta           │ 8-10   │ 10-13  │ Stable, external testing        │
    │ RC             │ 9-11   │ 12-14  │ Production tested               │
    │ Production     │ 10-12  │ 13-15  │ Full docs, monitoring, security │
    └────────────────┴────────┴────────┴─────────────────────────────────┘
    """

    def classify(
        self,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        structure_data: Dict[str, Any],
        static_metrics: Optional[Dict[str, Any]] = None,
    ) -> ProductClassification:
        """
        Classify repository into detailed product stage.

        Args:
            repo_health: Repo health scores (0-12)
            tech_debt: Tech debt scores (0-15)
            structure_data: Structure analysis data
            static_metrics: Optional static analysis metrics

        Returns:
            ProductClassification with all details
        """
        static_metrics = static_metrics or {}

        # Build signals
        signals = self._build_signals(structure_data, static_metrics)

        # Classify development stage
        stage, confidence, reasons = self._classify_stage(
            repo_health, tech_debt, signals
        )

        # Determine maintenance status
        maintenance = self._classify_maintenance(signals)

        # Detect project type
        project_type = self._detect_project_type(signals, structure_data)

        # Assess business readiness
        readiness = self._assess_readiness(
            stage, repo_health, tech_debt, signals
        )

        # Generate next stage requirements
        next_requirements = self._get_next_stage_requirements(
            stage, repo_health, tech_debt, signals
        )

        return ProductClassification(
            stage=stage,
            stage_confidence=confidence,
            maintenance_status=maintenance,
            project_type=project_type,
            readiness_level=readiness,
            repo_health_score=repo_health.total,
            tech_debt_score=tech_debt.total,
            signals=signals,
            stage_reasons=reasons,
            next_stage_requirements=next_requirements,
        )

    def _build_signals(
        self,
        structure_data: Dict[str, Any],
        static_metrics: Dict[str, Any],
    ) -> ClassificationSignals:
        """Build classification signals from data."""
        return ClassificationSignals(
            # Structure
            has_readme=structure_data.get("has_readme", False),
            has_docs=structure_data.get("has_docs_folder", False),
            has_api_docs=structure_data.get("has_api_docs", False),
            has_architecture_docs=structure_data.get("has_architecture_docs", False),
            has_changelog=structure_data.get("has_changelog", False),
            has_contributing=structure_data.get("has_contributing", False),
            has_license=structure_data.get("has_license", False),
            has_version=structure_data.get("has_version_file", False),

            # Code
            has_tests=bool(static_metrics.get("test_files_count", 0)),
            has_ci=static_metrics.get("has_ci", False),
            has_cd=static_metrics.get("has_deploy_config", False),
            has_docker=structure_data.get("has_dockerfile", False),
            has_kubernetes=structure_data.get("has_kubernetes", False),
            has_monitoring=structure_data.get("has_monitoring", False),
            has_logging=structure_data.get("has_logging", False),

            # Quality
            test_coverage=static_metrics.get("test_coverage", 0) or 0,
            code_quality_score=static_metrics.get("code_quality_score", 0),
            security_score=static_metrics.get("security_score", 0),

            # Activity
            commits_total=structure_data.get("commits_total", 0),
            commits_recent=structure_data.get("recent_commits", 0),
            authors_count=structure_data.get("authors_count", 0),
            days_since_last_commit=structure_data.get("days_since_last_commit", 999),

            # Size
            loc_total=static_metrics.get("total_loc", 0),
            files_total=static_metrics.get("files_count", 0),

            # Type detection
            has_setup_py=structure_data.get("has_setup_py", False),
            has_package_json="package.json" in str(structure_data.get("dependency_files", [])),
            has_web_framework=structure_data.get("has_web_framework", False),
            has_api_endpoints=structure_data.get("has_api_endpoints", False),
            has_ml_libs=structure_data.get("has_ml_libs", False),
            has_terraform=structure_data.get("has_terraform", False),
            has_helm=structure_data.get("has_helm", False),
        )

    def _classify_stage(
        self,
        health: RepoHealthScore,
        debt: TechDebtScore,
        signals: ClassificationSignals,
    ) -> Tuple[DevelopmentStage, float, List[str]]:
        """Classify into development stage."""
        h = health.total  # 0-12
        d = debt.total    # 0-15
        reasons = []

        # Production Ready (10-12 health, 13-15 debt)
        if h >= 10 and d >= 13:
            if signals.has_monitoring and signals.has_logging:
                reasons = [
                    f"High repo health ({h}/12)",
                    f"Low tech debt ({d}/15)",
                    "Has monitoring and logging",
                    "Comprehensive documentation",
                    "Strong test coverage",
                ]
                return DevelopmentStage.PRODUCTION, 0.9, reasons

        # Release Candidate (9-11 health, 12-14 debt)
        if h >= 9 and d >= 12:
            if signals.has_ci and signals.has_cd:
                reasons = [
                    f"Near-production health ({h}/12)",
                    f"Low tech debt ({d}/15)",
                    "CI/CD pipeline configured",
                    "Ready for final testing",
                ]
                return DevelopmentStage.RELEASE_CANDIDATE, 0.85, reasons

        # Beta (8-10 health, 10-13 debt)
        if h >= 8 and d >= 10:
            if signals.has_tests and signals.has_ci:
                reasons = [
                    f"Good repo health ({h}/12)",
                    f"Acceptable tech debt ({d}/15)",
                    "Test suite present",
                    "CI configured",
                    "Suitable for external testing",
                ]
                return DevelopmentStage.BETA, 0.8, reasons

        # Alpha (7-9 health, 8-11 debt)
        if h >= 7 and d >= 8:
            if signals.has_tests:
                reasons = [
                    f"Decent repo health ({h}/12)",
                    "Feature complete",
                    "Tests present",
                    "Ready for internal testing",
                ]
                return DevelopmentStage.ALPHA, 0.75, reasons

        # MVP (5-7 health, 6-9 debt)
        if h >= 5 and d >= 6:
            if signals.has_readme and (signals.has_docker or signals.has_ci):
                reasons = [
                    f"Functional repo health ({h}/12)",
                    "Core features implemented",
                    "Basic documentation",
                    "Deployable",
                ]
                return DevelopmentStage.MVP, 0.7, reasons

        # Prototype (4-6 health, 5-7 debt)
        if h >= 4 and d >= 5:
            reasons = [
                f"Basic repo health ({h}/12)",
                "Working implementation",
                "Some documentation or tests",
            ]
            return DevelopmentStage.PROTOTYPE, 0.65, reasons

        # Proof of Concept (2-4 health, 3-5 debt)
        if h >= 2 and d >= 3:
            reasons = [
                "Demonstrates technical feasibility",
                "Minimal documentation",
                "Limited structure",
            ]
            return DevelopmentStage.PROOF_OF_CONCEPT, 0.6, reasons

        # R&D Spike (default)
        reasons = [
            f"Low repo health ({h}/12)",
            f"High tech debt ({d}/15)",
            "Experimental code",
            "No tests or CI",
        ]
        return DevelopmentStage.RND_SPIKE, 0.5, reasons

    def _classify_maintenance(
        self,
        signals: ClassificationSignals,
    ) -> MaintenanceStatus:
        """Classify maintenance status based on activity."""
        days = signals.days_since_last_commit
        recent = signals.commits_recent

        if days > 365:
            if signals.has_changelog and "deprecated" in str(signals).lower():
                return MaintenanceStatus.DEPRECATED
            return MaintenanceStatus.ARCHIVED

        if days > 180:
            return MaintenanceStatus.LEGACY

        if days > 90 or recent < 2:
            return MaintenanceStatus.MAINTENANCE

        return MaintenanceStatus.ACTIVE

    def _detect_project_type(
        self,
        signals: ClassificationSignals,
        structure_data: Dict[str, Any],
    ) -> ProjectType:
        """Detect project type from signals."""
        # Check for infrastructure
        if signals.has_terraform or signals.has_helm or signals.has_kubernetes:
            return ProjectType.INFRASTRUCTURE

        # Check for ML/AI
        if signals.has_ml_libs:
            return ProjectType.ML_MODEL

        # Check for web service/API
        if signals.has_api_endpoints or signals.has_web_framework:
            if "frontend" in str(structure_data).lower():
                return ProjectType.WEB_APP
            return ProjectType.WEB_SERVICE

        # Check for CLI
        if signals.has_cli_commands or "cli" in str(structure_data).lower():
            return ProjectType.CLI

        # Check for library
        if signals.has_setup_py or signals.has_package_json:
            if signals.files_total < 50:
                return ProjectType.LIBRARY

        # Check for monorepo
        if "packages" in str(structure_data) or "apps" in str(structure_data):
            return ProjectType.MONOREPO

        return ProjectType.UNKNOWN

    def _assess_readiness(
        self,
        stage: DevelopmentStage,
        health: RepoHealthScore,
        debt: TechDebtScore,
        signals: ClassificationSignals,
    ) -> ReadinessLevel:
        """Assess business readiness level."""
        if stage == DevelopmentStage.PRODUCTION:
            if signals.has_monitoring and debt.security_deps >= 3:
                return ReadinessLevel.ENTERPRISE_READY
            return ReadinessLevel.MARKET_READY

        if stage in [DevelopmentStage.RELEASE_CANDIDATE, DevelopmentStage.BETA]:
            if signals.has_api_docs and signals.has_license:
                return ReadinessLevel.PARTNER_READY
            return ReadinessLevel.INTERNAL_ONLY

        if stage in [DevelopmentStage.ALPHA, DevelopmentStage.MVP]:
            return ReadinessLevel.INTERNAL_ONLY

        return ReadinessLevel.NOT_READY

    def _get_next_stage_requirements(
        self,
        stage: DevelopmentStage,
        health: RepoHealthScore,
        debt: TechDebtScore,
        signals: ClassificationSignals,
    ) -> List[str]:
        """Get requirements to reach next stage."""
        requirements = []

        if stage == DevelopmentStage.RND_SPIKE:
            requirements = [
                "Add README with project description",
                "Create basic project structure (src/, tests/)",
                "Add dependency management (requirements.txt / package.json)",
                "Write at least one test",
            ]

        elif stage == DevelopmentStage.PROOF_OF_CONCEPT:
            requirements = [
                "Add installation instructions to README",
                "Create basic test suite",
                "Add usage examples",
                "Organize code into modules",
            ]

        elif stage == DevelopmentStage.PROTOTYPE:
            requirements = [
                "Increase test coverage to 20%+",
                "Add CI pipeline (GitHub Actions / GitLab CI)",
                "Add Docker configuration",
                "Document core APIs/functions",
            ]

        elif stage == DevelopmentStage.MVP:
            requirements = [
                "Complete core feature set",
                "Increase test coverage to 40%+",
                "Add error handling and logging",
                "Create deployment documentation",
                "Add basic monitoring/health checks",
            ]

        elif stage == DevelopmentStage.ALPHA:
            requirements = [
                "Achieve 60%+ test coverage",
                "Add integration tests",
                "Configure CD pipeline",
                "Create API documentation",
                "Add CHANGELOG",
            ]

        elif stage == DevelopmentStage.BETA:
            requirements = [
                "Achieve 80%+ test coverage",
                "Add performance tests",
                "Configure monitoring and alerting",
                "Security audit / dependency scan",
                "Create user documentation",
            ]

        elif stage == DevelopmentStage.RELEASE_CANDIDATE:
            requirements = [
                "Complete security hardening",
                "Add production monitoring",
                "Create runbooks / operational docs",
                "Perform load testing",
                "Get stakeholder sign-off",
            ]

        elif stage == DevelopmentStage.PRODUCTION:
            requirements = [
                "Maintain high quality standards",
                "Continue security updates",
                "Monitor and optimize performance",
                "Gather user feedback",
            ]

        return requirements


# Singleton instance
product_classifier = ProductClassifier()


# Convenience function
def classify_product(
    repo_health: RepoHealthScore,
    tech_debt: TechDebtScore,
    structure_data: Dict[str, Any],
    static_metrics: Optional[Dict[str, Any]] = None,
) -> ProductClassification:
    """
    Classify repository into detailed product stage.

    Usage:
        result = classify_product(repo_health, tech_debt, structure_data)
        print(result.stage.value)  # "MVP"
        print(result.summary())    # Full summary
    """
    return product_classifier.classify(
        repo_health, tech_debt, structure_data, static_metrics
    )
