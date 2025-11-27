"""
File Storage Service - S3/MinIO Integration
============================================

Handles file uploads, downloads, and lifecycle management.
"""

import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.core.settings import settings

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    print("WARNING: minio package not installed. File storage unavailable.")

logger = logging.getLogger(__name__)


class StorageService:
    """
    Abstraction layer for file storage (MinIO/S3).

    Supports both MinIO (local) and AWS S3 (production).
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: str = "rexsyn-nexus",
        use_ssl: bool = False,
    ):
        """
        Initialize storage service.

        Args:
            endpoint: MinIO/S3 endpoint (e.g., "localhost:9000")
            access_key: Access key ID
            secret_key: Secret access key
            bucket_name: Default bucket name
            use_ssl: Use HTTPS (True for AWS S3)
        """
        if not MINIO_AVAILABLE:
            raise ImportError("minio package required for storage service")

        # Load from environment if not provided
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET
        self.use_ssl = use_ssl or settings.MINIO_SECURE

        missing = [
            name
            for name, value in [
                ("MINIO_ENDPOINT", self.endpoint),
                ("MINIO_ACCESS_KEY", self.access_key),
                ("MINIO_SECRET_KEY", self.secret_key),
            ]
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing MinIO configuration values. "
                f"Set environment variables: {', '.join(missing)}"
            )

        # Initialize MinIO client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.use_ssl,
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket already exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise

    def upload_file(
        self,
        file_path: str,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Upload a file to storage.

        Args:
            file_path: Local file path
            object_name: Object name in storage (e.g., "jobs/exp-001/structure.pdb")
            content_type: MIME type (auto-detected if None)
            metadata: Additional metadata

        Returns:
            dict with file info (path, size, md5, etc.)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect content type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or "application/octet-stream"

        # Calculate file size and hashes
        file_size = file_path.stat().st_size
        md5_hash = self._calculate_md5(file_path)
        sha256_hash = self._calculate_sha256(file_path)

        # Prepare metadata
        file_metadata = metadata or {}
        file_metadata.update({
            "md5": md5_hash,
            "sha256": sha256_hash,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Upload file
            self.client.fput_object(
                self.bucket_name,
                object_name,
                str(file_path),
                content_type=content_type,
                metadata=file_metadata,
            )

            logger.info(f"Uploaded file: {object_name} ({file_size} bytes)")

            return {
                "object_name": object_name,
                "file_size": file_size,
                "content_type": content_type,
                "md5_hash": md5_hash,
                "sha256_hash": sha256_hash,
                "bucket": self.bucket_name,
            }

        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Upload bytes directly to storage.

        Args:
            data: Bytes to upload
            object_name: Object name in storage
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            dict with file info
        """
        import io

        file_size = len(data)
        md5_hash = hashlib.md5(data, usedforsecurity=False).hexdigest()  # nosec B324
        sha256_hash = hashlib.sha256(data).hexdigest()

        # Prepare metadata
        file_metadata = metadata or {}
        file_metadata.update({
            "md5": md5_hash,
            "sha256": sha256_hash,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Upload bytes
            self.client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(data),
                length=file_size,
                content_type=content_type,
                metadata=file_metadata,
            )

            logger.info(f"Uploaded bytes: {object_name} ({file_size} bytes)")

            return {
                "object_name": object_name,
                "file_size": file_size,
                "content_type": content_type,
                "md5_hash": md5_hash,
                "sha256_hash": sha256_hash,
                "bucket": self.bucket_name,
            }

        except S3Error as e:
            logger.error(f"Failed to upload bytes: {e}")
            raise

    def download_file(self, object_name: str, file_path: str) -> Path:
        """
        Download a file from storage.

        Args:
            object_name: Object name in storage
            file_path: Local path to save file

        Returns:
            Path to downloaded file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.client.fget_object(
                self.bucket_name,
                object_name,
                str(file_path),
            )

            logger.info(f"Downloaded file: {object_name} -> {file_path}")
            return file_path

        except S3Error as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def download_bytes(self, object_name: str) -> bytes:
        """
        Download file as bytes.

        Args:
            object_name: Object name in storage

        Returns:
            File contents as bytes
        """
        try:
            response = self.client.get_object(
                self.bucket_name,
                object_name,
            )
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded bytes: {object_name} ({len(data)} bytes)")
            return data

        except S3Error as e:
            logger.error(f"Failed to download bytes: {e}")
            raise

    def delete_file(self, object_name: str):
        """
        Delete a file from storage.

        Args:
            object_name: Object name to delete
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file: {object_name}")

        except S3Error as e:
            logger.error(f"Failed to delete file: {e}")
            raise

    def delete_folder(self, prefix: str):
        """
        Delete all files with a given prefix (folder).

        Args:
            prefix: Object prefix (e.g., "jobs/exp-001/")
        """
        try:
            # List all objects with prefix
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=True,
            )

            # Delete each object
            deleted_count = 0
            for obj in objects:
                self.client.remove_object(self.bucket_name, obj.object_name)
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} files with prefix: {prefix}")

        except S3Error as e:
            logger.error(f"Failed to delete folder: {e}")
            raise

    def get_presigned_url(
        self,
        object_name: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a presigned URL for temporary access.

        Args:
            object_name: Object name
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires_in),
            )

            logger.info(f"Generated presigned URL for: {object_name}")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            object_name: Object name

        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_file_info(self, object_name: str) -> dict:
        """
        Get file metadata.

        Args:
            object_name: Object name

        Returns:
            dict with file info
        """
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)

            return {
                "object_name": object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata,
                "etag": stat.etag,
            }

        except S3Error as e:
            logger.error(f"Failed to get file info: {e}")
            raise

    @staticmethod
    def _calculate_md5(file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        md5 = hashlib.md5(usedforsecurity=False)  # nosec B324
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get storage service singleton.

    Lazily initialized on first use.
    """
    global _storage_service

    if _storage_service is None:
        if not MINIO_AVAILABLE:
            raise ImportError("minio package required")

        _storage_service = StorageService()

    return _storage_service


# Job-specific helper functions
def get_job_storage_prefix(job_id: str) -> str:
    """Get storage prefix for a job."""
    return f"jobs/{job_id}/"


def upload_job_file(
    job_id: str,
    file_path: str,
    file_type: str,
) -> dict:
    """
    Upload a file for a specific job.

    Args:
        job_id: Job identifier
        file_path: Local file path
        file_type: File type (pdb, pdf, fasta, etc.)

    Returns:
        dict with file info
    """
    storage = get_storage_service()
    file_name = Path(file_path).name
    object_name = f"{get_job_storage_prefix(job_id)}{file_type}/{file_name}"

    return storage.upload_file(file_path, object_name)


def delete_job_files(job_id: str):
    """
    Delete all files for a job.

    Args:
        job_id: Job identifier
    """
    storage = get_storage_service()
    prefix = get_job_storage_prefix(job_id)
    storage.delete_folder(prefix)
