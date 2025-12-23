"""
Git repository analyzer module.
Analyzes git history and commit patterns.
"""
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GitAnalyzer:
    """Analyzes git repository metrics."""

    async def analyze(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze git repository."""
        result = {
            "total_commits": 0,
            "authors_count": 0,
            "has_readme": False,
            "has_license": False,
            "last_commit_date": None,
            "first_commit_date": None,
            "branches_count": 1,
        }

        try:
            # Check for README
            readme_patterns = ["README.md", "README", "README.txt", "readme.md"]
            for pattern in readme_patterns:
                if (repo_path / pattern).exists():
                    result["has_readme"] = True
                    break

            # Check for LICENSE
            license_patterns = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]
            for pattern in license_patterns:
                if (repo_path / pattern).exists():
                    result["has_license"] = True
                    break

            # Git commands
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return result

            # Count commits
            try:
                output = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if output.returncode == 0:
                    result["total_commits"] = int(output.stdout.strip())
            except:
                pass

            # Count authors
            try:
                output = subprocess.run(
                    ["git", "shortlog", "-sn", "HEAD"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if output.returncode == 0:
                    result["authors_count"] = len(output.stdout.strip().split("\n"))
            except:
                pass

        except Exception as e:
            logger.warning(f"Git analysis failed: {e}")

        return result


# Singleton instance
git_analyzer = GitAnalyzer()
