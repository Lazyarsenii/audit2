"""
Repository fetcher module.

Handles cloning and managing local copies of repositories.
"""
import asyncio
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from git import Repo, GitCommandError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread pool for blocking git operations
_executor = ThreadPoolExecutor(max_workers=4)


class RepoFetchError(Exception):
    """Error during repository fetch."""
    pass


class RepoFetcher:
    """Handles repository cloning and local management."""

    def __init__(self, clone_dir: Optional[Path] = None):
        self.clone_dir = clone_dir or settings.CLONE_DIR
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    async def fetch(
        self,
        repo_url: str,
        branch: Optional[str] = None,
        depth: int = 1,
        token: Optional[str] = None,
    ) -> Path:
        """
        Clone a repository to local storage.

        Args:
            repo_url: Git repository URL (HTTPS)
            branch: Branch to clone (default: default branch)
            depth: Clone depth (default: 1 for shallow clone)
            token: GitHub PAT for private repos (optional, uses settings.GITHUB_PAT if not provided)

        Returns:
            Path to the cloned repository

        Raises:
            RepoFetchError: If cloning fails
        """
        # Validate URL to prevent command injection
        if not self._validate_url(repo_url):
            raise RepoFetchError(f"Invalid repository URL: {repo_url}")

        # Generate unique local path
        repo_name = self._extract_repo_name(repo_url)
        local_path = self.clone_dir / f"{repo_name}_{self._generate_suffix()}"

        # Inject token for authentication if available
        auth_url = self._inject_auth_token(repo_url, token)

        logger.info(f"Cloning {repo_url} to {local_path}")

        try:
            # Run blocking git clone in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _executor,
                self._clone_sync,
                auth_url,  # Use authenticated URL
                str(local_path),
                branch,
                depth,
            )

            logger.info(f"Successfully cloned {repo_url}")
            return local_path

        except GitCommandError as e:
            logger.error(f"Failed to clone {repo_url}: {e}")
            # Cleanup partial clone
            if local_path.exists():
                shutil.rmtree(local_path)
            raise RepoFetchError(f"Failed to clone repository: {e}")
        except Exception as e:
            logger.error(f"Unexpected error cloning {repo_url}: {e}")
            if local_path.exists():
                shutil.rmtree(local_path)
            raise RepoFetchError(f"Failed to clone repository: {e}")

    def _clone_sync(
        self,
        repo_url: str,
        local_path: str,
        branch: Optional[str],
        depth: int,
    ) -> None:
        """Synchronous clone operation for thread pool."""
        clone_args = {
            "url": repo_url,
            "to_path": local_path,
            "depth": depth,
        }

        if branch:
            clone_args["branch"] = branch

        Repo.clone_from(**clone_args)

    def _validate_url(self, url: str) -> bool:
        """Validate repository URL to prevent command injection."""
        try:
            parsed = urlparse(url)
            # Only allow http/https/git protocols
            if parsed.scheme not in ("http", "https", "git"):
                return False
            # Check for suspicious characters that could be used for injection
            dangerous_chars = [";", "&", "|", "$", "`", "(", ")", "{", "}", "<", ">"]
            if any(char in url for char in dangerous_chars):
                return False
            return True
        except Exception:
            return False

    def cleanup(self, local_path: Path) -> None:
        """Remove a cloned repository."""
        if local_path.exists() and local_path.is_dir():
            shutil.rmtree(local_path)
            logger.info(f"Cleaned up {local_path}")

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return path.split("/")[-1] or "repo"

    def _generate_suffix(self) -> str:
        """Generate unique suffix for clone directory."""
        import uuid
        return uuid.uuid4().hex[:8]

    def _inject_auth_token(self, url: str, token: Optional[str] = None) -> str:
        """
        Inject authentication token into repository URL.

        Converts: https://github.com/owner/repo.git
        To:       https://{token}@github.com/owner/repo.git

        Args:
            url: Original repository URL
            token: GitHub PAT (optional, uses settings.GITHUB_PAT if not provided)

        Returns:
            URL with authentication token injected
        """
        # Use provided token or fall back to settings
        auth_token = token or settings.GITHUB_PAT

        if not auth_token:
            # No token available, return original URL (will work for public repos)
            return url

        parsed = urlparse(url)

        # Only inject for HTTPS URLs
        if parsed.scheme != "https":
            return url

        # Inject token: https://token@github.com/...
        auth_netloc = f"{auth_token}@{parsed.netloc}"
        authenticated_url = parsed._replace(netloc=auth_netloc).geturl()

        logger.debug(f"Using authenticated URL for {parsed.netloc}")
        return authenticated_url


# Singleton instance
repo_fetcher = RepoFetcher()
