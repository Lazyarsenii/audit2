"""
Repo Auditor - Main FastAPI Application.

Run with: uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, analyze, reports, github_webhook, metrics, documents, contracts, projects
from app.api.routes import settings as settings_routes
from app.api.routes import financial_docs
from app.api.routes import llm as llm_routes
from app.api.routes import browse as browse_routes
from app.api.routes import contract_parser as contract_parser_routes
from app.api.routes import readiness as readiness_routes
from app.api.routes import upload as upload_routes
from app.api.routes import export as export_routes
from app.api.routes import gdrive as gdrive_routes
from app.api.routes import document_management as document_management_routes
from app.api.routes import github_repos as github_repos_routes
from app.api.routes import progress as progress_routes
from app.api.routes import quick_audit as quick_audit_routes
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.middleware import RateLimitMiddleware, APIKeyMiddleware, RequestLoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Repo Auditor...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Repo Auditor...")
    await close_db()
    logger.info("Cleanup complete")


app = FastAPI(
    title="Repo Auditor",
    description="Automated repository analysis and evaluation service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware - include Vercel domains automatically
cors_origins = settings.cors_origins_list.copy() if settings.cors_origins_list else []
# Add common Vercel deployment patterns
cors_origins.extend([
    "https://ui-maxs-projects-386ddd54.vercel.app",
    "https://ui-three-rho.vercel.app",
    "https://ui-git-main-maxs-projects-386ddd54.vercel.app",
])
# Remove duplicates
cors_origins = list(set(cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    burst_limit=settings.RATE_LIMIT_BURST,
)

# API key middleware (optional, controlled by settings)
if settings.API_KEY_REQUIRED:
    app.add_middleware(APIKeyMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(github_webhook.router, prefix="/api/github", tags=["GitHub"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(contracts.router, prefix="/api", tags=["Contracts"])
app.include_router(settings_routes.router, prefix="/api", tags=["Settings"])
app.include_router(financial_docs.router, prefix="/api", tags=["Financial"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(llm_routes.router, prefix="/api", tags=["LLM"])
app.include_router(browse_routes.router, tags=["Browse"])
app.include_router(contract_parser_routes.router, prefix="/api", tags=["Contract Parser"])
app.include_router(readiness_routes.router, prefix="/api", tags=["Readiness"])
app.include_router(upload_routes.router, prefix="/api", tags=["Upload"])
app.include_router(export_routes.router, prefix="/api", tags=["Export"])
app.include_router(gdrive_routes.router, prefix="/api", tags=["Google Drive"])
app.include_router(github_repos_routes.router, prefix="/api", tags=["GitHub Repos"])
app.include_router(progress_routes.router, prefix="/api", tags=["Progress"])
app.include_router(document_management_routes.router, prefix="/api", tags=["Document Management"])
app.include_router(quick_audit_routes.router, prefix="/api", tags=["Quick Audit"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Repo Auditor",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
