"""
Semgrep adapter module.

Runs Semgrep static analysis and parses results.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SemgrepError(Exception):
    """Error running Semgrep."""
    pass


class SemgrepAdapter:
    """Adapter for running Semgrep analysis."""

    def __init__(self, rules_dir: Optional[Path] = None):
        self.rules_dir = rules_dir or settings.SEMGREP_RULES_DIR
        self.enabled = settings.SEMGREP_ENABLED

    async def scan(self, local_path: Path) -> List[Dict[str, Any]]:
        """
        Run Semgrep scan on repository.

        Args:
            local_path: Path to repository

        Returns:
            List of findings, each containing:
                - path: str
                - line: int
                - rule_id: str
                - severity: str (ERROR, WARNING, INFO)
                - category: str (security, correctness, performance, etc.)
                - message: str
        """
        if not self.enabled:
            logger.info("Semgrep is disabled")
            return []

        logger.info(f"Running Semgrep scan on {local_path}")

        try:
            # Build command
            cmd = [
                "semgrep",
                "--json",
                "--config", "auto",  # Use auto config (p/default)
            ]

            # Add custom rules if available
            if self.rules_dir.exists():
                cmd.extend(["--config", str(self.rules_dir)])

            cmd.append(str(local_path))

            # Run Semgrep
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse output
            if result.returncode not in [0, 1]:  # 1 = findings found
                logger.warning(f"Semgrep returned {result.returncode}: {result.stderr}")

            findings = self._parse_output(result.stdout)
            logger.info(f"Semgrep found {len(findings)} issues")
            return findings

        except subprocess.TimeoutExpired:
            logger.error("Semgrep scan timed out")
            return []
        except FileNotFoundError:
            logger.error("Semgrep not found. Please install: pip install semgrep")
            return []
        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
            return []

    def _parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse Semgrep JSON output."""
        findings = []

        try:
            data = json.loads(output)
            results = data.get("results", [])

            for r in results:
                finding = {
                    "path": r.get("path", ""),
                    "line": r.get("start", {}).get("line", 0),
                    "rule_id": r.get("check_id", ""),
                    "severity": self._map_severity(r.get("extra", {}).get("severity", "INFO")),
                    "category": self._extract_category(r.get("check_id", "")),
                    "message": r.get("extra", {}).get("message", ""),
                }
                findings.append(finding)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Semgrep output: {e}")

        return findings

    def _map_severity(self, severity: str) -> str:
        """Map Semgrep severity to standard levels."""
        mapping = {
            "ERROR": "ERROR",
            "WARNING": "WARNING",
            "INFO": "INFO",
        }
        return mapping.get(severity.upper(), "INFO")

    def _extract_category(self, rule_id: str) -> str:
        """Extract category from rule ID."""
        # Semgrep rule IDs often look like: python.lang.security.audit.eval-detected
        parts = rule_id.lower().split(".")

        categories = ["security", "correctness", "performance", "style", "best-practice"]
        for cat in categories:
            if cat in parts:
                return cat

        # Default to security for audit rules
        if "audit" in parts or "security" in parts:
            return "security"

        return "other"


# Singleton instance
semgrep_adapter = SemgrepAdapter()
