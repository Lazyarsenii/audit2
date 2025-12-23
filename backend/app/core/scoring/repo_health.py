"""
Repo Health scoring module.

Calculates health scores (0-3) for:
- Documentation
- Structure
- Runability
- Commit History
"""
from dataclasses import dataclass
from typing import Dict, Any
import yaml
from pathlib import Path


@dataclass
class RepoHealthScore:
    """Repo Health scoring result."""
    documentation: int  # 0-3
    structure: int      # 0-3
    runability: int     # 0-3
    commit_history: int # 0-3

    @property
    def total(self) -> int:
        """Sum of all scores (0-12)."""
        return self.documentation + self.structure + self.runability + self.commit_history

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documentation": self.documentation,
            "structure": self.structure,
            "runability": self.runability,
            "commit_history": self.commit_history,
            "total": self.total,
            "max_possible": 12,
        }


def calculate_repo_health(structure_data: Dict[str, Any]) -> RepoHealthScore:
    """
    Calculate Repo Health scores from structure analysis data.

    Args:
        structure_data: Output from StructureAnalyzer containing:
            - has_readme: bool
            - readme_has_usage: bool
            - readme_has_install: bool
            - has_docs_folder: bool
            - has_architecture_docs: bool
            - directory_structure: list of recognized patterns
            - dependency_files: list of found dependency files
            - has_dockerfile: bool
            - has_docker_compose: bool
            - has_run_instructions: bool
            - commits_total: int
            - authors_count: int
            - recent_commits: int (in last N days)

    Returns:
        RepoHealthScore with 0-3 scores for each dimension.
    """
    doc_score = _score_documentation(structure_data)
    struct_score = _score_structure(structure_data)
    run_score = _score_runability(structure_data)
    history_score = _score_commit_history(structure_data)

    return RepoHealthScore(
        documentation=doc_score,
        structure=struct_score,
        runability=run_score,
        commit_history=history_score,
    )


def _score_documentation(data: Dict[str, Any]) -> int:
    """
    Score documentation quality.

    0: No README or empty
    1: Basic README only
    2: README + usage + install
    3: Full docs folder + architecture
    """
    has_readme = data.get("has_readme", False)
    has_usage = data.get("readme_has_usage", False)
    has_install = data.get("readme_has_install", False)
    has_docs = data.get("has_docs_folder", False)
    has_arch = data.get("has_architecture_docs", False)

    if not has_readme:
        return 0

    if has_docs and has_arch:
        return 3

    if has_usage and has_install:
        return 2

    return 1


def _score_structure(data: Dict[str, Any]) -> int:
    """
    Score project structure quality.

    0: No structure (dump in root)
    1: Some structure
    2: Reasonable structure
    3: Well-structured with clear layers
    """
    patterns = data.get("directory_structure", [])

    # Required patterns
    required = {"src", "tests", "config"}
    # Bonus patterns
    bonus = {"docs", "scripts", "infra", "domain", "application", "adapters"}

    found_required = len(required.intersection(set(patterns)))
    found_bonus = len(bonus.intersection(set(patterns)))

    if found_required == 0:
        return 0
    elif found_required == 1:
        return 1
    elif found_required >= 2 and found_bonus == 0:
        return 2
    else:
        return 3


def _score_runability(data: Dict[str, Any]) -> int:
    """
    Score ease of running the project.

    0: No deps file, no instructions
    1: Deps but no docs/docker
    2: Deps + run instructions
    3: Docker + compose + env
    """
    has_deps = len(data.get("dependency_files", [])) > 0
    has_dockerfile = data.get("has_dockerfile", False)
    has_compose = data.get("has_docker_compose", False)
    has_run_docs = data.get("has_run_instructions", False)

    if not has_deps:
        return 0

    if has_dockerfile and has_compose:
        return 3

    if has_deps and has_run_docs:
        return 2

    return 1


def _score_commit_history(data: Dict[str, Any]) -> int:
    """
    Score commit history activity.

    0: <= 5 commits
    1: 6-30 commits
    2: 31-200 commits
    3: > 200 commits
    """
    commits = data.get("commits_total", 0)
    authors = data.get("authors_count", 1)
    recent = data.get("recent_commits", 0)

    # Primary: commit count
    if commits <= 5:
        return 0
    elif commits <= 30:
        return 1
    elif commits <= 200:
        # Bump to 3 if many authors or recent activity
        if authors >= 3 and recent >= 10:
            return 3
        return 2
    else:
        return 3
