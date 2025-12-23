"""
GitHub Adapter.

Handles GitHub API interactions: webhooks, file commits, issue creation.
"""
import base64
import hashlib
import hmac
import logging
from typing import Dict, Any, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """GitHub API error."""
    pass


class GitHubAdapter:
    """Adapter for GitHub API interactions."""

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        app_id: Optional[str] = None,
        private_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.app_id = app_id or settings.GITHUB_APP_ID
        self.private_key = private_key or settings.GITHUB_APP_PRIVATE_KEY
        self.webhook_secret = webhook_secret or settings.GITHUB_WEBHOOK_SECRET
        self._installation_tokens: Dict[int, str] = {}

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return False

        if not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def get_installation_token(self, installation_id: int) -> str:
        """
        Get installation access token for a GitHub App installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Access token string
        """
        # Check cache (tokens are valid for 1 hour, but we don't cache that long)
        if installation_id in self._installation_tokens:
            return self._installation_tokens[installation_id]

        # Generate JWT for app authentication
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )

            if response.status_code != 201:
                raise GitHubError(f"Failed to get installation token: {response.text}")

            data = response.json()
            token = data["token"]
            self._installation_tokens[installation_id] = token
            return token

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in repository
            content: File content
            message: Commit message
            branch: Target branch
            token: Access token (installation token or PAT)

        Returns:
            API response data
        """
        if not token:
            raise GitHubError("Access token required")

        # Check if file exists to get SHA
        sha = await self._get_file_sha(owner, repo, path, branch, token)

        # Encode content to base64
        content_b64 = base64.b64encode(content.encode()).decode()

        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch,
        }

        if sha:
            payload["sha"] = sha

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json=payload,
            )

            if response.status_code not in [200, 201]:
                raise GitHubError(f"Failed to create/update file: {response.text}")

            return response.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body (Markdown)
            labels: List of label names
            token: Access token

        Returns:
            Created issue data
        """
        if not token:
            raise GitHubError("Access token required")

        payload: dict[str, str | list[str]] = {
            "title": title,
            "body": body,
        }

        if labels:
            payload["labels"] = labels

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json=payload,
            )

            if response.status_code != 201:
                raise GitHubError(f"Failed to create issue: {response.text}")

            return response.json()

    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            body: Comment body
            token: Access token

        Returns:
            Created comment data
        """
        if not token:
            raise GitHubError("Access token required")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"body": body},
            )

            if response.status_code != 201:
                raise GitHubError(f"Failed to create comment: {response.text}")

            return response.json()

    async def get_repo_info(
        self,
        owner: str,
        repo: str,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name
            token: Access token (optional for public repos)

        Returns:
            Repository data
        """
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{owner}/{repo}",
                headers=headers,
            )

            if response.status_code != 200:
                raise GitHubError(f"Failed to get repo info: {response.text}")

            return response.json()

    async def _get_file_sha(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str,
        token: str,
    ) -> Optional[str]:
        """Get SHA of existing file, or None if not exists."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                params={"ref": branch},
            )

            if response.status_code == 200:
                return response.json().get("sha")
            return None

    def _generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        import time
        import jwt

        if not self.app_id or not self.private_key:
            raise GitHubError("GitHub App credentials not configured")

        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 60 seconds ago
            "exp": now + (10 * 60),  # Expires in 10 minutes
            "iss": self.app_id,
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str]:
        """
        Parse GitHub URL to extract owner and repo.

        Args:
            url: GitHub repository URL

        Returns:
            Tuple of (owner, repo)
        """
        # Handle various URL formats
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # https://github.com/owner/repo
        # git@github.com:owner/repo
        if "github.com" in url:
            if ":" in url and "@" in url:
                # SSH format
                path = url.split(":")[-1]
            else:
                # HTTPS format
                path = url.split("github.com/")[-1]

            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]

        raise ValueError(f"Could not parse GitHub URL: {url}")


# Singleton instance
github_adapter = GitHubAdapter()
