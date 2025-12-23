"""
LLM API Routes for Repo Auditor
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm import get_llm_client, get_llm_analyzer, TaskType

router = APIRouter(prefix="/llm")


class ReadmeAnalysisRequest(BaseModel):
    content: str


class CodeQualityRequest(BaseModel):
    code: str
    language: str
    filename: str


class TZGenerationRequest(BaseModel):
    project_name: str
    repo_health: int
    tech_debt: int
    readiness: int
    issues: str
    project_type: str
    required_repo_health: int
    required_tech_debt: int
    required_readiness: int


class RecommendationsRequest(BaseModel):
    project_name: str
    analysis_summary: str
    health_gap: int
    debt_gap: int
    readiness_gap: int


class SimpleQueryRequest(BaseModel):
    prompt: str
    task_type: str = "simple_analysis"
    system_prompt: str = ""


@router.get("/providers")
async def get_available_providers() -> Dict[str, bool]:
    """Check which LLM providers are available"""
    client = get_llm_client()
    return await client.get_available_providers()


@router.post("/analyze/readme")
async def analyze_readme(request: ReadmeAnalysisRequest) -> Dict[str, Any]:
    """Analyze README quality"""
    if not request.content:
        raise HTTPException(status_code=400, detail="No README content provided")

    analyzer = get_llm_analyzer()
    result = await analyzer.analyze_readme(request.content)
    return result


@router.post("/analyze/code")
async def analyze_code_quality(request: CodeQualityRequest) -> Dict[str, Any]:
    """Analyze code quality for a file"""
    if not request.code:
        raise HTTPException(status_code=400, detail="No code content provided")

    analyzer = get_llm_analyzer()
    result = await analyzer.analyze_code_quality(
        request.code,
        request.language,
        request.filename,
    )
    return result


@router.post("/analyze/security")
async def security_review(request: CodeQualityRequest) -> Dict[str, Any]:
    """Security review for code"""
    if not request.code:
        raise HTTPException(status_code=400, detail="No code content provided")

    analyzer = get_llm_analyzer()
    result = await analyzer.security_review(
        request.code,
        request.language,
        request.filename,
    )
    return result


@router.post("/generate/tz")
async def generate_tz(request: TZGenerationRequest) -> Dict[str, str]:
    """Generate Technical Specification (ТЗ)"""
    analyzer = get_llm_analyzer()
    tz_content = await analyzer.generate_tz(
        project_name=request.project_name,
        repo_health=request.repo_health,
        tech_debt=request.tech_debt,
        readiness=request.readiness,
        issues=request.issues,
        project_type=request.project_type,
        required_repo_health=request.required_repo_health,
        required_tech_debt=request.required_tech_debt,
        required_readiness=request.required_readiness,
    )
    return {"tz": tz_content}


@router.post("/generate/recommendations")
async def generate_recommendations(request: RecommendationsRequest) -> Dict[str, Any]:
    """Generate prioritized recommendations"""
    analyzer = get_llm_analyzer()
    result = await analyzer.generate_recommendations(
        project_name=request.project_name,
        analysis_summary=request.analysis_summary,
        health_gap=request.health_gap,
        debt_gap=request.debt_gap,
        readiness_gap=request.readiness_gap,
    )
    return result


@router.post("/query")
async def simple_query(request: SimpleQueryRequest) -> Dict[str, str]:
    """Simple LLM query"""
    try:
        task_type = TaskType(request.task_type)
    except ValueError:
        task_type = TaskType.SIMPLE_ANALYSIS

    client = get_llm_client()
    result = await client.query_simple(
        prompt=request.prompt,
        task_type=task_type,
        system_prompt=request.system_prompt,
    )
    return {"response": result}
