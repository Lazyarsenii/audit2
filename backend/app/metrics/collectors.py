"""
Metrics Collectors — Datadog-style agents for gathering repository metrics.

Each collector is responsible for:
1. Gathering raw data from a specific source
2. Converting to standardized Metric format
3. Adding to MetricSet

Collectors:
- StructureCollector: README, docs, directory structure
- GitCollector: Commit history, authors, activity
- StaticCollector: LOC, files, complexity
- SecurityCollector: Semgrep findings, secrets detection
- DepsCollector: Dependencies analysis
- CICollector: CI/CD configuration
"""
import asyncio
import logging
import shlex
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import re

from .schema import (
    MetricSet,
    MetricSource,
    MetricCategory,
    MetricLabel,
    MetricNames,
)

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for all metric collectors."""

    source: MetricSource = MetricSource.MANUAL

    @abstractmethod
    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        """Collect metrics and add to MetricSet."""

    def _run_command(self, cmd: str, cwd: Path = None, use_shell: bool = False) -> str:
        """Run command and return output.

        Args:
            cmd: Command string to execute
            cwd: Working directory for the command
            use_shell: If True, run through shell (needed for pipes/redirects).
                      If False (default), use shlex.split for safer execution.
        """
        try:
            if use_shell:
                # Only use shell=True when absolutely needed (pipes, redirects)
                result = subprocess.run(
                    cmd,
                    shell=True,  # nosec B602 - required for shell features
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=60,
                    check=False,
                )
            else:
                # Safer execution without shell
                args = shlex.split(cmd)
                result = subprocess.run(
                    args,
                    shell=False,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=60,
                    check=False,
                )
            return result.stdout.strip()
        except Exception as e:
            logger.warning("Command failed: %s - %s", cmd, e)
            return ""


class StructureCollector(BaseCollector):
    """
    Collects repository structure metrics.

    Metrics collected:
    - Documentation: README, docs folder, architecture docs
    - Structure: directory organization
    - Runability: deps files, Docker, Makefile
    """

    source = MetricSource.STRUCTURE

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[StructureCollector] Scanning {repo_path}")

        # Documentation metrics
        await self._collect_docs_metrics(repo_path, metrics)

        # Structure metrics
        await self._collect_structure_metrics(repo_path, metrics)

        # Runability metrics
        await self._collect_runability_metrics(repo_path, metrics)

    async def _collect_docs_metrics(self, repo_path: Path, metrics: MetricSet) -> None:
        """Collect documentation-related metrics."""

        # README
        readme_path = repo_path / "README.md"
        has_readme = readme_path.exists()
        metrics.add_info(
            MetricNames.HAS_README,
            has_readme,
            self.source,
            MetricCategory.DOCUMENTATION,
            description="Repository has README.md",
        )

        if has_readme:
            readme_content = readme_path.read_text(errors="ignore").lower()
            readme_size = len(readme_content)

            metrics.add_gauge(
                MetricNames.README_SIZE,
                readme_size,
                self.source,
                MetricCategory.DOCUMENTATION,
                unit="bytes",
            )

            metrics.add_info(
                MetricNames.README_HAS_USAGE,
                "usage" in readme_content or "getting started" in readme_content or "quick start" in readme_content,
                self.source,
                MetricCategory.DOCUMENTATION,
            )

            metrics.add_info(
                MetricNames.README_HAS_INSTALL,
                "install" in readme_content or "setup" in readme_content or "requirements" in readme_content,
                self.source,
                MetricCategory.DOCUMENTATION,
            )

        # Docs folder
        docs_path = repo_path / "docs"
        has_docs = docs_path.is_dir()
        metrics.add_info(
            MetricNames.HAS_DOCS_FOLDER,
            has_docs,
            self.source,
            MetricCategory.DOCUMENTATION,
        )

        if has_docs:
            docs_files = list(docs_path.rglob("*.md"))
            metrics.add_gauge(
                MetricNames.DOCS_FILES_COUNT,
                len(docs_files),
                self.source,
                MetricCategory.DOCUMENTATION,
                unit="files",
            )

        # Architecture docs
        has_arch = any([
            (repo_path / "docs" / "ARCHITECTURE.md").exists(),
            (repo_path / "ARCHITECTURE.md").exists(),
            (repo_path / "docs" / "architecture.md").exists(),
            (repo_path / "doc" / "ARCHITECTURE.md").exists(),
        ])
        metrics.add_info(
            MetricNames.HAS_ARCHITECTURE_DOCS,
            has_arch,
            self.source,
            MetricCategory.DOCUMENTATION,
        )

        # API docs
        has_api = any([
            (repo_path / "docs" / "API.md").exists(),
            (repo_path / "docs" / "API_REFERENCE.md").exists(),
            (repo_path / "docs" / "api").is_dir(),
        ])
        metrics.add_info(
            MetricNames.HAS_API_DOCS,
            has_api,
            self.source,
            MetricCategory.DOCUMENTATION,
        )

        # Changelog
        has_changelog = any([
            (repo_path / "CHANGELOG.md").exists(),
            (repo_path / "CHANGES.md").exists(),
            (repo_path / "HISTORY.md").exists(),
        ])
        metrics.add_info(
            MetricNames.HAS_CHANGELOG,
            has_changelog,
            self.source,
            MetricCategory.DOCUMENTATION,
        )

    async def _collect_structure_metrics(self, repo_path: Path, metrics: MetricSet) -> None:
        """Collect project structure metrics."""

        dirs = {d.name.lower() for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith('.')}

        # Standard directories
        metrics.add_info(
            MetricNames.HAS_SRC_DIR,
            bool(dirs & {"src", "app", "lib", "source"}),
            self.source,
            MetricCategory.STRUCTURE,
        )

        metrics.add_info(
            MetricNames.HAS_TESTS_DIR,
            bool(dirs & {"tests", "test", "spec", "specs"}),
            self.source,
            MetricCategory.STRUCTURE,
        )

        metrics.add_info(
            MetricNames.HAS_DOCS_DIR,
            bool(dirs & {"docs", "doc", "documentation"}),
            self.source,
            MetricCategory.STRUCTURE,
        )

        metrics.add_info(
            MetricNames.HAS_CONFIG_DIR,
            bool(dirs & {"config", "conf", "configuration", "settings"}),
            self.source,
            MetricCategory.STRUCTURE,
        )

        # Calculate structure score based on found patterns
        score = 0
        if dirs & {"src", "app", "lib"}:
            score += 1
        if dirs & {"tests", "test"}:
            score += 1
        if dirs & {"docs", "doc"}:
            score += 1

        metrics.add_gauge(
            MetricNames.STRUCTURE_SCORE,
            min(score, 3),
            self.source,
            MetricCategory.STRUCTURE,
            description="Structure organization score (0-3)",
        )

    async def _collect_runability_metrics(self, repo_path: Path, metrics: MetricSet) -> None:
        """Collect runability-related metrics."""

        # Dependency files
        deps_files = {
            "requirements.txt": "pip",
            "pyproject.toml": "pip",
            "setup.py": "pip",
            "Pipfile": "pipenv",
            "package.json": "npm",
            "yarn.lock": "yarn",
            "go.mod": "go",
            "Cargo.toml": "cargo",
            "pom.xml": "maven",
            "build.gradle": "gradle",
        }

        found_deps = []
        for filename, manager in deps_files.items():
            if (repo_path / filename).exists():
                found_deps.append((filename, manager))

        metrics.add_info(
            MetricNames.HAS_DEPS_FILE,
            len(found_deps) > 0,
            self.source,
            MetricCategory.RUNABILITY,
        )

        if found_deps:
            metrics.add_info(
                MetricNames.DEPS_FILE_TYPE,
                found_deps[0][1],  # Primary package manager
                self.source,
                MetricCategory.RUNABILITY,
            )

        # Docker
        metrics.add_info(
            MetricNames.HAS_DOCKERFILE,
            (repo_path / "Dockerfile").exists(),
            self.source,
            MetricCategory.RUNABILITY,
        )

        metrics.add_info(
            MetricNames.HAS_DOCKER_COMPOSE,
            (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists(),
            self.source,
            MetricCategory.RUNABILITY,
        )

        # Makefile
        metrics.add_info(
            MetricNames.HAS_MAKEFILE,
            (repo_path / "Makefile").exists(),
            self.source,
            MetricCategory.RUNABILITY,
        )

        # Run instructions (check README)
        readme_path = repo_path / "README.md"
        has_run_instructions = False
        if readme_path.exists():
            content = readme_path.read_text(errors="ignore").lower()
            has_run_instructions = any(kw in content for kw in [
                "docker-compose up",
                "make run",
                "npm start",
                "python main",
                "uvicorn",
                "flask run",
            ])

        metrics.add_info(
            MetricNames.HAS_RUN_INSTRUCTIONS,
            has_run_instructions,
            self.source,
            MetricCategory.RUNABILITY,
        )


class GitCollector(BaseCollector):
    """
    Collects Git history metrics.

    Metrics collected:
    - Total commits
    - Recent commits (90 days)
    - Authors count
    - First/last commit dates
    - Active days
    """

    source = MetricSource.GIT

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[GitCollector] Analyzing git history at {repo_path}")

        if not (repo_path / ".git").exists():
            logger.warning(f"No .git directory found at {repo_path}")
            return

        # Total commits
        commits_total = self._run_command("git rev-list --count HEAD", repo_path)
        metrics.add_counter(
            MetricNames.COMMITS_TOTAL,
            int(commits_total) if commits_total.isdigit() else 0,
            self.source,
            MetricCategory.HISTORY,
        )

        # Recent commits (90 days) - requires shell for pipe
        recent = self._run_command("git log --since='90 days ago' --oneline | wc -l", repo_path, use_shell=True)
        metrics.add_counter(
            MetricNames.COMMITS_RECENT,
            int(recent.strip()) if recent.strip().isdigit() else 0,
            self.source,
            MetricCategory.HISTORY,
        )

        # Authors count - requires shell for pipe
        authors_output = self._run_command("git shortlog -sn --all | wc -l", repo_path, use_shell=True)
        metrics.add_gauge(
            MetricNames.AUTHORS_COUNT,
            int(authors_output.strip()) if authors_output.strip().isdigit() else 1,
            self.source,
            MetricCategory.HISTORY,
        )

        # First commit date - requires shell for pipe
        first_commit = self._run_command("git log --reverse --format=%aI | head -1", repo_path, use_shell=True)
        if first_commit:
            metrics.add_info(
                MetricNames.FIRST_COMMIT_DATE,
                first_commit,
                self.source,
                MetricCategory.HISTORY,
            )

        # Last commit date
        last_commit = self._run_command("git log -1 --format=%aI", repo_path)
        if last_commit:
            metrics.add_info(
                MetricNames.LAST_COMMIT_DATE,
                last_commit,
                self.source,
                MetricCategory.HISTORY,
            )

        # Active days (unique days with commits) - requires shell for pipes
        active_days = self._run_command("git log --format=%ad --date=short | sort -u | wc -l", repo_path, use_shell=True)
        metrics.add_gauge(
            MetricNames.ACTIVE_DAYS,
            int(active_days.strip()) if active_days.strip().isdigit() else 0,
            self.source,
            MetricCategory.HISTORY,
            unit="days",
        )


class StaticCollector(BaseCollector):
    """
    Collects static code analysis metrics.

    Metrics collected:
    - LOC (total and by language)
    - File counts
    - Test file counts
    - Max file/function lines
    """

    source = MetricSource.STATIC

    # Excluded directories
    EXCLUDE_DIRS = {"venv", "node_modules", ".git", "__pycache__", ".tox", "dist", "build", "_archive", "vendor"}

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[StaticCollector] Analyzing code at {repo_path}")

        # Collect by language
        languages = {
            "python": ["*.py"],
            "javascript": ["*.js", "*.jsx"],
            "typescript": ["*.ts", "*.tsx"],
            "go": ["*.go"],
            "rust": ["*.rs"],
            "java": ["*.java"],
        }

        total_loc = 0
        total_files = 0

        for lang, patterns in languages.items():
            lang_loc = 0
            lang_files = 0

            for pattern in patterns:
                # Build find command with exclusions - requires shell for glob patterns
                exclude_args = " ".join(f"-not -path '*/{d}/*'" for d in self.EXCLUDE_DIRS)
                cmd = f"find . -name '{pattern}' {exclude_args} -type f"
                files_output = self._run_command(cmd, repo_path, use_shell=True)

                if files_output:
                    files = [f for f in files_output.split('\n') if f]
                    lang_files += len(files)

                    # Count lines - requires shell for pipe and redirect
                    if files:
                        wc_cmd = f"find . -name '{pattern}' {exclude_args} -type f -exec wc -l {{}} + 2>/dev/null | tail -1"
                        wc_output = self._run_command(wc_cmd, repo_path, use_shell=True)
                        if wc_output:
                            try:
                                lang_loc += int(wc_output.split()[0])
                            except (ValueError, IndexError):
                                pass

            if lang_files > 0:
                metrics.add_gauge(
                    f"{MetricNames.LOC_BY_LANGUAGE}",
                    lang_loc,
                    self.source,
                    MetricCategory.SIZE,
                    labels=[MetricLabel("language", lang)],
                    unit="lines",
                )

                metrics.add_gauge(
                    f"{MetricNames.FILES_BY_TYPE}",
                    lang_files,
                    self.source,
                    MetricCategory.SIZE,
                    labels=[MetricLabel("language", lang)],
                    unit="files",
                )

            total_loc += lang_loc
            total_files += lang_files

        metrics.add_gauge(
            MetricNames.LOC_TOTAL,
            total_loc,
            self.source,
            MetricCategory.SIZE,
            unit="lines",
        )

        metrics.add_gauge(
            MetricNames.FILES_TOTAL,
            total_files,
            self.source,
            MetricCategory.SIZE,
            unit="files",
        )

        # Test files - requires shell for pipe and redirect
        exclude_args = " ".join(f"-not -path '*/{d}/*'" for d in self.EXCLUDE_DIRS)
        test_cmd = f"find . -name 'test_*.py' -o -name '*_test.py' -o -name '*.test.js' -o -name '*.spec.ts' {exclude_args} 2>/dev/null | wc -l"
        test_files = self._run_command(test_cmd, repo_path, use_shell=True)
        metrics.add_gauge(
            MetricNames.TEST_FILES_COUNT,
            int(test_files.strip()) if test_files.strip().isdigit() else 0,
            self.source,
            MetricCategory.TESTING,
            unit="files",
        )


class CICollector(BaseCollector):
    """
    Collects CI/CD configuration metrics.

    Metrics collected:
    - CI presence and provider
    - CI configuration details (tests, lint, deploy)
    """

    source = MetricSource.CI

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[CICollector] Analyzing CI/CD config at {repo_path}")

        # GitHub Actions
        gh_workflows = repo_path / ".github" / "workflows"
        has_github_actions = gh_workflows.is_dir()

        # GitLab CI
        has_gitlab = (repo_path / ".gitlab-ci.yml").exists()

        # CircleCI
        has_circle = (repo_path / ".circleci" / "config.yml").exists()

        # Travis
        has_travis = (repo_path / ".travis.yml").exists()

        has_ci = has_github_actions or has_gitlab or has_circle or has_travis
        metrics.add_info(
            MetricNames.HAS_CI,
            has_ci,
            self.source,
            MetricCategory.INFRASTRUCTURE,
        )

        if has_ci:
            # Determine provider
            if has_github_actions:
                provider = "github-actions"
            elif has_gitlab:
                provider = "gitlab-ci"
            elif has_circle:
                provider = "circleci"
            else:
                provider = "travis"

            metrics.add_info(
                MetricNames.CI_PROVIDER,
                provider,
                self.source,
                MetricCategory.INFRASTRUCTURE,
            )

            # Analyze GitHub Actions specifically
            if has_github_actions:
                await self._analyze_github_actions(gh_workflows, metrics)

        # Kubernetes config
        has_k8s = any([
            (repo_path / "k8s").is_dir(),
            (repo_path / "kubernetes").is_dir(),
            (repo_path / "deploy" / "kubernetes").is_dir(),
            (repo_path / "infrastructure" / "kubernetes").is_dir(),
        ])
        metrics.add_info(
            MetricNames.HAS_K8S_CONFIG,
            has_k8s,
            self.source,
            MetricCategory.INFRASTRUCTURE,
        )

    async def _analyze_github_actions(self, workflows_path: Path, metrics: MetricSet) -> None:
        """Analyze GitHub Actions workflows."""
        workflow_files = list(workflows_path.glob("*.yml")) + list(workflows_path.glob("*.yaml"))

        has_tests = False
        has_lint = False
        has_deploy = False

        for wf in workflow_files:
            try:
                content = wf.read_text().lower()
                if any(kw in content for kw in ["pytest", "jest", "test", "unittest", "cargo test"]):
                    has_tests = True
                if any(kw in content for kw in ["lint", "eslint", "ruff", "flake8", "pylint", "mypy"]):
                    has_lint = True
                if any(kw in content for kw in ["deploy", "release", "publish", "push"]):
                    has_deploy = True
            except Exception:
                continue

        metrics.add_info(MetricNames.CI_HAS_TESTS, has_tests, self.source, MetricCategory.INFRASTRUCTURE)
        metrics.add_info(MetricNames.CI_HAS_LINT, has_lint, self.source, MetricCategory.INFRASTRUCTURE)
        metrics.add_info(MetricNames.CI_HAS_DEPLOY, has_deploy, self.source, MetricCategory.INFRASTRUCTURE)


class SecurityCollector(BaseCollector):
    """
    Collects security-related metrics.

    Metrics collected:
    - Dependency vulnerabilities (Safety)
    - Code security issues (Bandit for Python)
    - Secrets detection
    - Semgrep findings (if available)
    """

    source = MetricSource.SEMGREP  # Using SEMGREP as security source

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[SecurityCollector] Scanning security at {repo_path}")

        # Run Safety for dependency vulnerabilities
        await self._collect_safety_vulnerabilities(repo_path, metrics)

        # Run Bandit for Python code security
        await self._collect_bandit_findings(repo_path, metrics)

        # Check for secrets in code
        await self._check_secrets(repo_path, metrics)

        # Run Semgrep if available
        await self._collect_semgrep_findings(repo_path, metrics)

    async def _collect_safety_vulnerabilities(self, repo_path: Path, metrics: MetricSet) -> None:
        """Run Safety to check for known vulnerabilities in dependencies."""
        requirements_file = repo_path / "requirements.txt"

        if not requirements_file.exists():
            metrics.add_gauge(
                MetricNames.DEPS_VULNERABILITIES,
                0,
                self.source,
                MetricCategory.SECURITY,
                description="No requirements.txt found",
            )
            return

        try:
            # Run safety check - requires shell for redirect and ||
            result = self._run_command(
                f"safety check -r {requirements_file} --json 2>/dev/null || true",
                repo_path,
                use_shell=True
            )

            vuln_count = 0
            vuln_details = []

            if result:
                try:
                    import json
                    data = json.loads(result)
                    # Safety JSON format: list of vulnerabilities
                    if isinstance(data, list):
                        vuln_count = len(data)
                        for vuln in data[:10]:  # Limit to first 10
                            if isinstance(vuln, list) and len(vuln) >= 5:
                                vuln_details.append({
                                    "package": vuln[0],
                                    "affected_version": vuln[1],
                                    "installed_version": vuln[2],
                                    "vulnerability": vuln[3][:100],
                                    "cve": vuln[4] if len(vuln) > 4 else None,
                                })
                except (json.JSONDecodeError, TypeError):
                    # Try parsing as text output
                    if "vulnerability" in result.lower():
                        vuln_count = result.lower().count("vulnerability")

            metrics.add_gauge(
                MetricNames.DEPS_VULNERABILITIES,
                vuln_count,
                self.source,
                MetricCategory.SECURITY,
                description=f"Found {vuln_count} dependency vulnerabilities",
            )

            # Store details as info metric
            if vuln_details:
                metrics.add_info(
                    "repo.security.vuln_details",
                    str(vuln_details[:5]),  # First 5 for display
                    self.source,
                    MetricCategory.SECURITY,
                )

        except Exception as e:
            logger.warning(f"Safety scan failed: {e}")
            metrics.add_gauge(
                MetricNames.DEPS_VULNERABILITIES,
                -1,  # -1 indicates scan failed
                self.source,
                MetricCategory.SECURITY,
                description=f"Safety scan failed: {str(e)[:50]}",
            )

    async def _collect_bandit_findings(self, repo_path: Path, metrics: MetricSet) -> None:
        """Run Bandit to check for Python security issues."""
        # Check if there are Python files
        py_files = list(repo_path.rglob("*.py"))
        py_files = [f for f in py_files if "venv" not in str(f) and "node_modules" not in str(f)]

        if not py_files:
            return

        try:
            # Run bandit with JSON output - requires shell for redirect and ||
            result = self._run_command(
                f"bandit -r {repo_path} -f json --exclude '**/venv/**,**/node_modules/**,**/.git/**' 2>/dev/null || true",
                repo_path,
                use_shell=True
            )

            critical = 0
            high = 0
            medium = 0
            low = 0

            if result:
                try:
                    import json
                    data = json.loads(result)
                    results = data.get("results", [])

                    for finding in results:
                        severity = finding.get("issue_severity", "").upper()
                        if severity == "HIGH":
                            high += 1
                        elif severity == "MEDIUM":
                            medium += 1
                        elif severity == "LOW":
                            low += 1

                except (json.JSONDecodeError, TypeError):
                    pass

            # Map bandit findings to semgrep metric names (security category)
            metrics.add_gauge(
                MetricNames.SEMGREP_CRITICAL,
                critical,
                self.source,
                MetricCategory.SECURITY,
                description="Critical security issues (Bandit)",
            )
            metrics.add_gauge(
                MetricNames.SEMGREP_HIGH,
                high,
                self.source,
                MetricCategory.SECURITY,
                description="High severity security issues (Bandit)",
            )
            metrics.add_gauge(
                MetricNames.SEMGREP_MEDIUM,
                medium,
                self.source,
                MetricCategory.SECURITY,
                description="Medium severity security issues (Bandit)",
            )
            metrics.add_gauge(
                MetricNames.SEMGREP_LOW,
                low,
                self.source,
                MetricCategory.SECURITY,
                description="Low severity security issues (Bandit)",
            )

        except Exception as e:
            logger.warning(f"Bandit scan failed: {e}")

    async def _check_secrets(self, repo_path: Path, metrics: MetricSet) -> None:
        """Check for potential secrets in code."""
        secret_patterns = [
            r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][^"\']+["\']',
            r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']',
            r'(?i)PRIVATE[_\s]?KEY',
            r'(?i)AWS_ACCESS_KEY',
            r'(?i)GITHUB_TOKEN',
            r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----',
        ]

        has_secrets = False
        secret_files = []

        try:
            for pattern in secret_patterns:
                # requires shell for pipe and redirect
                result = self._run_command(
                    f"grep -r -l -E '{pattern}' --include='*.py' --include='*.js' --include='*.ts' --include='*.json' --include='*.yml' --include='*.yaml' --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=.git . 2>/dev/null | head -5",
                    repo_path,
                    use_shell=True
                )
                if result:
                    # Filter out common false positives
                    files = [f for f in result.split('\n') if f and '.env.example' not in f and 'test' not in f.lower()]
                    if files:
                        has_secrets = True
                        secret_files.extend(files[:3])

            metrics.add_info(
                MetricNames.HAS_SECRETS_IN_CODE,
                has_secrets,
                self.source,
                MetricCategory.SECURITY,
                description="Potential secrets detected in code" if has_secrets else "No obvious secrets found",
            )

        except Exception as e:
            logger.warning(f"Secrets check failed: {e}")
            metrics.add_info(
                MetricNames.HAS_SECRETS_IN_CODE,
                False,
                self.source,
                MetricCategory.SECURITY,
            )

    async def _collect_semgrep_findings(self, repo_path: Path, metrics: MetricSet) -> None:
        """Run Semgrep for advanced security scanning (if available)."""
        # Check if semgrep is installed
        semgrep_check = self._run_command("which semgrep", repo_path)

        if not semgrep_check:
            logger.info("Semgrep not installed, skipping advanced security scan")
            return

        try:
            # Run semgrep with auto config - requires shell for redirect and ||
            result = self._run_command(
                f"semgrep --config auto --json --quiet {repo_path} 2>/dev/null || true",
                repo_path,
                use_shell=True
            )

            if result:
                import json
                try:
                    data = json.loads(result)
                    findings = data.get("results", [])

                    # Override bandit findings with semgrep if available
                    critical = sum(1 for f in findings if f.get("extra", {}).get("severity", "").upper() == "ERROR")
                    high = sum(1 for f in findings if f.get("extra", {}).get("severity", "").upper() == "WARNING")
                    medium = sum(1 for f in findings if f.get("extra", {}).get("severity", "").upper() == "INFO")

                    if findings:  # Only update if semgrep found something
                        metrics.add_gauge(MetricNames.SEMGREP_CRITICAL, critical, self.source, MetricCategory.SECURITY)
                        metrics.add_gauge(MetricNames.SEMGREP_HIGH, high, self.source, MetricCategory.SECURITY)
                        metrics.add_gauge(MetricNames.SEMGREP_MEDIUM, medium, self.source, MetricCategory.SECURITY)

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.warning(f"Semgrep scan failed: {e}")


class CoverageCollector(BaseCollector):
    """
    Collects test coverage metrics from coverage reports.

    Supports:
    - coverage.xml (pytest-cov, coverage.py)
    - cobertura.xml (generic Cobertura format)
    - lcov.info (LCOV format, common in JS/TS)
    - clover.xml (PHP)
    """

    source = MetricSource.COVERAGE

    # Common coverage file locations
    COVERAGE_FILES = [
        "coverage.xml",
        "cobertura.xml",
        "coverage/cobertura.xml",
        "coverage/coverage.xml",
        "reports/coverage.xml",
        "target/site/cobertura/coverage.xml",  # Maven
        "htmlcov/coverage.xml",
        ".coverage.xml",
    ]

    LCOV_FILES = [
        "lcov.info",
        "coverage/lcov.info",
        "coverage/lcov-report/lcov.info",
        ".nyc_output/lcov.info",
    ]

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[CoverageCollector] Searching for coverage reports at {repo_path}")

        coverage_pct = None
        source_file = None

        # Try XML coverage files (Cobertura format)
        for coverage_file in self.COVERAGE_FILES:
            coverage_path = repo_path / coverage_file
            if coverage_path.exists():
                coverage_pct = await self._parse_cobertura_xml(coverage_path)
                if coverage_pct is not None:
                    source_file = coverage_file
                    break

        # Try LCOV files if no XML found
        if coverage_pct is None:
            for lcov_file in self.LCOV_FILES:
                lcov_path = repo_path / lcov_file
                if lcov_path.exists():
                    coverage_pct = await self._parse_lcov(lcov_path)
                    if coverage_pct is not None:
                        source_file = lcov_file
                        break

        # Try to find coverage in CI artifacts
        if coverage_pct is None:
            coverage_pct = await self._extract_from_ci(repo_path)

        if coverage_pct is not None:
            metrics.add_gauge(
                MetricNames.TEST_COVERAGE,
                round(coverage_pct, 1),
                self.source,
                MetricCategory.TESTING,
                unit="percent",
                description=f"Test coverage from {source_file or 'CI'}" if source_file else "Test coverage percentage",
            )

            # Add info about coverage source
            if source_file:
                metrics.add_info(
                    "repo.testing.coverage_source",
                    source_file,
                    self.source,
                    MetricCategory.TESTING,
                )

            logger.info(f"  Found coverage: {coverage_pct:.1f}% from {source_file or 'CI'}")
        else:
            logger.info("  No coverage reports found")

    async def _parse_cobertura_xml(self, path: Path) -> Optional[float]:
        """Parse Cobertura/coverage.py XML format."""
        try:
            import defusedxml.ElementTree as ET

            tree = ET.parse(path)
            root = tree.getroot()

            # Try different XML structures
            # Standard Cobertura format
            if root.tag == "coverage":
                line_rate = root.get("line-rate")
                if line_rate:
                    return float(line_rate) * 100

                # Alternative: look for lines-covered and lines-valid
                lines_covered = root.get("lines-covered")
                lines_valid = root.get("lines-valid")
                if lines_covered and lines_valid and int(lines_valid) > 0:
                    return (int(lines_covered) / int(lines_valid)) * 100

            # Some formats nest under <report>
            report = root.find(".//report") or root
            coverage_elem = report.find(".//coverage")
            if coverage_elem is not None:
                line_rate = coverage_elem.get("line-rate")
                if line_rate:
                    return float(line_rate) * 100

            # Try summing packages
            packages = root.findall(".//package")
            if packages:
                total_lines = 0
                covered_lines = 0
                for pkg in packages:
                    for cls in pkg.findall(".//class"):
                        for line in cls.findall(".//line"):
                            total_lines += 1
                            if int(line.get("hits", 0)) > 0:
                                covered_lines += 1
                if total_lines > 0:
                    return (covered_lines / total_lines) * 100

        except Exception as e:
            logger.warning(f"Failed to parse coverage XML {path}: {e}")

        return None

    async def _parse_lcov(self, path: Path) -> Optional[float]:
        """Parse LCOV format coverage report."""
        try:
            content = path.read_text(errors="ignore")

            lines_found = 0
            lines_hit = 0

            for line in content.split('\n'):
                if line.startswith('LF:'):  # Lines Found
                    lines_found += int(line[3:])
                elif line.startswith('LH:'):  # Lines Hit
                    lines_hit += int(line[3:])

            if lines_found > 0:
                return (lines_hit / lines_found) * 100

        except Exception as e:
            logger.warning(f"Failed to parse LCOV {path}: {e}")

        return None

    async def _extract_from_ci(self, repo_path: Path) -> Optional[float]:
        """Try to extract coverage from CI configuration or badges."""
        # Check README for coverage badge
        readme_path = repo_path / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text(errors="ignore")

                # Look for coverage badge patterns
                # Codecov: ![codecov](https://codecov.io/gh/org/repo/branch/main/graph/badge.svg)
                # Coveralls: [![Coverage Status](...coveralls.io...)]
                # Generic: coverage-XX%

                import re

                # Pattern for coverage percentage in badges
                patterns = [
                    r'coverage[^\d]*(\d+(?:\.\d+)?)\s*%',
                    r'(\d+(?:\.\d+)?)\s*%\s*coverage',
                    r'badge[^\d]*coverage[^\d]*(\d+(?:\.\d+)?)',
                ]

                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return float(match.group(1))

            except Exception:
                pass

        return None


class MetricsAggregator:
    """
    Main aggregator that runs all collectors.

    Usage:
        aggregator = MetricsAggregator()
        metrics = await aggregator.collect_all(repo_path, analysis_id, repo_url)
    """

    def __init__(self, extended: bool = True):
        """
        Initialize aggregator.

        Args:
            extended: If True, include extended collectors (dependencies, duplication,
                     licenses, dead code, git analytics, docker, complexity).
        """
        self.collectors: List[BaseCollector] = [
            StructureCollector(),
            GitCollector(),
            StaticCollector(),
            CICollector(),
            SecurityCollector(),  # Security scanning
            CoverageCollector(),  # Test coverage parsing
        ]

        # Add extended collectors if enabled
        if extended:
            try:
                from .collectors_extended import EXTENDED_COLLECTORS
                for collector_cls in EXTENDED_COLLECTORS:
                    self.collectors.append(collector_cls())
                logger.info(f"Loaded {len(EXTENDED_COLLECTORS)} extended collectors")
            except ImportError as e:
                logger.warning(f"Extended collectors not available: {e}")

    async def collect_all(
        self,
        repo_path: Path,
        analysis_id: str,
        repo_url: str,
        branch: Optional[str] = None,
    ) -> MetricSet:
        """
        Run all collectors and return unified MetricSet.
        """
        metrics = MetricSet(
            analysis_id=analysis_id,
            repo_url=repo_url,
            branch=branch,
            collected_at=datetime.now(timezone.utc),
            metadata={
                "collectors": [c.__class__.__name__ for c in self.collectors],
            },
        )

        # Run collectors in parallel
        tasks = [
            collector.collect(repo_path, metrics)
            for collector in self.collectors
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Collected {len(metrics.metrics)} metrics from {len(self.collectors)} collectors")
        return metrics


# Singleton instance
metrics_aggregator = MetricsAggregator()
