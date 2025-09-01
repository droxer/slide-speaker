import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List
from moviepy import VideoFileClip, ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.fx.Resize import Resize

class VideoComposer:
    async def compose_video(self, slide_images: List[Path], avatar_videos: List[Path], 
                          audio_files: List[Path], output_path: Path):
        """
        Compose final video with slide images as background and AI avatar presenting
        """
        def _compose_video_sync():
            try:
                # Create video clips for each slide
                video_clips = []
                
                for i, (slide_image, avatar_video, audio_file) in enumerate(zip(slide_images, avatar_videos, audio_files)):
                    # Load assets
                    slide_clip = ImageClip(str(slide_image)).with_duration(AudioFileClip(str(audio_file)).duration)
                    avatar_clip = VideoFileClip(str(avatar_video))
                    audio_clip = AudioFileClip(str(audio_file))
                    
                    # Resize avatar to appropriate size for presentation (larger than PIP)
                    avatar_clip = avatar_clip.with_effects([Resize(height=400)])
                    
                    # Position avatar on the right side with some margin
                    avatar_clip = avatar_clip.with_position(('right', 'top'))
                    
                    # Ensure slide image fills the background
                    slide_clip = slide_clip.with_effects([Resize(width=1920, height=1080)])
                    
                    # Position slide image
                    slide_clip = slide_clip.with_position('center')
                    
                    # Combine slide (background) and avatar (presenter)
                    combined_clip = CompositeVideoClip([
                        slide_clip,
                        avatar_clip
                    ]).with_audio(audio_clip)
                    
                    video_clips.append(combined_clip)
                
                # Concatenate all clips
                final_clip = concatenate_videoclips(video_clips)
                
                # Write final video
                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    threads=4
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
        
    async def create_simple_video(self, slide_images: List[Path], audio_files: List[Path], output_path: Path):
        """
        Fallback method without avatar videos
        """
        def _create_simple_video_sync():
            try:
                video_clips = []
                
                for slide_image, audio_file in zip(slide_images, audio_files):
                    slide_clip = ImageClip(str(slide_image)).with_duration(AudioFileClip(str(audio_file)).duration)
                    slide_clip = slide_clip.with_audio(AudioFileClip(str(audio_file)))
                    video_clips.append(slide_clip)
                
                final_clip = concatenate_videoclips(video_clips)
                
                final_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    threads=4
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
    
    async def create_slide_video(self, image_path: Path, audio_path: Path, output_path: Path):
        """
        Create a single slide video with image and audio
        """
        def _create_slide_video_sync():
            try:
                # Load assets
                image_clip = ImageClip(str(image_path))
                audio_clip = AudioFileClip(str(audio_path))
                
                # Set image duration to match audio
                image_clip = image_clip.with_duration(audio_clip.duration)
                
                # Combine image and audio
                video_clip = image_clip.with_audio(audio_clip)
                
                # Write video
                video_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    threads=4
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