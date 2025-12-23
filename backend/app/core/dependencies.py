"""
Dependency Checker - проверка доступности внешних инструментов.

Сервис работает по принципу "Graceful Degradation":
- Базовые функции работают ВСЕГДА (анализ структуры, git, LOC)
- Расширенные функции включаются при наличии инструментов
- При отсутствии инструмента - метрика пропускается, не падает

Уровни зависимостей:
1. CORE (обязательно): Python stdlib, FastAPI, SQLAlchemy, GitPython
2. RECOMMENDED: bandit, safety, radon, vulture
3. OPTIONAL: semgrep, hadolint, jscpd, pipdeptree
4. EXTERNAL: npm, pip (системные)
"""
import shutil
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about an external tool."""
    name: str
    command: str
    description: str
    level: str  # core, recommended, optional
    installed: bool = False
    version: Optional[str] = None


@dataclass
class DependencyReport:
    """Report of all dependencies and their status."""
    tools: Dict[str, ToolInfo] = field(default_factory=dict)
    python_packages: Dict[str, bool] = field(default_factory=dict)

    @property
    def summary(self) -> Dict[str, int]:
        """Get summary counts."""
        installed = sum(1 for t in self.tools.values() if t.installed)
        total = len(self.tools)
        return {
            "tools_installed": installed,
            "tools_total": total,
            "tools_missing": total - installed,
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "summary": self.summary,
            "tools": {
                name: {
                    "installed": t.installed,
                    "description": t.description,
                    "level": t.level,
                    "version": t.version,
                }
                for name, t in self.tools.items()
            },
            "python_packages": self.python_packages,
        }


# Определение всех инструментов
TOOLS = [
    # Core - анализ работает всегда
    ToolInfo("git", "git", "Git version control", "core"),
    ToolInfo("python", "python3", "Python interpreter", "core"),

    # Recommended - значительно улучшают анализ
    ToolInfo("bandit", "bandit", "Python security linter", "recommended"),
    ToolInfo("safety", "safety", "Dependency vulnerability checker", "recommended"),
    ToolInfo("radon", "radon", "Code complexity analyzer", "recommended"),
    ToolInfo("vulture", "vulture", "Dead code detector", "recommended"),
    ToolInfo("pip-licenses", "pip-licenses", "License compliance checker", "recommended"),
    ToolInfo("pipdeptree", "pipdeptree", "Dependency tree analyzer", "recommended"),

    # Optional - дополнительные метрики
    ToolInfo("semgrep", "semgrep", "Advanced SAST scanner", "optional"),
    ToolInfo("hadolint", "hadolint", "Dockerfile linter", "optional"),
    ToolInfo("jscpd", "jscpd", "Code duplication detector", "optional"),
    ToolInfo("npm", "npm", "Node.js package manager", "optional"),
]


def check_tool(command: str) -> Optional[str]:
    """Check if a tool is available and return its path."""
    return shutil.which(command)


def get_tool_version(command: str) -> Optional[str]:
    """Try to get tool version."""
    import subprocess
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Return first line of version output
            return result.stdout.strip().split('\n')[0][:50]
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass  # Command not found or not executable
    return None


def check_python_package(package: str) -> bool:
    """Check if a Python package is importable and functional."""
    try:
        __import__(package)
        return True
    except (ImportError, OSError, Exception):
        # Some packages (like weasyprint) may raise OSError if system libs missing
        return False


@lru_cache(maxsize=1)
def check_all_dependencies() -> DependencyReport:
    """
    Check all dependencies and return a report.

    Результат кэшируется - вызывается один раз при старте.
    """
    report = DependencyReport()

    # Check external tools
    for tool in TOOLS:
        tool.installed = check_tool(tool.command) is not None
        if tool.installed:
            tool.version = get_tool_version(tool.command)
        report.tools[tool.name] = tool

        status = "✓" if tool.installed else "✗"
        logger.info(f"  [{status}] {tool.name}: {tool.description}")

    # Check Python packages
    packages = [
        "openpyxl",      # Excel export
        "weasyprint",    # PDF export (optional)
        "xhtml2pdf",     # PDF export (alternative)
        "anthropic",     # Claude API
        "openai",        # OpenAI API
        "semgrep",       # SAST
    ]

    for pkg in packages:
        report.python_packages[pkg] = check_python_package(pkg)

    # Log summary
    summary = report.summary
    logger.info(
        f"Dependencies: {summary['tools_installed']}/{summary['tools_total']} tools available"
    )

    return report


def get_available_features() -> Dict[str, bool]:
    """
    Get dictionary of available features based on dependencies.

    Возвращает что реально доступно пользователю.
    """
    report = check_all_dependencies()

    return {
        # Всегда работают (Python stdlib + basic deps)
        "structure_analysis": True,
        "git_analysis": report.tools.get("git", ToolInfo("", "", "", "")).installed,
        "loc_counting": True,
        "ci_detection": True,

        # Зависят от инструментов
        "security_bandit": report.tools.get("bandit", ToolInfo("", "", "", "")).installed,
        "security_safety": report.tools.get("safety", ToolInfo("", "", "", "")).installed,
        "security_semgrep": report.tools.get("semgrep", ToolInfo("", "", "", "")).installed,
        "complexity_radon": report.tools.get("radon", ToolInfo("", "", "", "")).installed,
        "dead_code_vulture": report.tools.get("vulture", ToolInfo("", "", "", "")).installed,
        "license_check": report.tools.get("pip-licenses", ToolInfo("", "", "", "")).installed,
        "dependency_tree": report.tools.get("pipdeptree", ToolInfo("", "", "", "")).installed,
        "dockerfile_lint": report.tools.get("hadolint", ToolInfo("", "", "", "")).installed,
        "duplication_check": report.tools.get("jscpd", ToolInfo("", "", "", "")).installed,

        # Export
        "export_excel": report.python_packages.get("openpyxl", False),
        "export_pdf": report.python_packages.get("weasyprint", False) or report.python_packages.get("xhtml2pdf", False),
        "export_markdown": True,

        # LLM
        "llm_claude": report.python_packages.get("anthropic", False),
        "llm_openai": report.python_packages.get("openai", False),
    }


# API endpoint data
def get_system_status() -> Dict:
    """Get full system status for API endpoint."""
    report = check_all_dependencies()
    features = get_available_features()

    return {
        "status": "ok",
        "dependencies": report.to_dict(),
        "features": features,
        "recommendations": _get_recommendations(report),
    }


def _get_recommendations(report: DependencyReport) -> List[str]:
    """Get installation recommendations for missing tools."""
    recommendations = []

    missing_recommended = [
        t for t in report.tools.values()
        if t.level == "recommended" and not t.installed
    ]

    if missing_recommended:
        pip_tools = ["bandit", "safety", "radon", "vulture", "pip-licenses", "pipdeptree"]
        missing_pip = [t.name for t in missing_recommended if t.name in pip_tools]

        if missing_pip:
            recommendations.append(
                f"pip install {' '.join(missing_pip)}"
            )

    missing_optional = [
        t for t in report.tools.values()
        if t.level == "optional" and not t.installed
    ]

    if any(t.name == "hadolint" for t in missing_optional):
        recommendations.append("brew install hadolint  # Dockerfile linting")

    if any(t.name == "jscpd" for t in missing_optional):
        recommendations.append("npm install -g jscpd  # Code duplication")

    return recommendations
