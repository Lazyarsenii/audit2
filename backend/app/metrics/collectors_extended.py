"""
Extended Metrics Collectors - Advanced code analysis.

Additional collectors for:
- Dependency analysis (outdated, tree)
- Code duplication (jscpd)
- License compliance
- Dead code detection (vulture)
- Git analytics (bus factor, hotspots)
- Docker best practices (hadolint)
"""
import asyncio
import json
import logging
import shlex
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .schema import (
    MetricSet,
    MetricSource,
    MetricCategory,
    MetricLabel,
    MetricNames,
)

logger = logging.getLogger(__name__)


class BaseCollector:
    """Base class for collectors."""
    source: MetricSource = MetricSource.STATIC

    def _run_command(self, cmd: str, cwd: Path = None, timeout: int = 60, use_shell: bool = False) -> str:
        """Run command and return output.

        Args:
            cmd: Command string to execute
            cwd: Working directory for the command
            timeout: Command timeout in seconds
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
                    timeout=timeout,
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
                    timeout=timeout,
                    check=False,
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out: %s", cmd)
            return ""
        except Exception as e:
            logger.warning("Command failed: %s - %s", cmd, e)
            return ""


class DependencyAnalyzer(BaseCollector):
    """
    Analyzes project dependencies.

    Metrics:
    - Total dependencies count
    - Outdated dependencies
    - Dependency depth
    - Direct vs transitive deps
    """

    source = MetricSource.DEPS

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[DependencyAnalyzer] Analyzing dependencies at {repo_path}")

        # Check for Python dependencies
        if (repo_path / "requirements.txt").exists():
            await self._analyze_python_deps(repo_path, metrics)

        # Check for Node.js dependencies
        if (repo_path / "package.json").exists():
            await self._analyze_node_deps(repo_path, metrics)

    async def _analyze_python_deps(self, repo_path: Path, metrics: MetricSet) -> None:
        """Analyze Python dependencies."""
        req_file = repo_path / "requirements.txt"

        try:
            content = req_file.read_text()
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#')]

            # Count direct dependencies
            direct_deps = len([l for l in lines if not l.startswith('-')])

            metrics.add_gauge(
                "repo.deps.python.direct",
                direct_deps,
                self.source,
                MetricCategory.DEPENDENCIES,
                unit="packages",
            )

            # Try to get outdated packages using pip - requires shell for redirect and ||
            outdated_output = self._run_command(
                "pip list --outdated --format=json 2>/dev/null || echo '[]'",
                repo_path,
                use_shell=True
            )

            try:
                outdated = json.loads(outdated_output) if outdated_output else []
                outdated_count = len(outdated)

                metrics.add_gauge(
                    "repo.deps.python.outdated",
                    outdated_count,
                    self.source,
                    MetricCategory.DEPENDENCIES,
                    unit="packages",
                    description=f"{outdated_count} packages have newer versions",
                )

                # Store outdated packages info
                if outdated:
                    outdated_info = [
                        f"{p['name']}: {p.get('version', '?')} -> {p.get('latest_version', '?')}"
                        for p in outdated[:10]
                    ]
                    metrics.add_info(
                        "repo.deps.python.outdated_list",
                        str(outdated_info),
                        self.source,
                        MetricCategory.DEPENDENCIES,
                    )

            except json.JSONDecodeError:
                pass

            # Try pipdeptree for dependency tree depth - requires shell for redirect and ||
            tree_output = self._run_command(
                "pipdeptree --json 2>/dev/null || echo '[]'",
                repo_path,
                use_shell=True
            )

            if tree_output and tree_output != '[]':
                try:
                    tree = json.loads(tree_output)
                    max_depth = self._calculate_tree_depth(tree)

                    metrics.add_gauge(
                        "repo.deps.python.max_depth",
                        max_depth,
                        self.source,
                        MetricCategory.DEPENDENCIES,
                        description="Maximum dependency tree depth",
                    )
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.warning(f"Python dependency analysis failed: {e}")

    async def _analyze_node_deps(self, repo_path: Path, metrics: MetricSet) -> None:
        """Analyze Node.js dependencies."""
        pkg_file = repo_path / "package.json"

        try:
            content = json.loads(pkg_file.read_text())

            deps = content.get("dependencies", {})
            dev_deps = content.get("devDependencies", {})

            metrics.add_gauge(
                "repo.deps.node.direct",
                len(deps),
                self.source,
                MetricCategory.DEPENDENCIES,
                unit="packages",
            )

            metrics.add_gauge(
                "repo.deps.node.dev",
                len(dev_deps),
                self.source,
                MetricCategory.DEPENDENCIES,
                unit="packages",
            )

            # Check for outdated using npm - requires shell for redirect and ||
            outdated_output = self._run_command(
                "npm outdated --json 2>/dev/null || echo '{}'",
                repo_path,
                timeout=120,
                use_shell=True
            )

            try:
                outdated = json.loads(outdated_output) if outdated_output else {}
                outdated_count = len(outdated)

                metrics.add_gauge(
                    "repo.deps.node.outdated",
                    outdated_count,
                    self.source,
                    MetricCategory.DEPENDENCIES,
                    unit="packages",
                )
            except json.JSONDecodeError:
                pass

        except Exception as e:
            logger.warning(f"Node.js dependency analysis failed: {e}")

    def _calculate_tree_depth(self, tree: list, depth: int = 0) -> int:
        """Calculate maximum depth of dependency tree."""
        if not tree:
            return depth

        max_depth = depth
        for pkg in tree:
            if isinstance(pkg, dict) and "dependencies" in pkg:
                child_depth = self._calculate_tree_depth(pkg["dependencies"], depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth


class CodeDuplicationAnalyzer(BaseCollector):
    """
    Detects code duplication using jscpd.

    Metrics:
    - Duplication percentage
    - Number of clones
    - Lines duplicated
    """

    source = MetricSource.STATIC

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[CodeDuplicationAnalyzer] Checking duplication at {repo_path}")

        # Check if jscpd is available - requires shell for || and redirect
        jscpd_check = self._run_command("which jscpd || npx jscpd --version 2>/dev/null", use_shell=True)

        if not jscpd_check:
            # Fall back to simple duplication check
            await self._simple_duplication_check(repo_path, metrics)
            return

        try:
            # Run jscpd with JSON output - requires shell for redirect
            result = self._run_command(
                f"npx jscpd {repo_path} --reporters json --output /tmp/jscpd-report --ignore '**/node_modules/**,**/venv/**,**/.git/**' 2>/dev/null",
                repo_path,
                timeout=180,
                use_shell=True
            )

            # Read the JSON report
            report_file = Path("/tmp/jscpd-report/jscpd-report.json")
            if report_file.exists():
                report = json.loads(report_file.read_text())

                statistics = report.get("statistics", {})
                total = statistics.get("total", {})

                duplication_pct = total.get("percentage", 0)
                duplicated_lines = total.get("duplicatedLines", 0)
                clones_count = len(report.get("duplicates", []))

                metrics.add_gauge(
                    "repo.quality.duplication_pct",
                    round(duplication_pct, 2),
                    self.source,
                    MetricCategory.CODE_QUALITY,
                    unit="percent",
                )

                metrics.add_gauge(
                    "repo.quality.duplicated_lines",
                    duplicated_lines,
                    self.source,
                    MetricCategory.CODE_QUALITY,
                    unit="lines",
                )

                metrics.add_gauge(
                    "repo.quality.clone_count",
                    clones_count,
                    self.source,
                    MetricCategory.CODE_QUALITY,
                )

                logger.info(f"  Duplication: {duplication_pct:.1f}%, {clones_count} clones")

        except Exception as e:
            logger.warning(f"jscpd analysis failed: {e}")
            await self._simple_duplication_check(repo_path, metrics)

    async def _simple_duplication_check(self, repo_path: Path, metrics: MetricSet) -> None:
        """Simple duplication estimation without jscpd."""
        # Count lines and estimate duplication based on file similarity
        try:
            file_hashes = {}
            total_lines = 0
            duplicate_lines = 0

            for ext in ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx']:
                for f in repo_path.rglob(ext):
                    if 'node_modules' in str(f) or 'venv' in str(f) or '.git' in str(f):
                        continue
                    try:
                        content = f.read_text(errors='ignore')
                        lines = len(content.split('\n'))
                        total_lines += lines

                        # Simple hash of normalized content
                        normalized = ''.join(content.split())
                        if normalized in file_hashes:
                            duplicate_lines += lines
                        else:
                            file_hashes[normalized] = f
                    except:
                        pass

            if total_lines > 0:
                duplication_pct = (duplicate_lines / total_lines) * 100
                metrics.add_gauge(
                    "repo.quality.duplication_pct",
                    round(duplication_pct, 2),
                    self.source,
                    MetricCategory.CODE_QUALITY,
                    unit="percent",
                    description="Estimated duplication (simple check)",
                )

        except Exception as e:
            logger.warning(f"Simple duplication check failed: {e}")


class LicenseAnalyzer(BaseCollector):
    """
    Analyzes license compliance.

    Metrics:
    - License type detected
    - Dependencies license compatibility
    - Copyleft risk
    """

    source = MetricSource.DEPS

    # License categories
    PERMISSIVE = ['MIT', 'Apache-2.0', 'BSD', 'ISC', 'Unlicense', 'CC0']
    COPYLEFT = ['GPL', 'LGPL', 'AGPL', 'MPL']
    PROBLEMATIC = ['AGPL-3.0', 'GPL-3.0', 'SSPL']

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[LicenseAnalyzer] Checking licenses at {repo_path}")

        # Detect project license
        project_license = await self._detect_project_license(repo_path)
        if project_license:
            metrics.add_info(
                "repo.license.type",
                project_license,
                self.source,
                MetricCategory.DEPENDENCIES,
            )

        # Check Python dependency licenses
        if (repo_path / "requirements.txt").exists():
            await self._check_python_licenses(repo_path, metrics)

        # Check Node.js dependency licenses
        if (repo_path / "package.json").exists():
            await self._check_node_licenses(repo_path, metrics)

    async def _detect_project_license(self, repo_path: Path) -> Optional[str]:
        """Detect project's own license."""
        license_files = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING']

        for lf in license_files:
            license_path = repo_path / lf
            if license_path.exists():
                content = license_path.read_text(errors='ignore').lower()

                if 'mit license' in content or 'permission is hereby granted' in content:
                    return 'MIT'
                elif 'apache license' in content:
                    return 'Apache-2.0'
                elif 'gnu general public license' in content:
                    if 'version 3' in content:
                        return 'GPL-3.0'
                    return 'GPL-2.0'
                elif 'bsd' in content:
                    return 'BSD'
                elif 'isc license' in content:
                    return 'ISC'

        return None

    async def _check_python_licenses(self, repo_path: Path, metrics: MetricSet) -> None:
        """Check Python dependency licenses using pip-licenses."""
        try:
            result = self._run_command(
                "pip-licenses --format=json 2>/dev/null || echo '[]'",
                repo_path,
                use_shell=True
            )

            if result and result != '[]':
                licenses = json.loads(result)

                license_counts = Counter()
                copyleft_packages = []
                problematic_packages = []

                for pkg in licenses:
                    lic = pkg.get('License', 'Unknown')
                    license_counts[lic] += 1

                    if any(cl in lic.upper() for cl in ['GPL', 'LGPL', 'AGPL']):
                        copyleft_packages.append(f"{pkg['Name']} ({lic})")

                    if any(p in lic.upper() for p in ['AGPL', 'SSPL']):
                        problematic_packages.append(f"{pkg['Name']} ({lic})")

                # Metrics
                metrics.add_gauge(
                    "repo.license.unique_count",
                    len(license_counts),
                    self.source,
                    MetricCategory.DEPENDENCIES,
                )

                metrics.add_gauge(
                    "repo.license.copyleft_count",
                    len(copyleft_packages),
                    self.source,
                    MetricCategory.DEPENDENCIES,
                    description="Packages with copyleft licenses",
                )

                metrics.add_gauge(
                    "repo.license.problematic_count",
                    len(problematic_packages),
                    self.source,
                    MetricCategory.DEPENDENCIES,
                    description="Packages with potentially problematic licenses (AGPL, SSPL)",
                )

                if copyleft_packages:
                    metrics.add_info(
                        "repo.license.copyleft_packages",
                        str(copyleft_packages[:10]),
                        self.source,
                        MetricCategory.DEPENDENCIES,
                    )

                logger.info(f"  Found {len(license_counts)} unique licenses, {len(copyleft_packages)} copyleft")

        except Exception as e:
            logger.warning(f"Python license check failed: {e}")

    async def _check_node_licenses(self, repo_path: Path, metrics: MetricSet) -> None:
        """Check Node.js dependency licenses."""
        try:
            result = self._run_command(
                "npx license-checker --json 2>/dev/null || echo '{}'",
                repo_path,
                timeout=120,
                use_shell=True
            )

            if result and result != '{}':
                licenses = json.loads(result)

                license_counts = Counter()
                for pkg, info in licenses.items():
                    lic = info.get('licenses', 'Unknown')
                    if isinstance(lic, list):
                        lic = ', '.join(lic)
                    license_counts[lic] += 1

                metrics.add_gauge(
                    "repo.license.node.unique_count",
                    len(license_counts),
                    self.source,
                    MetricCategory.DEPENDENCIES,
                )

        except Exception as e:
            logger.warning(f"Node.js license check failed: {e}")


class DeadCodeAnalyzer(BaseCollector):
    """
    Detects dead/unused code.

    Uses vulture for Python.

    Metrics:
    - Unused functions count
    - Unused variables count
    - Unused imports count
    """

    source = MetricSource.STATIC

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[DeadCodeAnalyzer] Checking for dead code at {repo_path}")

        # Check for Python files
        py_files = list(repo_path.rglob("*.py"))
        py_files = [f for f in py_files if 'venv' not in str(f) and 'node_modules' not in str(f)]

        if py_files:
            await self._analyze_python_dead_code(repo_path, metrics)

    async def _analyze_python_dead_code(self, repo_path: Path, metrics: MetricSet) -> None:
        """Analyze Python dead code using vulture."""
        try:
            result = self._run_command(
                f"vulture {repo_path} --min-confidence 80 2>/dev/null || true",
                repo_path,
                timeout=120,
                use_shell=True
            )

            if result:
                lines = result.split('\n')

                unused_functions = 0
                unused_variables = 0
                unused_imports = 0
                unused_classes = 0

                for line in lines:
                    if 'unused function' in line.lower():
                        unused_functions += 1
                    elif 'unused variable' in line.lower():
                        unused_variables += 1
                    elif 'unused import' in line.lower():
                        unused_imports += 1
                    elif 'unused class' in line.lower():
                        unused_classes += 1

                total_dead = unused_functions + unused_variables + unused_imports + unused_classes

                metrics.add_gauge(
                    "repo.quality.dead_code.total",
                    total_dead,
                    self.source,
                    MetricCategory.CODE_QUALITY,
                )

                metrics.add_gauge(
                    "repo.quality.dead_code.functions",
                    unused_functions,
                    self.source,
                    MetricCategory.CODE_QUALITY,
                )

                metrics.add_gauge(
                    "repo.quality.dead_code.imports",
                    unused_imports,
                    self.source,
                    MetricCategory.CODE_QUALITY,
                )

                logger.info(f"  Dead code: {total_dead} items ({unused_functions} functions, {unused_imports} imports)")

        except Exception as e:
            logger.warning(f"Vulture analysis failed: {e}")


class GitAnalyticsCollector(BaseCollector):
    """
    Advanced Git analytics.

    Metrics:
    - Bus factor (knowledge distribution)
    - Code hotspots (frequently changed files)
    - Code ownership
    - Churn rate
    """

    source = MetricSource.GIT

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[GitAnalyticsCollector] Analyzing git history at {repo_path}")

        if not (repo_path / ".git").exists():
            logger.warning("No git repository found")
            return

        await self._calculate_bus_factor(repo_path, metrics)
        await self._find_hotspots(repo_path, metrics)
        await self._calculate_churn(repo_path, metrics)

    async def _calculate_bus_factor(self, repo_path: Path, metrics: MetricSet) -> None:
        """
        Calculate bus factor - minimum number of developers that would need to leave
        for the project to lose significant knowledge.
        """
        try:
            # Get contribution by author
            result = self._run_command(
                "git shortlog -sn --all --no-merges",
                repo_path
            )

            if not result:
                return

            contributions = []
            for line in result.split('\n'):
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        commits = int(parts[0].strip())
                        contributions.append(commits)

            if not contributions:
                return

            total_commits = sum(contributions)
            contributions.sort(reverse=True)

            # Calculate bus factor: minimum authors to cover 50% of commits
            cumulative = 0
            bus_factor = 0
            for commits in contributions:
                cumulative += commits
                bus_factor += 1
                if cumulative >= total_commits * 0.5:
                    break

            metrics.add_gauge(
                "repo.git.bus_factor",
                bus_factor,
                self.source,
                MetricCategory.HISTORY,
                description="Minimum developers for 50% of commits",
            )

            # Knowledge concentration (Gini-like coefficient)
            if len(contributions) > 1:
                top_contributor_pct = (contributions[0] / total_commits) * 100
                metrics.add_gauge(
                    "repo.git.top_contributor_pct",
                    round(top_contributor_pct, 1),
                    self.source,
                    MetricCategory.HISTORY,
                    unit="percent",
                )

            logger.info(f"  Bus factor: {bus_factor}, top contributor: {top_contributor_pct:.1f}%")

        except Exception as e:
            logger.warning(f"Bus factor calculation failed: {e}")

    async def _find_hotspots(self, repo_path: Path, metrics: MetricSet) -> None:
        """Find code hotspots - files that change frequently."""
        try:
            # Files changed in last 90 days - requires shell for pipes
            result = self._run_command(
                "git log --since='90 days ago' --name-only --pretty=format: | sort | uniq -c | sort -rn | head -20",
                repo_path,
                use_shell=True
            )

            if not result:
                return

            hotspots = []
            for line in result.split('\n'):
                if line.strip():
                    parts = line.strip().split(None, 1)
                    if len(parts) == 2:
                        count = int(parts[0])
                        filename = parts[1]
                        if filename and not filename.startswith('.'):
                            hotspots.append((filename, count))

            if hotspots:
                # Store top hotspots
                top_hotspots = [f"{f} ({c} changes)" for f, c in hotspots[:5]]
                metrics.add_info(
                    "repo.git.hotspots",
                    str(top_hotspots),
                    self.source,
                    MetricCategory.HISTORY,
                )

                metrics.add_gauge(
                    "repo.git.hotspot_changes",
                    hotspots[0][1] if hotspots else 0,
                    self.source,
                    MetricCategory.HISTORY,
                    description="Changes to most modified file (90 days)",
                )

        except Exception as e:
            logger.warning(f"Hotspot analysis failed: {e}")

    async def _calculate_churn(self, repo_path: Path, metrics: MetricSet) -> None:
        """Calculate code churn (lines added + deleted)."""
        try:
            # Churn in last 30 days - requires shell for pipe and awk
            result = self._run_command(
                "git log --since='30 days ago' --numstat --pretty=format: | awk '{add+=$1; del+=$2} END {print add, del}'",
                repo_path,
                use_shell=True
            )

            if result:
                parts = result.split()
                if len(parts) >= 2:
                    added = int(parts[0]) if parts[0].isdigit() else 0
                    deleted = int(parts[1]) if parts[1].isdigit() else 0
                    churn = added + deleted

                    metrics.add_gauge(
                        "repo.git.churn_30d",
                        churn,
                        self.source,
                        MetricCategory.HISTORY,
                        unit="lines",
                        description="Lines added + deleted in last 30 days",
                    )

                    metrics.add_gauge(
                        "repo.git.lines_added_30d",
                        added,
                        self.source,
                        MetricCategory.HISTORY,
                        unit="lines",
                    )

                    metrics.add_gauge(
                        "repo.git.lines_deleted_30d",
                        deleted,
                        self.source,
                        MetricCategory.HISTORY,
                        unit="lines",
                    )

        except Exception as e:
            logger.warning(f"Churn calculation failed: {e}")


class DockerAnalyzer(BaseCollector):
    """
    Analyzes Docker configuration best practices.

    Uses hadolint for Dockerfile linting.

    Metrics:
    - Dockerfile issues count
    - Security issues
    - Best practice violations
    """

    source = MetricSource.CI

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        dockerfile = repo_path / "Dockerfile"

        if not dockerfile.exists():
            return

        logger.info(f"[DockerAnalyzer] Analyzing Dockerfile at {repo_path}")

        # Try hadolint
        await self._run_hadolint(repo_path, metrics)

        # Basic Dockerfile analysis
        await self._analyze_dockerfile(repo_path, metrics)

    async def _run_hadolint(self, repo_path: Path, metrics: MetricSet) -> None:
        """Run hadolint for Dockerfile best practices."""
        try:
            result = self._run_command(
                f"hadolint --format json {repo_path}/Dockerfile 2>/dev/null || echo '[]'",
                repo_path,
                use_shell=True
            )

            if result and result != '[]':
                issues = json.loads(result)

                error_count = sum(1 for i in issues if i.get('level') == 'error')
                warning_count = sum(1 for i in issues if i.get('level') == 'warning')
                info_count = sum(1 for i in issues if i.get('level') == 'info')

                metrics.add_gauge(
                    "repo.docker.hadolint_errors",
                    error_count,
                    self.source,
                    MetricCategory.INFRASTRUCTURE,
                )

                metrics.add_gauge(
                    "repo.docker.hadolint_warnings",
                    warning_count,
                    self.source,
                    MetricCategory.INFRASTRUCTURE,
                )

                # Store top issues
                if issues:
                    top_issues = [f"{i.get('code')}: {i.get('message', '')[:50]}" for i in issues[:5]]
                    metrics.add_info(
                        "repo.docker.issues",
                        str(top_issues),
                        self.source,
                        MetricCategory.INFRASTRUCTURE,
                    )

                logger.info(f"  Hadolint: {error_count} errors, {warning_count} warnings")

        except Exception as e:
            logger.warning(f"Hadolint analysis failed: {e}")

    async def _analyze_dockerfile(self, repo_path: Path, metrics: MetricSet) -> None:
        """Basic Dockerfile analysis."""
        dockerfile = repo_path / "Dockerfile"

        try:
            content = dockerfile.read_text()
            lines = content.split('\n')

            # Check for best practices
            has_user = any('USER' in l and not l.strip().startswith('#') for l in lines)
            has_healthcheck = any('HEALTHCHECK' in l for l in lines)
            uses_latest = any(':latest' in l for l in lines)
            has_multistage = content.count('FROM ') > 1

            # Calculate score
            score = 0
            if has_user:
                score += 1  # Non-root user
            if has_healthcheck:
                score += 1  # Health check defined
            if not uses_latest:
                score += 1  # Pinned versions
            if has_multistage:
                score += 1  # Multi-stage build

            metrics.add_gauge(
                "repo.docker.best_practices_score",
                score,
                self.source,
                MetricCategory.INFRASTRUCTURE,
                description="Docker best practices (0-4)",
            )

            metrics.add_info(
                "repo.docker.has_nonroot_user",
                has_user,
                self.source,
                MetricCategory.INFRASTRUCTURE,
            )

            metrics.add_info(
                "repo.docker.has_healthcheck",
                has_healthcheck,
                self.source,
                MetricCategory.INFRASTRUCTURE,
            )

            metrics.add_info(
                "repo.docker.uses_latest_tag",
                uses_latest,
                self.source,
                MetricCategory.INFRASTRUCTURE,
            )

            metrics.add_info(
                "repo.docker.multistage_build",
                has_multistage,
                self.source,
                MetricCategory.INFRASTRUCTURE,
            )

        except Exception as e:
            logger.warning(f"Dockerfile analysis failed: {e}")


class ComplexityAnalyzer(BaseCollector):
    """
    Analyzes code complexity using radon/lizard.

    Metrics:
    - Cyclomatic complexity (average, max)
    - Maintainability index
    - Halstead metrics
    """

    source = MetricSource.STATIC

    async def collect(self, repo_path: Path, metrics: MetricSet) -> None:
        logger.info(f"[ComplexityAnalyzer] Analyzing complexity at {repo_path}")

        # Check for Python files
        py_files = list(repo_path.rglob("*.py"))
        py_files = [f for f in py_files if 'venv' not in str(f) and 'node_modules' not in str(f)]

        if py_files:
            await self._analyze_python_complexity(repo_path, metrics)

    async def _analyze_python_complexity(self, repo_path: Path, metrics: MetricSet) -> None:
        """Analyze Python code complexity using radon."""
        try:
            # Cyclomatic complexity - requires shell for redirect and ||
            cc_result = self._run_command(
                f"radon cc {repo_path} -a -j --exclude '**/venv/**' 2>/dev/null || echo '{{}}'",
                repo_path,
                timeout=120,
                use_shell=True
            )

            if cc_result and cc_result != '{}':
                try:
                    data = json.loads(cc_result)

                    all_complexities = []
                    for file_path, functions in data.items():
                        if isinstance(functions, list):
                            for func in functions:
                                if isinstance(func, dict):
                                    all_complexities.append(func.get('complexity', 0))

                    if all_complexities:
                        avg_complexity = sum(all_complexities) / len(all_complexities)
                        max_complexity = max(all_complexities)

                        metrics.add_gauge(
                            "repo.quality.complexity_avg",
                            round(avg_complexity, 2),
                            self.source,
                            MetricCategory.CODE_QUALITY,
                        )

                        metrics.add_gauge(
                            "repo.quality.complexity_max",
                            max_complexity,
                            self.source,
                            MetricCategory.CODE_QUALITY,
                        )

                        # Count high complexity functions (>10)
                        high_complexity = sum(1 for c in all_complexities if c > 10)
                        metrics.add_gauge(
                            "repo.quality.high_complexity_count",
                            high_complexity,
                            self.source,
                            MetricCategory.CODE_QUALITY,
                            description="Functions with complexity > 10",
                        )

                        logger.info(f"  Complexity: avg={avg_complexity:.1f}, max={max_complexity}")

                except json.JSONDecodeError:
                    pass

            # Maintainability index - requires shell for redirect and ||
            mi_result = self._run_command(
                f"radon mi {repo_path} -j --exclude '**/venv/**' 2>/dev/null || echo '{{}}'",
                repo_path,
                timeout=120,
                use_shell=True
            )

            if mi_result and mi_result != '{}':
                try:
                    data = json.loads(mi_result)

                    mi_scores = []
                    for file_path, score in data.items():
                        if isinstance(score, dict):
                            mi_scores.append(score.get('mi', 0))

                    if mi_scores:
                        avg_mi = sum(mi_scores) / len(mi_scores)
                        metrics.add_gauge(
                            "repo.quality.maintainability_index",
                            round(avg_mi, 2),
                            self.source,
                            MetricCategory.CODE_QUALITY,
                            description="Maintainability Index (0-100, higher is better)",
                        )

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.warning(f"Python complexity analysis failed: {e}")


# Export all extended collectors
EXTENDED_COLLECTORS = [
    DependencyAnalyzer,
    CodeDuplicationAnalyzer,
    LicenseAnalyzer,
    DeadCodeAnalyzer,
    GitAnalyticsCollector,
    DockerAnalyzer,
    ComplexityAnalyzer,
]
