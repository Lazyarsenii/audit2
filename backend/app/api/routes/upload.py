"""
File upload API endpoints for local repository analysis.

Supports:
- ZIP file upload
- Multi-file upload (from Browser File System Access API)
"""
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel

router = APIRouter(prefix="/upload", tags=["Upload"])

# Store for tracking uploaded repos (in production, use Redis or DB)
UPLOAD_DIR = tempfile.gettempdir()
UPLOADS_TRACKER: dict[str, dict] = {}


class UploadResponse(BaseModel):
    """Response after successful upload."""
    upload_id: str
    path: str
    file_count: int
    total_size: int
    message: str


class UploadStatus(BaseModel):
    """Status of an upload."""
    upload_id: str
    path: str
    file_count: int
    total_size: int
    created_at: str
    expires_at: str


@router.post("/zip", response_model=UploadResponse)
async def upload_zip(
    file: UploadFile = File(...),
):
    """
    Upload a ZIP file containing repository code.

    The ZIP will be extracted and stored temporarily for analysis.
    Returns a path that can be used with /api/analyze endpoint.
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are accepted"
        )

    # Generate unique ID for this upload
    upload_id = str(uuid4())[:8]
    upload_path = os.path.join(UPLOAD_DIR, f"repo_upload_{upload_id}")

    try:
        # Create directory
        os.makedirs(upload_path, exist_ok=True)

        # Save ZIP file temporarily
        zip_path = os.path.join(upload_path, "upload.zip")
        content = await file.read()

        with open(zip_path, "wb") as f:
            f.write(content)

        # Extract ZIP
        extract_path = os.path.join(upload_path, "repo")
        os.makedirs(extract_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        # Remove ZIP file after extraction
        os.remove(zip_path)

        # Check if there's a single root folder and use it
        items = os.listdir(extract_path)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_path, items[0])):
            final_path = os.path.join(extract_path, items[0])
        else:
            final_path = extract_path

        # Count files and size
        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(final_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.'):
                    file_count += 1
                    total_size += os.path.getsize(os.path.join(root, f))

        # Track upload
        UPLOADS_TRACKER[upload_id] = {
            "path": final_path,
            "file_count": file_count,
            "total_size": total_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return UploadResponse(
            upload_id=upload_id,
            path=final_path,
            file_count=file_count,
            total_size=total_size,
            message=f"Successfully extracted {file_count} files ({total_size / 1024:.1f} KB)",
        )

    except zipfile.BadZipFile:
        # Cleanup on error
        shutil.rmtree(upload_path, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted ZIP file"
        )
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(upload_path, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process upload: {str(e)}"
        )


@router.post("/files", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    paths: List[str] = Form(...),
):
    """
    Upload multiple files with their relative paths.

    Used by Browser File System Access API to upload a directory structure.

    Args:
        files: List of file uploads
        paths: List of relative paths for each file (e.g., "src/index.ts")
    """
    if len(files) != len(paths):
        raise HTTPException(
            status_code=400,
            detail="Number of files must match number of paths"
        )

    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="No files provided"
        )

    # Generate unique ID for this upload
    upload_id = str(uuid4())[:8]
    upload_path = os.path.join(UPLOAD_DIR, f"repo_upload_{upload_id}", "repo")

    try:
        os.makedirs(upload_path, exist_ok=True)

        total_size = 0
        file_count = 0

        for file, rel_path in zip(files, paths):
            # Security: prevent path traversal
            safe_path = os.path.normpath(rel_path).lstrip(os.sep)
            if safe_path.startswith('..'):
                continue

            # Create directory structure
            file_path = os.path.join(upload_path, safe_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            total_size += len(content)
            file_count += 1

        # Track upload
        UPLOADS_TRACKER[upload_id] = {
            "path": upload_path,
            "file_count": file_count,
            "total_size": total_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return UploadResponse(
            upload_id=upload_id,
            path=upload_path,
            file_count=file_count,
            total_size=total_size,
            message=f"Successfully uploaded {file_count} files ({total_size / 1024:.1f} KB)",
        )

    except Exception as e:
        # Cleanup on error
        shutil.rmtree(os.path.dirname(upload_path), ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process upload: {str(e)}"
        )


@router.get("/status/{upload_id}", response_model=UploadStatus)
async def get_upload_status(upload_id: str):
    """Get status of an uploaded repository."""
    if upload_id not in UPLOADS_TRACKER:
        raise HTTPException(
            status_code=404,
            detail="Upload not found or expired"
        )

    info = UPLOADS_TRACKER[upload_id]
    return UploadStatus(
        upload_id=upload_id,
        path=info["path"],
        file_count=info["file_count"],
        total_size=info["total_size"],
        created_at=info["created_at"],
        expires_at="24 hours after creation",
    )


@router.delete("/cleanup/{upload_id}")
async def cleanup_upload(upload_id: str):
    """Delete an uploaded repository to free space."""
    if upload_id not in UPLOADS_TRACKER:
        raise HTTPException(
            status_code=404,
            detail="Upload not found"
        )

    info = UPLOADS_TRACKER[upload_id]
    path = info["path"]

    # Find root upload dir
    upload_root = path
    while os.path.basename(upload_root) != f"repo_upload_{upload_id}":
        parent = os.path.dirname(upload_root)
        if parent == upload_root:
            break
        upload_root = parent

    # Remove directory
    shutil.rmtree(upload_root, ignore_errors=True)
    del UPLOADS_TRACKER[upload_id]

    return {"message": "Upload cleaned up successfully"}
