"""
Document Repository - data access layer for documents.

Handles all document CRUD operations and queries.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.models.database import (
    Document,
    DocumentType,
    ProcessingStatus,
    ContractData,
    DocumentAnalysisLink,
    DocumentLinkType,
    ExtractionPattern,
)
from app.services.file_storage import FileStorageService, StorageError


class DocumentRepository:
    """Repository for document operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # DOCUMENT CRUD
    # =========================================================================

    async def create_document(
        self,
        title: str,
        document_type: DocumentType,
        file_content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        storage_backend: str = "local",
        analysis_id: Optional[UUID] = None,
        original_text: Optional[str] = None,
    ) -> Document:
        """
        Create a new document with optional file content.

        Args:
            title: Document title
            document_type: Type of document
            file_content: Raw file bytes (optional)
            file_name: Original filename (optional)
            mime_type: MIME type (optional)
            storage_backend: Where to store file (local, db, s3, gdrive)
            analysis_id: Link to analysis run (optional)
            original_text: Text content for text-based documents

        Returns:
            Created Document instance
        """
        storage_key = None
        file_size = None

        # Store file if provided
        if file_content:
            file_size = len(file_content)

            if storage_backend == "db":
                # Store in database (original_content field)
                storage_key = "db:inline"
            else:
                # Store in external storage
                storage_key, _ = await FileStorageService.save(
                    content=file_content,
                    filename=file_name or title,
                    content_type=mime_type,
                    backend=storage_backend,
                )

        document = Document(
            title=title,
            document_type=document_type,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            storage_backend=storage_backend,
            storage_key=storage_key,
            analysis_id=analysis_id,
            processing_status=ProcessingStatus.pending,
        )

        # Store text content in DB if provided or if using db backend
        if original_text:
            document.original_content = original_text
        elif storage_backend == "db" and file_content:
            # Store as text if text-based, otherwise keep binary reference
            if mime_type and mime_type.startswith("text/"):
                document.original_content = file_content.decode("utf-8", errors="replace")

        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def get_document(
        self,
        document_id: UUID,
        include_contract_data: bool = False,
        include_analysis_links: bool = False,
    ) -> Optional[Document]:
        """Get document by ID with optional related data."""
        query = select(Document).where(
            and_(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )

        if include_contract_data:
            query = query.options(selectinload(Document.contract_data))

        if include_analysis_links:
            query = query.options(selectinload(Document.analysis_links))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_document_content(self, document_id: UUID) -> Optional[bytes]:
        """
        Get document file content.

        Returns content from appropriate storage backend.
        """
        document = await self.get_document(document_id)
        if not document:
            return None

        if document.storage_backend == "db":
            # Content is in original_content field
            if document.original_content:
                return document.original_content.encode("utf-8")
            return None

        if not document.storage_key:
            return None

        # Load from external storage
        return await FileStorageService.load(
            storage_key=document.storage_key,
            backend=document.storage_backend,
        )

    async def update_document(
        self,
        document_id: UUID,
        **updates,
    ) -> Optional[Document]:
        """Update document fields."""
        document = await self.get_document(document_id)
        if not document:
            return None

        for key, value in updates.items():
            if hasattr(document, key):
                setattr(document, key, value)

        document.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def delete_document(
        self,
        document_id: UUID,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete document.

        Args:
            document_id: Document ID
            soft_delete: If True, set deleted_at instead of removing

        Returns:
            True if deleted
        """
        document = await self.get_document(document_id)
        if not document:
            return False

        if soft_delete:
            document.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()
        else:
            # Delete from storage first
            if document.storage_key and document.storage_backend != "db":
                try:
                    await FileStorageService.delete(
                        storage_key=document.storage_key,
                        backend=document.storage_backend,
                    )
                except StorageError:
                    pass  # Continue with DB deletion even if storage fails

            await self.session.delete(document)
            await self.session.commit()

        return True

    async def list_documents(
        self,
        document_type: Optional[DocumentType] = None,
        processing_status: Optional[ProcessingStatus] = None,
        analysis_id: Optional[UUID] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """
        List documents with filters.

        Args:
            document_type: Filter by type
            processing_status: Filter by processing status
            analysis_id: Filter by linked analysis
            search_query: Search in title/filename
            limit: Max results
            offset: Skip results

        Returns:
            List of documents
        """
        query = select(Document).where(Document.deleted_at.is_(None))

        if document_type:
            query = query.where(Document.document_type == document_type)

        if processing_status:
            query = query.where(Document.processing_status == processing_status)

        if analysis_id:
            query = query.where(Document.analysis_id == analysis_id)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                or_(
                    Document.title.ilike(search_pattern),
                    Document.file_name.ilike(search_pattern),
                )
            )

        query = query.order_by(Document.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # CONTRACT DATA
    # =========================================================================

    async def create_contract_data(
        self,
        document_id: UUID,
        **contract_fields,
    ) -> ContractData:
        """Create contract data for a document."""
        contract_data = ContractData(
            document_id=document_id,
            **contract_fields,
        )

        self.session.add(contract_data)
        await self.session.commit()
        await self.session.refresh(contract_data)

        return contract_data

    async def update_contract_data(
        self,
        document_id: UUID,
        **updates,
    ) -> Optional[ContractData]:
        """Update contract data fields."""
        query = select(ContractData).where(ContractData.document_id == document_id)
        result = await self.session.execute(query)
        contract_data = result.scalar_one_or_none()

        if not contract_data:
            return None

        for key, value in updates.items():
            if hasattr(contract_data, key):
                setattr(contract_data, key, value)

        contract_data.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(contract_data)

        return contract_data

    async def get_contract_data(self, document_id: UUID) -> Optional[ContractData]:
        """Get contract data by document ID."""
        query = select(ContractData).where(ContractData.document_id == document_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    # =========================================================================
    # DOCUMENT-ANALYSIS LINKS
    # =========================================================================

    async def link_document_to_analysis(
        self,
        document_id: UUID,
        analysis_id: UUID,
        link_type: DocumentLinkType = DocumentLinkType.reference,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> DocumentAnalysisLink:
        """Create link between document and analysis."""
        link = DocumentAnalysisLink(
            document_id=document_id,
            analysis_id=analysis_id,
            link_type=link_type,
            notes=notes,
            created_by=created_by,
        )

        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)

        return link

    async def get_documents_for_analysis(
        self,
        analysis_id: UUID,
        link_type: Optional[DocumentLinkType] = None,
    ) -> list[Document]:
        """Get all documents linked to an analysis."""
        query = (
            select(Document)
            .join(DocumentAnalysisLink)
            .where(
                and_(
                    DocumentAnalysisLink.analysis_id == analysis_id,
                    Document.deleted_at.is_(None),
                )
            )
        )

        if link_type:
            query = query.where(DocumentAnalysisLink.link_type == link_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_analyses_for_document(
        self,
        document_id: UUID,
    ) -> list[DocumentAnalysisLink]:
        """Get all analysis links for a document."""
        query = select(DocumentAnalysisLink).where(
            DocumentAnalysisLink.document_id == document_id
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def unlink_document_from_analysis(
        self,
        document_id: UUID,
        analysis_id: UUID,
    ) -> bool:
        """Remove link between document and analysis."""
        query = select(DocumentAnalysisLink).where(
            and_(
                DocumentAnalysisLink.document_id == document_id,
                DocumentAnalysisLink.analysis_id == analysis_id,
            )
        )
        result = await self.session.execute(query)
        link = result.scalar_one_or_none()

        if not link:
            return False

        await self.session.delete(link)
        await self.session.commit()
        return True

    # =========================================================================
    # PROCESSING STATUS
    # =========================================================================

    async def set_processing_status(
        self,
        document_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None,
        extraction_confidence: Optional[int] = None,
        extraction_method: Optional[str] = None,
    ) -> Optional[Document]:
        """Update document processing status."""
        document = await self.get_document(document_id)
        if not document:
            return None

        document.processing_status = status

        if status == ProcessingStatus.completed:
            document.processed_at = datetime.now(timezone.utc)

        if error_message:
            document.processing_error = error_message

        if extraction_confidence is not None:
            document.extraction_confidence = extraction_confidence

        if extraction_method:
            document.extraction_method = extraction_method

        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def get_pending_documents(
        self,
        limit: int = 10,
    ) -> list[Document]:
        """Get documents pending processing."""
        query = (
            select(Document)
            .where(
                and_(
                    Document.processing_status == ProcessingStatus.pending,
                    Document.deleted_at.is_(None),
                )
            )
            .order_by(Document.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # EXTRACTION PATTERNS
    # =========================================================================

    async def create_extraction_pattern(
        self,
        pattern_type: str,
        pattern_regex: str,
        pattern_description: Optional[str] = None,
        examples: Optional[list] = None,
    ) -> ExtractionPattern:
        """Create a new extraction pattern."""
        pattern = ExtractionPattern(
            pattern_type=pattern_type,
            pattern_regex=pattern_regex,
            pattern_description=pattern_description,
            examples=examples or [],
        )

        self.session.add(pattern)
        await self.session.commit()
        await self.session.refresh(pattern)

        return pattern

    async def get_active_patterns(
        self,
        pattern_type: Optional[str] = None,
    ) -> list[ExtractionPattern]:
        """Get active extraction patterns."""
        query = select(ExtractionPattern).where(
            ExtractionPattern.is_active == "true"
        )

        if pattern_type:
            query = query.where(ExtractionPattern.pattern_type == pattern_type)

        query = query.order_by(ExtractionPattern.confidence_score.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_pattern_usage(
        self,
        pattern_id: UUID,
        success: bool,
    ) -> None:
        """Update pattern usage statistics."""
        query = select(ExtractionPattern).where(ExtractionPattern.id == pattern_id)
        result = await self.session.execute(query)
        pattern = result.scalar_one_or_none()

        if pattern:
            pattern.usage_count = (pattern.usage_count or 0) + 1
            if success:
                pattern.success_count = (pattern.success_count or 0) + 1
            pattern.last_used_at = datetime.now(timezone.utc)

            # Update confidence based on success rate
            if pattern.usage_count >= 5:
                success_rate = pattern.success_count / pattern.usage_count
                pattern.confidence_score = int(success_rate * 100)

            await self.session.commit()

    # =========================================================================
    # DOCUMENT VERSIONING
    # =========================================================================

    async def create_document_version(
        self,
        parent_document_id: UUID,
        file_content: bytes,
        file_name: Optional[str] = None,
    ) -> Document:
        """Create a new version of a document."""
        parent = await self.get_document(parent_document_id)
        if not parent:
            raise ValueError(f"Parent document {parent_document_id} not found")

        # Create new document as version
        new_version = await self.create_document(
            title=parent.title,
            document_type=parent.document_type,
            file_content=file_content,
            file_name=file_name or parent.file_name,
            mime_type=parent.mime_type,
            storage_backend=parent.storage_backend,
            analysis_id=parent.analysis_id,
        )

        # Set parent reference and version number
        new_version.parent_document_id = parent_document_id
        new_version.version = parent.version + 1

        await self.session.commit()
        await self.session.refresh(new_version)

        return new_version

    async def get_document_versions(
        self,
        document_id: UUID,
    ) -> list[Document]:
        """Get all versions of a document."""
        # Find the root document (no parent)
        doc = await self.get_document(document_id)
        if not doc:
            return []

        # Find root
        root_id = document_id
        while doc.parent_document_id:
            root_id = doc.parent_document_id
            doc = await self.get_document(root_id)
            if not doc:
                break

        # Get all versions descending from root
        query = (
            select(Document)
            .where(
                or_(
                    Document.id == root_id,
                    Document.parent_document_id == root_id,
                )
            )
            .order_by(Document.version.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
