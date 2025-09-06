"""AWS S3 storage implementation.

Provides cloud storage using AWS S3 with support for presigned URLs.
"""

import logging
from pathlib import Path

from . import StorageProvider

# Optional imports for AWS S3 - will raise ImportError if not available
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    boto3 = None
    ClientError = None
    NoCredentialsError = None

logger = logging.getLogger(__name__)


class S3Storage(StorageProvider):
    """AWS S3 storage implementation."""

    def __init__(
        self,
        bucket_name: str,
        region_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        endpoint_url: str | None = None,
    ):
        """Initialize S3 storage.

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            endpoint_url: Custom endpoint URL (for testing/minio)
        """
        if not AWS_AVAILABLE:
            raise ImportError(
                "AWS S3 storage requires boto3. Install with: uv sync --extra=aws"
            )

        self.bucket_name = bucket_name
        self.region_name = region_name

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
        )

        # Verify bucket exists and is accessible
        self._verify_bucket_access()

    def _verify_bucket_access(self) -> None:
        """Verify that the S3 bucket is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise ValueError(f"S3 bucket '{self.bucket_name}' not found") from e
            elif error_code == "403":
                raise ValueError(
                    f"Access denied to S3 bucket '{self.bucket_name}'"
                ) from e
            else:
                raise ValueError(
                    f"Error accessing S3 bucket '{self.bucket_name}': {e}"
                ) from e
        except NoCredentialsError:
            raise ValueError(
                "AWS credentials not found. Please configure AWS credentials."
            ) from None

    def upload_file(
        self, file_path: str | Path, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload a file to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.upload_file(
                str(file_path), self.bucket_name, object_key, ExtraArgs=extra_args
            )

            logger.info(f"Uploaded file to S3: {object_key}")
            return f"s3://{self.bucket_name}/{object_key}"

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    def download_file(self, object_key: str, destination_path: str | Path) -> None:
        """Download a file from S3."""
        try:
            self.s3_client.download_file(
                self.bucket_name, object_key, str(destination_path)
            )
            logger.info(f"Downloaded file from S3: {object_key}")

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise

    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for S3 object."""
        try:
            url: str = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def delete_file(self, object_key: str) -> None:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Deleted file from S3: {object_key}")

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise

    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str | None = None
    ) -> str:
        """Upload bytes data to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=object_key, Body=data, **extra_args
            )

            logger.info(f"Uploaded bytes to S3: {object_key}")
            return f"s3://{self.bucket_name}/{object_key}"

        except ClientError as e:
            logger.error(f"Failed to upload bytes to S3: {e}")
            raise

    def download_bytes(self, object_key: str) -> bytes:
        """Download bytes data from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=object_key
            )
            data: bytes = response["Body"].read()
            return data

        except ClientError as e:
            logger.error(f"Failed to download bytes from S3: {e}")
            raise
