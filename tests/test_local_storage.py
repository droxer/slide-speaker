"""
Unit tests for the local storage module.
"""

import tempfile
from pathlib import Path

import pytest

from slidespeaker.storage.local_storage import LocalStorage


class TestLocalStorage:
    """Test cases for the LocalStorage class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def local_storage(self, temp_dir):
        """Create a LocalStorage instance with a temporary directory."""
        storage = LocalStorage(base_path=temp_dir, base_url="/test")
        return storage

    def test_init(self, temp_dir):
        """Test that LocalStorage can be instantiated."""
        storage = LocalStorage(base_path=temp_dir, base_url="/test")
        assert isinstance(storage, LocalStorage)
        assert storage.base_path == temp_dir
        assert storage.base_url == "/test"

    def test_upload_file_success(self, local_storage, temp_dir):
        """Test that upload_file successfully uploads a file."""
        # Create a test file
        test_file = temp_dir / "test_upload.txt"
        test_file.write_text("Hello, World!")

        # Upload the file
        result = local_storage.upload_file(
            file_path=test_file, object_key="test/test_file.txt"
        )

        # Verify the result
        assert result == str(temp_dir / "test/test_file.txt")
        assert (temp_dir / "test/test_file.txt").exists()
        assert (temp_dir / "test/test_file.txt").read_text() == "Hello, World!"

    def test_upload_file_nonexistent(self, local_storage, temp_dir):
        """Test that upload_file handles nonexistent files gracefully."""
        with pytest.raises(FileNotFoundError):
            local_storage.upload_file(
                file_path=temp_dir / "nonexistent.txt",
                object_key="test/nonexistent.txt",
            )

    def test_download_file_success(self, local_storage, temp_dir):
        """Test that download_file successfully downloads a file."""
        # Create a test file in storage
        storage_file = temp_dir / "test/download_file.txt"
        storage_file.parent.mkdir(parents=True, exist_ok=True)
        storage_file.write_text("Hello, Download!")

        # Download to a new location
        download_path = temp_dir / "downloads/downloaded_file.txt"
        download_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the file
        local_storage.download_file(
            object_key="test/download_file.txt", destination_path=download_path
        )

        # Verify the result
        assert download_path.exists()
        assert download_path.read_text() == "Hello, Download!"

    def test_download_file_nonexistent(self, local_storage, temp_dir):
        """Test that download_file handles nonexistent files gracefully."""
        download_path = temp_dir / "downloads/nonexistent.txt"
        download_path.parent.mkdir(parents=True, exist_ok=True)

        with pytest.raises(FileNotFoundError):
            local_storage.download_file(
                object_key="test/nonexistent.txt", destination_path=download_path
            )

    def test_get_file_url(self, local_storage):
        """Test that get_file_url returns the correct URL."""
        result = local_storage.get_file_url("test/file.txt")
        assert result == "/files/test/file.txt"

    def test_file_exists_true(self, local_storage, temp_dir):
        """Test that file_exists returns True for existing files."""
        # Create a test file
        test_file = temp_dir / "test/existing_file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Exists!")

        result = local_storage.file_exists("test/existing_file.txt")
        assert result is True

    def test_file_exists_false(self, local_storage):
        """Test that file_exists returns False for nonexistent files."""
        result = local_storage.file_exists("test/nonexistent_file.txt")
        assert result is False

    def test_delete_file_success(self, local_storage, temp_dir):
        """Test that delete_file successfully deletes a file."""
        # Create a test file
        test_file = temp_dir / "test/delete_file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("To be deleted!")

        # Delete the file
        local_storage.delete_file("test/delete_file.txt")

        # Verify the file is deleted
        assert not test_file.exists()

    def test_delete_file_nonexistent(self, local_storage):
        """Test that delete_file handles nonexistent files gracefully."""
        # Should not raise an exception
        local_storage.delete_file("test/nonexistent_file.txt")

    def test_upload_bytes_success(self, local_storage, temp_dir):
        """Test that upload_bytes successfully uploads bytes data."""
        test_data = b"Hello, Bytes!"

        # Upload bytes
        result = local_storage.upload_bytes(
            data=test_data, object_key="test/bytes_file.txt"
        )

        # Verify the result
        assert result == str(temp_dir / "test/bytes_file.txt")
        assert (temp_dir / "test/bytes_file.txt").exists()
        assert (temp_dir / "test/bytes_file.txt").read_bytes() == test_data

    def test_download_bytes_success(self, local_storage, temp_dir):
        """Test that download_bytes successfully downloads bytes data."""
        # Create a test file with bytes data
        test_file = temp_dir / "test/bytes_download.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_data = b"Hello, Download Bytes!"
        test_file.write_bytes(test_data)

        # Download bytes
        result = local_storage.download_bytes("test/bytes_download.txt")

        # Verify the result
        assert result == test_data

    def test_download_bytes_nonexistent(self, local_storage):
        """Test that download_bytes handles nonexistent files gracefully."""
        with pytest.raises(FileNotFoundError):
            local_storage.download_bytes("test/nonexistent_bytes.txt")
