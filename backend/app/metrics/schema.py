"""
Unified Metrics Schema — Datadog-style approach.

All metrics follow a standardized format for:
- Collection
- Storage
- Processing
- Querying

Based on OpenMetrics/Prometheus conventions with extensions for repo analysis.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Union
import json


class MetricType(str, Enum):
    """Types of metrics we collect."""
    GAUGE = "gauge"          # Point-in-time value (e.g., LOC count)
    COUNTER = "counter"      # Cumulative value (e.g., commits)
    HISTOGRAM = "histogram"  # Distribution (e.g., file sizes)
    SUMMARY = "summary"      # Statistical summary
    INFO = "info"            # Metadata/labels only


class MetricSource(str, Enum):
    """Source/collector that produced the metric."""
    STRUCTURE = "structure"    # StructureAnalyzer
    STATIC = "static"          # StaticAnalyzer
    GIT = "git"                # Git history
    SEMGREP = "semgrep"        # Security scanner
    DEPS = "deps"              # Dependency analyzer
    COVERAGE = "coverage"      # Test coverage
    CI = "ci"                  # CI/CD analysis
    MANUAL = "manual"          # Manual input


class MetricCategory(str, Enum):
    """Category for grouping metrics."""
    DOCUMENTATION = "documentation"
    STRUCTURE = "structure"
    RUNABILITY = "runability"
    HISTORY = "history"
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    TESTING = "testing"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    DEPENDENCIES = "dependencies"
    SIZE = "size"


@dataclass
class MetricLabel:
    """Label/tag for a metric (Datadog-style tagging)."""
    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.key}:{self.value}"


@dataclass
class Metric:
    """
    Single metric data point — Datadog-style.

    Example:
        Metric(
            name="repo.loc.total",
            value=135000,
            metric_type=MetricType.GAUGE,
            source=MetricSource.STATIC,
            category=MetricCategory.SIZE,
            labels=[MetricLabel("language", "python")],
            timestamp=datetime.now(timezone.utc),
        )
    """
    name: str                           # Namespaced name: "repo.health.documentation"
    value: Union[int, float, bool, str] # Metric value
    metric_type: MetricType             # Type of metric
    source: MetricSource                # What collected it
    category: MetricCategory            # Logical grouping
    labels: List[MetricLabel] = field(default_factory=list)  # Tags
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unit: Optional[str] = None          # "lines", "files", "percent", etc.
    description: Optional[str] = None   # Human-readable description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "source": self.source.value,
            "category": self.category.value,
            "labels": {l.key: l.value for l in self.labels},
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
            "description": self.description,
        }

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        labels_str = ",".join(f'{l.key}="{l.value}"' for l in self.labels)
        if labels_str:
            return f'{self.name}{{{labels_str}}} {self.value}'
        return f'{self.name} {self.value}'

    def to_datadog(self) -> Dict[str, Any]:
        """Export in Datadog DogStatsD format."""
        return {
            "metric": self.name,
            "points": [[int(self.timestamp.timestamp()), self.value]],
            "type": self.metric_type.value,
            "tags": [str(l) for l in self.labels],
        }


@dataclass
class MetricSet:
    """
    Collection of metrics for a single analysis run.

    This is the standardized container that flows through the pipeline:
    Collectors -> MetricSet -> Storage -> Scoring Engine -> Reports
    """
    analysis_id: str
    repo_url: str
    branch: Optional[str]
    collected_at: datetime
    metrics: List[Metric] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, metric: Metric) -> None:
        """Add a metric to the set."""
        self.metrics.append(metric)

    def add_gauge(
        self,
        name: str,
        value: Union[int, float],
        source: MetricSource,
        category: MetricCategory,
        labels: List[MetricLabel] = None,
        unit: str = None,
        description: str = None,
    ) -> None:
        """Convenience method to add a gauge metric."""
        self.add(Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            source=source,
            category=category,
            labels=labels or [],
            unit=unit,
            description=description,
        ))

    def add_counter(
        self,
        name: str,
        value: int,
        source: MetricSource,
        category: MetricCategory,
        labels: List[MetricLabel] = None,
        description: str = None,
    ) -> None:
        """Convenience method to add a counter metric."""
        self.add(Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            source=source,
            category=category,
            labels=labels or [],
            description=description,
        ))

    def add_info(
        self,
        name: str,
        value: Union[bool, str],
        source: MetricSource,
        category: MetricCategory,
        labels: List[MetricLabel] = None,
        description: str = None,
    ) -> None:
        """Convenience method to add an info/boolean metric."""
        self.add(Metric(
            name=name,
            value=value,
            metric_type=MetricType.INFO,
            source=source,
            category=category,
            labels=labels or [],
            description=description,
        ))

    def get(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def get_value(self, name: str, default: Any = None) -> Any:
        """Get metric value by name."""
        m = self.get(name)
        return m.value if m else default

    def filter_by_category(self, category: MetricCategory) -> List[Metric]:
        """Get all metrics in a category."""
        return [m for m in self.metrics if m.category == category]

    def filter_by_source(self, source: MetricSource) -> List[Metric]:
        """Get all metrics from a source."""
        return [m for m in self.metrics if m.source == source]

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "collected_at": self.collected_at.isoformat(),
            "metrics_count": len(self.metrics),
            "metrics": [m.to_dict() for m in self.metrics],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Export as flat dictionary for easy access.

        Returns: {"repo.loc.total": 135000, "repo.health.has_readme": True, ...}
        """
        return {m.name: m.value for m in self.metrics}


# Standard metric names (constants for consistency)
class MetricNames:
    """Standard metric names used across the system."""

    # Size metrics
    LOC_TOTAL = "repo.size.loc_total"
    LOC_BY_LANGUAGE = "repo.size.loc"  # with language label
    FILES_TOTAL = "repo.size.files_total"
    FILES_BY_TYPE = "repo.size.files"  # with type label
    TEST_FILES_COUNT = "repo.size.test_files"

    # Documentation metrics
    HAS_README = "repo.docs.has_readme"
    README_SIZE = "repo.docs.readme_size"
    README_HAS_USAGE = "repo.docs.readme_has_usage"
    README_HAS_INSTALL = "repo.docs.readme_has_install"
    HAS_DOCS_FOLDER = "repo.docs.has_docs_folder"
    HAS_ARCHITECTURE_DOCS = "repo.docs.has_architecture"
    HAS_API_DOCS = "repo.docs.has_api_docs"
    HAS_CHANGELOG = "repo.docs.has_changelog"
    DOCS_FILES_COUNT = "repo.docs.files_count"

    # Structure metrics
    HAS_SRC_DIR = "repo.structure.has_src"
    HAS_TESTS_DIR = "repo.structure.has_tests"
    HAS_DOCS_DIR = "repo.structure.has_docs"
    HAS_CONFIG_DIR = "repo.structure.has_config"
    STRUCTURE_SCORE = "repo.structure.score"  # 0-3

    # Runability metrics
    HAS_DEPS_FILE = "repo.run.has_deps_file"
    DEPS_FILE_TYPE = "repo.run.deps_file_type"
    HAS_DOCKERFILE = "repo.run.has_dockerfile"
    HAS_DOCKER_COMPOSE = "repo.run.has_docker_compose"
    HAS_MAKEFILE = "repo.run.has_makefile"
    HAS_RUN_INSTRUCTIONS = "repo.run.has_instructions"

    # Git history metrics
    COMMITS_TOTAL = "repo.git.commits_total"
    COMMITS_RECENT = "repo.git.commits_recent"  # last 90 days
    AUTHORS_COUNT = "repo.git.authors_count"
    FIRST_COMMIT_DATE = "repo.git.first_commit"
    LAST_COMMIT_DATE = "repo.git.last_commit"
    ACTIVE_DAYS = "repo.git.active_days"

    # Code quality metrics
    MAX_FILE_LINES = "repo.quality.max_file_lines"
    MAX_FUNCTION_LINES = "repo.quality.max_function_lines"
    AVG_FILE_LINES = "repo.quality.avg_file_lines"
    AVG_FUNCTION_LINES = "repo.quality.avg_function_lines"
    CYCLOMATIC_COMPLEXITY_AVG = "repo.quality.complexity_avg"
    DUPLICATION_PERCENT = "repo.quality.duplication_pct"
    CODE_SMELLS_COUNT = "repo.quality.smells_count"

    # Testing metrics
    TEST_COVERAGE = "repo.testing.coverage_pct"
    UNIT_TESTS_COUNT = "repo.testing.unit_count"
    INTEGRATION_TESTS_COUNT = "repo.testing.integration_count"
    E2E_TESTS_COUNT = "repo.testing.e2e_count"

    # Infrastructure metrics
    HAS_CI = "repo.infra.has_ci"
    CI_PROVIDER = "repo.infra.ci_provider"
    CI_HAS_TESTS = "repo.infra.ci_has_tests"
    CI_HAS_LINT = "repo.infra.ci_has_lint"
    CI_HAS_DEPLOY = "repo.infra.ci_has_deploy"
    HAS_K8S_CONFIG = "repo.infra.has_kubernetes"

    # Security metrics
    SEMGREP_CRITICAL = "repo.security.semgrep_critical"
    SEMGREP_HIGH = "repo.security.semgrep_high"
    SEMGREP_MEDIUM = "repo.security.semgrep_medium"
    SEMGREP_LOW = "repo.security.semgrep_low"
    DEPS_VULNERABILITIES = "repo.security.deps_vulnerabilities"
    HAS_SECRETS_IN_CODE = "repo.security.has_secrets"

    # Dependencies metrics
    DEPS_COUNT = "repo.deps.total_count"
    DEPS_OUTDATED = "repo.deps.outdated_count"
    DEPS_DIRECT = "repo.deps.direct_count"
    DEPS_DEV = "repo.deps.dev_count"
    DEPS_MAX_DEPTH = "repo.deps.max_depth"

    # Git analytics (extended)
    BUS_FACTOR = "repo.git.bus_factor"
    TOP_CONTRIBUTOR_PCT = "repo.git.top_contributor_pct"
    HOTSPOTS = "repo.git.hotspots"
    CHURN_30D = "repo.git.churn_30d"
    LINES_ADDED_30D = "repo.git.lines_added_30d"
    LINES_DELETED_30D = "repo.git.lines_deleted_30d"

    # Dead code metrics
    DEAD_CODE_TOTAL = "repo.quality.dead_code.total"
    DEAD_CODE_FUNCTIONS = "repo.quality.dead_code.functions"
    DEAD_CODE_IMPORTS = "repo.quality.dead_code.imports"

    # Extended code quality
    COMPLEXITY_MAX = "repo.quality.complexity_max"
    HIGH_COMPLEXITY_COUNT = "repo.quality.high_complexity_count"
    MAINTAINABILITY_INDEX = "repo.quality.maintainability_index"
    DUPLICATED_LINES = "repo.quality.duplicated_lines"
    CLONE_COUNT = "repo.quality.clone_count"

    # License metrics
    LICENSE_TYPE = "repo.license.type"
    LICENSE_UNIQUE_COUNT = "repo.license.unique_count"
    LICENSE_COPYLEFT_COUNT = "repo.license.copyleft_count"
    LICENSE_PROBLEMATIC_COUNT = "repo.license.problematic_count"

    # Docker metrics
    DOCKER_BEST_PRACTICES_SCORE = "repo.docker.best_practices_score"
    DOCKER_HADOLINT_ERRORS = "repo.docker.hadolint_errors"
    DOCKER_HADOLINT_WARNINGS = "repo.docker.hadolint_warnings"
    DOCKER_HAS_NONROOT_USER = "repo.docker.has_nonroot_user"
    DOCKER_HAS_HEALTHCHECK = "repo.docker.has_healthcheck"
    DOCKER_USES_LATEST_TAG = "repo.docker.uses_latest_tag"
    DOCKER_MULTISTAGE_BUILD = "repo.docker.multistage_build"

    # Scored metrics (calculated by scoring engine)
    SCORE_DOCUMENTATION = "repo.score.documentation"
    SCORE_STRUCTURE = "repo.score.structure"
    SCORE_RUNABILITY = "repo.score.runability"
    SCORE_HISTORY = "repo.score.history"
    SCORE_ARCHITECTURE = "repo.score.architecture"
    SCORE_CODE_QUALITY = "repo.score.code_quality"
    SCORE_TESTING = "repo.score.testing"
    SCORE_INFRASTRUCTURE = "repo.score.infrastructure"
    SCORE_SECURITY = "repo.score.security"
    SCORE_REPO_HEALTH_TOTAL = "repo.score.health_total"
    SCORE_TECH_DEBT_TOTAL = "repo.score.tech_debt_total"
