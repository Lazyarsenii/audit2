"""
GitHub Repositories API routes.

Endpoints for listing available repositories using GitHub PAT.
"""
import logging
from typing import Optional, List

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubRepo(BaseModel):
    """GitHub repository info."""
    id: int
    name: str
    full_name: str
    url: str
    clone_url: str
    private: bool
    description: Optional[str] = None
    language: Optional[str] = None
    default_branch: str = "main"
    updated_at: Optional[str] = None
    stargazers_count: int = 0


class GitHubReposResponse(BaseModel):
    """Response for repos list."""
    repos: List[GitHubRepo]
    total: int
    configured: bool


class GitHubOrg(BaseModel):
    """GitHub organization info."""
    login: str
    id: int
    description: Optional[str] = None
    avatar_url: Optional[str] = None


@router.get("/github/status")
async def github_status():
    """Check if GitHub PAT is configured."""
    configured = bool(settings.GITHUB_PAT)

    if not configured:
        return {
            "configured": False,
            "message": "GitHub PAT not configured. Set GITHUB_PAT in .env"
        }

    # Verify token works
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/user",
                headers={
                    "Authorization": f"Bearer {settings.GITHUB_PAT}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                user = resp.json()
                return {
                    "configured": True,
                    "username": user.get("login"),
                    "name": user.get("name"),
                    "avatar_url": user.get("avatar_url"),
                }
            else:
                return {
                    "configured": False,
                    "message": f"GitHub token invalid: {resp.status_code}"
                }
    except Exception as e:
        logger.error(f"GitHub status check failed: {e}")
        return {
            "configured": False,
            "message": f"Failed to verify token: {str(e)}"
        }


@router.get("/github/orgs")
async def list_organizations():
    """List organizations the user has access to."""
    if not settings.GITHUB_PAT:
        raise HTTPException(status_code=400, detail="GitHub PAT not configured")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/user/orgs",
                headers={
                    "Authorization": f"Bearer {settings.GITHUB_PAT}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                timeout=10.0
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"GitHub API error: {resp.text}"
                )

            orgs = resp.json()
            return {
                "orgs": [
                    GitHubOrg(
                        login=org["login"],
                        id=org["id"],
                        description=org.get("description"),
                        avatar_url=org.get("avatar_url"),
                    )
                    for org in orgs
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list orgs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/repos", response_model=GitHubReposResponse)
async def list_repositories(
    org: Optional[str] = Query(None, description="Organization name (optional)"),
    type: str = Query("all", description="Type: all, owner, public, private, member"),
    sort: str = Query("updated", description="Sort: created, updated, pushed, full_name"),
    per_page: int = Query(100, le=100, description="Results per page (max 100)"),
):
    """
    List repositories accessible via GitHub PAT.

    Args:
        org: Organization name (if not provided, lists user's repos)
        type: Filter by repo type
        sort: Sort field
        per_page: Number of results

    Returns:
        List of repositories
    """
    if not settings.GITHUB_PAT:
        return GitHubReposResponse(repos=[], total=0, configured=False)

    try:
        async with httpx.AsyncClient() as client:
            # Choose endpoint based on org
            if org:
                url = f"{GITHUB_API}/orgs/{org}/repos"
            else:
                url = f"{GITHUB_API}/user/repos"

            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {settings.GITHUB_PAT}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                params={
                    "type": type,
                    "sort": sort,
                    "per_page": per_page,
                    "direction": "desc",
                },
                timeout=15.0
            )

            if resp.status_code != 200:
                logger.error(f"GitHub API error: {resp.status_code} - {resp.text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"GitHub API error: {resp.text}"
                )

            repos_data = resp.json()

            repos = [
                GitHubRepo(
                    id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    private=repo["private"],
                    description=repo.get("description"),
                    language=repo.get("language"),
                    default_branch=repo.get("default_branch", "main"),
                    updated_at=repo.get("updated_at"),
                    stargazers_count=repo.get("stargazers_count", 0),
                )
                for repo in repos_data
            ]

            return GitHubReposResponse(
                repos=repos,
                total=len(repos),
                configured=True,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list repos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/repos/search")
async def search_repositories(
    q: str = Query(..., description="Search query"),
    org: Optional[str] = Query(None, description="Limit to organization"),
    per_page: int = Query(30, le=100),
):
    """
    Search repositories.

    Args:
        q: Search query
        org: Limit search to organization
        per_page: Results per page
    """
    if not settings.GITHUB_PAT:
        raise HTTPException(status_code=400, detail="GitHub PAT not configured")

    try:
        async with httpx.AsyncClient() as client:
            # Build search query
            search_query = q
            if org:
                search_query = f"org:{org} {q}"

            resp = await client.get(
                f"{GITHUB_API}/search/repositories",
                headers={
                    "Authorization": f"Bearer {settings.GITHUB_PAT}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                params={
                    "q": search_query,
                    "per_page": per_page,
                    "sort": "updated",
                },
                timeout=15.0
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"GitHub API error: {resp.text}"
                )

            data = resp.json()
            repos = [
                GitHubRepo(
                    id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    private=repo["private"],
                    description=repo.get("description"),
                    language=repo.get("language"),
                    default_branch=repo.get("default_branch", "main"),
                    updated_at=repo.get("updated_at"),
                    stargazers_count=repo.get("stargazers_count", 0),
                )
                for repo in data.get("items", [])
            ]

            return {
                "repos": repos,
                "total": data.get("total_count", 0),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
