"""
Contract Compliance Checker

Compares actual repository metrics against contract/policy requirements
and produces a compliance report.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ComplianceStatus(str, Enum):
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RequirementResult:
    """Result of checking a single requirement."""
    requirement_id: str
    title: str
    category: str
    metric_mapping: Optional[str]
    min_level: int
    fact_level: Optional[int]
    priority: str
    blocking: bool
    status: ComplianceStatus
    gap: int = 0  # Difference between required and actual
    section_ref: str = ""
    description: str = ""


@dataclass
class ComplianceReport:
    """Full compliance report against a contract profile."""
    contract_profile_id: str
    contract_label: str
    total_requirements: int
    passed: int
    partial: int
    failed: int
    not_applicable: int
    critical_failed: int
    blocking_failed: int
    compliance_percent: float
    verdict: str  # COMPLIANT, PARTIAL, NON_COMPLIANT
    details: List[RequirementResult] = field(default_factory=list)
    qualitative_notes: List[Dict[str, Any]] = field(default_factory=list)
    acceptance_thresholds: Dict[str, Any] = field(default_factory=dict)
    threshold_results: Dict[str, bool] = field(default_factory=dict)


class ContractComplianceChecker:
    """
    Checks repository analysis results against contract requirements.
    """

    PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles" / "contract"

    # Mapping from contract categories to metric names
    METRIC_MAPPING = {
        "documentation": "documentation",
        "structure": "structure",
        "runability": "runability",
        "history": "history",
        "architecture": "architecture",
        "code_quality": "code_quality",
        "testing": "testing",
        "infrastructure": "infrastructure",
        "security": "security",
    }

    def __init__(self):
        self._profiles_cache: Dict[str, Dict] = {}

    def list_profiles(self) -> List[Dict[str, str]]:
        """List all available contract profiles."""
        profiles = []
        for yaml_file in self.PROFILES_DIR.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue  # Skip templates
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                profiles.append({
                    "id": data.get("id", yaml_file.stem),
                    "label": data.get("label", yaml_file.stem),
                    "description": data.get("description", "")[:100],
                    "source_type": data.get("source", {}).get("type", "unknown"),
                })
            except Exception:
                continue
        return profiles

    def load_profile(self, profile_id: str) -> Optional[Dict]:
        """Load a contract profile by ID."""
        if profile_id in self._profiles_cache:
            return self._profiles_cache[profile_id]

        # Try to find the profile file
        yaml_file = self.PROFILES_DIR / f"{profile_id}.yaml"
        if not yaml_file.exists():
            # Search by id field
            for f in self.PROFILES_DIR.glob("*.yaml"):
                try:
                    with open(f) as fp:
                        data = yaml.safe_load(fp)
                    if data.get("id") == profile_id:
                        self._profiles_cache[profile_id] = data
                        return data
                except Exception:
                    continue
            return None

        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            self._profiles_cache[profile_id] = data
            return data
        except Exception:
            return None

    def check_compliance(
        self,
        profile_id: str,
        repo_health: Dict[str, int],
        tech_debt: Dict[str, int],
    ) -> ComplianceReport:
        """
        Check compliance against a contract profile.

        Args:
            profile_id: Contract profile ID to check against
            repo_health: Dict with keys: documentation, structure, runability, history, total
            tech_debt: Dict with keys: architecture, code_quality, testing, infrastructure, security, total

        Returns:
            ComplianceReport with detailed results
        """
        profile = self.load_profile(profile_id)
        if not profile:
            return ComplianceReport(
                contract_profile_id=profile_id,
                contract_label="Unknown",
                total_requirements=0,
                passed=0,
                partial=0,
                failed=0,
                not_applicable=0,
                critical_failed=0,
                blocking_failed=0,
                compliance_percent=0.0,
                verdict="ERROR: Profile not found",
            )

        # Combine all metrics into one dict for easy lookup
        all_metrics = {
            "documentation": repo_health.get("documentation", 0),
            "structure": repo_health.get("structure", 0),
            "runability": repo_health.get("runability", 0),
            "history": repo_health.get("history", 0),
            "architecture": tech_debt.get("architecture", 0),
            "code_quality": tech_debt.get("code_quality", 0),
            "testing": tech_debt.get("testing", 0),
            "infrastructure": tech_debt.get("infrastructure", 0),
            "security": tech_debt.get("security", 0),
        }

        # Check each requirement
        results: List[RequirementResult] = []
        passed = 0
        partial = 0
        failed = 0
        not_applicable = 0
        critical_failed = 0
        blocking_failed = 0

        requirements = profile.get("requirements", [])

        for req in requirements:
            req_id = req.get("id", "UNKNOWN")
            title = req.get("title", "")
            category = req.get("category", "")
            metric_key = req.get("metric_mapping", "")
            min_level = req.get("min_level", 0)
            priority = req.get("priority", "medium")
            blocking = req.get("blocking", False)
            section_ref = req.get("section_ref", "")
            description = req.get("description", "")

            # Get actual level
            if metric_key and metric_key in all_metrics:
                fact_level = all_metrics[metric_key]
            else:
                # Cannot measure this requirement
                results.append(RequirementResult(
                    requirement_id=req_id,
                    title=title,
                    category=category,
                    metric_mapping=metric_key,
                    min_level=min_level,
                    fact_level=None,
                    priority=priority,
                    blocking=blocking,
                    status=ComplianceStatus.NOT_APPLICABLE,
                    section_ref=section_ref,
                    description=description,
                ))
                not_applicable += 1
                continue

            # Determine status
            gap = min_level - fact_level
            if fact_level >= min_level:
                status = ComplianceStatus.PASSED
                passed += 1
            elif fact_level >= min_level - 1:
                status = ComplianceStatus.PARTIAL
                partial += 1
            else:
                status = ComplianceStatus.FAILED
                failed += 1
                if priority == "critical":
                    critical_failed += 1
                if blocking:
                    blocking_failed += 1

            results.append(RequirementResult(
                requirement_id=req_id,
                title=title,
                category=category,
                metric_mapping=metric_key,
                min_level=min_level,
                fact_level=fact_level,
                priority=priority,
                blocking=blocking,
                status=status,
                gap=max(0, gap),
                section_ref=section_ref,
                description=description,
            ))

        total = len(requirements)
        measurable = total - not_applicable
        compliance_percent = (passed / measurable * 100) if measurable > 0 else 0

        # Check acceptance thresholds
        thresholds = profile.get("acceptance_thresholds", {})
        threshold_results = {}

        if "min_repo_health" in thresholds:
            threshold_results["repo_health"] = repo_health.get("total", 0) >= thresholds["min_repo_health"]
        if "min_tech_debt" in thresholds:
            threshold_results["tech_debt"] = tech_debt.get("total", 0) >= thresholds["min_tech_debt"]
        if "min_compliance_percent" in thresholds:
            threshold_results["compliance_percent"] = compliance_percent >= thresholds["min_compliance_percent"]
        if "max_critical_failures" in thresholds:
            threshold_results["critical_failures"] = critical_failed <= thresholds["max_critical_failures"]
        if "max_blocking_failures" in thresholds:
            threshold_results["blocking_failures"] = blocking_failed <= thresholds["max_blocking_failures"]

        # Determine verdict
        all_thresholds_passed = all(threshold_results.values()) if threshold_results else True

        if blocking_failed > 0:
            verdict = "NON_COMPLIANT"
        elif critical_failed > 0:
            verdict = "NON_COMPLIANT"
        elif not all_thresholds_passed:
            verdict = "PARTIAL"
        elif compliance_percent >= 90:
            verdict = "COMPLIANT"
        elif compliance_percent >= 70:
            verdict = "PARTIAL"
        else:
            verdict = "NON_COMPLIANT"

        return ComplianceReport(
            contract_profile_id=profile_id,
            contract_label=profile.get("label", profile_id),
            total_requirements=total,
            passed=passed,
            partial=partial,
            failed=failed,
            not_applicable=not_applicable,
            critical_failed=critical_failed,
            blocking_failed=blocking_failed,
            compliance_percent=round(compliance_percent, 1),
            verdict=verdict,
            details=results,
            qualitative_notes=profile.get("qualitative_notes", []),
            acceptance_thresholds=thresholds,
            threshold_results=threshold_results,
        )

    def get_remediation_tasks(self, report: ComplianceReport) -> List[Dict[str, Any]]:
        """
        Generate remediation tasks for failed requirements.

        Returns list of tasks with priority, category, and estimated effort.
        """
        tasks = []

        # Sort by priority: critical > high > medium > low, blocking first
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        failed_reqs = [r for r in report.details if r.status in (ComplianceStatus.FAILED, ComplianceStatus.PARTIAL)]
        failed_reqs.sort(key=lambda r: (not r.blocking, priority_order.get(r.priority, 3), r.gap))

        for req in failed_reqs:
            # Estimate hours based on gap and category
            base_hours = {
                "documentation": 4,
                "testing": 8,
                "security": 12,
                "infrastructure": 6,
                "architecture": 16,
                "code_quality": 8,
                "structure": 4,
                "runability": 2,
            }

            hours = base_hours.get(req.category, 8) * max(1, req.gap)

            tasks.append({
                "requirement_id": req.requirement_id,
                "title": f"[{req.priority.upper()}] {req.title}",
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "blocking": req.blocking,
                "current_level": req.fact_level,
                "required_level": req.min_level,
                "gap": req.gap,
                "estimated_hours": hours,
                "section_ref": req.section_ref,
            })

        return tasks

    def to_dict(self, report: ComplianceReport) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "contract_profile_id": report.contract_profile_id,
            "contract_label": report.contract_label,
            "total_requirements": report.total_requirements,
            "passed": report.passed,
            "partial": report.partial,
            "failed": report.failed,
            "not_applicable": report.not_applicable,
            "critical_failed": report.critical_failed,
            "blocking_failed": report.blocking_failed,
            "compliance_percent": report.compliance_percent,
            "verdict": report.verdict,
            "details": [
                {
                    "requirement_id": r.requirement_id,
                    "title": r.title,
                    "category": r.category,
                    "metric": r.metric_mapping,
                    "min_level": r.min_level,
                    "fact_level": r.fact_level,
                    "priority": r.priority,
                    "blocking": r.blocking,
                    "status": r.status.value,
                    "gap": r.gap,
                    "section_ref": r.section_ref,
                }
                for r in report.details
            ],
            "qualitative_notes": report.qualitative_notes,
            "acceptance_thresholds": report.acceptance_thresholds,
            "threshold_results": report.threshold_results,
        }


# Singleton instance
compliance_checker = ContractComplianceChecker()
