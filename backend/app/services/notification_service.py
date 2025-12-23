"""
Notification Service - Send alerts via Slack and Email.

Sends notifications when:
- Analysis completes
- Critical security issues found
- Cost estimates ready
"""
import logging
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from enum import Enum

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    ANALYSIS_COMPLETE = "analysis_complete"
    SECURITY_ALERT = "security_alert"
    COST_ESTIMATE = "cost_estimate"


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    email_enabled: bool = False
    email_recipients: Optional[List[str]] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


class NotificationService:
    """Service for sending notifications."""

    def __init__(self):
        self.config = NotificationConfig(
            slack_webhook_url=getattr(settings, 'SLACK_WEBHOOK_URL', None),
            slack_channel=getattr(settings, 'SLACK_CHANNEL', '#repo-auditor'),
            email_enabled=getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False),
            email_recipients=getattr(settings, 'EMAIL_RECIPIENTS', '').split(',') if getattr(settings, 'EMAIL_RECIPIENTS', '') else [],
            smtp_host=getattr(settings, 'SMTP_HOST', 'smtp.gmail.com'),
            smtp_port=getattr(settings, 'SMTP_PORT', 587),
            smtp_user=getattr(settings, 'SMTP_USER', None),
            smtp_password=getattr(settings, 'SMTP_PASSWORD', None),
        )

    async def notify_analysis_complete(
        self,
        analysis_id: str,
        repo_url: str,
        repo_health_total: int,
        tech_debt_total: int,
        product_level: str,
        security_score: int,
        hours_estimate: float,
    ) -> Dict[str, bool]:
        """
        Send notifications when analysis completes.

        Returns dict with status for each notification channel.
        """
        results = {}

        # Build message
        status_emoji = self._get_status_emoji(repo_health_total, security_score)

        message = self._build_analysis_message(
            analysis_id=analysis_id,
            repo_url=repo_url,
            repo_health_total=repo_health_total,
            tech_debt_total=tech_debt_total,
            product_level=product_level,
            security_score=security_score,
            hours_estimate=hours_estimate,
            status_emoji=status_emoji,
        )

        # Send Slack notification
        if self.config.slack_webhook_url:
            results['slack'] = await self._send_slack(message)

        # Send Email notification
        if self.config.email_enabled and self.config.email_recipients:
            subject = f"{status_emoji} Repo Audit Complete: {self._extract_repo_name(repo_url)}"
            results['email'] = await self._send_email(subject, message)

        return results

    async def notify_security_alert(
        self,
        analysis_id: str,
        repo_url: str,
        critical_count: int,
        high_count: int,
        vulnerabilities: int,
        has_secrets: bool,
    ) -> Dict[str, bool]:
        """Send urgent security alert."""
        results = {}

        message = self._build_security_alert(
            analysis_id=analysis_id,
            repo_url=repo_url,
            critical_count=critical_count,
            high_count=high_count,
            vulnerabilities=vulnerabilities,
            has_secrets=has_secrets,
        )

        # Send Slack with @channel mention for urgency
        if self.config.slack_webhook_url:
            results['slack'] = await self._send_slack(message, urgent=True)

        # Send Email
        if self.config.email_enabled and self.config.email_recipients:
            subject = f"SECURITY ALERT: {self._extract_repo_name(repo_url)}"
            results['email'] = await self._send_email(subject, message, priority=True)

        return results

    def _build_analysis_message(
        self,
        analysis_id: str,
        repo_url: str,
        repo_health_total: int,
        tech_debt_total: int,
        product_level: str,
        security_score: int,
        hours_estimate: float,
        status_emoji: str,
    ) -> str:
        """Build analysis complete message."""
        repo_name = self._extract_repo_name(repo_url)

        # Determine UI URL if available
        ui_url = getattr(settings, 'UI_URL', 'https://ui-three-rho.vercel.app')
        analysis_link = f"{ui_url}/analysis/{analysis_id}"

        return f"""
{status_emoji} *Repository Audit Complete*

*Repository:* `{repo_name}`
*URL:* {repo_url}

*Results:*
- Repo Health: {repo_health_total}/12
- Tech Debt: {tech_debt_total}/15
- Security: {security_score}/3 {'(Critical issues!)' if security_score == 0 else ''}
- Product Level: {product_level}
- Estimated Hours: ~{hours_estimate:.0f}h

<{analysis_link}|View Full Analysis>
"""

    def _build_security_alert(
        self,
        analysis_id: str,
        repo_url: str,
        critical_count: int,
        high_count: int,
        vulnerabilities: int,
        has_secrets: bool,
    ) -> str:
        """Build security alert message."""
        repo_name = self._extract_repo_name(repo_url)

        issues = []
        if critical_count > 0:
            issues.append(f"- {critical_count} CRITICAL severity issues")
        if high_count > 0:
            issues.append(f"- {high_count} HIGH severity issues")
        if vulnerabilities > 0:
            issues.append(f"- {vulnerabilities} dependency vulnerabilities")
        if has_secrets:
            issues.append(f"- Potential secrets/credentials in code")

        ui_url = getattr(settings, 'UI_URL', 'https://ui-three-rho.vercel.app')
        analysis_link = f"{ui_url}/analysis/{analysis_id}"

        return f"""
:rotating_light: *SECURITY ALERT* :rotating_light:

*Repository:* `{repo_name}`

*Issues Found:*
{chr(10).join(issues)}

*Immediate Action Required:*
1. Review the security findings
2. Fix critical issues before deployment
3. Rotate any exposed credentials

<{analysis_link}|View Security Details>
"""

    async def _send_slack(self, message: str, urgent: bool = False) -> bool:
        """Send message to Slack webhook."""
        if not self.config.slack_webhook_url:
            return False

        try:
            payload = {
                "text": message,
                "unfurl_links": False,
            }

            if self.config.slack_channel:
                payload["channel"] = self.config.slack_channel

            if urgent:
                payload["text"] = f"<!channel>\n{message}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.slack_webhook_url,
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.warning(f"Slack notification failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return False

    async def _send_email(
        self,
        subject: str,
        body: str,
        priority: bool = False,
    ) -> bool:
        """Send email notification."""
        if not self.config.smtp_user or not self.config.smtp_password:
            logger.warning("Email not configured (missing SMTP credentials)")
            return False

        if not self.config.email_recipients:
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.smtp_user
            msg['To'] = ', '.join(self.config.email_recipients)

            if priority:
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'

            # Convert Slack-style formatting to plain text and HTML
            plain_body = body.replace('*', '').replace('`', '').replace('<', '').replace('>', '').replace('|', ': ')
            html_body = self._slack_to_html(body)

            msg.attach(MIMEText(plain_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(
                    self.config.smtp_user,
                    self.config.email_recipients,
                    msg.as_string()
                )

            logger.info(f"Email sent to {len(self.config.email_recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False

    def _slack_to_html(self, text: str) -> str:
        """Convert Slack markdown to HTML."""
        import re

        html = text
        # Bold: *text* -> <strong>text</strong>
        html = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', html)
        # Code: `text` -> <code>text</code>
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        # Links: <url|text> -> <a href="url">text</a>
        html = re.sub(r'<([^|>]+)\|([^>]+)>', r'<a href="\1">\2</a>', html)
        # Newlines
        html = html.replace('\n', '<br>')

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
        {html}
        </body>
        </html>
        """

    def _get_status_emoji(self, repo_health: int, security_score: int) -> str:
        """Get status emoji based on scores."""
        if security_score == 0:
            return ":rotating_light:"
        elif security_score == 1 or repo_health < 6:
            return ":warning:"
        elif repo_health >= 10 and security_score >= 2:
            return ":white_check_mark:"
        else:
            return ":mag:"

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL."""
        try:
            return url.rstrip('/').split('/')[-1].replace('.git', '')
        except:
            return url


# Singleton instance
notification_service = NotificationService()
