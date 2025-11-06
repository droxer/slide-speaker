"""
Video pipeline coordinator for SlideSpeaker (PDF and Slides sources).

Provides two entry points:
- from_pdf(...): video processing for PDF inputs
- from_slide(...): video processing for PPT/PPTX inputs

Podcast generation is handled in the separate podcast pipeline.
"""

from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager

from ..base import BasePipeline
from ..helpers import (
    fetch_task_state,
)

# PDF steps (video)
from ..steps.video.pdf import (
    compose_video_step as pdf_compose_video_step,
)
from ..steps.video.pdf import (
    generate_audio_step as pdf_generate_audio_step,
)
from ..steps.video.pdf import (
    generate_frames_step as pdf_generate_frames_step,
)
from ..steps.video.pdf import (
    generate_subtitles_step as pdf_generate_subtitles_step,
)
from ..steps.video.pdf import (
    revise_transcripts_step as pdf_revise_transcripts_step,
)
from ..steps.video.pdf import (
    segment_content_step as pdf_segment_content_step,
)
from ..steps.video.pdf import (
    translate_subtitle_transcripts_step as pdf_translate_subs_step,
)
from ..steps.video.pdf import (
    translate_voice_transcripts_step as pdf_translate_voice_step,
)

# Slides steps (video)
from ..steps.video.slides import (
    analyze_slides_step,
    convert_slides_step,
    extract_slides_step,
    generate_avatar_step,
    generate_transcripts_step,
)
from ..steps.video.slides import (
    compose_video_step as slide_compose_video_step,
)
from ..steps.video.slides import (
    generate_audio_step as slide_generate_audio_step,
)
from ..steps.video.slides import (
    generate_subtitles_step as slide_generate_subtitles_step,
)
from ..steps.video.slides import (
    revise_transcripts_step as slide_revise_transcripts_step,
)
from ..steps.video.slides import (
    translate_subtitle_transcripts_step as slide_translate_subs_step,
)
from ..steps.video.slides import (
    translate_voice_transcripts_step as slide_translate_voice_step,
)


def _pdf_step_name(
    step: str, voice_language: str | None, subtitle_language: str | None
) -> str:
    """Get display name for PDF video steps."""
    base = {
        "segment_pdf_content": "Segmenting PDF content into chapters",
        "revise_pdf_transcripts": "Revising and refining chapter transcripts",
        "translate_voice_transcripts": "Translating voice transcripts",
        "translate_subtitle_transcripts": "Translating subtitle transcripts",
        "generate_pdf_chapter_images": "Generating chapter images",
        "generate_pdf_audio": "Generating chapter audio",
        "generate_pdf_subtitles": "Generating subtitles",
        "compose_video": "Composing final video",
    }
    if step in ("translate_voice_transcripts", "translate_subtitle_transcripts"):
        vl = (voice_language or "english").lower()
        sl = (subtitle_language or vl).lower()
        if vl == sl and vl != "english":
            return "Translating transcripts"
    return base.get(step, step)


def _pdf_steps(
    voice_language: str,
    subtitle_language: str | None,
    generate_subtitles: bool,
    generate_video: bool,
) -> list[str]:
    """Determine ordered steps for PDF video processing."""
    steps: list[str] = ["segment_pdf_content", "revise_pdf_transcripts"]
    if voice_language.lower() != "english":
        steps.append("translate_voice_transcripts")
    if subtitle_language and subtitle_language.lower() != "english":
        steps.append("translate_subtitle_transcripts")
    if generate_video:
        steps.extend(["generate_pdf_chapter_images", "generate_pdf_audio"])
        if generate_subtitles:
            steps.append("generate_pdf_subtitles")
        steps.append("compose_video")
    return steps


async def from_pdf(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_subtitles: bool = True,
    generate_video: bool = True,
    task_id: str | None = None,
) -> None:
    """Process PDF file to generate video."""
    pipeline = PDFVideoPipeline(
        file_id=file_id,
        file_path=file_path,
        task_id=task_id,
        voice_language=voice_language,
        subtitle_language=subtitle_language,
        generate_subtitles=generate_subtitles,
        generate_video=generate_video,
    )
    await pipeline.execute_pipeline()


class PDFVideoPipeline(BasePipeline):
    """PDF Video Pipeline Implementation."""

    def __init__(
        self,
        file_id: str,
        file_path: Path,
        task_id: str | None = None,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        generate_subtitles: bool = True,
        generate_video: bool = True,
    ):
        super().__init__(file_id, file_path, task_id)
        self.voice_language = voice_language
        self.subtitle_language = subtitle_language
        self.generate_subtitles = generate_subtitles
        self.generate_video = generate_video

        # Define step execution mapping
        self._pdf_step_map = {
            "segment_pdf_content": lambda: pdf_segment_content_step(
                self.file_id, self.file_path, "english"
            ),
            "revise_pdf_transcripts": lambda: pdf_revise_transcripts_step(
                self.file_id, "english", task_id=self.task_id
            ),
            "translate_voice_transcripts": lambda: pdf_translate_voice_step(
                self.file_id,
                source_language="english",
                target_language=self.voice_language,
            ),
            "translate_subtitle_transcripts": lambda: pdf_translate_subs_step(
                self.file_id,
                source_language="english",
                target_language=self.subtitle_language or "english",
            ),
            "generate_pdf_chapter_images": lambda: pdf_generate_frames_step(
                self.file_id, self.voice_language
            ),
            "generate_pdf_audio": lambda: pdf_generate_audio_step(
                self.file_id, self.voice_language
            ),
            "generate_pdf_subtitles": lambda: pdf_generate_subtitles_step(
                self.file_id, self.subtitle_language or "english"
            ),
            "compose_video": lambda: pdf_compose_video_step(self.file_id),
        }

    def get_step_display_name(self, step_name: str) -> str:
        return _pdf_step_name(step_name, self.voice_language, self.subtitle_language)

    async def execute_pipeline(self) -> None:
        logger.info(f"Initiating video generation (PDF) for file: {self.file_id}")
        logger.info(
            f"Voice language: {self.voice_language}, Subtitle language: {self.subtitle_language}"
        )
        logger.info(
            f"Generate subtitles: {self.generate_subtitles}, Generate video: {self.generate_video}"
        )

        if not await self._check_and_handle_prerequisites():
            return

        # Initialize/refresh state flags relevant to video
        task_state = await fetch_task_state(self.file_id)
        if task_state:
            task_state["voice_language"] = self.voice_language
            task_state["subtitle_language"] = self.subtitle_language
            task_state["generate_avatar"] = False
            task_state["generate_subtitles"] = self.generate_subtitles
            task_state["generate_video"] = self.generate_video
            if self.task_id:
                task_state["task_id"] = self.task_id
            await state_manager.save_task_state(self.file_id, task_state)

        if self.task_id:
            logger.info(
                f"=== Starting PDF video processing for task {self.task_id} ==="
            )

        steps_order = _pdf_steps(
            self.voice_language,
            self.subtitle_language,
            self.generate_subtitles,
            self.generate_video,
        )

        try:
            for step_name in steps_order:
                success = await self._execute_step(
                    step_name, self._execute_pdf_step, step_name
                )
                if not success:
                    return

            if self.generate_video:
                await state_manager.mark_completed(self.file_id)
                logger.info(
                    f"All PDF video processing steps completed for file {self.file_id}"
                )
        except Exception as e:
            logger.error(f"PDF video processing failed: {e}")
            await state_manager.mark_failed(self.file_id)
            raise

    async def _execute_pdf_step(self, step_name: str):
        """Execute a specific PDF processing step using the step mapping."""
        step_func = self._pdf_step_map.get(step_name)
        if step_func:
            await step_func()


# ----------------------- Slides Coordinator (from_slide) ----------------------


def _slide_step_name(step: str) -> str:
    """Get display name for slides video steps."""
    base = {
        "extract_slides": "Extracting slides",
        "convert_slides": "Converting slides to images",
        "analyze_slides": "Analyzing slide content",
        "generate_transcripts": "Generating transcripts",
        "revise_transcripts": "Revising transcripts",
        "generate_audio": "Generating audio",
        "generate_avatar": "Generating avatar",
        "generate_subtitles": "Generating subtitles",
        "compose_video": "Composing final video",
        "translate_voice_transcripts": "Translating voice transcripts",
        "translate_subtitle_transcripts": "Translating subtitle transcripts",
    }
    return base.get(step, step)


def _slide_state_key(step: str) -> str:
    """Map human-readable step names to their underlying state keys."""
    mapping = {
        "convert_slides": "convert_slides_to_images",
        "analyze_slides": "analyze_slide_images",
        "generate_avatar": "generate_avatar_videos",
    }
    return mapping.get(step, step)


def _slide_steps(
    generate_video: bool,
    generate_avatar: bool,
    generate_subtitles: bool,
    *,
    voice_language: str | None = None,
    subtitle_language: str | None = None,
) -> list[str]:
    """Determine ordered steps for slide video processing."""
    steps: list[str] = [
        "extract_slides",
        "convert_slides",
        "analyze_slides",
        "generate_transcripts",
        "revise_transcripts",
    ]
    # Translation steps mirror PDF behavior: translate when target differs from English
    if (voice_language or "english").lower() != "english":
        steps.append("translate_voice_transcripts")
    if subtitle_language and subtitle_language.lower() != "english":
        steps.append("translate_subtitle_transcripts")
    # Audio and optional avatar
    if generate_video:
        steps.append("generate_audio")
        if generate_avatar:
            steps.append("generate_avatar")
        if generate_subtitles:
            steps.append("generate_subtitles")
        steps.append("compose_video")
    return steps


async def from_slide(
    file_id: str,
    file_path: Path,
    file_ext: str,
    voice_language: str = "english",
    subtitle_language: str | None = None,
    generate_avatar: bool = False,
    generate_subtitles: bool = True,
    generate_video: bool = True,
    task_id: str | None = None,
) -> None:
    """Process slide file to generate video."""
    pipeline = SlidesVideoPipeline(
        file_id=file_id,
        file_path=file_path,
        file_ext=file_ext,
        task_id=task_id,
        voice_language=voice_language,
        subtitle_language=subtitle_language,
        generate_avatar=generate_avatar,
        generate_subtitles=generate_subtitles,
        generate_video=generate_video,
    )
    await pipeline.execute_pipeline()


class SlidesVideoPipeline(BasePipeline):
    """Slides Video Pipeline Implementation."""

    def __init__(
        self,
        file_id: str,
        file_path: Path,
        file_ext: str,
        task_id: str | None = None,
        voice_language: str = "english",
        subtitle_language: str | None = None,
        generate_avatar: bool = False,
        generate_subtitles: bool = True,
        generate_video: bool = True,
    ):
        super().__init__(file_id, file_path, task_id)
        self.file_ext = file_ext
        self.voice_language = voice_language
        self.subtitle_language = subtitle_language
        self.generate_avatar = generate_avatar
        self.generate_subtitles = generate_subtitles
        self.generate_video = generate_video

        # Define step execution mapping
        self._slide_step_map = {
            "extract_slides": lambda: extract_slides_step(
                self.file_id, self.file_path, self.file_ext
            ),
            "convert_slides": lambda: convert_slides_step(
                self.file_id, self.file_path, self.file_ext
            ),
            "analyze_slides": lambda: analyze_slides_step(self.file_id),
            "generate_transcripts": lambda: generate_transcripts_step(
                self.file_id, "english"
            ),
            "revise_transcripts": lambda: slide_revise_transcripts_step(
                self.file_id, "english", task_id=self.task_id
            ),
            "translate_voice_transcripts": lambda: slide_translate_voice_step(
                self.file_id,
                source_language="english",
                target_language=self.voice_language,
            ),
            "translate_subtitle_transcripts": lambda: slide_translate_subs_step(
                self.file_id,
                source_language="english",
                target_language=self.subtitle_language or "english",
            ),
            "generate_audio": lambda: slide_generate_audio_step(
                self.file_id, self.voice_language
            ),
            "generate_avatar": lambda: generate_avatar_step(self.file_id),
            "generate_subtitles": lambda: slide_generate_subtitles_step(
                self.file_id, self.subtitle_language or "english"
            ),
            "compose_video": lambda: slide_compose_video_step(
                self.file_id, self.file_path
            ),
        }

    def get_step_display_name(self, step_name: str) -> str:
        return _slide_step_name(step_name)

    async def execute_pipeline(self) -> None:
        logger.info(f"Starting slides video processing for file {self.file_id}")
        logger.info(
            f"Voice language: {self.voice_language}, Subtitle language: {self.subtitle_language}"
        )
        logger.debug(
            "Generate video: %s, Generate avatar: %s, Generate subtitles: %s",
            self.generate_video,
            self.generate_avatar,
            self.generate_subtitles,
        )

        if not await self._check_and_handle_prerequisites():
            return

        # Initialize/refresh state flags relevant to slides video processing
        state = await state_manager.get_state(self.file_id)
        if state:
            state["voice_language"] = self.voice_language
            state["subtitle_language"] = self.subtitle_language
            state["generate_avatar"] = self.generate_avatar
            state["generate_subtitles"] = self.generate_subtitles
            state["generate_video"] = self.generate_video
            if self.task_id:
                state["task_id"] = self.task_id
            await state_manager.save_state(self.file_id, state)

        steps_order = _slide_steps(
            self.generate_video,
            self.generate_avatar,
            self.generate_subtitles,
            voice_language=self.voice_language,
            subtitle_language=self.subtitle_language,
        )

        try:
            for step_name in steps_order:
                step_key = _slide_state_key(step_name)
                success = await self._execute_step(
                    step_key, self._execute_slide_step, step_name
                )
                if not success:
                    return

            await state_manager.mark_completed(self.file_id)
            logger.info(
                f"All slides video processing steps completed for file {self.file_id}"
            )
        except Exception as e:
            logger.error(f"Slides video processing failed: {e}")
            await state_manager.mark_failed(self.file_id)
            raise

    async def _execute_slide_step(self, step_name: str):
        """Execute a specific slide processing step using the step mapping."""
        step_func = self._slide_step_map.get(step_name)
        if step_func:
            await step_func()
