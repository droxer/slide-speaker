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

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.Resize import Resize
from moviepy.video.VideoClip import TextClip

logger = logging.getLogger(__name__)


class VideoComposer:
    """Composer for creating final presentation videos from components"""

    def __init__(self, max_memory_mb: int = 500):
        """
        Initialize VideoComposer with memory constraints

        Args:
            max_memory_mb: Maximum memory to use for video processing (MB)
        """
        self.max_memory_mb = max_memory_mb

    def _validate_video_file(self, video_path: Path) -> tuple[bool, str]:
        """
        Validate video file exists and is not corrupted

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not video_path.exists():
            return False, f"Video file does not exist: {video_path}"

        if video_path.stat().st_size == 0:
            return False, f"Video file is empty: {video_path}"

        try:
            # Quick validation by loading just the first frame
            with VideoFileClip(str(video_path)) as clip:
                _ = clip.duration  # This will raise if file is corrupted
                return True, ""
        except Exception as e:
            return False, f"Video file is corrupted: {video_path} - {str(e)}"

    def _validate_audio_file(self, audio_path: Path) -> tuple[bool, str]:
        """
        Validate audio file exists and is not corrupted

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not audio_path.exists():
            return False, f"Audio file does not exist: {audio_path}"

        if audio_path.stat().st_size == 0:
            return False, f"Audio file is empty: {audio_path}"

        try:
            # Quick validation by loading the audio file
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

    def _get_memory_safe_size(
        self, original_clip: object, max_width: int = 1920, max_height: int = 1080
    ) -> tuple[int, int]:
        """
        Calculate memory-safe dimensions for video processing

        Returns:
            Tuple of (width, height) for memory-safe processing
        """
        try:
            original_width, original_height = original_clip.size  # type: ignore[attr-defined]

            # Calculate aspect ratios
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_ratio = min(width_ratio, height_ratio, 1.0)  # Don't scale up

            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

            # Ensure dimensions are even (required by some codecs)
            new_width = new_width - (new_width % 2)
            new_height = new_height - (new_height % 2)

            return max(new_width, 320), max(new_height, 240)  # Minimum dimensions
        except Exception:
            return 1280, 720  # Safe fallback

    def _create_watermark(self, final_clip: VideoFileClip) -> TextClip | None:
        """Create a highly visible SlideSpeaker AI watermark - memory-optimized for long videos"""
        try:
            from slidespeaker.utils.config import config

            if not config.watermark_enabled:
                logger.info("Watermark disabled via configuration")
                return None

            logger.info("Starting watermark creation...")

            try:
                visible_font_size = max(config.watermark_size, 48)
                try:
                    watermark = TextClip(
                        text=config.watermark_text,
                        font_size=visible_font_size,
                        color="white",
                        stroke_color="black",
                        stroke_width=4,  # Thicker stroke for maximum contrast
                        method="label",
                        font="Arial",  # Use standard Arial font
                    )
                    logger.info("✓ Enhanced watermark created successfully")
                except Exception as font_error:
                    logger.warning(
                        f"Enhanced watermark with Arial failed: {font_error}"
                    )
                    # Fallback to system default font
                    watermark = TextClip(
                        text=config.watermark_text,
                        font_size=visible_font_size,
                        color="white",
                        stroke_color="black",
                        stroke_width=3,
                        method="label",
                    )
                    logger.info("✓ Fallback watermark created successfully")

            except Exception as e:
                logger.warning(f"Enhanced watermark failed: {e}")
                logger.info("Attempting fallback watermark...")

                try:
                    # Use enhanced fallback with larger size
                    visible_font_size = max(config.watermark_size, 42)
                    watermark = TextClip(
                        text=config.watermark_text,
                        font_size=visible_font_size,
                        color="white",
                        stroke_color="black",
                        stroke_width=3,  # Thicker fallback stroke
                        font="Arial",
                    )
                    logger.info("✓ Fallback watermark created successfully")
                except Exception as e2:
                    logger.error(f"Fallback watermark also failed: {e2}")
                    return None

            # Position watermark relative to video dimensions with margins
            # Calculate exact position: video.w - watermark.w - 50, video.h - watermark.h - 50
            # Use lambda function for dynamic positioning based on video dimensions
            watermark_width = watermark.size[0]
            watermark_height = watermark.size[1]

            try:
                width = int(final_clip.w)
                height = int(final_clip.h)
            except (AttributeError, ValueError):
                # Fallback if clip doesn't have w/h attributes
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
            # Increase opacity for better visibility
            visible_opacity = min(max(config.watermark_opacity, 0.9), 1.0)
            watermark = watermark.with_opacity(visible_opacity)

            logger.info(f"✓ Watermark ready: '{config.watermark_text}'")
            logger.info("=== WATERMARK CREATION COMPLETE ===")
            return watermark

        except Exception as e:
            logger.error(f"Watermark creation failed: {e}")
            logger.exception("Full watermark creation traceback:")
            return None

    async def compose_video(
        self,
        slide_images: list[Path],
        avatar_videos: list[Path],
        audio_files: list[Path],
        output_path: Path,
    ) -> None:
        """
        Compose final video with slide images as background and AI avatar presenting
        Memory-efficient version with progress tracking, error handling, and timeout protection
        """

        def _compose_video_sync() -> None:
            try:
                logger.info(
                    f"Starting video composition with {len(slide_images)} slides and avatars"
                )

                # Validate inputs
                if not slide_images:
                    raise ValueError("No slide images provided")
                if not avatar_videos:
                    logger.warning(
                        "No avatar videos provided, falling back to simple video"
                    )
                    return
                if len(slide_images) != len(avatar_videos) or len(slide_images) != len(
                    audio_files
                ):
                    logger.warning(
                        f"Mismatched file counts: slides={len(slide_images)}, "
                        f"avatars={len(avatar_videos)}, audio={len(audio_files)}"
                    )

                # Ensure minimum for processing
                min_files = min(len(slide_images), len(avatar_videos), len(audio_files))
                if min_files == 0:
                    raise ValueError("No valid files for video composition")

                # Truncate to minimum to prevent mismatched processing
                valid_slide_images = slide_images[:min_files]
                valid_avatar_videos = avatar_videos[:min_files]
                valid_audio_files = audio_files[:min_files]

                # Validate all avatar videos before processing
                final_avatar_videos = []
                final_audio_files = []
                final_slide_images = []

                for i, (slide_image, avatar_video, audio_file) in enumerate(
                    zip(
                        valid_slide_images,
                        valid_avatar_videos,
                        valid_audio_files,
                        strict=False,
                    )
                ):
                    logger.info(f"Validating slide {i + 1} components...")

                    # Validate files
                    is_valid, error_msg = self._validate_video_file(avatar_video)
                    if not is_valid:
                        logger.warning(f"Skipping avatar video {i + 1}: {error_msg}")
                        continue

                    if not slide_image.exists():
                        logger.warning(
                            f"Skipping slide image {i + 1}: {slide_image} not found"
                        )
                        continue

                    is_valid, error_msg = self._validate_audio_file(audio_file)
                    if not is_valid:
                        logger.warning(f"Skipping audio file {i + 1}: {error_msg}")
                        continue

                    final_slide_images.append(slide_image)
                    final_avatar_videos.append(avatar_video)
                    final_audio_files.append(audio_file)

                if not final_slide_images:
                    raise ValueError("No valid slide/image combinations found")

                logger.info(f"Processing {len(final_slide_images)} valid slides...")

                # Process slides one at a time to avoid memory issues
                video_clips = []

                logger.info(
                    f"Processing {len(final_slide_images)} slides individually..."
                )

                for i, (slide_image, avatar_video, audio_file) in enumerate(
                    zip(
                        final_slide_images,
                        final_avatar_videos,
                        final_audio_files,
                        strict=False,
                    )
                ):
                    logger.info(
                        f"Processing slide {i + 1}/{len(final_slide_images)}..."
                    )

                    try:
                        # Load audio to get duration
                        audio_clip = AudioFileClip(str(audio_file))
                        duration = audio_clip.duration

                        # Load slide image
                        slide_clip = ImageClip(str(slide_image)).with_duration(duration)
                        safe_width, safe_height = self._get_memory_safe_size(slide_clip)
                        slide_clip = slide_clip.with_effects(
                            [Resize(width=safe_width, height=safe_height)]
                        )
                        slide_clip = slide_clip.with_position("center")

                        # Load avatar video
                        avatar_clip = VideoFileClip(str(avatar_video))
                        avatar_height = min(400, int(avatar_clip.h * 0.4))
                        avatar_clip = avatar_clip.with_effects(
                            [Resize(height=avatar_height)]
                        )
                        avatar_clip = avatar_clip.with_position(("right", "top"))
                        avatar_clip = avatar_clip.with_duration(duration)

                        # Create composite
                        combined_clip = CompositeVideoClip([slide_clip, avatar_clip])
                        combined_clip = combined_clip.with_audio(audio_clip)

                        video_clips.append(combined_clip)

                        # Force garbage collection after each slide
                        gc.collect()

                    except Exception as e:
                        logger.error(f"Error processing slide {i + 1}: {e}")
                        # Clean up any open clips for this slide
                        try:
                            if "audio_clip" in locals():
                                audio_clip.close()
                            if "slide_clip" in locals():
                                slide_clip.close()
                            if "avatar_clip" in locals():
                                avatar_clip.close()
                        except Exception:
                            pass
                        continue

                if not video_clips:
                    raise ValueError("No valid clips were created")

                logger.info("Concatenating all clips...")
                final_clip = concatenate_videoclips(video_clips)
                watermark = self._create_watermark(final_clip)
                if watermark:
                    logger.info("✓ Watermark received from _create_watermark")
                    logger.info("Adding watermark to final video...")

                    try:
                        # Use memory-efficient composition
                        final_clip = CompositeVideoClip(
                            [final_clip, watermark], use_bgclip=True
                        )
                        logger.info(
                            "✓ Watermark successfully composited with final video"
                        )
                    except Exception as e:
                        logger.error(f"Failed to composite watermark: {e}")
                        logger.exception("Watermark composition traceback:")
                else:
                    logger.warning(
                        "✗ No watermark created or watermark creation failed"
                    )

                logger.info("=== WATERMARK INTEGRATION COMPLETE ===")

                logger.info("Writing final video...")

                # Write with optimized settings
                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,  # Reduce threads to save memory
                    preset="medium",  # Balance quality vs speed
                    bitrate="2000k",  # Limit bitrate for memory
                    audio_bitrate="128k",
                    temp_audiofile=str(output_path.parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,  # Disable moviepy logging
                )

                logger.info(f"Video composition completed: {output_path}")

            except Exception as e:
                logger.error(f"Video composition error: {e}")
                raise
            finally:
                # Clean up all clips
                try:
                    for clip in video_clips:
                        clip.close()
                    if "final_clip" in locals():
                        final_clip.close()
                except Exception:
                    pass
                gc.collect()

        # Run with timeout to prevent hanging
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _compose_video_sync),
                    timeout=1800,  # 30 minutes timeout
                )
            except TimeoutError:
                raise Exception(
                    "Video composition timed out after 30 minutes"
                ) from None

    async def create_images_only_video(
        self, slide_images: list[Path], output_path: Path
    ) -> None:
        """
        Create a video with only images and no audio
        """
        await self._create_video(slide_images, [], output_path)

    async def _create_video(
        self, slide_images: list[Path], audio_files: list[Path], output_path: Path
    ) -> None:
        """
        Common method for creating basic videos with or without audio
        """

        def _create_basic_video_sync() -> None:
            try:
                video_clips = []

                if not slide_images:
                    raise ValueError("No slide images provided")

                has_audio = bool(audio_files and len(audio_files) > 0)
                logger.info(
                    f"Creating basic video with {len(slide_images)} slides, audio={has_audio}"
                )

                if has_audio:
                    # Process with audio
                    for slide_image, audio_file in zip(
                        slide_images, audio_files, strict=False
                    ):
                        # Validate audio file before processing
                        is_valid, error_msg = self._validate_audio_file(audio_file)
                        if not is_valid:
                            logger.warning(f"Skipping audio file: {error_msg}")
                            continue

                        try:
                            audio_clip = AudioFileClip(str(audio_file))
                            duration = audio_clip.duration
                            if duration <= 0:
                                logger.warning(
                                    f"Skipping audio file with zero duration: {audio_file}"
                                )
                                audio_clip.close()
                                continue

                            slide_clip = ImageClip(str(slide_image)).with_duration(
                                duration
                            )
                            slide_clip = slide_clip.with_audio(audio_clip)
                            video_clips.append(slide_clip)
                        except Exception as e:
                            logger.error(f"Error loading audio file {audio_file}: {e}")
                            continue
                else:
                    # Process without audio
                    for slide_image in slide_images:
                        # Default duration of 5 seconds per slide if no audio
                        slide_clip = ImageClip(str(slide_image)).with_duration(5.0)
                        video_clips.append(slide_clip)

                if not video_clips:
                    raise ValueError("No valid video clips were created")

                final_clip = concatenate_videoclips(video_clips)

                watermark = self._create_watermark(final_clip)
                if watermark:
                    final_clip = CompositeVideoClip([final_clip, watermark])

                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac" if has_audio else None,
                    threads=2,
                    preset="medium",
                    bitrate="2000k",
                    audio_bitrate="128k",
                    temp_audiofile=str(output_path.parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,
                )

            except Exception as e:
                logger.error(f"Basic video composition error: {e}")
                raise
            finally:
                # Aggressive cleanup
                try:
                    for clip in video_clips:
                        clip.close()
                    if "final_clip" in locals():
                        final_clip.close()
                    if "watermark" in locals() and watermark:
                        watermark.close()
                except Exception:
                    pass
                gc.collect()

        # Run with timeout to prevent hanging
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _create_basic_video_sync),
                    timeout=1800,  # 30 minutes timeout
                )
            except TimeoutError:
                video_type = "simple" if audio_files else "images-only"
                raise Exception(
                    f"{video_type} video composition timed out after 30 minutes"
                ) from None

    async def create_slide_video(
        self, image_path: Path, audio_path: Path, output_path: Path
    ) -> None:
        """
        Create a single slide video with image and audio
        """

        def _create_slide_video_sync() -> None:
            try:
                # Load assets
                image_clip = ImageClip(str(image_path))
                audio_clip = AudioFileClip(str(audio_path))

                # Set image duration to match audio
                image_clip = image_clip.with_duration(audio_clip.duration)

                # Combine image and audio
                video_clip = image_clip.with_audio(audio_clip)

                watermark = self._create_watermark(video_clip)
                if watermark:
                    logger.info("Adding watermark to single slide video...")
                    video_clip = CompositeVideoClip([video_clip, watermark])
                    logger.info("✓ Watermark added to single slide video")
                else:
                    logger.warning("✗ No watermark for single slide video")

                # Write video with memory-optimized settings
                video_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,  # Reduced threads to prevent hanging
                    preset="medium",  # Balance quality vs speed
                    bitrate="2000k",  # Limit bitrate for memory
                    audio_bitrate="128k",
                    temp_audiofile=str(output_path.parent / "temp_audio.m4a"),
                    remove_temp=True,
                    logger=None,  # Disable moviepy logging
                )

            except Exception as e:
                logger.error(f"Slide video creation error: {e}")
                raise
            finally:
                # Aggressive cleanup
                try:
                    image_clip.close()
                    audio_clip.close()
                    video_clip.close()
                    if "watermark" in locals() and watermark:
                        watermark.close()
                except Exception:
                    pass
                gc.collect()

        # Run with timeout to prevent hanging
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, _create_slide_video_sync),
                    timeout=1800,  # 30 minutes timeout
                )
            except TimeoutError:
                raise Exception(
                    "Single slide video composition timed out after 30 minutes"
                ) from None
