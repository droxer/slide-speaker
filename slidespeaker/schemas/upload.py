"""
Pydantic models for upload endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class UploadPayload(BaseModel):
    """Schema for upload payload validation."""

    filename: str = Field(..., description="Name of the file being uploaded")
    file_data: str = Field(..., description="Base64 encoded file data")
    voice_language: str = Field(
        default="english", description="Voice language for narration"
    )
    subtitle_language: str | None = Field(None, description="Subtitle language")
    transcript_language: str | None = Field(None, description="Transcript language")
    video_resolution: Literal["sd", "hd", "fullhd"] = Field(
        default="hd", description="Video resolution"
    )
    generate_avatar: bool = Field(
        default=False, description="Whether to generate avatar"
    )
    generate_subtitles: bool = Field(
        default=True, description="Whether to generate subtitles"
    )
    generate_podcast: bool = Field(
        default=False, description="Whether to generate podcast"
    )
    generate_video: bool = Field(default=True, description="Whether to generate video")
    task_type: Literal["video", "podcast", "both"] | None = Field(
        None, description="Type of task to generate"
    )
    source_type: Literal["pdf", "slides"] | None = Field(
        None, description="Source file type"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename has a supported extension."""
        if not v:
            raise ValueError("Filename is required")

        ext = Path(v).suffix.lower()
        if ext not in [".pdf", ".pptx", ".ppt"]:
            raise ValueError("Only PDF and PowerPoint files are supported")

        return v

    @field_validator("file_data")
    @classmethod
    def validate_file_data(cls, v: str) -> str:
        """Validate file data is base64 encoded."""
        if not v:
            raise ValueError("File data is required")

        # Basic validation - check if it looks like base64
        if len(v) % 4 != 0:
            raise ValueError("Invalid base64 file data")

        return v

    @field_validator("voice_language")
    @classmethod
    def validate_voice_language(cls, v: str) -> str:
        """Normalize voice language."""
        if not v:
            return "english"
        return v.lower()

    @field_validator("subtitle_language")
    @classmethod
    def validate_subtitle_language(cls, v: str | None) -> str | None:
        """Normalize subtitle language."""
        if v is None:
            return None
        if not v:
            return None
        return v.lower()

    @field_validator("transcript_language")
    @classmethod
    def validate_transcript_language(cls, v: str | None) -> str | None:
        """Normalize transcript language."""
        if v is None:
            return None
        if not v:
            return None
        return v.lower()

    @field_validator("video_resolution")
    @classmethod
    def validate_video_resolution(cls, v: str) -> str:
        """Validate video resolution."""
        if v not in ["sd", "hd", "fullhd"]:
            raise ValueError(
                f"Unsupported video resolution: {v}. Valid options: sd, hd, fullhd"
            )
        return v

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate and derive source type."""
        if v is None:
            # If source_type is not provided, derive from filename
            filename = info.data.get("filename")
            if filename:
                ext = Path(filename).suffix.lower()
                return (
                    "pdf"
                    if ext == ".pdf"
                    else "slides"
                    if ext in [".pptx", ".ppt"]
                    else None
                )
        elif v not in ("pdf", "slides"):
            raise ValueError(f"Invalid source_type: {v}. Must be 'pdf' or 'slides'.")
        return v


class MultipartUploadPayload(BaseModel):
    """Schema for multipart upload payload validation."""

    voice_language: str = Field(
        default="english", description="Voice language for narration"
    )
    subtitle_language: str | None = Field(None, description="Subtitle language")
    transcript_language: str | None = Field(None, description="Transcript language")
    video_resolution: Literal["sd", "hd", "fullhd"] = Field(
        default="hd", description="Video resolution"
    )
    generate_avatar: bool = Field(
        default=False, description="Whether to generate avatar"
    )
    generate_subtitles: bool = Field(
        default=True, description="Whether to generate subtitles"
    )
    generate_podcast: bool = Field(
        default=False, description="Whether to generate podcast"
    )
    generate_video: bool = Field(default=True, description="Whether to generate video")
    task_type: Literal["video", "podcast", "both"] | None = Field(
        None, description="Type of task to generate"
    )
    source_type: Literal["pdf", "slides"] | None = Field(
        None, description="Source file type"
    )

    @field_validator("voice_language")
    @classmethod
    def validate_voice_language(cls, v: str) -> str:
        """Normalize voice language."""
        if not v:
            return "english"
        return v.lower()

    @field_validator("subtitle_language")
    @classmethod
    def validate_subtitle_language(cls, v: str | None) -> str | None:
        """Normalize subtitle language."""
        if v is None:
            return None
        if not v:
            return None
        return v.lower()

    @field_validator("transcript_language")
    @classmethod
    def validate_transcript_language(cls, v: str | None) -> str | None:
        """Normalize transcript language."""
        if v is None:
            return None
        if not v:
            return None
        return v.lower()

    @field_validator("video_resolution")
    @classmethod
    def validate_video_resolution(cls, v: str) -> str:
        """Validate video resolution."""
        if v not in ["sd", "hd", "fullhd"]:
            raise ValueError(
                f"Unsupported video resolution: {v}. Valid options: sd, hd, fullhd"
            )
        return v
