"""
Video composition module for SlideSpeaker.

This module handles the creation of final presentation videos by combining
slide images, audio files, avatar videos, and subtitles. It supports both
full-featured presentations with AI avatars and simpler image+audio presentations.
"""

import asyncio
import gc
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.Resize import Resize
from moviepy.video.VideoClip import TextClip

from slidespeaker.utils.config import get_storage_provider

logger = logging.getLogger(__name__)


class VideoComposer:
    """Composer for creating final presentation videos from components"""

    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.storage_provider = get_storage_provider()
        self.temp_files: list[Path] = []

    def _validate_video_file(self, video_path: Path) -> tuple[bool, str]:
        if not video_path.exists():
            return False, f"Video file does not exist: {video_path}"
        if video_path.stat().st_size == 0:
            return False, f"Video file is empty: {video_path}"
        try:
            with VideoFileClip(str(video_path)) as clip:
                _ = clip.duration
                return True, ""
        except Exception as e:
            return False, f"Video file is corrupted: {video_path} - {str(e)}"

    def _validate_audio_file(self, audio_path: Path) -> tuple[bool, str]:
        if not audio_path.exists():
            return False, f"Audio file does not exist: {audio_path}"
        if audio_path.stat().st_size == 0:
            return False, f"Audio file is empty: {audio_path}"
        try:
            with AudioFileClip(str(audio_path)) as clip:
                duration = clip.duration
                if duration <= 0:
                    return (
                        False,
                        f"Audio file has zero or negative duration: {audio_path}",
                    )
                return True, ""
        except Exception as e:
            return False, f"Audio file is corrupted: {audio_path} - {str(e)}"

    def _get_resolution_dimensions(self, video_resolution: str) -> tuple[int, int]:
        resolution_map = {"sd": (640, 480), "hd": (1280, 720), "fullhd": (1920, 1080)}
        return resolution_map.get(video_resolution, (1280, 720))

    def _get_memory_safe_size(
        self,
        original_clip: object,
        max_width: int = 1920,
        max_height: int = 1080,
    ) -> tuple[int, int]:
        try:
            original_width, original_height = original_clip.size  # type: ignore[attr-defined]
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_ratio = min(width_ratio, height_ratio, 1.0)
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)
            return max(new_width, 320), max(new_height, 240)
        except Exception:
            return 1280, 720

    def _create_watermark(self, final_clip: VideoFileClip) -> TextClip | None:
        try:
            from slidespeaker.utils.config import config

            if not config.watermark_enabled:
                logger.info("Watermark disabled via configuration")
                return None
            visible_font_size = max(config.watermark_size, 48)
            try:
                watermark = TextClip(
                    text=config.watermark_text,
                    font_size=visible_font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=4,
                    method="label",
                    font="Arial",
                )
            except Exception:
                watermark = TextClip(
                    text=config.watermark_text,
                    font_size=visible_font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    method="label",
                )
            watermark_width = watermark.size[0]
            watermark_height = watermark.size[1]
            try:
                width = int(final_clip.w)
                height = int(final_clip.h)
            except (AttributeError, ValueError):
                if hasattr(final_clip, "size") and len(final_clip.size) >= 2:
                    width = int(final_clip.size[0])
                    height = int(final_clip.size[1])
                else:
                    width = 1920
                    height = 1080
            watermark = watermark.with_position(
                (
                    max(0, width - watermark_width - 50),
                    max(0, height - watermark_height - 50),
                )
            )
            watermark = watermark.with_duration(final_clip.duration)
            visible_opacity = min(max(config.watermark_opacity, 0.9), 1.0)
            watermark = watermark.with_opacity(visible_opacity)
            return watermark
        except Exception as e:
            logger.error(f"Watermark creation failed: {e}")
            return None

    def _is_cloud_url(self, path: str) -> bool:
        return path.startswith(("s3://", "gs://", "https://", "http://"))

    def _get_local_path_from_url(self, url: str) -> Path:
        if url.startswith("s3://"):
            parsed = urlparse(url)
            key = parsed.path.lstrip("/")
            return Path(key)
        elif url.startswith(("https://", "http://")):
            parsed = urlparse(url)
            path = parsed.path.lstrip("/")
            return Path(path)
        else:
            return Path(url)

    async def _download_cloud_file(self, url: str, temp_dir: str) -> Path:
        try:
            object_key = str(self._get_local_path_from_url(url))
            temp_path = Path(temp_dir) / Path(object_key).name
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_provider.download_file(object_key, temp_path)
            self.temp_files.append(temp_path)
            return temp_path
        except Exception as e:
            logger.error(f"Failed to download cloud file {url}: {e}")
            raise

    async def _prepare_files_for_processing(
        self, file_paths: list[Path], temp_dir: str
    ) -> list[Path]:
        prepared_paths = []
        for file_path in file_paths:
            file_str = str(file_path)
            if self._is_cloud_url(file_str):
                local_path = await self._download_cloud_file(file_str, temp_dir)
                prepared_paths.append(local_path)
            else:
                prepared_paths.append(Path(file_path))
        return prepared_paths

    def cleanup_temp_files(self) -> None:
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        self.temp_files.clear()

    async def create_images_only_video(
        self, slide_images: list[Path], output_path: Path, video_resolution: str = "hd"
    ) -> None:
        await self._create_video(slide_images, [], output_path, video_resolution)

    async def create_video_with_audio(
        self,
        slide_images: list[Path],
        audio_files: list[Path],
        output_path: Path,
        video_resolution: str = "hd",
    ) -> None:
        await self._create_video(
            slide_images, audio_files, output_path, video_resolution
        )

    async def compose_video(
        self,
        slide_images: list[Path],
        avatar_videos: list[Path],
        audio_files: list[Path],
        output_path: Path,
        video_resolution: str = "hd",
    ) -> None:
        await self._compose_video_with_local_files(
            slide_images, avatar_videos, audio_files, output_path, video_resolution
        )

    async def compose_video_from_segments(
        self,
        segments: list[dict[str, Any]],
        output_path: str,
        video_resolution: str = "hd",
    ) -> None:
        await self._compose_video_from_segments(segments, output_path, video_resolution)

    async def _compose_video_from_segments(
        self,
        segments: list[dict[str, Any]],
        output_path: str,
        video_resolution: str = "hd",
    ) -> None:
        def _compose_video_from_segments_sync() -> None:
            try:
                if not segments:
                    raise ValueError("No segments provided for video composition")
                video_clips = []
                for segment in segments:
                    duration = float(segment.get("duration", 0))
                    if duration <= 0:
                        continue
                    image_path = Path(segment["image"]) if "image" in segment else None
                    audio_path = Path(segment["audio"]) if "audio" in segment else None
                    subtitle_text = segment.get("subtitle")
                    video_clip = None
                    if image_path and image_path.exists():
                        video_clip = ImageClip(str(image_path), duration=duration)
                    if audio_path and audio_path.exists():
                        audio_clip = AudioFileClip(str(audio_path))
                        if video_clip is None:
                            video_clip = ImageClip(
                                color=(255, 255, 255), duration=audio_clip.duration
                            )
                        video_clip = video_clip.with_audio(audio_clip)
                    if subtitle_text:
                        subtitle_text = (subtitle_text or "").strip()
                    if video_clip is not None:
                        video_clips.append(video_clip)
                if not video_clips:
                    raise ValueError("No valid clips generated for composition")
                final_clip = concatenate_videoclips(video_clips, method="compose")
                watermark = self._create_watermark(final_clip)
                if watermark is not None:
                    try:
                        original_audio = final_clip.audio
                        final_clip = CompositeVideoClip([final_clip, watermark])
                        if original_audio is not None:
                            final_clip = final_clip.with_audio(original_audio)
                    except Exception:
                        pass
                target_width, target_height = self._get_resolution_dimensions(
                    video_resolution
                )
                final_clip_resized = final_clip.with_effects(
                    [Resize(width=target_width, height=target_height)]
                )
                final_clip_resized.write_videofile(
                    output_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,
                    preset="medium",
                    bitrate="2000k",
                    audio_bitrate="128k",
                    temp_audiofile=str(Path(output_path).parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,
                )
            except Exception as e:
                logger.error(f"Video composition error: {e}")
                raise
            finally:
                try:
                    for clip in video_clips:
                        clip.close()
                    if "final_clip" in locals():
                        final_clip.close()
                    if "final_clip_resized" in locals():
                        final_clip_resized.close()
                except Exception:
                    pass
                gc.collect()

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _compose_video_from_segments_sync),
                    timeout=1800,
                )
            except TimeoutError:
                raise Exception(
                    "Video composition timed out after 30 minutes"
                ) from None

    async def _compose_video_with_local_files(
        self,
        slide_images: list[Path],
        avatar_videos: list[Path],
        audio_files: list[Path],
        output_path: Path,
        video_resolution: str = "hd",
    ) -> None:
        def _compose_video_sync() -> None:
            try:
                if not slide_images:
                    raise ValueError("No slide images provided")
                if not avatar_videos:
                    return
                if len(slide_images) != len(avatar_videos) or len(slide_images) != len(
                    audio_files
                ):
                    logger.warning(
                        "Mismatched counts; attempting best-effort composition"
                    )
                video_clips = []
                num_segments = min(
                    len(slide_images), len(avatar_videos), len(audio_files)
                )
                for i in range(num_segments):
                    image_path = slide_images[i]
                    avatar_path = avatar_videos[i]
                    audio_path = audio_files[i]
                    if not image_path.exists() or not avatar_path.exists():
                        continue
                    bg_clip = ImageClip(str(image_path))
                    with AudioFileClip(str(audio_path)) as audio_clip:
                        duration = audio_clip.duration
                    bg_clip = bg_clip.with_duration(duration)
                    fg_clip = VideoFileClip(str(avatar_path)).with_duration(duration)
                    fg_clip = fg_clip.resize(height=int(bg_clip.h * 0.9))
                    fg_clip = fg_clip.with_position(
                        (
                            int((bg_clip.w - fg_clip.w) / 2),
                            int((bg_clip.h - fg_clip.h) / 2),
                        )
                    )
                    comp_clip = CompositeVideoClip([bg_clip, fg_clip])
                    from contextlib import suppress

                    with suppress(Exception):
                        comp_clip = comp_clip.with_audio(AudioFileClip(str(audio_path)))
                    video_clips.append(comp_clip)
                if not video_clips:
                    raise ValueError("No valid clips for composition")
                final_clip = concatenate_videoclips(video_clips, method="compose")
                watermark = self._create_watermark(final_clip)
                if watermark is not None:
                    try:
                        original_audio = final_clip.audio
                        final_clip = CompositeVideoClip([final_clip, watermark])
                        if original_audio is not None:
                            final_clip = final_clip.with_audio(original_audio)
                    except Exception:
                        pass
                target_width, target_height = self._get_resolution_dimensions(
                    video_resolution
                )
                final_clip_resized = final_clip.with_effects(
                    [Resize(width=target_width, height=target_height)]
                )
                final_clip_resized.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,
                    preset="medium",
                    bitrate="2000k",
                    audio_bitrate="128k",
                    temp_audiofile=str(Path(output_path).parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,
                )
            except Exception as e:
                logger.error(f"Error composing video: {e}")
                raise
            finally:
                gc.collect()

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _compose_video_sync), timeout=1800
                )
            except TimeoutError:
                raise Exception(
                    "Video composition timed out after 30 minutes"
                ) from None

    async def _create_video(
        self,
        slide_images: list[Path],
        audio_files: list[Path],
        output_path: Path,
        video_resolution: str = "hd",
    ) -> None:
        def _create_video_sync() -> None:
            try:
                if not slide_images:
                    raise ValueError("No slide images provided")
                video_clips = []
                for i, image_path in enumerate(slide_images):
                    image_path = Path(image_path)
                    if not image_path.exists():
                        continue
                    duration = 5.0
                    if i < len(audio_files):
                        ap = Path(audio_files[i])
                        if ap.exists():
                            try:
                                with AudioFileClip(str(ap)) as ac:
                                    duration = ac.duration
                            except Exception:
                                pass
                    video_clip = ImageClip(str(image_path), duration=duration)
                    if i < len(audio_files):
                        ap = Path(audio_files[i])
                        if ap.exists():
                            from contextlib import suppress

                            with suppress(Exception):
                                video_clip = video_clip.with_audio(
                                    AudioFileClip(str(ap))
                                )
                    video_clips.append(video_clip)
                if not video_clips:
                    raise ValueError("No valid clips for video creation")
                final_clip = concatenate_videoclips(video_clips, method="compose")
                watermark = self._create_watermark(final_clip)
                if watermark is not None:
                    try:
                        original_audio = final_clip.audio
                        final_clip = CompositeVideoClip([final_clip, watermark])
                        if original_audio is not None:
                            final_clip = final_clip.with_audio(original_audio)
                    except Exception:
                        pass
                target_width, target_height = self._get_resolution_dimensions(
                    video_resolution
                )
                final_clip_resized = final_clip.with_effects(
                    [Resize(width=target_width, height=target_height)]
                )
                final_clip_resized.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,
                    preset="medium",
                    bitrate="2000k",
                    audio_bitrate="128k",
                    temp_audiofile=str(Path(output_path).parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,
                )
            except Exception as e:
                logger.error(f"Error creating video: {e}")
                raise
            finally:
                gc.collect()

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _create_video_sync), timeout=1800
                )
            except TimeoutError:
                raise Exception("Video creation timed out after 30 minutes") from None
