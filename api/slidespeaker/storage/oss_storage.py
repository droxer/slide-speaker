"""Aliyun OSS (Object Storage Service) implementation.

Provides cloud storage using Aliyun OSS with support for presigned URLs.
Designed to be compatible with the existing storage provider interface.
"""

import logging
from pathlib import Path

from . import StorageProvider

# Optional imports for Aliyun OSS - will raise ImportError if not available
try:
    import oss2
    from oss2.exceptions import NoSuchBucket, NoSuchKey, OssError

    OSS_AVAILABLE = True
except ImportError:
    OSS_AVAILABLE = False
    oss2 = None
    OssError = None
    NoSuchBucket = None
    NoSuchKey = None

logger = logging.getLogger(__name__)


class OSSStorage(StorageProvider):
    """Aliyun OSS storage implementation."""

    def __init__(
        self,
        bucket_name: str,
        endpoint: str,
        access_key_id: str,
        access_key_secret: str,
        region: str | None = None,
        is_cname: bool = False,
    ):
        """Initialize Aliyun OSS storage.

        Args:
            bucket_name: OSS bucket name
            endpoint: OSS endpoint (e.g., 'oss-cn-hangzhou.aliyuncs.com')
            access_key_id: Aliyun AccessKey ID
            access_key_secret: Aliyun AccessKey Secret
            region: OSS region (optional, can be extracted from endpoint)
            internal_endpoint: Whether to use internal endpoint for faster access
        """
        if not OSS_AVAILABLE:
            raise ImportError(
                "Aliyun OSS storage requires oss2. Install with: uv sync --extra=oss"
            )

        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.region = region or self._extract_region_from_endpoint(endpoint)
        self.is_cname = is_cname

        # Initialize OSS client
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        # If using a custom CNAME domain for the bucket, pass is_cname=True
        self.bucket = oss2.Bucket(
            self.auth, f"https://{endpoint}", bucket_name, is_cname=self.is_cname
        )

        # Verify bucket exists and is accessible
        self._verify_bucket_access()

    def _extract_region_from_endpoint(self, endpoint: str) -> str:
        """Extract region from OSS endpoint."""
        # Endpoints are typically in format: oss-cn-region.aliyuncs.com
        if "oss-cn-" in endpoint:
            parts = endpoint.split(".")
            if len(parts) > 0 and parts[0].startswith("oss-cn-"):
                return parts[0].replace("oss-cn-", "")
        return "unknown"

    def _verify_bucket_access(self) -> None:
        """Verify that the OSS bucket is accessible."""
        try:
            # Simple operation to verify bucket access
            self.bucket.get_bucket_info()
            logger.info(f"Successfully connected to OSS bucket: {self.bucket_name}")
        except NoSuchBucket:
            raise ValueError(f"OSS bucket '{self.bucket_name}' not found") from None
        except OssError as e:
            if "AccessDenied" in str(e):
                raise ValueError(
                    f"Access denied to OSS bucket '{self.bucket_name}'"
                ) from e
            else:
                raise ValueError(
                    f"Error accessing OSS bucket '{self.bucket_name}': {e}"
                ) from e

    def upload_file(
        self, file_path: str | Path, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload a file to OSS."""
        try:
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type
            # Encourage inline rendering by default for common types
            lower_key = object_key.lower()
            if lower_key.endswith(
                (".mp4", ".mp3", ".vtt", ".srt", ".md", ".png", ".jpg", ".jpeg")
            ):
                from pathlib import Path as _Path

                headers["Content-Disposition"] = (
                    f"inline; filename={_Path(object_key).name}"
                )

            self.bucket.put_object_from_file(
                object_key, str(file_path), headers=headers
            )

            logger.info(f"Uploaded file to OSS: {object_key}")
            return f"oss://{self.bucket_name}/{object_key}"

        except OssError as e:
            logger.error(f"Failed to upload file to OSS: {e}")
            raise

    def download_file(self, object_key: str, destination_path: str | Path) -> None:
        """Download a file from OSS."""
        try:
            self.bucket.get_object_to_file(object_key, str(destination_path))
            logger.info(f"Downloaded file from OSS: {object_key}")

        except OssError as e:
            logger.error(f"Failed to download file from OSS: {e}")
            raise

    def get_file_url(
        self,
        object_key: str,
        expires_in: int = 3600,
        content_disposition: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """Generate a signed URL for OSS object with inline disposition.

        Adds response headers to encourage inline playback for media and to set
        accurate content types for browsers. CORS must still be configured at
        the bucket for cross-origin access.
        """
        try:
            # Infer content-type from file extension when not provided
            ct = content_type
            key_lower = object_key.lower()
            if ct is None and key_lower.endswith(".mp4"):
                ct = "video/mp4"
            elif ct is None and key_lower.endswith(".mp3"):
                ct = "audio/mpeg"
            elif ct is None and key_lower.endswith(".vtt"):
                ct = "text/vtt"
            elif ct is None and key_lower.endswith(".srt"):
                ct = "text/plain"
            elif ct is None and key_lower.endswith(".md"):
                ct = "text/markdown"
            elif ct is None and key_lower.endswith(".png"):
                ct = "image/png"
            elif ct is None and (
                key_lower.endswith(".jpg") or key_lower.endswith(".jpeg")
            ):
                ct = "image/jpeg"

            # Build response override params when requested
            params = None
            if content_disposition or (ct and not key_lower.endswith(".mp4")):
                params = {}
                if content_disposition:
                    params["response-content-disposition"] = content_disposition
                elif not key_lower.endswith(".mp4"):
                    # Default to inline for non-mp4 when not specified
                    filename = Path(object_key).name
                    params["response-content-disposition"] = (
                        f"inline; filename={filename}"
                    )
                if ct:
                    params["response-content-type"] = ct

            url: str = (
                self.bucket.sign_url("GET", object_key, expires_in, params=params)
                if params is not None
                else self.bucket.sign_url("GET", object_key, expires_in)
            )

            logger.debug(
                f"Generated OSS presigned URL for {object_key}: {url[:100]}..."
            )
            return url
        except OssError as e:
            logger.error(f"Failed to generate signed URL for {object_key}: {e}")
            raise

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in OSS."""
        try:
            exists: bool = self.bucket.object_exists(object_key)
            return exists
        except OssError as e:
            if "NoSuchKey" in str(e):
                return False
            raise

    def delete_file(self, object_key: str) -> None:
        """Delete file from OSS."""
        try:
            self.bucket.delete_object(object_key)
            logger.info(f"Deleted file from OSS: {object_key}")

        except OssError as e:
            logger.error(f"Failed to delete file from OSS: {e}")
            raise

    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload bytes data to OSS."""
        try:
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type
            # Encourage inline rendering by default for text/media
            lower_key = object_key.lower()
            if lower_key.endswith(
                (".mp4", ".mp3", ".vtt", ".srt", ".md", ".png", ".jpg", ".jpeg")
            ):
                from pathlib import Path as _Path

                headers["Content-Disposition"] = (
                    f"inline; filename={_Path(object_key).name}"
                )

            self.bucket.put_object(object_key, data, headers=headers)

            logger.info(f"Uploaded bytes to OSS: {object_key}")
            return f"oss://{self.bucket_name}/{object_key}"

        except OssError as e:
            logger.error(f"Failed to upload bytes to OSS: {e}")
            raise

    def download_bytes(self, object_key: str) -> bytes:
        """Download bytes data from OSS."""
        try:
            result = self.bucket.get_object(object_key)
            data: bytes = result.read()
            return data

        except OssError as e:
            logger.error(f"Failed to download bytes from OSS: {e}")
            raise

    def get_object_info(self, object_key: str) -> dict[str, object]:
        """Get object metadata from OSS."""
        """Get object information (for internal use)."""
        try:
            object_meta = self.bucket.get_object_meta(object_key)
            return {
                "size": object_meta.content_length,
                "content_type": object_meta.content_type,
                "last_modified": object_meta.last_modified,
            }
        except OssError as e:
            logger.error(f"Failed to get object info from OSS: {e}")
            raise
