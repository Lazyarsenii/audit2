"""
Google Drive Adapter.

Handles Google Drive API interactions: browse folders, download/upload files.
Uses Service Account for server-to-server authentication.
"""
import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from app.core.config import settings

logger = logging.getLogger(__name__)


# MIME types mapping
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".csv": "text/csv",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class GoogleDriveError(Exception):
    """Google Drive API error."""
    pass


class GoogleDriveAdapter:
    """Adapter for Google Drive API interactions."""

    # Full access scope for read/write operations
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',  # Access files created by app
        'https://www.googleapis.com/auth/drive',       # Full drive access
    ]

    def __init__(self, service_account_file: Optional[str] = None):
        self.service_account_file = service_account_file or settings.GOOGLE_SERVICE_ACCOUNT_JSON
        self._service = None

    def _get_service(self):
        """Get or create Google Drive service."""
        if self._service is not None:
            return self._service

        if not self.service_account_file:
            raise GoogleDriveError(
                "Google Drive not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"
            )

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.SCOPES
            )
            self._service = build('drive', 'v3', credentials=credentials)
            return self._service
        except ImportError:
            raise GoogleDriveError(
                "Google API client not installed. Run: pip install google-api-python-client google-auth"
            )
        except Exception as e:
            raise GoogleDriveError(f"Failed to initialize Google Drive: {e}")

    def is_configured(self) -> bool:
        """Check if Google Drive is configured."""
        return bool(self.service_account_file and os.path.exists(self.service_account_file))

    async def list_folder(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List files and folders in a Google Drive folder.

        Args:
            folder_id: Folder ID to list (uses root from settings if not provided)
            page_size: Number of items per page

        Returns:
            List of file/folder metadata
        """
        service = self._get_service()
        folder_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID or 'root'

        try:
            query = f"'{folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                orderBy="folder,name"
            ).execute()

            items = results.get('files', [])

            # Format response
            return [
                {
                    "id": item['id'],
                    "name": item['name'],
                    "type": "folder" if item['mimeType'] == 'application/vnd.google-apps.folder' else "file",
                    "mimeType": item['mimeType'],
                    "size": item.get('size'),
                    "modifiedTime": item.get('modifiedTime'),
                }
                for item in items
            ]
        except Exception as e:
            raise GoogleDriveError(f"Failed to list folder: {e}")

    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get metadata for a file or folder.

        Args:
            file_id: Google Drive file/folder ID

        Returns:
            File metadata
        """
        service = self._get_service()

        try:
            file = service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, parents"
            ).execute()

            return {
                "id": file['id'],
                "name": file['name'],
                "type": "folder" if file['mimeType'] == 'application/vnd.google-apps.folder' else "file",
                "mimeType": file['mimeType'],
                "size": file.get('size'),
                "modifiedTime": file.get('modifiedTime'),
            }
        except Exception as e:
            raise GoogleDriveError(f"Failed to get file info: {e}")

    async def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes
        """
        service = self._get_service()

        try:
            from googleapiclient.http import MediaIoBaseDownload

            request = service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                _, done = downloader.next_chunk()

            file_buffer.seek(0)
            return file_buffer.read()
        except Exception as e:
            raise GoogleDriveError(f"Failed to download file: {e}")

    async def download_folder_as_zip(
        self,
        folder_id: str,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Download entire folder as ZIP file.

        Args:
            folder_id: Google Drive folder ID
            output_path: Where to save ZIP (temp file if not provided)

        Returns:
            Path to ZIP file
        """
        service = self._get_service()

        # Create temp directory for downloads
        temp_dir = tempfile.mkdtemp(prefix="gdrive_")

        try:
            # Get folder name
            folder_info = await self.get_file_info(folder_id)
            folder_name = folder_info['name']

            # Download folder recursively
            await self._download_folder_recursive(folder_id, Path(temp_dir) / folder_name)

            # Create ZIP
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix='.zip', prefix='gdrive_'))

            shutil.make_archive(
                str(output_path.with_suffix('')),
                'zip',
                temp_dir,
                folder_name
            )

            return output_path

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _download_folder_recursive(self, folder_id: str, local_path: Path) -> None:
        """Recursively download folder contents."""
        local_path.mkdir(parents=True, exist_ok=True)

        items = await self.list_folder(folder_id)

        for item in items:
            item_path = local_path / item['name']

            if item['type'] == 'folder':
                await self._download_folder_recursive(item['id'], item_path)
            else:
                # Skip Google Docs native formats (can't be downloaded directly)
                if item['mimeType'].startswith('application/vnd.google-apps.'):
                    logger.warning(f"Skipping Google Docs file: {item['name']}")
                    continue

                content = await self.download_file(item['id'])
                item_path.write_bytes(content)

    async def download_folder_to_local(
        self,
        folder_id: str,
        local_dir: Optional[Path] = None,
    ) -> Path:
        """
        Download folder to local directory (for analysis).

        Args:
            folder_id: Google Drive folder ID
            local_dir: Where to download (temp dir if not provided)

        Returns:
            Path to downloaded folder
        """
        if local_dir is None:
            local_dir = Path(settings.CLONE_DIR) / f"gdrive_{folder_id[:8]}"

        local_dir.mkdir(parents=True, exist_ok=True)

        folder_info = await self.get_file_info(folder_id)
        target_path = local_dir / folder_info['name']

        await self._download_folder_recursive(folder_id, target_path)

        return target_path

    async def search(
        self,
        query: str,
        folder_id: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for files in Google Drive.

        Args:
            query: Search query (file name)
            folder_id: Limit search to folder
            file_type: Filter by mime type

        Returns:
            List of matching files
        """
        service = self._get_service()

        q_parts = [f"name contains '{query}'", "trashed = false"]

        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")

        if file_type:
            q_parts.append(f"mimeType = '{file_type}'")

        try:
            results = service.files().list(
                q=" and ".join(q_parts),
                pageSize=50,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()

            return [
                {
                    "id": item['id'],
                    "name": item['name'],
                    "type": "folder" if item['mimeType'] == 'application/vnd.google-apps.folder' else "file",
                    "mimeType": item['mimeType'],
                    "size": item.get('size'),
                    "modifiedTime": item.get('modifiedTime'),
                }
                for item in results.get('files', [])
            ]
        except Exception as e:
            raise GoogleDriveError(f"Search failed: {e}")

    # =========================================================================
    # UPLOAD METHODS
    # =========================================================================

    async def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: Parent folder ID (uses root from settings if not provided)

        Returns:
            Created folder metadata with 'id' and 'name'
        """
        service = self._get_service()
        parent_id = parent_folder_id or settings.GOOGLE_DRIVE_FOLDER_ID

        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = service.files().create(
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()

            logger.info(f"Created folder '{folder_name}' with ID: {folder['id']}")

            return {
                "id": folder['id'],
                "name": folder['name'],
                "type": "folder",
                "webViewLink": folder.get('webViewLink'),
            }
        except Exception as e:
            raise GoogleDriveError(f"Failed to create folder: {e}")

    async def upload_file(
        self,
        file_content: Union[bytes, io.BytesIO],
        file_name: str,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.

        Args:
            file_content: File content as bytes or BytesIO
            file_name: Name for the file in Drive
            folder_id: Destination folder ID (uses root from settings if not provided)
            mime_type: MIME type (auto-detected from extension if not provided)

        Returns:
            Uploaded file metadata with 'id', 'name', 'webViewLink'
        """
        service = self._get_service()
        parent_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID

        # Auto-detect MIME type from extension
        if mime_type is None:
            ext = Path(file_name).suffix.lower()
            mime_type = MIME_TYPES.get(ext, 'application/octet-stream')

        try:
            from googleapiclient.http import MediaIoBaseUpload

            # Ensure we have BytesIO
            if isinstance(file_content, bytes):
                file_buffer = io.BytesIO(file_content)
            else:
                file_buffer = file_content
                file_buffer.seek(0)

            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]

            media = MediaIoBaseUpload(
                file_buffer,
                mimetype=mime_type,
                resumable=True
            )

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size'
            ).execute()

            logger.info(f"Uploaded file '{file_name}' with ID: {file['id']}")

            return {
                "id": file['id'],
                "name": file['name'],
                "type": "file",
                "webViewLink": file.get('webViewLink'),
                "size": file.get('size'),
                "mimeType": mime_type,
            }
        except Exception as e:
            raise GoogleDriveError(f"Failed to upload file: {e}")

    async def upload_document(
        self,
        document_content: bytes,
        document_name: str,
        document_type: str,
        folder_id: Optional[str] = None,
        create_subfolder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a generated document to Google Drive.

        Args:
            document_content: Document content as bytes
            document_name: Name for the document
            document_type: Type of document (pdf, docx, xlsx, md, etc.)
            folder_id: Destination folder ID
            create_subfolder: If provided, create/use this subfolder

        Returns:
            Upload result with file metadata and folder info
        """
        target_folder_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID

        # Create subfolder if requested
        subfolder_info = None
        if create_subfolder:
            subfolder_info = await self.create_folder(create_subfolder, target_folder_id)
            target_folder_id = subfolder_info['id']

        # Determine file extension and mime type
        ext_map = {
            'pdf': '.pdf',
            'docx': '.docx',
            'word': '.docx',
            'xlsx': '.xlsx',
            'excel': '.xlsx',
            'md': '.md',
            'markdown': '.md',
            'json': '.json',
            'csv': '.csv',
            'txt': '.txt',
        }

        ext = ext_map.get(document_type.lower(), f'.{document_type}')
        if not document_name.endswith(ext):
            document_name = f"{document_name}{ext}"

        # Upload file
        file_info = await self.upload_file(
            file_content=document_content,
            file_name=document_name,
            folder_id=target_folder_id,
        )

        return {
            "file": file_info,
            "subfolder": subfolder_info,
            "document_type": document_type,
        }

    async def upload_multiple_documents(
        self,
        documents: List[Dict[str, Any]],
        folder_id: Optional[str] = None,
        folder_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload multiple documents to Google Drive.

        Args:
            documents: List of dicts with 'content', 'name', 'type'
            folder_id: Destination folder ID
            folder_name: If provided, create a folder with this name for all docs

        Returns:
            Upload results for all documents
        """
        target_folder_id = folder_id or settings.GOOGLE_DRIVE_FOLDER_ID

        # Create folder for batch upload
        folder_info = None
        if folder_name:
            folder_info = await self.create_folder(folder_name, target_folder_id)
            target_folder_id = folder_info['id']

        # Upload all documents
        results = []
        errors = []

        for doc in documents:
            try:
                result = await self.upload_document(
                    document_content=doc['content'],
                    document_name=doc['name'],
                    document_type=doc['type'],
                    folder_id=target_folder_id,
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "name": doc['name'],
                    "error": str(e),
                })
                logger.error(f"Failed to upload {doc['name']}: {e}")

        return {
            "folder": folder_info,
            "uploaded": results,
            "errors": errors,
            "total": len(documents),
            "success_count": len(results),
            "error_count": len(errors),
        }

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.

        Args:
            file_id: ID of file to delete

        Returns:
            True if deleted successfully
        """
        service = self._get_service()

        try:
            service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file with ID: {file_id}")
            return True
        except Exception as e:
            raise GoogleDriveError(f"Failed to delete file: {e}")


# Singleton instance
gdrive_adapter = GoogleDriveAdapter()
