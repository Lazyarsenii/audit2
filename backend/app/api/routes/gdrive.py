"""
Google Drive API routes.

Endpoints for browsing and downloading from Google Drive.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.adapters.gdrive_adapter import gdrive_adapter, GoogleDriveError

router = APIRouter()


class FolderItem(BaseModel):
    """File or folder item from Google Drive."""
    id: str
    name: str
    type: str  # "file" or "folder"
    mimeType: str
    size: Optional[int] = None
    modifiedTime: Optional[str] = None


class ListResponse(BaseModel):
    """Response for list folder endpoint."""
    items: list[FolderItem]
    folder_id: str


@router.get("/gdrive/status")
async def gdrive_status():
    """Check if Google Drive is configured."""
    return {
        "configured": gdrive_adapter.is_configured(),
        "message": "Google Drive is configured" if gdrive_adapter.is_configured()
                   else "Google Drive not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"
    }


@router.get("/gdrive/list")
async def list_folder(folder_id: Optional[str] = None):
    """
    List files and folders in a Google Drive folder.

    Args:
        folder_id: Folder ID to list (uses configured root if not provided)

    Returns:
        List of files and folders
    """
    try:
        items = await gdrive_adapter.list_folder(folder_id)
        return {
            "items": items,
            "folder_id": folder_id or "root"
        }
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gdrive/file/{file_id}")
async def get_file_info(file_id: str):
    """
    Get metadata for a file or folder.

    Args:
        file_id: Google Drive file/folder ID

    Returns:
        File metadata
    """
    try:
        return await gdrive_adapter.get_file_info(file_id)
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gdrive/download/{file_id}")
async def download_file(file_id: str):
    """
    Download a file from Google Drive.

    Args:
        file_id: Google Drive file ID

    Returns:
        File content as stream
    """
    try:
        info = await gdrive_adapter.get_file_info(file_id)

        if info['type'] == 'folder':
            raise HTTPException(
                status_code=400,
                detail="Cannot download folder directly. Use /gdrive/download-folder/{folder_id}"
            )

        content = await gdrive_adapter.download_file(file_id)

        return StreamingResponse(
            iter([content]),
            media_type=info['mimeType'],
            headers={
                "Content-Disposition": f"attachment; filename=\"{info['name']}\""
            }
        )
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gdrive/download-folder/{folder_id}")
async def download_folder_zip(folder_id: str):
    """
    Download a folder as ZIP file.

    Args:
        folder_id: Google Drive folder ID

    Returns:
        ZIP file stream
    """
    try:
        info = await gdrive_adapter.get_file_info(folder_id)

        if info['type'] != 'folder':
            raise HTTPException(
                status_code=400,
                detail="Not a folder. Use /gdrive/download/{file_id} for files"
            )

        zip_path = await gdrive_adapter.download_folder_as_zip(folder_id)

        def file_iterator():
            with open(zip_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
            # Cleanup
            zip_path.unlink(missing_ok=True)

        return StreamingResponse(
            file_iterator(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=\"{info['name']}.zip\""
            }
        )
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/gdrive/search")
async def search_files(
    query: str,
    folder_id: Optional[str] = None,
):
    """
    Search for files in Google Drive.

    Args:
        query: Search query (file name)
        folder_id: Limit search to folder (optional)

    Returns:
        List of matching files
    """
    try:
        items = await gdrive_adapter.search(query, folder_id)
        return {"items": items, "query": query}
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================================
# UPLOAD ENDPOINTS
# =========================================================================


class CreateFolderRequest(BaseModel):
    """Request to create a folder."""
    folder_name: str
    parent_folder_id: Optional[str] = None


class UploadDocumentRequest(BaseModel):
    """Request to upload a generated document."""
    document_content: str  # base64 encoded content
    document_name: str
    document_type: str  # pdf, docx, xlsx, md, json, csv
    folder_id: Optional[str] = None
    create_subfolder: Optional[str] = None


class UploadBatchRequest(BaseModel):
    """Request to upload multiple documents."""
    folder_name: Optional[str] = None
    folder_id: Optional[str] = None


class UploadFileRequest(BaseModel):
    """Request to upload a file with base64 content."""
    file_content: str  # base64 encoded content
    file_name: str
    folder_id: Optional[str] = None
    mime_type: Optional[str] = None


@router.post("/gdrive/create-folder")
async def create_folder(request: CreateFolderRequest):
    """
    Create a folder in Google Drive.

    Args:
        folder_name: Name of the folder to create
        parent_folder_id: Parent folder ID (uses configured root if not provided)

    Returns:
        Created folder metadata with 'id' and 'webViewLink'
    """
    try:
        result = await gdrive_adapter.create_folder(
            folder_name=request.folder_name,
            parent_folder_id=request.parent_folder_id,
        )
        return result
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gdrive/upload")
async def upload_file(request: UploadFileRequest):
    """
    Upload a file to Google Drive.

    Args:
        file_content: Base64 encoded file content
        file_name: Name for the file in Drive
        folder_id: Destination folder ID
        mime_type: MIME type (auto-detected if not provided)

    Returns:
        Uploaded file metadata with 'id', 'webViewLink'
    """
    import base64

    try:
        # Decode base64 content
        file_bytes = base64.b64decode(request.file_content)

        result = await gdrive_adapter.upload_file(
            file_content=file_bytes,
            file_name=request.file_name,
            folder_id=request.folder_id,
            mime_type=request.mime_type,
        )
        return result
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file content: {e}")


@router.post("/gdrive/upload-document")
async def upload_document(request: UploadDocumentRequest):
    """
    Upload a generated document to Google Drive.

    Args:
        document_content: Base64 encoded document content
        document_name: Name for the document
        document_type: Type (pdf, docx, xlsx, md, json, csv)
        folder_id: Destination folder ID
        create_subfolder: Create subfolder with this name

    Returns:
        Upload result with file metadata and folder info
    """
    import base64

    try:
        # Decode base64 content
        document_bytes = base64.b64decode(request.document_content)

        result = await gdrive_adapter.upload_document(
            document_content=document_bytes,
            document_name=request.document_name,
            document_type=request.document_type,
            folder_id=request.folder_id,
            create_subfolder=request.create_subfolder,
        )
        return result
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid document content: {e}")


@router.delete("/gdrive/file/{file_id}")
async def delete_file(file_id: str):
    """
    Delete a file from Google Drive.

    Args:
        file_id: ID of file to delete

    Returns:
        Success status
    """
    try:
        await gdrive_adapter.delete_file(file_id)
        return {"success": True, "message": f"File {file_id} deleted"}
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))
