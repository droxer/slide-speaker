"""
Repository package for SlideSpeaker.

This package contains database repository implementations.
"""

from .task import get_statistics, insert_task, list_tasks, update_task
from .upload import get_upload, list_uploads_for_user, upsert_upload
