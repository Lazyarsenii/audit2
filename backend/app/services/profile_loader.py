"""
Profile Loader Service

Loads scoring templates, pricing profiles, and contract profiles from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


PROFILES_BASE = Path(__file__).parent.parent.parent / "profiles"


@dataclass
class ScoringTemplate:
    """Scoring template with weights and thresholds."""
    id: str
    label: str
    description: str
    weights: Dict[str, Dict[str, float]]
    thresholds: Dict[str, Dict[str, Dict[str, int]]]
    levels: Dict[str, Dict[str, int]]
    notes: str = ""


@dataclass
class PricingProfile:
    """Pricing profile with regional rates."""
    id: str
    label: str
    description: str
    regions: Dict[str, Dict[str, Any]]
    discount_factor: float
    overhead_multiplier: float
    notes: str = ""


class ProfileLoader:
    """Loads and caches profile configurations."""

    def __init__(self):
        self._scoring_cache: Dict[str, ScoringTemplate] = {}
        self._pricing_cache: Dict[str, PricingProfile] = {}

    # -------------------------------------------------------------------------
    # Scoring Templates
    # -------------------------------------------------------------------------

    def list_scoring_templates(self) -> List[Dict[str, str]]:
        """List all available scoring templates."""
        templates = []
        scoring_dir = PROFILES_BASE / "scoring"
        if not scoring_dir.exists():
            return templates

        for yaml_file in scoring_dir.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                templates.append({
                    "id": data.get("id", yaml_file.stem),
                    "label": data.get("label", yaml_file.stem),
                    "description": data.get("description", "")[:100],
                })
            except (OSError, yaml.YAMLError):
                continue  # Skip invalid files
        return templates

    def load_scoring_template(self, template_id: str) -> Optional[ScoringTemplate]:
        """Load a scoring template by ID."""
        if template_id in self._scoring_cache:
            return self._scoring_cache[template_id]

        scoring_dir = PROFILES_BASE / "scoring"
        yaml_file = scoring_dir / f"{template_id}.yaml"

        if not yaml_file.exists():
            # Search by id field
            for f in scoring_dir.glob("*.yaml"):
                try:
                    with open(f) as fp:
                        data = yaml.safe_load(fp)
                    if data.get("id") == template_id:
                        template = self._parse_scoring_template(data)
                        self._scoring_cache[template_id] = template
                        return template
                except (OSError, yaml.YAMLError):
                    continue  # Skip invalid files
            return None

        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            template = self._parse_scoring_template(data)
            self._scoring_cache[template_id] = template
            return template
        except (OSError, yaml.YAMLError):
            return None  # Invalid template file

    def _parse_scoring_template(self, data: Dict) -> ScoringTemplate:
        return ScoringTemplate(
            id=data.get("id", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            weights=data.get("weights", {}),
            thresholds=data.get("thresholds", {}),
            levels=data.get("levels", {}),
            notes=data.get("notes", ""),
        )

    def get_weighted_scores(
        self,
        template_id: str,
        repo_health: Dict[str, int],
        tech_debt: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Apply scoring template weights to raw scores.

        Returns weighted scores and threshold violations.
        """
        template = self.load_scoring_template(template_id)
        if not template:
            # Return unweighted scores if template not found
            return {
                "repo_health_weighted": sum(repo_health.values()),
                "tech_debt_weighted": sum(tech_debt.values()),
                "violations": [],
            }

        # Apply weights to repo_health
        rh_weights = template.weights.get("repo_health", {})
        rh_weighted = sum(
            repo_health.get(k, 0) * rh_weights.get(k, 1.0)
            for k in repo_health.keys()
            if k != "total"
        )

        # Apply weights to tech_debt
        td_weights = template.weights.get("tech_debt", {})
        td_weighted = sum(
            tech_debt.get(k, 0) * td_weights.get(k, 1.0)
            for k in tech_debt.keys()
            if k != "total"
        )

        # Check threshold violations
        violations = []
        rh_thresholds = template.thresholds.get("repo_health", {})
        for metric, rules in rh_thresholds.items():
            min_val = rules.get("min", 0)
            actual = repo_health.get(metric, 0)
            if actual < min_val:
                violations.append({
                    "category": "repo_health",
                    "metric": metric,
                    "min_required": min_val,
                    "actual": actual,
                })

        td_thresholds = template.thresholds.get("tech_debt", {})
        for metric, rules in td_thresholds.items():
            min_val = rules.get("min", 0)
            actual = tech_debt.get(metric, 0)
            if actual < min_val:
                violations.append({
                    "category": "tech_debt",
                    "metric": metric,
                    "min_required": min_val,
                    "actual": actual,
                })

        return {
            "repo_health_weighted": round(rh_weighted, 2),
            "tech_debt_weighted": round(td_weighted, 2),
            "violations": violations,
            "template_id": template.id,
            "template_label": template.label,
        }

    # -------------------------------------------------------------------------
    # Pricing Profiles
    # -------------------------------------------------------------------------

    def list_pricing_profiles(self) -> List[Dict[str, str]]:
        """List all available pricing profiles."""
        profiles = []
        pricing_dir = PROFILES_BASE / "pricing"
        if not pricing_dir.exists():
            return profiles

        for yaml_file in pricing_dir.glob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                profiles.append({
                    "id": data.get("id", yaml_file.stem),
                    "label": data.get("label", yaml_file.stem),
                    "description": data.get("description", "")[:100],
                    "regions": list(data.get("regions", {}).keys()),
                })
            except Exception:
                continue
        return profiles

    def load_pricing_profile(self, profile_id: str) -> Optional[PricingProfile]:
        """Load a pricing profile by ID."""
        if profile_id in self._pricing_cache:
            return self._pricing_cache[profile_id]

        pricing_dir = PROFILES_BASE / "pricing"
        yaml_file = pricing_dir / f"{profile_id}.yaml"

        if not yaml_file.exists():
            # Search by id field
            for f in pricing_dir.glob("*.yaml"):
                try:
                    with open(f) as fp:
                        data = yaml.safe_load(fp)
                    if data.get("id") == profile_id:
                        profile = self._parse_pricing_profile(data)
                        self._pricing_cache[profile_id] = profile
                        return profile
                except Exception:
                    continue
            return None

        try:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            profile = self._parse_pricing_profile(data)
            self._pricing_cache[profile_id] = profile
            return profile
        except Exception:
            return None

    def _parse_pricing_profile(self, data: Dict) -> PricingProfile:
        return PricingProfile(
            id=data.get("id", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            regions=data.get("regions", {}),
            discount_factor=data.get("discount_factor", 1.0),
            overhead_multiplier=data.get("overhead_multiplier", 1.0),
            notes=data.get("notes", ""),
        )

    def calculate_cost(
        self,
        profile_id: str,
        base_hours: int,
        region: str = "EU",
    ) -> Dict[str, Any]:
        """
        Calculate cost using a pricing profile.

        Args:
            profile_id: Pricing profile ID
            base_hours: Estimated hours for the work
            region: Region code (EU, UA, US)

        Returns:
            Cost estimate with min/max range
        """
        profile = self.load_pricing_profile(profile_id)
        if not profile:
            # Fallback to defaults
            return {
                "hours": base_hours,
                "currency": "EUR",
                "min": base_hours * 40,
                "max": base_hours * 80,
                "profile_id": "default",
            }

        region_data = profile.regions.get(region)
        if not region_data:
            # Try first available region
            region = list(profile.regions.keys())[0] if profile.regions else "EU"
            region_data = profile.regions.get(region, {})

        blended = region_data.get("blended_rate", {"min": 40, "max": 80})
        currency = region_data.get("currency", "EUR")

        min_cost = int(
            base_hours * blended["min"] * profile.overhead_multiplier * profile.discount_factor
        )
        max_cost = int(
            base_hours * blended["max"] * profile.overhead_multiplier * profile.discount_factor
        )

        return {
            "hours": base_hours,
            "currency": currency,
            "min": min_cost,
            "max": max_cost,
            "formatted": f"{currency} {min_cost:,} - {max_cost:,}",
            "profile_id": profile.id,
            "profile_label": profile.label,
            "region": region,
            "discount_factor": profile.discount_factor,
            "overhead_multiplier": profile.overhead_multiplier,
        }


# Singleton instance
profile_loader = ProfileLoader()
