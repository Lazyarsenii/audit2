"""
Evaluation Profiles Configuration.

Defines evaluation standards, pricing, and procedures for different:
- Countries/regions
- Project types
- Industry standards
- Acceptance criteria

Used by finance and operations teams to configure evaluation parameters.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class Region(str, Enum):
    """Supported regions."""
    EU = "eu"
    UA = "ua"
    US = "us"
    ASIA = "asia"
    GLOBAL = "global"


class Currency(str, Enum):
    """Supported currencies."""
    EUR = "EUR"
    USD = "USD"
    UAH = "UAH"
    GBP = "GBP"


class EvaluationStandard(str, Enum):
    """Evaluation standards."""
    BASIC = "basic"               # Minimal checks
    STANDARD = "standard"         # Standard R&D evaluation
    ENTERPRISE = "enterprise"     # Enterprise-grade
    GOVERNMENT = "government"     # Government/public sector
    FINTECH = "fintech"          # Financial technology
    HEALTHCARE = "healthcare"     # Healthcare/medical


@dataclass
class HourlyRates:
    """Hourly rates by seniority level."""
    junior: float
    middle: float
    senior: float
    lead: float
    architect: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "junior": self.junior,
            "middle": self.middle,
            "senior": self.senior,
            "lead": self.lead,
            "architect": self.architect,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "HourlyRates":
        return cls(**data)


@dataclass
class PricingConfig:
    """Pricing configuration for a region."""
    currency: Currency
    hourly_rates: HourlyRates
    overhead_multiplier: float = 1.3    # Overhead costs
    tax_rate: float = 0.0               # VAT/tax
    discount_volume: float = 0.0        # Volume discount
    min_project_cost: float = 1000      # Minimum project cost

    def calculate_cost(
        self,
        hours: float,
        seniority_mix: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Calculate project cost based on hours and seniority mix."""
        if seniority_mix is None:
            seniority_mix = {"middle": 0.5, "senior": 0.3, "junior": 0.2}

        # Calculate weighted hourly rate
        rates = self.hourly_rates.to_dict()
        weighted_rate = sum(
            rates.get(level, rates["middle"]) * pct
            for level, pct in seniority_mix.items()
        )

        base_cost = hours * weighted_rate
        with_overhead = base_cost * self.overhead_multiplier
        with_tax = with_overhead * (1 + self.tax_rate)
        final = max(with_tax, self.min_project_cost)

        return {
            "currency": self.currency.value,
            "hours": hours,
            "base_cost": round(base_cost, 2),
            "with_overhead": round(with_overhead, 2),
            "with_tax": round(with_tax, 2),
            "final_cost": round(final, 2),
            "hourly_rate_effective": round(weighted_rate, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency": self.currency.value,
            "hourly_rates": self.hourly_rates.to_dict(),
            "overhead_multiplier": self.overhead_multiplier,
            "tax_rate": self.tax_rate,
            "discount_volume": self.discount_volume,
            "min_project_cost": self.min_project_cost,
        }


@dataclass
class AcceptanceCriteria:
    """Project acceptance criteria."""
    min_repo_health: int = 6           # Minimum repo health score
    min_tech_debt: int = 6             # Minimum tech debt score
    min_readiness: float = 60.0        # Minimum readiness %
    required_docs: List[str] = field(default_factory=lambda: ["readme", "install"])
    required_tests: bool = True
    required_ci: bool = False
    required_docker: bool = False
    max_critical_issues: int = 0       # Max critical security issues
    custom_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_repo_health": self.min_repo_health,
            "min_tech_debt": self.min_tech_debt,
            "min_readiness": self.min_readiness,
            "required_docs": self.required_docs,
            "required_tests": self.required_tests,
            "required_ci": self.required_ci,
            "required_docker": self.required_docker,
            "max_critical_issues": self.max_critical_issues,
            "custom_checks": self.custom_checks,
        }


@dataclass
class DeliveryRequirements:
    """Delivery documentation requirements."""
    # Required documents
    repo_review: bool = True
    technical_summary: bool = True
    partner_report: bool = False
    act_of_work: bool = True
    invoice: bool = True

    # Document format
    format: str = "markdown"  # markdown, pdf, docx
    language: str = "en"      # en, uk, de, etc.

    # Report sections
    include_metrics: bool = True
    include_cost_breakdown: bool = True
    include_recommendations: bool = True
    include_task_list: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_review": self.repo_review,
            "technical_summary": self.technical_summary,
            "partner_report": self.partner_report,
            "act_of_work": self.act_of_work,
            "invoice": self.invoice,
            "format": self.format,
            "language": self.language,
            "include_metrics": self.include_metrics,
            "include_cost_breakdown": self.include_cost_breakdown,
            "include_recommendations": self.include_recommendations,
            "include_task_list": self.include_task_list,
        }


@dataclass
class EvaluationProfile:
    """Complete evaluation profile."""
    id: str
    name: str
    description: str
    region: Region
    standard: EvaluationStandard
    pricing: PricingConfig
    acceptance: AcceptanceCriteria
    delivery: DeliveryRequirements
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "region": self.region.value,
            "standard": self.standard.value,
            "pricing": self.pricing.to_dict(),
            "acceptance": self.acceptance.to_dict(),
            "delivery": self.delivery.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationProfile":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            region=Region(data["region"]),
            standard=EvaluationStandard(data["standard"]),
            pricing=PricingConfig(
                currency=Currency(data["pricing"]["currency"]),
                hourly_rates=HourlyRates.from_dict(data["pricing"]["hourly_rates"]),
                overhead_multiplier=data["pricing"].get("overhead_multiplier", 1.3),
                tax_rate=data["pricing"].get("tax_rate", 0),
                discount_volume=data["pricing"].get("discount_volume", 0),
                min_project_cost=data["pricing"].get("min_project_cost", 1000),
            ),
            acceptance=AcceptanceCriteria(**data.get("acceptance", {})),
            delivery=DeliveryRequirements(**data.get("delivery", {})),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# PREDEFINED PROFILES
# ============================================================================

PROFILES: Dict[str, EvaluationProfile] = {
    # EU Standard Profile
    "eu_standard": EvaluationProfile(
        id="eu_standard",
        name="EU Standard R&D",
        description="Standard evaluation for EU-based R&D projects",
        region=Region.EU,
        standard=EvaluationStandard.STANDARD,
        pricing=PricingConfig(
            currency=Currency.EUR,
            hourly_rates=HourlyRates(
                junior=35,
                middle=55,
                senior=85,
                lead=110,
                architect=140,
            ),
            overhead_multiplier=1.35,
            tax_rate=0.20,  # VAT
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=6,
            min_tech_debt=6,
            min_readiness=60,
            required_docs=["readme", "install", "usage"],
            required_tests=True,
            required_ci=True,
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            act_of_work=True,
            invoice=True,
            format="pdf",
            language="en",
        ),
    ),

    # Ukraine Profile
    "ua_standard": EvaluationProfile(
        id="ua_standard",
        name="Ukraine R&D Standard",
        description="Standard evaluation for Ukrainian development teams",
        region=Region.UA,
        standard=EvaluationStandard.STANDARD,
        pricing=PricingConfig(
            currency=Currency.USD,
            hourly_rates=HourlyRates(
                junior=15,
                middle=30,
                senior=50,
                lead=70,
                architect=90,
            ),
            overhead_multiplier=1.20,
            tax_rate=0.05,  # Single tax
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=5,
            min_tech_debt=5,
            min_readiness=50,
            required_docs=["readme", "install"],
            required_tests=True,
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            act_of_work=True,
            invoice=True,
            format="markdown",
            language="uk",
        ),
    ),

    # EU Enterprise Profile
    "eu_enterprise": EvaluationProfile(
        id="eu_enterprise",
        name="EU Enterprise",
        description="Enterprise-grade evaluation with strict requirements",
        region=Region.EU,
        standard=EvaluationStandard.ENTERPRISE,
        pricing=PricingConfig(
            currency=Currency.EUR,
            hourly_rates=HourlyRates(
                junior=45,
                middle=70,
                senior=110,
                lead=150,
                architect=200,
            ),
            overhead_multiplier=1.50,
            tax_rate=0.20,
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=9,
            min_tech_debt=10,
            min_readiness=80,
            required_docs=["readme", "install", "usage", "api", "architecture"],
            required_tests=True,
            required_ci=True,
            required_docker=True,
            max_critical_issues=0,
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            partner_report=True,
            act_of_work=True,
            invoice=True,
            format="pdf",
            language="en",
            include_metrics=True,
            include_cost_breakdown=True,
            include_recommendations=True,
        ),
    ),

    # US Standard Profile
    "us_standard": EvaluationProfile(
        id="us_standard",
        name="US Standard",
        description="Standard evaluation for US-based projects",
        region=Region.US,
        standard=EvaluationStandard.STANDARD,
        pricing=PricingConfig(
            currency=Currency.USD,
            hourly_rates=HourlyRates(
                junior=50,
                middle=85,
                senior=130,
                lead=175,
                architect=225,
            ),
            overhead_multiplier=1.40,
            tax_rate=0.0,  # No VAT, state taxes vary
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=6,
            min_tech_debt=6,
            min_readiness=60,
            required_docs=["readme", "install", "usage"],
            required_tests=True,
            required_ci=True,
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            invoice=True,
            format="pdf",
            language="en",
        ),
    ),

    # FinTech Profile
    "fintech": EvaluationProfile(
        id="fintech",
        name="FinTech",
        description="Financial technology evaluation with security focus",
        region=Region.GLOBAL,
        standard=EvaluationStandard.FINTECH,
        pricing=PricingConfig(
            currency=Currency.EUR,
            hourly_rates=HourlyRates(
                junior=50,
                middle=80,
                senior=120,
                lead=160,
                architect=210,
            ),
            overhead_multiplier=1.50,
            tax_rate=0.20,
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=9,
            min_tech_debt=12,
            min_readiness=85,
            required_docs=["readme", "install", "usage", "api", "architecture", "security"],
            required_tests=True,
            required_ci=True,
            required_docker=True,
            max_critical_issues=0,
            custom_checks=["pci_dss_compliance", "encryption_at_rest", "audit_logging"],
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            partner_report=True,
            act_of_work=True,
            invoice=True,
            format="pdf",
            language="en",
            include_metrics=True,
            include_cost_breakdown=True,
            include_recommendations=True,
        ),
        metadata={
            "compliance": ["PCI-DSS", "GDPR"],
            "security_scan_required": True,
        },
    ),

    # Minimal/Startup Profile
    "startup": EvaluationProfile(
        id="startup",
        name="Startup/MVP",
        description="Lightweight evaluation for startups and MVPs",
        region=Region.GLOBAL,
        standard=EvaluationStandard.BASIC,
        pricing=PricingConfig(
            currency=Currency.USD,
            hourly_rates=HourlyRates(
                junior=25,
                middle=45,
                senior=70,
                lead=95,
                architect=120,
            ),
            overhead_multiplier=1.15,
            tax_rate=0.0,
            min_project_cost=500,
        ),
        acceptance=AcceptanceCriteria(
            min_repo_health=3,
            min_tech_debt=3,
            min_readiness=30,
            required_docs=["readme"],
            required_tests=False,
        ),
        delivery=DeliveryRequirements(
            repo_review=True,
            technical_summary=True,
            invoice=True,
            format="markdown",
            language="en",
        ),
    ),
}


class ProfileManager:
    """Manages evaluation profiles."""

    def __init__(self, custom_profiles_path: Optional[Path] = None):
        self.profiles: Dict[str, EvaluationProfile] = PROFILES.copy()
        self.custom_path = custom_profiles_path

        if custom_profiles_path and custom_profiles_path.exists():
            self._load_custom_profiles()

    def _load_custom_profiles(self) -> None:
        """Load custom profiles from JSON file."""
        if not self.custom_path:
            return

        try:
            data = json.loads(self.custom_path.read_text())
            for profile_data in data.get("profiles", []):
                profile = EvaluationProfile.from_dict(profile_data)
                self.profiles[profile.id] = profile
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading custom profiles: {e}")

    def get(self, profile_id: str) -> Optional[EvaluationProfile]:
        """Get profile by ID."""
        return self.profiles.get(profile_id)

    def list(self) -> List[EvaluationProfile]:
        """List all profiles."""
        return list(self.profiles.values())

    def list_by_region(self, region: Region) -> List[EvaluationProfile]:
        """List profiles for a specific region."""
        return [p for p in self.profiles.values() if p.region == region or p.region == Region.GLOBAL]

    def add_custom(self, profile: EvaluationProfile) -> None:
        """Add a custom profile."""
        self.profiles[profile.id] = profile

    def save_custom(self) -> None:
        """Save custom profiles to file."""
        if not self.custom_path:
            return

        custom_profiles = [
            p.to_dict() for p in self.profiles.values()
            if p.id not in PROFILES
        ]

        self.custom_path.write_text(json.dumps({"profiles": custom_profiles}, indent=2))

    def create_from_template(
        self,
        template_id: str,
        new_id: str,
        name: str,
        **overrides,
    ) -> EvaluationProfile:
        """Create a new profile from an existing template."""
        template = self.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        data = template.to_dict()
        data["id"] = new_id
        data["name"] = name

        # Apply overrides
        for key, value in overrides.items():
            if key in data:
                if isinstance(data[key], dict) and isinstance(value, dict):
                    data[key].update(value)
                else:
                    data[key] = value

        return EvaluationProfile.from_dict(data)


# Default manager instance
profile_manager = ProfileManager()
