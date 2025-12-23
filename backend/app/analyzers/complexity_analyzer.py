"""
Code complexity and duplication analysis.
"""
import hashlib
from typing import Dict, Any, List, Tuple
from collections import defaultdict

try:
    from radon.complexity import cc_visit
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False


def analyze_python_complexity(content: str) -> List[Tuple[str, int, int]]:
    """
    Analyze Python code complexity using radon.
    Returns list of (function_name, complexity, lines) tuples.
    """
    if not RADON_AVAILABLE:
        return []
    results = []
    try:
        for item in cc_visit(content):
            func_lines = (item.endline - item.lineno + 1) if hasattr(item, 'endline') else 10
            results.append((item.name, item.complexity, func_lines))
    except:
        pass
    return results


def detect_duplication(
    files_content: List[Tuple[str, List[str]]],
    min_block_size: int = 6
) -> Tuple[float, List[Dict]]:
    """
    Detect code duplication using line hashing.
    Returns (duplication_percent, list of duplicate blocks).
    """
    if not files_content:
        return 0, []

    hash_to_locs = defaultdict(list)
    total_lines = 0
    dup_lines = set()

    for fp, lines in files_content:
        total_lines += len(lines)
        if len(lines) < min_block_size:
            continue
        for i in range(len(lines) - min_block_size + 1):
            block = "
".join(lines[i:i + min_block_size])
            if len(block.replace(" ", "").replace("
", "")) < 20:
                continue
            block_hash = hashlib.md5(block.encode()).hexdigest()
            hash_to_locs[block_hash].append((fp, i))

    dup_blocks = []
    seen = set()

    for h, locs in hash_to_locs.items():
        if len(locs) > 1 and h not in seen:
            seen.add(h)
            for fp, sl in locs:
                for ln in range(sl, sl + min_block_size):
                    dup_lines.add((fp, ln))
            dup_blocks.append({
                "locations": [{"file": l[0], "line": l[1] + 1} for l in locs[:5]],
                "occurrences": len(locs),
                "lines": min_block_size,
            })

    dup_pct = round((len(dup_lines) / total_lines) * 100, 1) if total_lines > 0 else 0
    dup_blocks.sort(key=lambda x: x["occurrences"], reverse=True)
    return dup_pct, dup_blocks
