import asyncio
import gc
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


class VideoComposer:
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

    def _create_watermark(self, duration: float) -> TextClip | None:
        """Create a semi-transparent SlideSpeaker AI watermark"""
        try:
            watermark = TextClip(
                "SlideSpeaker AI",
                fontsize=20,
                color="white",
                font="Arial-Bold",
                bg_color="rgba(0,0,0,0.4)",  # Semi-transparent black background
                size=(200, 40),
                method="caption",
            )

            # Set position (bottom right corner with some margin)
            watermark = watermark.with_position(("right", "bottom")).with_duration(
                duration
            )

            # Add slight transparency to the watermark itself
            watermark = watermark.with_effects([lambda clip: clip.with_opacity(0.7)])

            return watermark
        except Exception as e:
            print(f"Watermark creation error: {e}")
            # Return None if watermark creation fails - don't break the video
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
        Memory-efficient version with progress tracking and error handling
        """

        def _compose_video_sync() -> None:
            try:
                print(
                    f"Starting video composition with {len(slide_images)} slides and avatars"
                )

                # Validate all avatar videos before processing
                valid_avatar_videos = []
                valid_audio_files = []
                valid_slide_images = []

                for i, (slide_image, avatar_video, audio_file) in enumerate(
                    zip(slide_images, avatar_videos, audio_files, strict=False)
                ):
                    print(f"Validating slide {i + 1} components...")

                    # Validate files
                    is_valid, error_msg = self._validate_video_file(avatar_video)
                    if not is_valid:
                        print(f"Skipping avatar video {i + 1}: {error_msg}")
                        continue

                    if not slide_image.exists():
                        print(f"Skipping slide image {i + 1}: {slide_image} not found")
                        continue

                    if not audio_file.exists():
                        print(f"Skipping audio file {i + 1}: {audio_file} not found")
                        continue

                    valid_slide_images.append(slide_image)
                    valid_avatar_videos.append(avatar_video)
                    valid_audio_files.append(audio_file)

                if not valid_slide_images:
                    raise ValueError("No valid slide/image combinations found")

                print(f"Processing {len(valid_slide_images)} valid slides...")

                # Process slides one at a time to avoid memory issues
                video_clips = []

                print(f"Processing {len(valid_slide_images)} slides individually...")

                for i, (slide_image, avatar_video, audio_file) in enumerate(
                    zip(
                        valid_slide_images,
                        valid_avatar_videos,
                        valid_audio_files,
                        strict=False,
                    )
                ):
                    print(f"Processing slide {i + 1}/{len(valid_slide_images)}...")

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
                        print(f"Error processing slide {i + 1}: {e}")
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

                print("Concatenating all clips...")
                final_clip = concatenate_videoclips(video_clips)

                # Add watermark
                watermark = self._create_watermark(final_clip.duration)
                if watermark:
                    final_clip = CompositeVideoClip([final_clip, watermark])

                print("Writing final video...")

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

                print(f"Video composition completed: {output_path}")

            except Exception as e:
                print(f"Video composition error: {e}")
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

    async def create_simple_video(
        self, slide_images: list[Path], audio_files: list[Path], output_path: Path
    ) -> None:
        """
        Fallback method without avatar videos
        """

        def _create_simple_video_sync() -> None:
            try:
                video_clips = []

                # Handle case where audio_files might be empty
                if audio_files:
                    for slide_image, audio_file in zip(
                        slide_images, audio_files, strict=False
                    ):
                        slide_clip = ImageClip(str(slide_image)).with_duration(
                            AudioFileClip(str(audio_file)).duration
                        )
                        slide_clip = slide_clip.with_audio(
                            AudioFileClip(str(audio_file))
                        )
                        video_clips.append(slide_clip)
                else:
                    # Create video clips without audio
                    for slide_image in slide_images:
                        # Default duration of 5 seconds per slide if no audio
                        slide_clip = ImageClip(str(slide_image)).with_duration(5.0)
                        video_clips.append(slide_clip)

                final_clip = concatenate_videoclips(video_clips)

                # Add SlideSpeaker AI watermark
                watermark = self._create_watermark(final_clip.duration)
                if watermark:
                    final_clip = CompositeVideoClip([final_clip, watermark])

                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac"
                    if audio_files
                    else None,  # No audio codec if no audio files
                    threads=4,
                )

                for clip in video_clips:
                    clip.close()
                final_clip.close()

            except Exception as e:
                print(f"Simple video composition error: {e}")
                raise

        # Run the CPU-intensive video composition in a separate thread
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, _create_simple_video_sync)

    async def create_images_only_video(
        self, slide_images: list[Path], output_path: Path
    ) -> None:
        """
        Create a video with only images and no audio
        """

        def _create_images_only_video_sync() -> None:
            try:
                video_clips = []

                # Create video clips without audio (5 seconds per slide)
                for slide_image in slide_images:
                    slide_clip = ImageClip(str(slide_image)).with_duration(5.0)
                    video_clips.append(slide_clip)

                final_clip = concatenate_videoclips(video_clips)

                # Add SlideSpeaker AI watermark
                watermark = self._create_watermark(final_clip.duration)
                if watermark:
                    final_clip = CompositeVideoClip([final_clip, watermark])

                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec=None,  # No audio
                    threads=4,
                )

                for clip in video_clips:
                    clip.close()
                final_clip.close()

            except Exception as e:
                print(f"Images-only video composition error: {e}")
                raise

        # Run the CPU-intensive video composition in a separate thread
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, _create_images_only_video_sync)

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

                # Add SlideSpeaker AI watermark
                watermark = self._create_watermark(video_clip.duration)
                if watermark:
                    video_clip = CompositeVideoClip([video_clip, watermark])

                # Write video
                video_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=4,
                )

                # Close clips
                image_clip.close()
                audio_clip.close()
                video_clip.close()

            except Exception as e:
                print(f"Slide video creation error: {e}")
                raise

        # Run the CPU-intensive video composition in a separate thread
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, _create_slide_video_sync)
