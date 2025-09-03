import asyncio
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
        """

        def _compose_video_sync() -> None:
            try:
                # Create video clips for each slide
                video_clips = []

                for _i, (slide_image, avatar_video, audio_file) in enumerate(
                    zip(slide_images, avatar_videos, audio_files, strict=False)
                ):
                    # Load assets
                    slide_clip = ImageClip(str(slide_image)).with_duration(
                        AudioFileClip(str(audio_file)).duration
                    )
                    avatar_clip = VideoFileClip(str(avatar_video))
                    audio_clip = AudioFileClip(str(audio_file))

                    # Resize avatar to appropriate size for presentation (larger than PIP)
                    avatar_clip = avatar_clip.with_effects([Resize(height=400)])

                    # Position avatar on the right side with some margin
                    avatar_clip = avatar_clip.with_position(("right", "top"))

                    # Ensure slide image fills the background
                    slide_clip = slide_clip.with_effects(
                        [Resize(width=1920, height=1080)]
                    )

                    # Position slide image
                    slide_clip = slide_clip.with_position("center")

                    # Combine slide (background) and avatar (presenter)
                    combined_clip = CompositeVideoClip(
                        [slide_clip, avatar_clip]
                    ).with_audio(audio_clip)

                    video_clips.append(combined_clip)

                # Concatenate all clips
                final_clip = concatenate_videoclips(video_clips)

                # Add SlideSpeaker AI watermark
                watermark = self._create_watermark(final_clip.duration)
                if watermark:
                    final_clip = CompositeVideoClip([final_clip, watermark])

                # Write final video
                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    threads=4,
                )

                # Close all clips to free resources
                for clip in video_clips:
                    clip.close()
                final_clip.close()

            except Exception as e:
                print(f"Video composition error: {e}")
                raise

        # Run the CPU-intensive video composition in a separate thread
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, _compose_video_sync)

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
