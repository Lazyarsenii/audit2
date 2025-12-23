"""
Tech Debt scoring module.

Calculates technical debt scores (0-3) for:
- Architecture
- Code Quality
- Testing
- Infrastructure
- Security & Dependencies
"""
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class TechDebtScore:
    """Tech Debt scoring result."""
    architecture: int       # 0-3
    code_quality: int       # 0-3
    testing: int            # 0-3
    infrastructure: int     # 0-3
    security_deps: int      # 0-3

    @property
    def total(self) -> int:
        """Sum of all scores (0-15)."""
        return (
            self.architecture +
            self.code_quality +
            self.testing +
            self.infrastructure +
            self.security_deps
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture": self.architecture,
            "code_quality": self.code_quality,
            "testing": self.testing,
            "infrastructure": self.infrastructure,
            "security_deps": self.security_deps,
            "total": self.total,
            "max_possible": 15,
        }


def calculate_tech_debt(
    static_metrics: Dict[str, Any],
    semgrep_findings: List[Dict[str, Any]],
) -> TechDebtScore:
    """
    Calculate Tech Debt scores from static analysis and Semgrep findings.

    Args:
        static_metrics: Output from StaticAnalyzer containing:
            - total_loc: int
            - files_count: int
            - large_files: list of files > threshold
            - max_file_lines: int
            - max_function_lines: int
            - avg_function_lines: float
            - cyclomatic_complexity_avg: float
            - duplication_percent: float
            - test_files_count: int
            - test_coverage: float (if available)
            - has_ci: bool
            - ci_has_tests: bool
            - has_dockerfile: bool

        semgrep_findings: List of findings, each containing:
            - severity: "ERROR" | "WARNING" | "INFO"
            - category: "security" | "correctness" | "performance" | etc.

    Returns:
        TechDebtScore with 0-3 scores for each dimension.
    """
    arch_score = _score_architecture(static_metrics)
    quality_score = _score_code_quality(static_metrics)
    testing_score = _score_testing(static_metrics)
    infra_score = _score_infrastructure(static_metrics)
    security_score = _score_security_deps(semgrep_findings)

    return TechDebtScore(
        architecture=arch_score,
        code_quality=quality_score,
        testing=testing_score,
        infrastructure=infra_score,
        security_deps=security_score,
    )


def _score_architecture(metrics: Dict[str, Any]) -> int:
    """
    Score architecture quality.

    Based on:
    - File/function sizes
    - Presence of clear layers
    - Module organization
    """
    max_file = metrics.get("max_file_lines", 0)
    max_func = metrics.get("max_function_lines", 0)
    has_layers = metrics.get("has_clear_layers", False)

    # High complexity indicators
    if max_file > 1000 or max_func > 100:
        return 0

    if max_file > 500 or max_func > 50:
        return 1 if not has_layers else 2

    if has_layers:
        return 3

    return 2


def _score_code_quality(metrics: Dict[str, Any]) -> int:
    """
    Score code quality.

    Based on:
    - Duplication
    - Complexity
    - Code smells count
    """
    duplication = metrics.get("duplication_percent", 0)
    complexity = metrics.get("cyclomatic_complexity_avg", 0)
    smells_per_kloc = metrics.get("code_smells_per_kloc", 0)

    # Heavy duplication or complexity
    if duplication > 15 or complexity > 20 or smells_per_kloc > 20:
        return 0

    if duplication > 10 or complexity > 15 or smells_per_kloc > 10:
        return 1

    if duplication > 5 or complexity > 10 or smells_per_kloc > 5:
        return 2

    return 3


def _score_testing(metrics: Dict[str, Any]) -> int:
    """
    Score testing maturity.

    Based on:
    - Test coverage (if available)
    - Test file count
    - Test patterns detected
    """
    coverage = metrics.get("test_coverage")
    test_files = metrics.get("test_files_count", 0)
    total_files = metrics.get("files_count", 1)

    # If we have coverage data, use it
    if coverage is not None:
        if coverage < 1:
            return 0
        elif coverage < 20:
            return 1
        elif coverage < 60:
            return 2
        else:
            return 3

    # Fallback: estimate from test file ratio
    if test_files == 0:
        return 0

    ratio = test_files / max(total_files, 1)
    if ratio < 0.05:
        return 1
    elif ratio < 0.15:
        return 2
    else:
        return 3


def _score_infrastructure(metrics: Dict[str, Any]) -> int:
    """
    Score infrastructure maturity.

    Based on:
    - CI presence and configuration
    - Docker/containerization
    - Deployment setup
    """
    has_ci = metrics.get("has_ci", False)
    ci_has_tests = metrics.get("ci_has_tests", False)
    has_docker = metrics.get("has_dockerfile", False)
    has_deploy = metrics.get("has_deploy_config", False)

    if not has_ci and not has_docker:
        return 0

    if has_docker and not has_ci:
        return 1

    if has_ci and ci_has_tests:
        if has_deploy:
            return 3
        return 2

    return 1


def _score_security_deps(findings: List[Dict[str, Any]]) -> int:
    """
    Score security and dependency health.

    Based on Semgrep findings severity.
    """
    if not findings:
        return 3

    # Weight findings by severity
    weights = {
        "ERROR": 10,
        "WARNING": 3,
        "INFO": 1,
    }

    total_weight = sum(
        weights.get(f.get("severity", "INFO"), 1)
        for f in findings
        if f.get("category") == "security"
    )

    if total_weight >= 50:
        return 0
    elif total_weight >= 20:
        return 1
    elif total_weight >= 5:
        return 2
    else:
        return 3
