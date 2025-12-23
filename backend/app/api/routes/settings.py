"""
Settings API endpoints.

Manage profiles, templates, and system configuration.
"""
import os
import shutil
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(prefix="/settings", tags=["settings"])

PROFILES_DIR = Path(__file__).parent.parent.parent.parent / "profiles"


# =============================================================================
# Models
# =============================================================================

class ProfileCreate(BaseModel):
    """Create a new profile."""
    profile_type: str  # contract, scoring, pricing
    id: str
    label: str
    description: str
    data: Dict[str, Any]


class ProfileUpdate(BaseModel):
    """Update existing profile."""
    label: Optional[str] = None
    description: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class TemplateInfo(BaseModel):
    """Document template info."""
    id: str
    name: str
    type: str  # act, invoice, contract, report
    language: str
    description: str
    variables: List[str]


# =============================================================================
# Profile Management
# =============================================================================

@router.get("/profiles")
async def list_all_profiles():
    """List all profiles organized by type."""
    result = {
        "contract": [],
        "scoring": [],
        "pricing": [],
    }

    for profile_type in result.keys():
        type_dir = PROFILES_DIR / profile_type
        if type_dir.exists():
            for f in type_dir.glob("*.yaml"):
                if f.name.startswith("_"):
                    continue
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = yaml.safe_load(fp)
                        result[profile_type].append({
                            "id": data.get("id", f.stem),
                            "label": data.get("label", f.stem),
                            "description": data.get("description", ""),
                            "file": f.name,
                        })
                except Exception:
                    pass

    return result


@router.get("/profiles/{profile_type}")
async def list_profiles_by_type(profile_type: str):
    """List profiles of a specific type."""
    type_dir = PROFILES_DIR / profile_type
    if not type_dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile type '{profile_type}' not found")

    profiles = []
    for f in type_dir.glob("*.yaml"):
        if f.name.startswith("_"):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
                profiles.append({
                    "id": data.get("id", f.stem),
                    "label": data.get("label", f.stem),
                    "description": data.get("description", ""),
                    "file": f.name,
                    "data": data,
                })
        except Exception as e:
            profiles.append({
                "id": f.stem,
                "label": f.stem,
                "error": str(e),
            })

    return {"profiles": profiles, "count": len(profiles)}


@router.get("/profiles/{profile_type}/{profile_id}")
async def get_profile(profile_type: str, profile_id: str):
    """Get a specific profile with full data."""
    profile_path = PROFILES_DIR / profile_type / f"{profile_id}.yaml"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return {
        "id": profile_id,
        "type": profile_type,
        "file": profile_path.name,
        "data": data,
    }


@router.post("/profiles/{profile_type}")
async def create_profile(profile_type: str, profile: ProfileCreate):
    """Create a new profile."""
    type_dir = PROFILES_DIR / profile_type
    type_dir.mkdir(parents=True, exist_ok=True)

    profile_path = type_dir / f"{profile.id}.yaml"
    if profile_path.exists():
        raise HTTPException(status_code=409, detail=f"Profile '{profile.id}' already exists")

    # Build profile data
    profile_data = {
        "id": profile.id,
        "label": profile.label,
        "description": profile.description,
        **profile.data,
    }

    # Add metadata
    profile_data["_meta"] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)

    return {"message": "Profile created", "id": profile.id, "path": str(profile_path)}


@router.put("/profiles/{profile_type}/{profile_id}")
async def update_profile(profile_type: str, profile_id: str, update: ProfileUpdate):
    """Update an existing profile."""
    profile_path = PROFILES_DIR / profile_type / f"{profile_id}.yaml"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Update fields
    if update.label:
        data["label"] = update.label
    if update.description:
        data["description"] = update.description
    if update.data:
        data.update(update.data)

    # Update metadata
    if "_meta" not in data:
        data["_meta"] = {}
    data["_meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    return {"message": "Profile updated", "id": profile_id}


@router.delete("/profiles/{profile_type}/{profile_id}")
async def delete_profile(profile_type: str, profile_id: str):
    """Delete a profile."""
    profile_path = PROFILES_DIR / profile_type / f"{profile_id}.yaml"
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    # Create backup
    backup_dir = PROFILES_DIR / "_backup"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"{profile_type}_{profile_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.yaml"
    shutil.copy(profile_path, backup_path)

    # Delete
    profile_path.unlink()

    return {"message": "Profile deleted", "id": profile_id, "backup": str(backup_path)}


# =============================================================================
# Contract/Policy Upload & Parsing
# =============================================================================

@router.post("/upload-contract")
async def upload_contract(
    file: UploadFile = File(...),
    profile_id: str = Form(...),
    label: str = Form(...),
    description: str = Form(default=""),
    source_type: str = Form(default="grant_contract"),
):
    """
    Upload a contract/policy document and create a profile template.

    Supports: PDF, DOCX, TXT
    The document will be stored and a basic profile template created.
    You can then edit the profile to map specific requirements.
    """
    # Validate file type
    allowed_types = [".pdf", ".docx", ".doc", ".txt", ".md"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )

    # Create directories
    contracts_dir = PROFILES_DIR / "contract"
    uploads_dir = PROFILES_DIR / "_uploads"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    upload_filename = f"{profile_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}{file_ext}"
    upload_path = uploads_dir / upload_filename

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract text for analysis (basic)
    extracted_text = ""
    try:
        if file_ext == ".txt" or file_ext == ".md":
            extracted_text = content.decode("utf-8", errors="ignore")
        elif file_ext == ".pdf":
            # Would need PyPDF2 or pdfplumber
            extracted_text = "[PDF content - install PyPDF2 for extraction]"
        elif file_ext in [".docx", ".doc"]:
            # Would need python-docx
            extracted_text = "[DOCX content - install python-docx for extraction]"
    except Exception:
        pass

    # Create profile template
    profile_data = {
        "id": profile_id,
        "label": label,
        "source": {
            "type": source_type,
            "name": label,
            "version": "v1.0",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "original_files": [upload_filename],
        },
        "description": description or f"Profile created from {file.filename}",
        "suggested_scoring_template": "standard_rnd",
        "suggested_pricing_profile": "commercial_eu_ua",
        "requirements": [
            {
                "id": f"REQ_{profile_id.upper()}_001",
                "section_ref": "Section X.Y",
                "category": "documentation",
                "title": "Example Requirement",
                "description": "Edit this requirement based on your contract.",
                "metric_mapping": "documentation",
                "min_level": 2,
                "priority": "high",
                "blocking": False,
            }
        ],
        "qualitative_notes": [],
        "acceptance_thresholds": {
            "min_repo_health": 6,
            "min_tech_debt": 7,
            "min_compliance_percent": 70,
            "max_critical_failures": 0,
            "max_blocking_failures": 0,
        },
        "_meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "extracted_text_preview": extracted_text[:500] if extracted_text else None,
        },
    }

    profile_path = contracts_dir / f"{profile_id}.yaml"
    with open(profile_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)

    return {
        "message": "Contract uploaded and profile created",
        "profile_id": profile_id,
        "profile_path": str(profile_path),
        "upload_path": str(upload_path),
        "next_steps": [
            f"Edit the profile at /api/settings/profiles/contract/{profile_id}",
            "Add specific requirements mapped to metrics",
            "Set acceptance thresholds based on contract terms",
        ],
    }


# =============================================================================
# Document Templates
# =============================================================================

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"


@router.get("/templates")
async def list_templates():
    """List available document templates."""
    templates = [
        {
            "id": "act_of_work",
            "name": "Act of Work (Акт виконаних робіт)",
            "type": "act",
            "languages": ["en", "uk", "ru"],
            "description": "Official acceptance document for completed work",
            "variables": [
                "project_name", "contractor_name", "client_name",
                "work_description", "total_hours", "total_cost",
                "start_date", "end_date", "acceptance_date",
            ],
        },
        {
            "id": "invoice",
            "name": "Invoice (Рахунок-фактура)",
            "type": "invoice",
            "languages": ["en", "uk"],
            "description": "Payment invoice for services",
            "variables": [
                "invoice_number", "invoice_date", "due_date",
                "contractor_name", "contractor_address", "contractor_iban",
                "client_name", "client_address",
                "items", "subtotal", "tax", "total",
            ],
        },
        {
            "id": "service_contract",
            "name": "Service Contract (Договір на послуги)",
            "type": "contract",
            "languages": ["en", "uk"],
            "description": "Standard service agreement",
            "variables": [
                "contract_number", "contract_date",
                "contractor_name", "contractor_address",
                "client_name", "client_address",
                "scope_of_work", "deliverables",
                "price", "payment_terms", "duration",
            ],
        },
        {
            "id": "audit_report",
            "name": "Audit Report",
            "type": "report",
            "languages": ["en"],
            "description": "Full repository audit report",
            "variables": [
                "repo_name", "repo_url", "analysis_date",
                "scores", "recommendations", "cost_estimates",
            ],
        },
        {
            "id": "technical_summary",
            "name": "Technical Summary",
            "type": "report",
            "languages": ["en", "uk"],
            "description": "Brief technical overview for stakeholders",
            "variables": [
                "repo_name", "product_level", "complexity",
                "key_findings", "next_steps",
            ],
        },
    ]

    return {"templates": templates, "count": len(templates)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str, language: str = "en"):
    """Get template details and content."""
    # In production, load from templates directory
    # For now, return structure info
    return {
        "id": template_id,
        "language": language,
        "content_type": "jinja2",
        "message": "Template content would be loaded here",
    }


# =============================================================================
# System Settings
# =============================================================================

@router.get("/system")
async def get_system_settings():
    """Get current system settings."""
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "region_mode": settings.REGION_MODE,
        "clone_timeout": settings.CLONE_TIMEOUT,
        "max_repo_size_mb": settings.MAX_REPO_SIZE_MB,
        "semgrep_enabled": settings.SEMGREP_ENABLED,
        "api_key_required": settings.API_KEY_REQUIRED,
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
    }


@router.get("/system/health")
async def system_health():
    """Check system health and dependencies."""
    health = {
        "status": "healthy",
        "checks": {},
    }

    # Check profiles directory
    health["checks"]["profiles_dir"] = {
        "exists": PROFILES_DIR.exists(),
        "contract_count": len(list((PROFILES_DIR / "contract").glob("*.yaml"))) if (PROFILES_DIR / "contract").exists() else 0,
        "scoring_count": len(list((PROFILES_DIR / "scoring").glob("*.yaml"))) if (PROFILES_DIR / "scoring").exists() else 0,
        "pricing_count": len(list((PROFILES_DIR / "pricing").glob("*.yaml"))) if (PROFILES_DIR / "pricing").exists() else 0,
    }

    # Check optional dependencies
    try:
        import reportlab
        health["checks"]["reportlab"] = {"installed": True, "for": "PDF generation"}
    except ImportError:
        health["checks"]["reportlab"] = {"installed": False, "for": "PDF generation"}

    try:
        import openpyxl
        health["checks"]["openpyxl"] = {"installed": True, "for": "Excel generation"}
    except ImportError:
        health["checks"]["openpyxl"] = {"installed": False, "for": "Excel generation"}

    try:
        import docx
        health["checks"]["python-docx"] = {"installed": True, "for": "Word generation"}
    except ImportError:
        health["checks"]["python-docx"] = {"installed": False, "for": "Word generation"}

    return health
