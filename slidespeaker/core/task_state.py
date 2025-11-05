"""
Typed helpers for sharing task state between pipeline steps.

These objects provide a light abstraction over the raw state dictionaries stored
by :mod:`slidespeaker.core.state_manager`. They behave like ordinary dict/list
structures so existing pipeline code continues to work, while also exposing
convenience accessors and normalization helpers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

DEFAULT_STEP_ORDER = [
    # Slide ingestion
    "extract_slides",
    "convert_slides_to_images",
    "analyze_slide_images",
    # PDF ingestion
    "segment_pdf_content",
    # Script generation & refinement
    "generate_transcripts",
    "revise_transcripts",
    "revise_pdf_transcripts",
    "generate_subtitle_transcripts",
    "generate_podcast_script",
    # Translation
    "translate_voice_transcripts",
    "translate_subtitle_transcripts",
    "translate_podcast_script",
    # Visual preparation
    "generate_pdf_chapter_images",
    # Audio generation
    "generate_audio",
    "generate_pdf_audio",
    "generate_podcast_audio",
    "generate_podcast_subtitles",
    "generate_avatar_videos",
    # Subtitle assets
    "generate_subtitles",
    "generate_pdf_subtitles",
    # Final assembly
    "compose_video",
    "compose_podcast",
    # Fallback for unknown / legacy step names
    "unknown",
]

_STATUS_MAP = {
    "completed": "completed",
    "complete": "completed",
    "processing": "processing",
    "in_progress": "processing",
    "running": "processing",
    "failed": "failed",
    "error": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "skipped": "skipped",
    "queued": "pending",
    "waiting": "pending",
    "pending": "pending",
}

_FIELD_ALIAS_MAP = {
    "subtitle_language": "subtitle_language_raw",
}


def _clean_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def normalize_step_status(status: object | None) -> str:
    """Normalize a raw status string into the canonical set used by the UI."""
    key = _clean_str(status)
    if key is None:
        return "pending"
    return _STATUS_MAP.get(key.lower(), "pending")


class StepSnapshot(dict):
    """Structured view of a single pipeline step (dict-compatible)."""

    __slots__ = ("name",)

    def __init__(self, name: str, payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(payload or {})
        self.name = name
        self.setdefault("status", "pending")

    @property
    def status(self) -> str:
        return str(self.get("status", "pending"))

    @status.setter
    def status(self, value: str) -> None:
        self["status"] = value

    @property
    def data(self) -> Any:
        return self.get("data")

    @data.setter
    def data(self, value: Any) -> None:
        self["data"] = value

    def as_dict(self, *, normalize_status_flag: bool = False) -> dict[str, Any]:
        result = dict(self)
        if normalize_status_flag:
            result["status"] = normalize_step_status(result.get("status"))
        return result


class TaskErrorEntry(dict):
    """Representation of an error collected during processing (dict-compatible)."""

    __slots__ = ()

    @classmethod
    def from_mapping(cls, payload: Any) -> TaskErrorEntry:
        if isinstance(payload, Mapping):
            return cls(payload)
        cleaned = _clean_str(payload)
        return cls(
            {"error": cleaned or (str(payload) if payload is not None else None)}
        )

    @property
    def step(self) -> str | None:
        return _clean_str(self.get("step"))

    @property
    def error(self) -> str | None:
        raw = self.get("error")
        cleaned = _clean_str(raw)
        return (
            cleaned if cleaned is not None else (str(raw) if raw is not None else None)
        )

    @property
    def timestamp(self) -> str | None:
        return _clean_str(self.get("timestamp"))

    def as_dict(self) -> dict[str, Any]:
        return dict(self)


class TaskState(dict):
    """Structured snapshot of the shared task state persisted between steps."""

    __slots__ = (
        "steps",
        "errors",
        "status",
        "current_step",
        "voice_language",
        "subtitle_language_raw",
        "podcast_transcript_language",
        "voice_id",
        "podcast_host_voice",
        "podcast_guest_voice",
        "generate_video",
        "generate_podcast",
        "generate_subtitles",
        "filename",
        "file_ext",
        "source_type",
        "created_at",
        "updated_at",
        "task_config",
        "task_kwargs",
        "settings",
    )

    def __init__(self, payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(payload or {})
        self.steps: dict[str, StepSnapshot] = {}
        self.errors: list[TaskErrorEntry] = []
        self.status: str = _clean_str(self.get("status")) or "unknown"
        self.current_step: str | None = _clean_str(self.get("current_step"))
        self.voice_language: str | None = None
        self.subtitle_language_raw: str | None = None
        self.podcast_transcript_language: str | None = None
        self.voice_id: str | None = None
        self.podcast_host_voice: str | None = None
        self.podcast_guest_voice: str | None = None
        self.generate_video: bool = bool(self.get("generate_video", True))
        self.generate_podcast: bool = bool(self.get("generate_podcast", False))
        self.generate_subtitles: bool = bool(self.get("generate_subtitles", True))
        self.filename: str | None = _clean_str(self.get("filename"))
        self.file_ext: str | None = _clean_str(self.get("file_ext"))
        self.source_type: str | None = _clean_str(
            self.get("source_type") or self.get("source")
        )
        self.created_at: str | None = _clean_str(self.get("created_at"))
        self.updated_at: str | None = _clean_str(self.get("updated_at"))
        self.task_config: dict[str, Any] = dict(self.get("task_config") or {})
        self.task_kwargs: dict[str, Any] = dict(self.get("task_kwargs") or {})
        self.settings: dict[str, Any] = dict(self.get("settings") or {})
        self._hydrate_steps()
        self._hydrate_errors()
        self._sync_string_fields()

    @classmethod
    def from_mapping(cls, payload: Any) -> TaskState:
        return cls(payload if isinstance(payload, Mapping) else {})

    # Internal helpers --------------------------------------------------------
    def _hydrate_steps(self) -> None:
        raw_steps = self.get("steps")
        self.steps = {}
        if isinstance(raw_steps, Mapping):
            for name, payload in raw_steps.items():
                snapshot = (
                    payload
                    if isinstance(payload, StepSnapshot)
                    else StepSnapshot(
                        str(name), payload if isinstance(payload, Mapping) else {}
                    )
                )
                self.steps[str(name)] = snapshot
        super().__setitem__("steps", self.steps)

    def _hydrate_errors(self) -> None:
        raw_errors = self.get("errors")
        self.errors = []
        if isinstance(raw_errors, list):
            for item in raw_errors:
                if item is None:
                    continue
                entry = (
                    item
                    if isinstance(item, TaskErrorEntry)
                    else TaskErrorEntry.from_mapping(item)
                )
                self.errors.append(entry)
        super().__setitem__("errors", self.errors)

    def _sync_string_fields(self) -> None:
        self.voice_language = _clean_str(self.get("voice_language"))
        self.subtitle_language_raw = _clean_str(self.get("subtitle_language"))
        self.podcast_transcript_language = _clean_str(
            self.get("podcast_transcript_language")
        )
        self.voice_id = _clean_str(self.get("voice_id"))
        self.podcast_host_voice = _clean_str(self.get("podcast_host_voice"))
        self.podcast_guest_voice = _clean_str(self.get("podcast_guest_voice"))
        self.status = _clean_str(self.get("status")) or "unknown"
        self.current_step = _clean_str(self.get("current_step"))

    def _apply_alias(self, key: str) -> str:
        return _FIELD_ALIAS_MAP.get(key, key)

    # dict overrides ----------------------------------------------------------
    def __setitem__(self, key: str, value: Any) -> None:
        alias = self._apply_alias(key)
        if alias == "steps":
            if isinstance(value, Mapping):
                new_steps: dict[str, StepSnapshot] = {}
                for name, payload in value.items():
                    snapshot = (
                        payload
                        if isinstance(payload, StepSnapshot)
                        else StepSnapshot(
                            str(name), payload if isinstance(payload, Mapping) else {}
                        )
                    )
                    new_steps[str(name)] = snapshot
                self.steps = new_steps
            elif isinstance(value, list):
                self.steps = {
                    str(idx): StepSnapshot(
                        str(idx), item if isinstance(item, Mapping) else {}
                    )
                    for idx, item in enumerate(value)
                }
            else:
                self.steps = {}
            super().__setitem__("steps", self.steps)
            return

        if alias == "errors":
            new_errors: list[TaskErrorEntry] = []
            if isinstance(value, list):
                for item in value:
                    if item is None:
                        continue
                    entry = (
                        item
                        if isinstance(item, TaskErrorEntry)
                        else TaskErrorEntry.from_mapping(item)
                    )
                    new_errors.append(entry)
            self.errors = new_errors
        super().__setitem__("errors", self.errors)
        return

        if alias == "status":
            self.status = _clean_str(value) or "unknown"
            super().__setitem__("status", self.status)
            return
        if alias == "current_step":
            self.current_step = _clean_str(value)
            super().__setitem__("current_step", self.current_step)
            return

        super().__setitem__(key, value)
        if alias in {
            "voice_language",
            "subtitle_language_raw",
            "podcast_transcript_language",
            "voice_id",
            "podcast_host_voice",
            "podcast_guest_voice",
            "filename",
            "file_ext",
            "source_type",
            "created_at",
            "updated_at",
        }:
            setattr(self, alias, _clean_str(value))
        elif alias in {"generate_video", "generate_podcast", "generate_subtitles"}:
            setattr(self, alias, bool(value))
        elif alias in {"task_config", "task_kwargs", "settings"}:
            setattr(self, alias, dict(value) if isinstance(value, Mapping) else {})

    # Convenience methods -----------------------------------------------------
    def get_step(self, name: str) -> StepSnapshot | None:
        return self.steps.get(name)

    @property
    def effective_subtitle_language(self) -> str | None:
        for candidate in (
            self.subtitle_language_raw,
            self.podcast_transcript_language,
            self.voice_language,
        ):
            cleaned = _clean_str(candidate)
            if cleaned:
                return cleaned
        return None

    def ordered_steps(
        self,
        order: Sequence[str] | None = None,
        *,
        normalize_status_flag: bool = False,
    ) -> dict[str, Any]:
        step_order = list(order or DEFAULT_STEP_ORDER)
        priority = {step_name: idx for idx, step_name in enumerate(step_order)}

        def _step_priority(item: tuple[str, StepSnapshot]) -> int:
            return priority.get(item[0], len(step_order))

        sorted_items = sorted(self.steps.items(), key=_step_priority)
        return {
            name: snapshot.as_dict(normalize_status_flag=normalize_status_flag)
            for name, snapshot in sorted_items
        }

    def to_dict(self) -> dict[str, Any]:
        data = dict(self)
        data["steps"] = {name: dict(snapshot) for name, snapshot in self.steps.items()}
        data["errors"] = [dict(entry) for entry in self.errors]
        data["status"] = self.status
        data["current_step"] = self.current_step
        if self.voice_language is not None:
            data["voice_language"] = self.voice_language
        if self.subtitle_language_raw is not None:
            data["subtitle_language"] = self.subtitle_language_raw
        if self.podcast_transcript_language is not None:
            data["podcast_transcript_language"] = self.podcast_transcript_language
        if self.voice_id is not None:
            data["voice_id"] = self.voice_id
        if self.podcast_host_voice is not None:
            data["podcast_host_voice"] = self.podcast_host_voice
        if self.podcast_guest_voice is not None:
            data["podcast_guest_voice"] = self.podcast_guest_voice
        data["generate_video"] = self.generate_video
        data["generate_podcast"] = self.generate_podcast
        data["generate_subtitles"] = self.generate_subtitles
        if self.filename is not None:
            data["filename"] = self.filename
        if self.file_ext is not None:
            data["file_ext"] = self.file_ext
        if self.source_type is not None:
            data["source_type"] = self.source_type
        if self.created_at is not None:
            data["created_at"] = self.created_at
        if self.updated_at is not None:
            data["updated_at"] = self.updated_at
        data["task_config"] = deepcopy(self.task_config)
        data["task_kwargs"] = deepcopy(self.task_kwargs)
        data["settings"] = deepcopy(self.settings)
        return data
