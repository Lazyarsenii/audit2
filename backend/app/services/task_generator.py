"""
Task Generator service.

Generates actionable improvement tasks based on analysis results.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel
from app.core.scoring.complexity import Complexity

logger = logging.getLogger(__name__)


class TaskCategory(str, Enum):
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"


class TaskPriority(str, Enum):
    P1 = "P1"  # Critical
    P2 = "P2"  # Important
    P3 = "P3"  # Nice to have


@dataclass
class GeneratedTask:
    """A generated improvement task."""
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    estimate_hours: int
    labels: List[str] = field(default_factory=list)
    source: str = ""  # What triggered this task

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "estimate_hours": self.estimate_hours,
            "labels": self.labels,
            "source": self.source,
        }


class TaskGenerator:
    """Generates improvement tasks from analysis results."""

    # Default hour estimates by category and size
    HOUR_ESTIMATES = {
        TaskCategory.DOCUMENTATION: {"small": 2, "medium": 4, "large": 8},
        TaskCategory.TESTING: {"small": 4, "medium": 8, "large": 16},
        TaskCategory.REFACTORING: {"small": 4, "medium": 12, "large": 24},
        TaskCategory.INFRASTRUCTURE: {"small": 4, "medium": 8, "large": 16},
        TaskCategory.SECURITY: {"small": 2, "medium": 6, "large": 12},
    }

    def __init__(self):
        pass

    def generate(
        self,
        repo_health: RepoHealthScore,
        tech_debt: TechDebtScore,
        semgrep_findings: List[Dict[str, Any]],
        structure_data: Dict[str, Any],
        product_level: ProductLevel,
        complexity: Complexity,
    ) -> List[GeneratedTask]:
        """
        Generate improvement tasks based on analysis.

        Args:
            repo_health: Repository health scores
            tech_debt: Technical debt scores
            semgrep_findings: Security/quality findings from Semgrep
            structure_data: Structure analysis data
            product_level: Current product maturity level
            complexity: Project complexity

        Returns:
            List of generated tasks, sorted by priority
        """
        tasks: List[GeneratedTask] = []

        # Generate tasks from each source
        tasks.extend(self._tasks_from_repo_health(repo_health, structure_data))
        tasks.extend(self._tasks_from_tech_debt(tech_debt, structure_data))
        tasks.extend(self._tasks_from_semgrep(semgrep_findings))
        tasks.extend(self._tasks_for_product_level(product_level, repo_health, tech_debt))

        # Adjust estimates based on complexity
        tasks = self._adjust_for_complexity(tasks, complexity)

        # Sort by priority
        priority_order = {TaskPriority.P1: 0, TaskPriority.P2: 1, TaskPriority.P3: 2}
        tasks.sort(key=lambda t: priority_order[t.priority])

        logger.info(f"Generated {len(tasks)} improvement tasks")
        return tasks

    def _tasks_from_repo_health(
        self,
        health: RepoHealthScore,
        structure_data: Dict[str, Any],
    ) -> List[GeneratedTask]:
        """Generate tasks from repo health gaps."""
        tasks = []

        # Documentation tasks
        if health.documentation == 0:
            tasks.append(GeneratedTask(
                title="Create README.md with project overview",
                description=(
                    "Create a comprehensive README.md that includes:\n"
                    "- Project description and purpose\n"
                    "- Installation instructions\n"
                    "- Usage examples\n"
                    "- Contributing guidelines"
                ),
                category=TaskCategory.DOCUMENTATION,
                priority=TaskPriority.P1,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.DOCUMENTATION]["medium"],
                labels=["documentation", "readme"],
                source="repo_health.documentation=0",
            ))
        elif health.documentation == 1:
            tasks.append(GeneratedTask(
                title="Improve README with installation and usage instructions",
                description=(
                    "Expand the README to include:\n"
                    "- Step-by-step installation guide\n"
                    "- Configuration options\n"
                    "- Basic usage examples\n"
                    "- Troubleshooting section"
                ),
                category=TaskCategory.DOCUMENTATION,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.DOCUMENTATION]["small"],
                labels=["documentation", "readme"],
                source="repo_health.documentation=1",
            ))

        if health.documentation < 3 and not structure_data.get("has_docs_folder"):
            tasks.append(GeneratedTask(
                title="Create docs/ folder with architecture documentation",
                description=(
                    "Create a docs/ directory with:\n"
                    "- ARCHITECTURE.md - system design overview\n"
                    "- API.md - API documentation (if applicable)\n"
                    "- DEVELOPMENT.md - developer setup guide"
                ),
                category=TaskCategory.DOCUMENTATION,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.DOCUMENTATION]["large"],
                labels=["documentation", "architecture"],
                source="missing_docs_folder",
            ))

        # Structure tasks
        if health.structure <= 1:
            tasks.append(GeneratedTask(
                title="Reorganize project structure",
                description=(
                    "Improve project organization:\n"
                    "- Separate source code into src/ or app/ directory\n"
                    "- Move tests to dedicated tests/ directory\n"
                    "- Isolate configuration files\n"
                    "- Consider domain-driven structure if applicable"
                ),
                category=TaskCategory.REFACTORING,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.REFACTORING]["medium"],
                labels=["structure", "refactoring"],
                source=f"repo_health.structure={health.structure}",
            ))

        # Runability tasks
        if health.runability == 0:
            tasks.append(GeneratedTask(
                title="Add dependency management file",
                description=(
                    "Create proper dependency declaration:\n"
                    "- For Python: requirements.txt or pyproject.toml\n"
                    "- For Node: package.json\n"
                    "- Include all runtime and dev dependencies\n"
                    "- Pin versions for reproducibility"
                ),
                category=TaskCategory.INFRASTRUCTURE,
                priority=TaskPriority.P1,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.INFRASTRUCTURE]["small"],
                labels=["dependencies", "setup"],
                source="repo_health.runability=0",
            ))

        if health.runability < 3 and not structure_data.get("has_dockerfile"):
            tasks.append(GeneratedTask(
                title="Add Docker configuration",
                description=(
                    "Create Docker setup for consistent environments:\n"
                    "- Dockerfile for the application\n"
                    "- docker-compose.yml for local development\n"
                    "- Include all dependencies and services\n"
                    "- Document usage in README"
                ),
                category=TaskCategory.INFRASTRUCTURE,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.INFRASTRUCTURE]["medium"],
                labels=["docker", "infrastructure"],
                source="missing_dockerfile",
            ))

        return tasks

    def _tasks_from_tech_debt(
        self,
        debt: TechDebtScore,
        structure_data: Dict[str, Any],
    ) -> List[GeneratedTask]:
        """Generate tasks from tech debt issues."""
        tasks = []

        # Architecture tasks
        if debt.architecture <= 1:
            tasks.append(GeneratedTask(
                title="Refactor architecture to separate concerns",
                description=(
                    "Improve code architecture:\n"
                    "- Identify and separate domain logic from infrastructure\n"
                    "- Create clear module boundaries\n"
                    "- Reduce coupling between components\n"
                    "- Define clear interfaces between layers"
                ),
                category=TaskCategory.REFACTORING,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.REFACTORING]["large"],
                labels=["architecture", "refactoring", "tech-debt"],
                source=f"tech_debt.architecture={debt.architecture}",
            ))

        # Code quality tasks
        if debt.code_quality <= 1:
            tasks.append(GeneratedTask(
                title="Address code quality issues",
                description=(
                    "Improve code quality:\n"
                    "- Break down large functions (>50 lines)\n"
                    "- Reduce code duplication\n"
                    "- Simplify complex logic\n"
                    "- Add type hints (Python) or strict types (TS)\n"
                    "- Run linter and fix issues"
                ),
                category=TaskCategory.REFACTORING,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.REFACTORING]["medium"],
                labels=["code-quality", "refactoring", "tech-debt"],
                source=f"tech_debt.code_quality={debt.code_quality}",
            ))

        # Testing tasks
        if debt.testing == 0:
            tasks.append(GeneratedTask(
                title="Implement basic test suite",
                description=(
                    "Add automated testing:\n"
                    "- Set up test framework (pytest, jest, etc.)\n"
                    "- Write unit tests for core business logic\n"
                    "- Add at least one integration test\n"
                    "- Configure test runner in CI"
                ),
                category=TaskCategory.TESTING,
                priority=TaskPriority.P1,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.TESTING]["large"],
                labels=["testing", "quality"],
                source="tech_debt.testing=0",
            ))
        elif debt.testing == 1:
            tasks.append(GeneratedTask(
                title="Expand test coverage",
                description=(
                    "Improve test coverage:\n"
                    "- Identify untested critical paths\n"
                    "- Add tests for edge cases\n"
                    "- Target minimum 40% coverage\n"
                    "- Add coverage reporting to CI"
                ),
                category=TaskCategory.TESTING,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.TESTING]["medium"],
                labels=["testing", "coverage"],
                source="tech_debt.testing=1",
            ))

        # Infrastructure tasks
        if debt.infrastructure == 0:
            tasks.append(GeneratedTask(
                title="Set up CI/CD pipeline",
                description=(
                    "Implement continuous integration:\n"
                    "- Create GitHub Actions workflow (or equivalent)\n"
                    "- Run linting on every PR\n"
                    "- Run tests on every PR\n"
                    "- Block merge on failures"
                ),
                category=TaskCategory.INFRASTRUCTURE,
                priority=TaskPriority.P1,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.INFRASTRUCTURE]["medium"],
                labels=["ci-cd", "infrastructure"],
                source="tech_debt.infrastructure=0",
            ))
        elif debt.infrastructure == 1:
            tasks.append(GeneratedTask(
                title="Enhance CI pipeline with tests",
                description=(
                    "Improve CI pipeline:\n"
                    "- Add test execution step\n"
                    "- Add coverage reporting\n"
                    "- Consider adding security scanning"
                ),
                category=TaskCategory.INFRASTRUCTURE,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.INFRASTRUCTURE]["small"],
                labels=["ci-cd", "testing"],
                source="tech_debt.infrastructure=1",
            ))

        return tasks

    def _tasks_from_semgrep(
        self,
        findings: List[Dict[str, Any]],
    ) -> List[GeneratedTask]:
        """Generate tasks from Semgrep findings."""
        tasks = []

        if not findings:
            return tasks

        # Group findings by category and severity
        security_critical = []
        security_medium = []
        other_issues = []

        for f in findings:
            category = f.get("category", "other")
            severity = f.get("severity", "INFO")

            if category == "security":
                if severity == "ERROR":
                    security_critical.append(f)
                else:
                    security_medium.append(f)
            else:
                other_issues.append(f)

        # Critical security issues
        if security_critical:
            files = list(set(f.get("path", "unknown") for f in security_critical[:5]))
            tasks.append(GeneratedTask(
                title=f"Fix {len(security_critical)} critical security issues",
                description=(
                    f"Critical security vulnerabilities detected:\n\n"
                    f"Affected files:\n" +
                    "\n".join(f"- {f}" for f in files) +
                    f"\n\nTotal issues: {len(security_critical)}\n"
                    "Review each finding and apply appropriate fixes."
                ),
                category=TaskCategory.SECURITY,
                priority=TaskPriority.P1,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.SECURITY]["large"],
                labels=["security", "critical"],
                source=f"semgrep_critical_count={len(security_critical)}",
            ))

        # Medium security issues
        if security_medium:
            tasks.append(GeneratedTask(
                title=f"Address {len(security_medium)} security warnings",
                description=(
                    f"Security warnings detected that should be reviewed:\n"
                    f"- Total warnings: {len(security_medium)}\n"
                    "- Review and fix or document accepted risks"
                ),
                category=TaskCategory.SECURITY,
                priority=TaskPriority.P2,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.SECURITY]["medium"],
                labels=["security", "warning"],
                source=f"semgrep_warning_count={len(security_medium)}",
            ))

        # Other code issues
        if len(other_issues) > 10:
            tasks.append(GeneratedTask(
                title=f"Review {len(other_issues)} code quality findings",
                description=(
                    "Static analysis found potential issues:\n"
                    f"- Total findings: {len(other_issues)}\n"
                    "- Review and address as appropriate"
                ),
                category=TaskCategory.REFACTORING,
                priority=TaskPriority.P3,
                estimate_hours=self.HOUR_ESTIMATES[TaskCategory.REFACTORING]["medium"],
                labels=["code-quality", "static-analysis"],
                source=f"semgrep_other_count={len(other_issues)}",
            ))

        return tasks

    def _tasks_for_product_level(
        self,
        level: ProductLevel,
        health: RepoHealthScore,
        debt: TechDebtScore,
    ) -> List[GeneratedTask]:
        """Generate tasks to advance product level."""
        tasks = []

        if level == ProductLevel.RND_SPIKE:
            tasks.append(GeneratedTask(
                title="Evaluate spike for further development",
                description=(
                    "This appears to be an R&D spike. Consider:\n"
                    "- Document learnings and decisions\n"
                    "- Decide if this should be promoted to prototype\n"
                    "- If promoting: plan cleanup and documentation"
                ),
                category=TaskCategory.DOCUMENTATION,
                priority=TaskPriority.P3,
                estimate_hours=2,
                labels=["planning", "evaluation"],
                source="product_level=rnd_spike",
            ))

        elif level == ProductLevel.PROTOTYPE:
            if health.documentation < 2:
                tasks.append(GeneratedTask(
                    title="Document prototype for handoff",
                    description=(
                        "Prepare prototype for potential promotion:\n"
                        "- Document what works and what doesn't\n"
                        "- List known limitations\n"
                        "- Outline steps to make production-ready"
                    ),
                    category=TaskCategory.DOCUMENTATION,
                    priority=TaskPriority.P2,
                    estimate_hours=4,
                    labels=["documentation", "prototype"],
                    source="product_level=prototype",
                ))

        elif level == ProductLevel.INTERNAL_TOOL:
            if debt.testing < 2:
                tasks.append(GeneratedTask(
                    title="Add tests for reliability",
                    description=(
                        "Internal tool needs more test coverage:\n"
                        "- Focus on critical user workflows\n"
                        "- Add error handling tests\n"
                        "- Document manual test procedures"
                    ),
                    category=TaskCategory.TESTING,
                    priority=TaskPriority.P2,
                    estimate_hours=8,
                    labels=["testing", "reliability"],
                    source="product_level=internal_tool",
                ))

        elif level == ProductLevel.PLATFORM_MODULE:
            tasks.append(GeneratedTask(
                title="Prepare for platform integration",
                description=(
                    "Ready module for platform inclusion:\n"
                    "- Define clear API boundaries\n"
                    "- Document integration points\n"
                    "- Ensure consistent error handling\n"
                    "- Add health check endpoint if applicable"
                ),
                category=TaskCategory.REFACTORING,
                priority=TaskPriority.P2,
                estimate_hours=12,
                labels=["integration", "platform"],
                source="product_level=platform_module",
            ))

        return tasks

    def _adjust_for_complexity(
        self,
        tasks: List[GeneratedTask],
        complexity: Complexity,
    ) -> List[GeneratedTask]:
        """Adjust task estimates based on project complexity."""
        multipliers = {
            Complexity.SMALL: 0.8,
            Complexity.MEDIUM: 1.0,
            Complexity.LARGE: 1.5,
            Complexity.XLARGE: 2.0,
        }

        mult = multipliers.get(complexity, 1.0)

        for task in tasks:
            task.estimate_hours = max(1, int(task.estimate_hours * mult))

        return tasks


# Singleton instance
task_generator = TaskGenerator()
