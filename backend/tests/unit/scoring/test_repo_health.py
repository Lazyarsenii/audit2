"""
Tests for Repo Health scoring module.
"""
import pytest

from app.core.scoring.repo_health import (
    calculate_repo_health,
    RepoHealthScore,
)


class TestRepoHealthScoring:
    """Test cases for Repo Health calculation."""

    def test_empty_repo_scores_zero(self):
        """Empty/minimal repo should score 0 across all dimensions."""
        structure_data = {
            "has_readme": False,
            "has_docs_folder": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 0,
            "authors_count": 0,
        }

        result = calculate_repo_health(structure_data)

        assert result.documentation == 0
        assert result.structure == 0
        assert result.runability == 0
        assert result.commit_history == 0
        assert result.total == 0

    def test_basic_readme_scores_one(self):
        """Basic README without docs folder should score 1 for documentation."""
        structure_data = {
            "has_readme": True,
            "readme_has_usage": False,
            "readme_has_install": False,
            "has_docs_folder": False,
            "has_architecture_docs": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 0,
            "authors_count": 0,
        }

        result = calculate_repo_health(structure_data)

        assert result.documentation == 1

    def test_full_docs_scores_three(self):
        """Full docs with architecture should score 3."""
        structure_data = {
            "has_readme": True,
            "readme_has_usage": True,
            "readme_has_install": True,
            "has_docs_folder": True,
            "has_architecture_docs": True,
            "directory_structure": ["docs"],
            "dependency_files": ["requirements.txt"],
            "has_dockerfile": False,
            "commits_total": 10,
            "authors_count": 1,
        }

        result = calculate_repo_health(structure_data)

        assert result.documentation == 3

    def test_structure_scoring(self):
        """Test structure scoring with different directory patterns."""
        # No structure
        data_no_structure = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_no_structure).structure == 0

        # One pattern (src)
        data_one_pattern = {
            "has_readme": False,
            "directory_structure": ["src"],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_one_pattern).structure == 1

        # Two patterns
        data_two_patterns = {
            "has_readme": False,
            "directory_structure": ["src", "tests"],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_two_patterns).structure == 2

    def test_runability_scoring(self):
        """Test runability scoring."""
        # No deps
        data_no_deps = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "has_docker_compose": False,
            "has_run_instructions": False,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_no_deps).runability == 0

        # Deps only
        data_deps_only = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": ["requirements.txt"],
            "has_dockerfile": False,
            "has_docker_compose": False,
            "has_run_instructions": False,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_deps_only).runability == 1

        # Full docker setup
        data_full_docker = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": ["requirements.txt"],
            "has_dockerfile": True,
            "has_docker_compose": True,
            "has_run_instructions": True,
            "commits_total": 0,
            "authors_count": 0,
        }
        assert calculate_repo_health(data_full_docker).runability == 3

    def test_commit_history_scoring(self):
        """Test commit history scoring."""
        # Few commits
        data_few = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 3,
            "authors_count": 1,
        }
        assert calculate_repo_health(data_few).commit_history == 0

        # Moderate commits
        data_moderate = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 50,
            "authors_count": 2,
            "recent_commits": 5,
        }
        assert calculate_repo_health(data_moderate).commit_history == 2

        # Many commits with activity
        data_active = {
            "has_readme": False,
            "directory_structure": [],
            "dependency_files": [],
            "has_dockerfile": False,
            "commits_total": 250,
            "authors_count": 5,
            "recent_commits": 20,
        }
        assert calculate_repo_health(data_active).commit_history == 3

    def test_repo_health_score_total(self):
        """Test that total is calculated correctly."""
        score = RepoHealthScore(
            documentation=2,
            structure=3,
            runability=1,
            commit_history=2,
        )

        assert score.total == 8
        assert score.to_dict()["total"] == 8
        assert score.to_dict()["max_possible"] == 12
