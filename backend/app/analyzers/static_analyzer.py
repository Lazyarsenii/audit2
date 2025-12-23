"""
Static code analyzer module.

Analyzes code metrics: LOC, file sizes, complexity, etc.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict

from app.analyzers.complexity_analyzer import (
    analyze_python_complexity,
    detect_duplication,
)

logger = logging.getLogger(__name__)


# Language extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs"},
    "typescript": {".ts", ".tsx"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java"},
    "kotlin": {".kt", ".kts"},
    "ruby": {".rb"},
    "php": {".php"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".hpp", ".cc", ".hh"},
    "csharp": {".cs"},
    "swift": {".swift"},
    "scala": {".scala"},
}

# Files/folders to skip
SKIP_PATTERNS = {
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".next",
    "target",
    ".idea",
    ".vscode",
}

# Test file patterns
TEST_PATTERNS = [
    r"test_.*\.py$",
    r".*_test\.py$",
    r".*\.test\.[jt]sx?$",
    r".*\.spec\.[jt]sx?$",
    r".*_test\.go$",
    r"Test.*\.java$",
]


class StaticAnalyzer:
    """Analyzes code metrics."""

    def __init__(self):
        self.test_patterns = [re.compile(p) for p in TEST_PATTERNS]

    async def analyze(self, local_path: Path) -> Dict[str, Any]:
        """
        Analyze code metrics.

        Args:
            local_path: Path to repository

        Returns:
            Dictionary with code metrics
        """
        logger.info(f"Running static analysis on {local_path}")

        result = {
            "total_loc": 0,
            "files_count": 0,
            "test_files_count": 0,
            "languages": {},
            "large_files": [],
            "max_file_lines": 0,
            "max_function_lines": 0,
            "avg_function_lines": 0,
            "cyclomatic_complexity_avg": 0,
            "cyclomatic_complexity_max": 0,
            "complex_functions": [],
            "duplication_percent": 0,
            "duplicate_blocks": [],
            "code_smells_per_kloc": 0,
            "has_clear_layers": False,
            "external_deps_count": 0,
            "test_coverage": None,
        }
        
        # For complexity and duplication analysis
        all_files_content: List[Tuple[str, List[str]]] = []
        complexity_scores: List[float] = []
        function_lines: List[int] = []

        # Collect file stats
        files_by_lang: Dict[str, List[Dict]] = defaultdict(list)

        for file_path in self._iter_code_files(local_path):
            try:
                stats = self._analyze_file(file_path)
                if stats:
                    lang = stats["language"]
                    files_by_lang[lang].append(stats)

                    result["files_count"] += 1
                    result["total_loc"] += stats["loc"]

                    if stats["is_test"]:
                        result["test_files_count"] += 1

                    if stats["loc"] > result["max_file_lines"]:
                        result["max_file_lines"] = stats["loc"]

                    if stats["loc"] > 500:
                        result["large_files"].append({
                            "path": str(file_path.relative_to(local_path)),
                            "loc": stats["loc"],
                        })

                    # Collect content for duplication analysis
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    all_files_content.append((str(file_path.relative_to(local_path)), lines))

                    # Analyze complexity for Python files
                    if lang == "python":
                        cc_results = analyze_python_complexity(content)
                        for func_name, cc, fl in cc_results:
                            complexity_scores.append(cc)
                            function_lines.append(fl)
                            if cc > 10:
                                result["complex_functions"].append({
                                    "file": str(file_path.relative_to(local_path)),
                                    "function": func_name,
                                    "complexity": cc,
                                })

            except Exception as e:
                logger.debug(f"Failed to analyze {file_path}: {e}")

        # Aggregate by language
        for lang, files in files_by_lang.items():
            total_loc = sum(f["loc"] for f in files)
            result["languages"][lang] = {
                "files": len(files),
                "loc": total_loc,
            }

        # Calculate complexity averages
        if complexity_scores:
            result["cyclomatic_complexity_avg"] = round(sum(complexity_scores) / len(complexity_scores), 2)
            result["cyclomatic_complexity_max"] = max(complexity_scores)

        # Calculate function line averages
        if function_lines:
            result["avg_function_lines"] = round(sum(function_lines) / len(function_lines), 1)
            result["max_function_lines"] = max(function_lines)

        # Detect code duplication
        dup_pct, dup_blocks = detect_duplication(all_files_content)
        result["duplication_percent"] = dup_pct
        result["duplicate_blocks"] = dup_blocks[:10]

        # Calculate code smells per KLOC
        if result["total_loc"] > 0:
            smell_count = len(result["large_files"]) + len(result["complex_functions"]) + len(dup_blocks)
            result["code_smells_per_kloc"] = round(smell_count / (result["total_loc"] / 1000), 2)

        # Check for clear architectural layers
        result["has_clear_layers"] = self._check_layers(local_path)

        # Count external dependencies
        result["external_deps_count"] = self._count_dependencies(local_path)

        logger.info(f"Static analysis complete: {result['files_count']} files, {result['total_loc']} LOC")
        return result

    def _iter_code_files(self, path: Path):
        """Iterate over code files, skipping ignored directories."""
        all_extensions = set()
        for exts in LANGUAGE_EXTENSIONS.values():
            all_extensions.update(exts)

        for item in path.rglob("*"):
            # Skip ignored patterns
            if any(skip in item.parts for skip in SKIP_PATTERNS):
                continue

            if item.is_file() and item.suffix in all_extensions:
                yield item

    def _analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single file."""
        # Determine language
        language = None
        for lang, exts in LANGUAGE_EXTENSIONS.items():
            if file_path.suffix in exts:
                language = lang
                break

        if not language:
            return None

        # Count lines
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
        except (OSError, IOError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to read file {file_path}: {e}")
            return None

        # Check if test file
        is_test = any(p.match(file_path.name) for p in self.test_patterns)

        return {
            "path": str(file_path),
            "language": language,
            "loc": loc,
            "is_test": is_test,
        }

    def _check_layers(self, path: Path) -> bool:
        """Check if repository has clear architectural layers."""
        layer_indicators = {
            "domain": ["domain", "models", "entities"],
            "application": ["services", "use_cases", "application"],
            "infrastructure": ["adapters", "infra", "repositories", "infrastructure"],
            "api": ["api", "routes", "controllers", "handlers"],
        }

        found_layers = set()
        for item in path.iterdir():
            if item.is_dir():
                name_lower = item.name.lower()
                for layer, indicators in layer_indicators.items():
                    if name_lower in indicators:
                        found_layers.add(layer)

        # Consider "clear layers" if at least 2 distinct layers found
        return len(found_layers) >= 2

    def _count_dependencies(self, path: Path) -> int:
        """Count external dependencies from dependency files."""
        count = 0

        # Python requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            try:
                lines = req_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                count += len([l for l in lines if l.strip() and not l.startswith("#")])
            except (OSError, IOError) as e:
                logger.debug(f"Failed to read requirements.txt: {e}")

        # Node package.json
        pkg_file = path / "package.json"
        if pkg_file.exists():
            try:
                data = json.loads(pkg_file.read_text(encoding="utf-8"))
                count += len(data.get("dependencies", {}))
                count += len(data.get("devDependencies", {}))
            except (OSError, IOError, json.JSONDecodeError) as e:
                logger.debug(f"Failed to read package.json: {e}")

        return count


# Singleton instance
static_analyzer = StaticAnalyzer()
