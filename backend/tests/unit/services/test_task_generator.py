"""
Tests for Task Generator service.
"""
import pytest

from app.core.scoring.repo_health import RepoHealthScore
from app.core.scoring.tech_debt import TechDebtScore
from app.core.scoring.product_level import ProductLevel
from app.core.scoring.complexity import Complexity
from app.services.task_generator import (
    TaskGenerator,
    GeneratedTask,
    TaskCategory,
    TaskPriority,
)


class TestTaskGenerator:
    """Test cases for Task Generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TaskGenerator()

    def test_generates_tasks_for_missing_readme(self):
        """Missing README should generate P1 documentation task."""
        repo_health = RepoHealthScore(
            documentation=0,
            structure=2,
            runability=2,
            commit_history=2,
        )
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)
        structure_data = {"has_docs_folder": False}

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.PROTOTYPE,
            complexity=Complexity.SMALL,
        )

        # Should have at least one documentation task
        doc_tasks = [t for t in tasks if t.category == TaskCategory.DOCUMENTATION]
        assert len(doc_tasks) > 0

        # At least one should be P1
        p1_doc_tasks = [t for t in doc_tasks if t.priority == TaskPriority.P1]
        assert len(p1_doc_tasks) > 0

    def test_generates_tasks_for_no_tests(self):
        """No tests should generate P1 testing task."""
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(
            architecture=2,
            code_quality=2,
            testing=0,  # No tests
            infrastructure=2,
            security_deps=2,
        )
        structure_data = {}

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.INTERNAL_TOOL,
            complexity=Complexity.MEDIUM,
        )

        test_tasks = [t for t in tasks if t.category == TaskCategory.TESTING]
        assert len(test_tasks) > 0

        # Should be P1 for no tests
        p1_test_tasks = [t for t in test_tasks if t.priority == TaskPriority.P1]
        assert len(p1_test_tasks) > 0

    def test_generates_tasks_for_no_ci(self):
        """No CI should generate infrastructure task."""
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(
            architecture=2,
            code_quality=2,
            testing=2,
            infrastructure=0,  # No CI
            security_deps=2,
        )
        structure_data = {}

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.INTERNAL_TOOL,
            complexity=Complexity.MEDIUM,
        )

        infra_tasks = [t for t in tasks if t.category == TaskCategory.INFRASTRUCTURE]
        assert len(infra_tasks) > 0

    def test_generates_security_tasks_for_findings(self):
        """Security findings should generate security tasks."""
        repo_health = RepoHealthScore(2, 2, 2, 2)
        tech_debt = TechDebtScore(2, 2, 2, 2, 2)
        semgrep_findings = [
            {"severity": "ERROR", "category": "security", "path": "app.py", "message": "SQL injection"},
            {"severity": "ERROR", "category": "security", "path": "auth.py", "message": "Hardcoded secret"},
            {"severity": "ERROR", "category": "security", "path": "api.py", "message": "XSS vulnerability"},
        ]
        structure_data = {}

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=semgrep_findings,
            structure_data=structure_data,
            product_level=ProductLevel.INTERNAL_TOOL,
            complexity=Complexity.MEDIUM,
        )

        security_tasks = [t for t in tasks if t.category == TaskCategory.SECURITY]
        assert len(security_tasks) > 0

        # Should be P1 for critical security
        p1_security = [t for t in security_tasks if t.priority == TaskPriority.P1]
        assert len(p1_security) > 0

    def test_complexity_adjusts_estimates(self):
        """Task estimates should be adjusted by complexity."""
        repo_health = RepoHealthScore(0, 0, 0, 0)  # Will generate many tasks
        tech_debt = TechDebtScore(0, 0, 0, 0, 0)
        structure_data = {"has_docs_folder": False}

        # Small complexity
        tasks_small = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.RND_SPIKE,
            complexity=Complexity.SMALL,
        )

        # XL complexity
        tasks_xl = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.RND_SPIKE,
            complexity=Complexity.XLARGE,
        )

        # Same tasks but XL should have higher estimates
        if tasks_small and tasks_xl:
            # Get matching tasks by title
            small_hours = sum(t.estimate_hours for t in tasks_small)
            xl_hours = sum(t.estimate_hours for t in tasks_xl)
            assert xl_hours > small_hours

    def test_tasks_are_sorted_by_priority(self):
        """Generated tasks should be sorted by priority."""
        repo_health = RepoHealthScore(0, 1, 0, 1)
        tech_debt = TechDebtScore(1, 1, 0, 0, 1)
        structure_data = {"has_docs_folder": False}

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[
                {"severity": "ERROR", "category": "security", "path": "app.py", "message": "Issue"},
            ],
            structure_data=structure_data,
            product_level=ProductLevel.PROTOTYPE,
            complexity=Complexity.MEDIUM,
        )

        # Check that P1 tasks come before P2, and P2 before P3
        priority_order = {"P1": 0, "P2": 1, "P3": 2}
        for i in range(len(tasks) - 1):
            current_order = priority_order[tasks[i].priority.value]
            next_order = priority_order[tasks[i + 1].priority.value]
            assert current_order <= next_order

    def test_task_to_dict(self):
        """Test that tasks serialize correctly."""
        task = GeneratedTask(
            title="Test Task",
            description="Test Description",
            category=TaskCategory.TESTING,
            priority=TaskPriority.P2,
            estimate_hours=8,
            labels=["testing", "unit"],
            source="test",
        )

        data = task.to_dict()

        assert data["title"] == "Test Task"
        assert data["category"] == "testing"
        assert data["priority"] == "P2"
        assert data["estimate_hours"] == 8
        assert "testing" in data["labels"]

    def test_healthy_repo_generates_few_tasks(self):
        """A healthy repo should generate fewer tasks."""
        repo_health = RepoHealthScore(3, 3, 3, 3)  # Perfect health
        tech_debt = TechDebtScore(3, 3, 3, 3, 3)  # No debt
        structure_data = {
            "has_docs_folder": True,
            "has_version_file": True,
        }

        tasks = self.generator.generate(
            repo_health=repo_health,
            tech_debt=tech_debt,
            semgrep_findings=[],
            structure_data=structure_data,
            product_level=ProductLevel.NEAR_PRODUCT,
            complexity=Complexity.MEDIUM,
        )

        # Should have very few tasks
        assert len(tasks) < 5
