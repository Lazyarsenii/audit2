"""
File Storage Service - abstraction layer for multiple storage backends.

Supports: Database (BLOB), Local filesystem, S3, Google Drive
"""
import os
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime, timezone
import mimetypes

from app.core.config import settings


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Save file content and return storage key.

        Args:
            content: File bytes
            filename: Original filename
            content_type: MIME type

        Returns:
            Storage key for retrieval
        """
        pass

    @abstractmethod
    async def load(self, storage_key: str) -> bytes:
        """
        Load file content by storage key.

        Args:
            storage_key: Key returned from save()

        Returns:
            File bytes
        """
        pass

    @abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """
        Delete file by storage key.

        Args:
            storage_key: Key returned from save()

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if file exists."""
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend identifier."""
        pass


class LocalFileStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.UPLOAD_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def backend_name(self) -> str:
        return "local"

    def _generate_key(self, filename: str, content: bytes) -> str:
        """Generate unique storage key."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.sha256(content).hexdigest()[:12]
        safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        return f"{timestamp}_{content_hash}_{safe_name}"

    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        try:
            storage_key = self._generate_key(filename, content)
            file_path = self.base_path / storage_key

            with open(file_path, "wb") as f:
                f.write(content)

            return storage_key
        except Exception as e:
            raise StorageError(f"Failed to save file locally: {e}")

    async def load(self, storage_key: str) -> bytes:
        try:
            file_path = self.base_path / storage_key
            if not file_path.exists():
                raise StorageError(f"File not found: {storage_key}")

            with open(file_path, "rb") as f:
                return f.read()
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to load file: {e}")

    async def delete(self, storage_key: str) -> bool:
        try:
            file_path = self.base_path / storage_key
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            raise StorageError(f"Failed to delete file: {e}")

    async def exists(self, storage_key: str) -> bool:
        file_path = self.base_path / storage_key
        return file_path.exists()


class DatabaseStorage(StorageBackend):
    """
    Database storage backend.

    Stores file content directly in the Document model's original_content field.
    This backend is special - it doesn't actually store separately,
    the content is stored in the Document table itself.
    """

    @property
    def backend_name(self) -> str:
        return "db"

    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        # For DB storage, we return a special key indicating content is inline
        # The actual storage happens in the Document model's original_content field
        content_hash = hashlib.sha256(content).hexdigest()
        return f"db:inline:{content_hash}"

    async def load(self, storage_key: str) -> bytes:
        # DB content is loaded directly from Document.original_content
        # This method exists for interface compliance
        raise StorageError("DB storage loads directly from Document model")

    async def delete(self, storage_key: str) -> bool:
        # DB content is deleted with the Document record
        return True

    async def exists(self, storage_key: str) -> bool:
        # Existence is checked via Document record
        return True


class S3Storage(StorageBackend):
    """
    AWS S3 storage backend.

    Requires: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET in settings
    """

    def __init__(self):
        self.bucket = getattr(settings, 'S3_BUCKET', None)
        self.region = getattr(settings, 'AWS_REGION', 'us-east-1')
        self._client = None

    @property
    def backend_name(self) -> str:
        return "s3"

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    's3',
                    region_name=self.region,
                )
            except ImportError:
                raise StorageError("boto3 not installed. Run: pip install boto3")
        return self._client

    def _generate_key(self, filename: str, content: bytes) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        content_hash = hashlib.sha256(content).hexdigest()[:12]
        safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        return f"documents/{timestamp}/{content_hash}_{safe_name}"

    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        if not self.bucket:
            raise StorageError("S3_BUCKET not configured")

        try:
            client = self._get_client()
            storage_key = self._generate_key(filename, content)

            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=content,
                **extra_args
            )

            return storage_key
        except Exception as e:
            raise StorageError(f"Failed to upload to S3: {e}")

    async def load(self, storage_key: str) -> bytes:
        if not self.bucket:
            raise StorageError("S3_BUCKET not configured")

        try:
            client = self._get_client()
            response = client.get_object(Bucket=self.bucket, Key=storage_key)
            return response['Body'].read()
        except Exception as e:
            raise StorageError(f"Failed to download from S3: {e}")

    async def delete(self, storage_key: str) -> bool:
        if not self.bucket:
            raise StorageError("S3_BUCKET not configured")

        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete from S3: {e}")

    async def exists(self, storage_key: str) -> bool:
        if not self.bucket:
            return False

        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception:
            return False


class GoogleDriveStorage(StorageBackend):
    """
    Google Drive storage backend.

    Uses existing gdrive_adapter for operations.
    """

    def __init__(self):
        from app.adapters.gdrive_adapter import gdrive_adapter
        self.adapter = gdrive_adapter

    @property
    def backend_name(self) -> str:
        return "gdrive"

    async def save(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        if not self.adapter.is_configured():
            raise StorageError("Google Drive not configured")

        try:
            result = await self.adapter.upload_file(
                file_content=content,
                file_name=filename,
                mime_type=content_type,
            )
            # Return the Google Drive file ID as storage key
            return result['id']
        except Exception as e:
            raise StorageError(f"Failed to upload to Google Drive: {e}")

    async def load(self, storage_key: str) -> bytes:
        if not self.adapter.is_configured():
            raise StorageError("Google Drive not configured")

        try:
            return await self.adapter.download_file(storage_key)
        except Exception as e:
            raise StorageError(f"Failed to download from Google Drive: {e}")

    async def delete(self, storage_key: str) -> bool:
        if not self.adapter.is_configured():
            raise StorageError("Google Drive not configured")

        try:
            await self.adapter.delete_file(storage_key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete from Google Drive: {e}")

    async def exists(self, storage_key: str) -> bool:
        if not self.adapter.is_configured():
            return False

        try:
            await self.adapter.get_file_info(storage_key)
            return True
        except Exception:
            return False


class FileStorageService:
    """
    File storage service factory.

    Manages multiple storage backends and provides unified interface.
    """

    _backends: dict[str, StorageBackend] = {}
    _default_backend: str = "local"

    @classmethod
    def get_backend(cls, backend_name: str) -> StorageBackend:
        """Get storage backend by name."""
        if backend_name not in cls._backends:
            cls._backends[backend_name] = cls._create_backend(backend_name)
        return cls._backends[backend_name]

    @classmethod
    def _create_backend(cls, backend_name: str) -> StorageBackend:
        """Create storage backend instance."""
        backends = {
            "local": LocalFileStorage,
            "db": DatabaseStorage,
            "s3": S3Storage,
            "gdrive": GoogleDriveStorage,
        }

        if backend_name not in backends:
            raise StorageError(f"Unknown storage backend: {backend_name}")

        return backends[backend_name]()

    @classmethod
    def get_default_backend(cls) -> StorageBackend:
        """Get default storage backend."""
        return cls.get_backend(cls._default_backend)

    @classmethod
    def set_default_backend(cls, backend_name: str):
        """Set default storage backend."""
        # Validate backend exists
        cls.get_backend(backend_name)
        cls._default_backend = backend_name

    @classmethod
    async def save(
        cls,
        content: bytes,
        filename: str,
        content_type: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Save file to storage.

        Args:
            content: File bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            backend: Backend name (uses default if not provided)

        Returns:
            Tuple of (storage_key, backend_name)
        """
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)

        backend_name = backend or cls._default_backend
        storage_backend = cls.get_backend(backend_name)

        storage_key = await storage_backend.save(content, filename, content_type)
        return storage_key, backend_name

    @classmethod
    async def load(cls, storage_key: str, backend: str) -> bytes:
        """
        Load file from storage.

        Args:
            storage_key: Storage key from save()
            backend: Backend name

        Returns:
            File bytes
        """
        storage_backend = cls.get_backend(backend)
        return await storage_backend.load(storage_key)

    @classmethod
    async def delete(cls, storage_key: str, backend: str) -> bool:
        """
        Delete file from storage.

        Args:
            storage_key: Storage key from save()
            backend: Backend name

        Returns:
            True if deleted
        """
        storage_backend = cls.get_backend(backend)
        return await storage_backend.delete(storage_key)

    @classmethod
    async def exists(cls, storage_key: str, backend: str) -> bool:
        """Check if file exists in storage."""
        storage_backend = cls.get_backend(backend)
        return await storage_backend.exists(storage_key)

    @classmethod
    def list_backends(cls) -> list[dict]:
        """List available storage backends with their status."""
        backends_info = []

        # Local storage
        backends_info.append({
            "name": "local",
            "label": "Local Filesystem",
            "available": True,
            "configured": True,
        })

        # Database storage
        backends_info.append({
            "name": "db",
            "label": "Database (PostgreSQL)",
            "available": True,
            "configured": True,
        })

        # S3 storage
        s3_configured = bool(getattr(settings, 'S3_BUCKET', None))
        backends_info.append({
            "name": "s3",
            "label": "AWS S3",
            "available": True,
            "configured": s3_configured,
        })

        # Google Drive storage
        try:
            from app.adapters.gdrive_adapter import gdrive_adapter
            gdrive_configured = gdrive_adapter.is_configured()
        except Exception:
            gdrive_configured = False

        backends_info.append({
            "name": "gdrive",
            "label": "Google Drive",
            "available": True,
            "configured": gdrive_configured,
        })

        return backends_info


# Convenience instance
file_storage = FileStorageService()
