"""
Document Management API endpoints.

Handles document upload, storage, processing, and retrieval
for contracts, policies, templates, and other documents.
"""
import base64
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.database import (
    DocumentType,
    ProcessingStatus,
    DocumentLinkType,
)
from app.services.document_repository import DocumentRepository
from app.services.file_storage import FileStorageService, StorageError
from app.core.config import settings

router = APIRouter(prefix="/document-management", tags=["Document Management"])


# =========================================================================
# PYDANTIC MODELS
# =========================================================================


class DocumentResponse(BaseModel):
    """Response model for document."""
    id: str
    title: str
    document_type: str
    file_name: Optional[str]
    mime_type: Optional[str]
    file_size: Optional[int]
    storage_backend: str
    processing_status: str
    extraction_confidence: Optional[int]
    extraction_method: Optional[str]
    created_at: str
    updated_at: Optional[str]
    version: int

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for document list."""
    documents: List[DocumentResponse]
    total: int
    limit: int
    offset: int


class ContractDataResponse(BaseModel):
    """Response model for contract data."""
    id: str
    document_id: str
    contract_number: Optional[str]
    contract_title: Optional[str]
    contract_date: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    total_amount: Optional[int]
    currency: Optional[str]
    client_name: Optional[str]
    contractor_name: Optional[str]
    work_plan: Optional[list]
    budget_breakdown: Optional[list]
    milestones: Optional[list]
    deliverables: Optional[list]

    class Config:
        from_attributes = True


class UploadDocumentRequest(BaseModel):
    """Request to upload document via base64."""
    title: str
    document_type: str
    file_content: str  # base64 encoded
    file_name: str
    storage_backend: str = "local"
    analysis_id: Optional[str] = None


class UpdateContractDataRequest(BaseModel):
    """Request to update contract data."""
    contract_number: Optional[str] = None
    contract_title: Optional[str] = None
    contract_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_amount: Optional[int] = None
    currency: Optional[str] = None
    client_name: Optional[str] = None
    contractor_name: Optional[str] = None
    work_plan: Optional[list] = None
    budget_breakdown: Optional[list] = None
    milestones: Optional[list] = None
    deliverables: Optional[list] = None


class LinkDocumentRequest(BaseModel):
    """Request to link document to analysis."""
    document_id: str
    analysis_id: str
    link_type: str = "reference"
    notes: Optional[str] = None


class StorageBackendInfo(BaseModel):
    """Storage backend information."""
    name: str
    label: str
    available: bool
    configured: bool


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================


def get_mime_type(filename: str) -> str:
    """Guess MIME type from filename."""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def document_to_response(doc) -> DocumentResponse:
    """Convert Document model to response."""
    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        document_type=doc.document_type.value if doc.document_type else "other",
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        storage_backend=doc.storage_backend or "db",
        processing_status=doc.processing_status.value if doc.processing_status else "pending",
        extraction_confidence=doc.extraction_confidence,
        extraction_method=doc.extraction_method,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
        version=doc.version or 1,
    )


# =========================================================================
# MOCK DATABASE SESSION (Replace with real dependency injection)
# =========================================================================


# In production, this would be injected via FastAPI Depends
# For now, we'll create a mock that works without actual DB
class MockSession:
    """Mock session for development without DB."""

    _documents = {}
    _contract_data = {}
    _links = {}

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    def add(self, obj):
        if hasattr(obj, '__tablename__'):
            if obj.__tablename__ == 'documents':
                self._documents[str(obj.id)] = obj
            elif obj.__tablename__ == 'contract_data':
                self._contract_data[str(obj.document_id)] = obj

    async def delete(self, obj):
        if hasattr(obj, '__tablename__'):
            if obj.__tablename__ == 'documents':
                self._documents.pop(str(obj.id), None)

    async def execute(self, query):
        # Return empty result
        class MockResult:
            def scalar_one_or_none(self):
                return None
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return []
                return MockScalars()
        return MockResult()


async def get_db_session():
    """Get database session - mock for now."""
    # In production, use proper async session from SQLAlchemy
    # from app.core.database import get_session
    # return await get_session()
    return MockSession()


# =========================================================================
# ENDPOINTS: Storage
# =========================================================================


@router.get("/storage/backends")
async def list_storage_backends():
    """
    List available storage backends and their status.

    Returns configured backends: local, db, s3, gdrive
    """
    backends = FileStorageService.list_backends()
    return {
        "backends": backends,
        "default": FileStorageService._default_backend,
    }


# =========================================================================
# ENDPOINTS: Documents CRUD
# =========================================================================


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(default="other"),
    storage_backend: str = Form(default="local"),
    analysis_id: Optional[str] = Form(default=None),
):
    """
    Upload a document file.

    Supports: PDF, DOCX, DOC, TXT, MD, JSON, CSV, XLSX, XLS

    Args:
        file: File to upload
        title: Document title
        document_type: Type (contract, policy, template, report, invoice, act, other)
        storage_backend: Where to store (local, db, s3, gdrive)
        analysis_id: Optional analysis to link to
    """
    # Validate document type
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        valid_types = [dt.value for dt in DocumentType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {document_type}. Valid: {valid_types}"
        )

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate storage backend
    valid_backends = ["local", "db", "s3", "gdrive"]
    if storage_backend not in valid_backends:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid storage backend: {storage_backend}. Valid: {valid_backends}"
        )

    try:
        # Get session
        session = await get_db_session()
        repo = DocumentRepository(session)

        # Create document
        document = await repo.create_document(
            title=title,
            document_type=doc_type,
            file_content=content,
            file_name=file.filename,
            mime_type=file.content_type or get_mime_type(file.filename or ""),
            storage_backend=storage_backend,
            analysis_id=UUID(analysis_id) if analysis_id else None,
        )

        return document_to_response(document)

    except StorageError as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.post("/documents/base64", response_model=DocumentResponse)
async def upload_document_base64(request: UploadDocumentRequest):
    """
    Upload a document via base64 encoded content.

    Useful for API integrations and browser uploads.
    """
    # Validate document type
    try:
        doc_type = DocumentType(request.document_type)
    except ValueError:
        valid_types = [dt.value for dt in DocumentType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {request.document_type}. Valid: {valid_types}"
        )

    # Decode base64 content
    try:
        content = base64.b64decode(request.file_content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")

    if not content:
        raise HTTPException(status_code=400, detail="Empty file content")

    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        document = await repo.create_document(
            title=request.title,
            document_type=doc_type,
            file_content=content,
            file_name=request.file_name,
            mime_type=get_mime_type(request.file_name),
            storage_backend=request.storage_backend,
            analysis_id=UUID(request.analysis_id) if request.analysis_id else None,
        )

        return document_to_response(document)

    except StorageError as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    document_type: Optional[str] = Query(default=None),
    processing_status: Optional[str] = Query(default=None),
    analysis_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List documents with optional filters.

    Args:
        document_type: Filter by type (contract, policy, etc.)
        processing_status: Filter by status (pending, processing, completed, failed)
        analysis_id: Filter by linked analysis
        search: Search in title/filename
        limit: Max results (default 50, max 100)
        offset: Skip results for pagination
    """
    # Parse filters
    doc_type = None
    if document_type:
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            pass

    status = None
    if processing_status:
        try:
            status = ProcessingStatus(processing_status)
        except ValueError:
            pass

    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        documents = await repo.list_documents(
            document_type=doc_type,
            processing_status=status,
            analysis_id=UUID(analysis_id) if analysis_id else None,
            search_query=search,
            limit=limit,
            offset=offset,
        )

        return DocumentListResponse(
            documents=[document_to_response(d) for d in documents],
            total=len(documents),  # In production, get actual count
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e}")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get document metadata by ID."""
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        document = await repo.get_document(
            UUID(document_id),
            include_contract_data=True,
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document_to_response(document)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {e}")


@router.get("/documents/{document_id}/download")
async def download_document(document_id: str):
    """
    Download document content.

    Returns file as streaming response with appropriate content type.
    """
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        document = await repo.get_document(UUID(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        content = await repo.get_document_content(UUID(document_id))
        if not content:
            raise HTTPException(status_code=404, detail="Document content not found")

        return StreamingResponse(
            iter([content]),
            media_type=document.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{document.file_name or document.title}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download: {e}")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    permanent: bool = Query(default=False),
):
    """
    Delete a document.

    Args:
        document_id: Document ID
        permanent: If True, permanently delete. Otherwise soft delete.
    """
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        deleted = await repo.delete_document(
            UUID(document_id),
            soft_delete=not permanent,
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"success": True, "message": "Document deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")


# =========================================================================
# ENDPOINTS: Contract Data
# =========================================================================


@router.get("/documents/{document_id}/contract-data", response_model=ContractDataResponse)
async def get_contract_data(document_id: str):
    """Get extracted contract data for a document."""
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        contract_data = await repo.get_contract_data(UUID(document_id))
        if not contract_data:
            raise HTTPException(status_code=404, detail="Contract data not found")

        return ContractDataResponse(
            id=str(contract_data.id),
            document_id=str(contract_data.document_id),
            contract_number=contract_data.contract_number,
            contract_title=contract_data.contract_title,
            contract_date=contract_data.contract_date.isoformat() if contract_data.contract_date else None,
            start_date=contract_data.start_date.isoformat() if contract_data.start_date else None,
            end_date=contract_data.end_date.isoformat() if contract_data.end_date else None,
            total_amount=contract_data.total_amount,
            currency=contract_data.currency,
            client_name=contract_data.client_name,
            contractor_name=contract_data.contractor_name,
            work_plan=contract_data.work_plan,
            budget_breakdown=contract_data.budget_breakdown,
            milestones=contract_data.milestones,
            deliverables=contract_data.deliverables,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract data: {e}")


@router.put("/documents/{document_id}/contract-data", response_model=ContractDataResponse)
async def update_contract_data(
    document_id: str,
    request: UpdateContractDataRequest,
):
    """
    Update contract data for a document.

    Can be used to:
    - Manually correct extracted data
    - Add missing fields
    - Update after review
    """
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        # Check document exists
        document = await repo.get_document(UUID(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Build update dict (only non-None values)
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        # Parse dates if provided
        for date_field in ['contract_date', 'start_date', 'end_date']:
            if date_field in updates and isinstance(updates[date_field], str):
                from datetime import datetime
                updates[date_field] = datetime.fromisoformat(updates[date_field])

        # Get or create contract data
        contract_data = await repo.get_contract_data(UUID(document_id))

        if contract_data:
            contract_data = await repo.update_contract_data(UUID(document_id), **updates)
        else:
            contract_data = await repo.create_contract_data(UUID(document_id), **updates)

        return ContractDataResponse(
            id=str(contract_data.id),
            document_id=str(contract_data.document_id),
            contract_number=contract_data.contract_number,
            contract_title=contract_data.contract_title,
            contract_date=contract_data.contract_date.isoformat() if contract_data.contract_date else None,
            start_date=contract_data.start_date.isoformat() if contract_data.start_date else None,
            end_date=contract_data.end_date.isoformat() if contract_data.end_date else None,
            total_amount=contract_data.total_amount,
            currency=contract_data.currency,
            client_name=contract_data.client_name,
            contractor_name=contract_data.contractor_name,
            work_plan=contract_data.work_plan,
            budget_breakdown=contract_data.budget_breakdown,
            milestones=contract_data.milestones,
            deliverables=contract_data.deliverables,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update contract data: {e}")


# =========================================================================
# ENDPOINTS: Document-Analysis Linking
# =========================================================================


@router.post("/documents/link")
async def link_document_to_analysis(request: LinkDocumentRequest):
    """
    Link a document to an analysis run.

    Link types:
    - source_contract: Original contract for analysis
    - reference: Reference document
    - generated: Document generated from analysis
    - comparison: Document used for comparison
    """
    try:
        link_type = DocumentLinkType(request.link_type)
    except ValueError:
        valid_types = [lt.value for lt in DocumentLinkType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid link type: {request.link_type}. Valid: {valid_types}"
        )

    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        link = await repo.link_document_to_analysis(
            document_id=UUID(request.document_id),
            analysis_id=UUID(request.analysis_id),
            link_type=link_type,
            notes=request.notes,
        )

        return {
            "success": True,
            "link_id": str(link.id),
            "document_id": request.document_id,
            "analysis_id": request.analysis_id,
            "link_type": request.link_type,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to link document: {e}")


@router.get("/documents/by-analysis/{analysis_id}")
async def get_documents_for_analysis(
    analysis_id: str,
    link_type: Optional[str] = Query(default=None),
):
    """Get all documents linked to an analysis."""
    lt = None
    if link_type:
        try:
            lt = DocumentLinkType(link_type)
        except ValueError:
            pass

    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        documents = await repo.get_documents_for_analysis(
            UUID(analysis_id),
            link_type=lt,
        )

        return {
            "analysis_id": analysis_id,
            "documents": [document_to_response(d) for d in documents],
            "count": len(documents),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {e}")


@router.delete("/documents/{document_id}/unlink/{analysis_id}")
async def unlink_document_from_analysis(document_id: str, analysis_id: str):
    """Remove link between document and analysis."""
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        unlinked = await repo.unlink_document_from_analysis(
            UUID(document_id),
            UUID(analysis_id),
        )

        if not unlinked:
            raise HTTPException(status_code=404, detail="Link not found")

        return {"success": True, "message": "Document unlinked from analysis"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unlink: {e}")


# =========================================================================
# ENDPOINTS: Processing
# =========================================================================


@router.post("/documents/{document_id}/process")
async def trigger_document_processing(document_id: str):
    """
    Trigger processing/extraction for a document.

    This will:
    1. Extract text from PDF/DOCX
    2. Run pattern-based extraction
    3. Run LLM extraction (if enabled)
    4. Store extracted data
    """
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        document = await repo.get_document(UUID(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update status to processing
        await repo.set_processing_status(
            UUID(document_id),
            ProcessingStatus.processing,
        )

        # TODO: Queue actual processing job
        # For now, just return acknowledgement

        return {
            "success": True,
            "document_id": document_id,
            "status": "processing",
            "message": "Document queued for processing",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {e}")


@router.get("/documents/pending")
async def get_pending_documents(limit: int = Query(default=10, le=50)):
    """Get documents pending processing."""
    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        documents = await repo.get_pending_documents(limit=limit)

        return {
            "documents": [document_to_response(d) for d in documents],
            "count": len(documents),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending documents: {e}")


# =========================================================================
# ENDPOINTS: Document Types Info
# =========================================================================


@router.get("/document-types")
async def list_document_types():
    """List available document types."""
    return {
        "types": [
            {
                "id": dt.value,
                "name": dt.value.replace("_", " ").title(),
                "description": _get_type_description(dt),
            }
            for dt in DocumentType
        ]
    }


def _get_type_description(dt: DocumentType) -> str:
    """Get description for document type."""
    descriptions = {
        DocumentType.contract: "Contracts and agreements",
        DocumentType.policy: "Policies and compliance documents",
        DocumentType.template: "Document templates",
        DocumentType.report: "Reports and analysis documents",
        DocumentType.invoice: "Invoices and billing documents",
        DocumentType.act: "Acts and certificates",
        DocumentType.other: "Other documents",
    }
    return descriptions.get(dt, "")


# =========================================================================
# ENDPOINTS: Extraction
# =========================================================================


class ExtractionRequest(BaseModel):
    """Request for document extraction."""
    method: str = "hybrid"  # regex, llm, hybrid
    task_type: str = "contract"  # contract, policy


class ExtractionResponse(BaseModel):
    """Response from document extraction."""
    success: bool
    method: str
    confidence: int
    contract_number: Optional[str] = None
    contract_title: Optional[str] = None
    contract_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_amount: Optional[int] = None
    currency: Optional[str] = None
    client_name: Optional[str] = None
    contractor_name: Optional[str] = None
    work_plan: Optional[list] = None
    budget_breakdown: Optional[list] = None
    milestones: Optional[list] = None
    deliverables: Optional[list] = None
    error: Optional[str] = None


@router.post("/documents/{document_id}/extract", response_model=ExtractionResponse)
async def extract_document_data(
    document_id: str,
    request: ExtractionRequest,
):
    """
    Extract structured data from a document using LLM and patterns.

    Methods:
    - regex: Fast pattern-based extraction (lower confidence)
    - llm: LLM-based extraction (higher confidence, requires API)
    - hybrid: Combined approach (best results)

    Task types:
    - contract: Extract contract metadata, work plan, budget
    - policy: Extract policies and requirements
    """
    from app.services.document_extraction import extraction_service
    from app.llm.models import TaskType

    # Validate method
    valid_methods = ["regex", "llm", "hybrid"]
    if request.method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid method: {request.method}. Valid: {valid_methods}"
        )

    # Map task type
    task_type = (
        TaskType.POLICY_EXTRACTION
        if request.task_type == "policy"
        else TaskType.CONTRACT_EXTRACTION
    )

    try:
        session = await get_db_session()
        repo = DocumentRepository(session)

        # Get document
        document = await repo.get_document(UUID(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get document content
        content = await repo.get_document_content(UUID(document_id))
        if not content:
            raise HTTPException(status_code=404, detail="Document content not found")

        # Update status to processing
        await repo.set_processing_status(UUID(document_id), ProcessingStatus.processing)

        # Run extraction
        result = await extraction_service.extract(
            content=content,
            mime_type=document.mime_type or "application/octet-stream",
            method=request.method,
            task_type=task_type,
        )

        # Update status and store results
        if result.success:
            await repo.set_processing_status(
                UUID(document_id),
                ProcessingStatus.completed,
                extraction_confidence=result.confidence,
                extraction_method=result.method,
            )

            # Store contract data
            contract_data_dict = {
                "contract_number": result.contract_number,
                "contract_title": result.contract_title,
                "contract_date": result.contract_date,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "total_amount": result.total_amount,
                "currency": result.currency,
                "client_name": result.client_name,
                "client_address": result.client_address,
                "contractor_name": result.contractor_name,
                "contractor_address": result.contractor_address,
                "work_plan": result.work_plan,
                "budget_breakdown": result.budget_breakdown,
                "milestones": result.milestones,
                "deliverables": result.deliverables,
                "indicators": result.indicators,
                "policies": result.policies,
                "raw_sections": result.raw_sections,
            }

            # Check if contract data exists
            existing = await repo.get_contract_data(UUID(document_id))
            if existing:
                await repo.update_contract_data(UUID(document_id), **contract_data_dict)
            else:
                await repo.create_contract_data(UUID(document_id), **contract_data_dict)
        else:
            await repo.set_processing_status(
                UUID(document_id),
                ProcessingStatus.failed,
                error_message=result.error,
            )

        return ExtractionResponse(
            success=result.success,
            method=result.method,
            confidence=result.confidence,
            contract_number=result.contract_number,
            contract_title=result.contract_title,
            contract_date=result.contract_date.isoformat() if result.contract_date else None,
            start_date=result.start_date.isoformat() if result.start_date else None,
            end_date=result.end_date.isoformat() if result.end_date else None,
            total_amount=result.total_amount,
            currency=result.currency,
            client_name=result.client_name,
            contractor_name=result.contractor_name,
            work_plan=result.work_plan,
            budget_breakdown=result.budget_breakdown,
            milestones=result.milestones,
            deliverables=result.deliverables,
            error=result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@router.post("/extract/text")
async def extract_from_text(
    text: str = Form(...),
    method: str = Form(default="hybrid"),
    task_type: str = Form(default="contract"),
):
    """
    Extract structured data from raw text.

    Useful for testing extraction without uploading a file.
    """
    from app.services.document_extraction import extraction_service
    from app.llm.models import TaskType

    task = (
        TaskType.POLICY_EXTRACTION
        if task_type == "policy"
        else TaskType.CONTRACT_EXTRACTION
    )

    try:
        result = await extraction_service.extract_from_text(
            text=text,
            method=method,
            task_type=task,
        )

        return ExtractionResponse(
            success=result.success,
            method=result.method,
            confidence=result.confidence,
            contract_number=result.contract_number,
            contract_title=result.contract_title,
            contract_date=result.contract_date.isoformat() if result.contract_date else None,
            start_date=result.start_date.isoformat() if result.start_date else None,
            end_date=result.end_date.isoformat() if result.end_date else None,
            total_amount=result.total_amount,
            currency=result.currency,
            client_name=result.client_name,
            contractor_name=result.contractor_name,
            work_plan=result.work_plan,
            budget_breakdown=result.budget_breakdown,
            milestones=result.milestones,
            deliverables=result.deliverables,
            error=result.error,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
