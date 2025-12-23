"""
Structure analyzer module.

Analyzes repository structure, documentation, and commit history.
"""
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from git import Repo

logger = logging.getLogger(__name__)


class StructureAnalyzer:
    """Analyzes repository structure and metadata."""

    # Patterns for documentation
    README_PATTERNS = ["README.md", "README.rst", "README.txt", "README"]
    DOCS_FOLDERS = ["docs", "doc", "documentation", "wiki"]

    # Patterns for dependencies
    DEPENDENCY_FILES = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "Pipfile",
        "package.json",
        "yarn.lock",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
    ]

    # Patterns for tests
    TEST_FOLDERS = ["tests", "test", "spec", "__tests__"]

    # Patterns for CI
    CI_PATTERNS = [
        ".github/workflows",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".circleci",
        "azure-pipelines.yml",
        ".travis.yml",
    ]

    def __init__(self):
        pass

    async def analyze(self, local_path: Path) -> Dict[str, Any]:
        """
        Analyze repository structure.

        Args:
            local_path: Path to cloned repository

        Returns:
            Dictionary with structure analysis results
        """
        logger.info(f"Analyzing structure of {local_path}")

        result = {
            # Documentation
            "has_readme": False,
            "readme_has_usage": False,
            "readme_has_install": False,
            "has_docs_folder": False,
            "has_architecture_docs": False,

            # Structure
            "directory_structure": [],

            # Dependencies
            "dependency_files": [],

            # Docker/Infra
            "has_dockerfile": False,
            "has_docker_compose": False,
            "has_run_instructions": False,

            # CI
            "has_ci": False,
            "ci_configs": [],

            # Tests
            "has_tests": False,
            "test_folders": [],

            # Git history
            "commits_total": 0,
            "authors_count": 0,
            "recent_commits": 0,
            "first_commit_date": None,
            "last_commit_date": None,

            # Extras
            "has_version_file": False,
            "has_changelog": False,
            "has_api_docs": False,
        }

        # Analyze file structure
        self._analyze_files(local_path, result)

        # Analyze README content
        self._analyze_readme(local_path, result)

        # Analyze git history
        self._analyze_git_history(local_path, result)

        return result

    def _analyze_files(self, path: Path, result: Dict[str, Any]) -> None:
        """Scan directory structure."""
        for item in path.iterdir():
            if item.name.startswith("."):
                # Check for CI
                if item.name == ".github" and (item / "workflows").exists():
                    result["has_ci"] = True
                    result["ci_configs"].append(".github/workflows")
                elif item.name in [".gitlab-ci.yml", ".travis.yml"]:
                    result["has_ci"] = True
                    result["ci_configs"].append(item.name)
                continue

            if item.is_file():
                name_lower = item.name.lower()

                # README
                if item.name in self.README_PATTERNS:
                    result["has_readme"] = True

                # Dependencies
                if item.name in self.DEPENDENCY_FILES:
                    result["dependency_files"].append(item.name)

                # Docker
                if name_lower == "dockerfile":
                    result["has_dockerfile"] = True
                elif name_lower in ["docker-compose.yml", "docker-compose.yaml"]:
                    result["has_docker_compose"] = True

                # Version/Changelog
                if name_lower in ["version", "version.txt", "__version__.py"]:
                    result["has_version_file"] = True
                if name_lower in ["changelog.md", "changelog", "history.md"]:
                    result["has_changelog"] = True

                # CI files
                if item.name in ["Jenkinsfile", "azure-pipelines.yml"]:
                    result["has_ci"] = True
                    result["ci_configs"].append(item.name)

            elif item.is_dir():
                name_lower = item.name.lower()
                result["directory_structure"].append(item.name)

                # Docs
                if name_lower in self.DOCS_FOLDERS:
                    result["has_docs_folder"] = True
                    # Check for architecture docs
                    for doc in item.glob("*"):
                        if "arch" in doc.name.lower() or "design" in doc.name.lower():
                            result["has_architecture_docs"] = True
                            break

                # Tests
                if name_lower in self.TEST_FOLDERS:
                    result["has_tests"] = True
                    result["test_folders"].append(item.name)

                # API docs
                if name_lower in ["api", "api-docs", "openapi", "swagger"]:
                    result["has_api_docs"] = True

    def _analyze_readme(self, path: Path, result: Dict[str, Any]) -> None:
        """Analyze README content."""
        readme_path = None
        for pattern in self.README_PATTERNS:
            candidate = path / pattern
            if candidate.exists():
                readme_path = candidate
                break

        if not readme_path:
            return

        try:
            content = readme_path.read_text(encoding="utf-8", errors="ignore").lower()

            # Check for usage instructions
            usage_keywords = ["usage", "how to use", "getting started", "quick start", "example"]
            result["readme_has_usage"] = any(kw in content for kw in usage_keywords)

            # Check for install instructions
            install_keywords = ["install", "setup", "pip install", "npm install", "requirements"]
            result["readme_has_install"] = any(kw in content for kw in install_keywords)

            # Check for run instructions
            run_keywords = ["run", "start", "uvicorn", "npm run", "python", "docker"]
            result["has_run_instructions"] = any(kw in content for kw in run_keywords)

        except Exception as e:
            logger.warning(f"Failed to read README: {e}")

    def _analyze_git_history(self, path: Path, result: Dict[str, Any]) -> None:
        """Analyze git commit history."""
        try:
            repo = Repo(path)

            # Count commits
            commits = list(repo.iter_commits())
            result["commits_total"] = len(commits)

            if commits:
                # Authors
                authors = set(c.author.email for c in commits)
                result["authors_count"] = len(authors)

                # Dates
                result["first_commit_date"] = commits[-1].committed_datetime.isoformat()
                result["last_commit_date"] = commits[0].committed_datetime.isoformat()

                # Recent commits (last 90 days)
                cutoff = datetime.now(commits[0].committed_datetime.tzinfo) - timedelta(days=90)
                result["recent_commits"] = sum(
                    1 for c in commits if c.committed_datetime > cutoff
                )

        except Exception as e:
            logger.warning(f"Failed to analyze git history: {e}")


# Singleton instance
structure_analyzer = StructureAnalyzer()
