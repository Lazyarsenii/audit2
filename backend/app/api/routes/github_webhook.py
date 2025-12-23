"""
GitHub webhook handler endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.models.repository import RepositoryRepo, AnalysisRepo
from app.adapters.github_adapter import github_adapter, GitHubError
from app.services.analysis_runner import run_analysis_task

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookResponse(BaseModel):
    """Webhook response model."""
    status: str
    message: str
    analysis_id: Optional[str] = None


@router.post("/webhook", response_model=WebhookResponse)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle GitHub App webhooks.

    Supported events:
    - issue_comment: Look for /audit command to trigger analysis
    """
    # Get signature header
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if settings.GITHUB_WEBHOOK_SECRET:
        if not github_adapter.verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    logger.info(f"Received GitHub webhook: {event_type}")

    # Handle issue_comment event
    if event_type == "issue_comment":
        return await _handle_issue_comment(payload, background_tasks, db)

    # Handle installation event
    if event_type == "installation":
        action = payload.get("action")
        logger.info(f"GitHub App installation: {action}")
        return WebhookResponse(
            status="ok",
            message=f"Installation {action} received",
        )

    # Handle push event (optional: auto-analyze on push)
    if event_type == "push":
        return WebhookResponse(
            status="ok",
            message="Push event received (auto-analyze not enabled)",
        )

    return WebhookResponse(
        status="ok",
        message=f"Event {event_type} received but not processed",
    )


async def _handle_issue_comment(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> WebhookResponse:
    """Handle issue_comment event, looking for /audit command."""
    action = payload.get("action")

    # Only process new comments
    if action != "created":
        return WebhookResponse(
            status="ok",
            message=f"Comment action {action} ignored",
        )

    comment = payload.get("comment", {})
    body = comment.get("body", "")

    # Check for /audit command
    if not body.strip().startswith("/audit"):
        return WebhookResponse(
            status="ok",
            message="Comment does not contain /audit command",
        )

    # Extract repo info
    repo_data = payload.get("repository", {})
    repo_url = repo_data.get("html_url", "")
    default_branch = repo_data.get("default_branch", "main")
    owner = repo_data.get("owner", {}).get("login", "")
    repo_name = repo_data.get("name", "")

    issue = payload.get("issue", {})
    issue_number = issue.get("number")

    logger.info(f"Processing /audit command for {repo_url}")

    # Parse branch from command (e.g., /audit branch:develop)
    branch = default_branch
    parts = body.strip().split()
    for part in parts[1:]:
        if part.startswith("branch:"):
            branch = part.split(":")[1]

    # Create analysis
    repo_repo = RepositoryRepo(db)
    analysis_repo = AnalysisRepo(db)

    repository = await repo_repo.get_or_create(url=repo_url)
    analysis_run = await analysis_repo.create(
        repository_id=repository.id,
        branch=branch,
    )
    await db.commit()

    analysis_id = str(analysis_run.id)

    # Queue analysis
    background_tasks.add_task(
        run_analysis_task,
        analysis_id=analysis_id,
        repo_url=repo_url,
        branch=branch,
    )

    # Post comment acknowledging the command
    try:
        installation_id = payload.get("installation", {}).get("id")
        if installation_id:
            token = await github_adapter.get_installation_token(installation_id)
            await github_adapter.create_issue_comment(
                owner=owner,
                repo=repo_name,
                issue_number=issue_number,
                body=(
                    f"**Repo Auditor** starting analysis...\n\n"
                    f"- **Branch:** `{branch}`\n"
                    f"- **Analysis ID:** `{analysis_id}`\n\n"
                    f"Results will be posted when complete."
                ),
                token=token,
            )
    except GitHubError as e:
        logger.warning(f"Failed to post acknowledgment comment: {e}")
    except Exception as e:
        logger.warning(f"Failed to post acknowledgment comment: {e}")

    return WebhookResponse(
        status="ok",
        message="Analysis started",
        analysis_id=analysis_id,
    )


@router.post("/webhook/complete/{analysis_id}")
async def notify_analysis_complete(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint to post results after analysis completes.

    Called by the analysis runner when GitHub integration is enabled.
    """
    # This would be called internally to post results back to GitHub
    # Implementation depends on how you want to track the original issue

    return {"status": "ok", "message": "Notification endpoint (not fully implemented)"}
