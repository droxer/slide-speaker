"""
Unit tests for the background jobs package.
"""

from unittest.mock import patch

from slidespeaker.jobs import file_purger
from slidespeaker.jobs.file_purger import FilePurger


class TestBackgroundJobs:
    """Test cases for the background jobs package."""

    def test_file_purger_import(self):
        """Test that FilePurger class can be imported."""
        assert FilePurger is not None

    def test_file_purger_instance(self):
        """Test that FilePurger can be instantiated."""
        with (
            patch("slidespeaker.storage.StorageConfig"),
            patch("slidespeaker.jobs.file_purger.get_storage_provider"),
            patch("slidespeaker.jobs.file_purger.config"),
        ):
            purger = FilePurger()
            assert isinstance(purger, FilePurger)

    def test_file_purger_global_instance(self):
        """Test that global file_purger instance exists."""
        assert file_purger.file_purger is not None
        assert isinstance(file_purger.file_purger, FilePurger)
