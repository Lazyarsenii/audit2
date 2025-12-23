"""
Pytest configuration and fixtures.

IMPORTANT: Environment variables must be set BEFORE importing app!
"""
import os
import pytest
import asyncio
from typing import Generator

# ============================================================
# SET TEST ENV BEFORE ANY APP IMPORTS
# ============================================================
os.environ["API_KEY_REQUIRED"] = "false"
os.environ["API_KEYS"] = "test_key_12345"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

# Now import app (after env vars are set)
from fastapi.testclient import TestClient
from app.main import app

# Test API key for authentication
TEST_API_KEY = "test_key_12345"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """
    Create a test client.
    Authentication is disabled via environment variables.
    """
    return TestClient(app)


@pytest.fixture
def authenticated_client() -> TestClient:
    """
    Create a test client WITH authentication headers.
    Use this when testing with auth enabled.
    """
    client = TestClient(app)
    client.headers.update({"X-API-Key": TEST_API_KEY})
    return client


@pytest.fixture
def sample_structure_data() -> dict:
    """Sample structure analysis data for testing."""
    return {
        "has_readme": True,
        "readme_has_usage": True,
        "readme_has_install": True,
        "has_docs_folder": True,
        "has_architecture_docs": False,
        "directory_structure": ["src", "tests", "docs"],
        "dependency_files": ["requirements.txt"],
        "has_dockerfile": True,
        "has_docker_compose": True,
        "has_run_instructions": True,
        "has_ci": True,
        "ci_configs": [".github/workflows"],
        "has_tests": True,
        "test_folders": ["tests"],
        "commits_total": 150,
        "authors_count": 4,
        "recent_commits": 25,
        "first_commit_date": "2023-01-15T10:00:00",
        "last_commit_date": "2024-01-10T15:30:00",
        "has_version_file": False,
        "has_changelog": False,
        "has_api_docs": False,
    }


@pytest.fixture
def sample_static_metrics() -> dict:
    """Sample static analysis metrics for testing."""
    return {
        "total_loc": 15000,
        "files_count": 80,
        "test_files_count": 15,
        "languages": {
            "python": {"files": 60, "loc": 12000},
            "javascript": {"files": 20, "loc": 3000},
        },
        "large_files": [
            {"path": "src/main.py", "loc": 450},
        ],
        "max_file_lines": 450,
        "max_function_lines": 40,
        "avg_function_lines": 15,
        "cyclomatic_complexity_avg": 8,
        "duplication_percent": 3,
        "code_smells_per_kloc": 4,
        "has_clear_layers": True,
        "external_deps_count": 20,
        "test_coverage": None,
        "has_ci": True,
        "ci_has_tests": True,
        "has_dockerfile": True,
        "has_deploy_config": False,
    }


@pytest.fixture
def sample_semgrep_findings() -> list:
    """Sample Semgrep findings for testing."""
    return [
        {
            "path": "src/api/auth.py",
            "line": 42,
            "rule_id": "python.security.audit.hardcoded-password",
            "severity": "WARNING",
            "category": "security",
            "message": "Possible hardcoded password",
        },
        {
            "path": "src/utils/db.py",
            "line": 15,
            "rule_id": "python.security.audit.sql-injection",
            "severity": "ERROR",
            "category": "security",
            "message": "Possible SQL injection",
        },
        {
            "path": "src/main.py",
            "line": 100,
            "rule_id": "python.best-practice.print-function",
            "severity": "INFO",
            "category": "best-practice",
            "message": "Avoid print in production code",
        },
    ]


@pytest.fixture
def healthy_repo_data() -> tuple:
    """Data representing a healthy, well-maintained repository."""
    structure_data = {
        "has_readme": True,
        "readme_has_usage": True,
        "readme_has_install": True,
        "has_docs_folder": True,
        "has_architecture_docs": True,
        "directory_structure": ["src", "tests", "docs", "scripts", "config"],
        "dependency_files": ["pyproject.toml", "requirements.txt"],
        "has_dockerfile": True,
        "has_docker_compose": True,
        "has_run_instructions": True,
        "has_ci": True,
        "commits_total": 500,
        "authors_count": 8,
        "recent_commits": 50,
        "has_version_file": True,
        "has_changelog": True,
        "has_api_docs": True,
    }

    static_metrics = {
        "total_loc": 25000,
        "files_count": 120,
        "test_files_count": 40,
        "max_file_lines": 300,
        "max_function_lines": 30,
        "duplication_percent": 2,
        "cyclomatic_complexity_avg": 6,
        "code_smells_per_kloc": 2,
        "has_clear_layers": True,
        "external_deps_count": 15,
        "test_coverage": 75,
        "has_ci": True,
        "ci_has_tests": True,
        "has_dockerfile": True,
        "has_deploy_config": True,
    }

    semgrep_findings = []  # No findings

    return structure_data, static_metrics, semgrep_findings


@pytest.fixture
def unhealthy_repo_data() -> tuple:
    """Data representing an unhealthy, poorly-maintained repository."""
    structure_data = {
        "has_readme": False,
        "has_docs_folder": False,
        "directory_structure": [],
        "dependency_files": [],
        "has_dockerfile": False,
        "has_docker_compose": False,
        "has_run_instructions": False,
        "has_ci": False,
        "commits_total": 5,
        "authors_count": 1,
        "recent_commits": 0,
    }

    static_metrics = {
        "total_loc": 5000,
        "files_count": 30,
        "test_files_count": 0,
        "max_file_lines": 1500,
        "max_function_lines": 200,
        "duplication_percent": 20,
        "cyclomatic_complexity_avg": 25,
        "code_smells_per_kloc": 30,
        "has_clear_layers": False,
        "external_deps_count": 5,
        "test_coverage": None,
        "has_ci": False,
        "ci_has_tests": False,
        "has_dockerfile": False,
    }

    semgrep_findings = [
        {"severity": "ERROR", "category": "security", "path": "app.py", "message": "Critical issue"},
        {"severity": "ERROR", "category": "security", "path": "db.py", "message": "SQL injection"},
        {"severity": "ERROR", "category": "security", "path": "auth.py", "message": "Hardcoded secret"},
        {"severity": "ERROR", "category": "security", "path": "api.py", "message": "XSS"},
        {"severity": "ERROR", "category": "security", "path": "utils.py", "message": "Path traversal"},
        {"severity": "WARNING", "category": "security", "path": "config.py", "message": "Weak crypto"},
    ]

    return structure_data, static_metrics, semgrep_findings
