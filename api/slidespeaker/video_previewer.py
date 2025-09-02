import json
from pathlib import Path
from typing import List, Dict
import base64
from loguru import logger

from .locale_utils import locale_utils

class VideoPreviewer:
    """Generate preview data for videos with subtitles"""
    
    def generate_preview_data(self, file_id: str, output_dir: Path = Path("output"), 
                            subtitle_language: str = "english") -> dict:
        """
        Generate preview data including video info and subtitle content
        
        Args:
            file_id: The file ID of the generated video
            output_dir: Directory where files are stored
            subtitle_language: Language of the subtitles
            
        Returns:
            Dictionary with preview information
        """
        try:
            # Check if video exists
            video_path = output_dir / f"{file_id}_final.mp4"
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Get video info
            video_info = {
                "file_id": file_id,
                "video_url": f"/api/video/{file_id}",
                "file_size": video_path.stat().st_size,
                "file_name": f"presentation_{file_id}.mp4"
            }
            
            # Check for subtitles
            subtitle_info = {}
            srt_path = output_dir / f"{file_id}_final.srt"
            vtt_path = output_dir / f"{file_id}_final.vtt"
            
            logger.info(f"Checking for subtitle files: SRT={srt_path.exists()}, VTT={vtt_path.exists()}")
            logger.info(f"SRT path: {srt_path}")
            logger.info(f"VTT path: {vtt_path}")
            
            if srt_path.exists():
                try:
                    with open(srt_path, 'r', encoding='utf-8') as f:
                        subtitle_info["srt_content"] = f.read()
                    subtitle_info["srt_url"] = f"/api/subtitles/{file_id}/srt"
                    logger.info(f"SRT file found and read successfully")
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")
                
            if vtt_path.exists():
                try:
                    with open(vtt_path, 'r', encoding='utf-8') as f:
                        subtitle_info["vtt_content"] = f.read()
                    subtitle_info["vtt_url"] = f"/api/subtitles/{file_id}/vtt"
                    logger.info(f"VTT file found and read successfully")
                except Exception as e:
                    logger.error(f"Error reading VTT file: {e}")
            
            # Get subtitle tracks for HTML5 video
            subtitle_tracks = self.get_subtitle_tracks(file_id, output_dir, subtitle_language)
            
            # Generate preview data
            preview_data = {
                "video": video_info,
                "subtitles": subtitle_info,
                "subtitle_tracks": subtitle_tracks,
                "preview_available": True,
                "timestamp": Path.cwd().stat().st_mtime  # Use current dir mtime as timestamp
            }
            
            return preview_data
            
        except Exception as e:
            print(f"Preview generation error: {e}")
            return {
                "preview_available": False,
                "error": str(e)
            }
    
    def get_subtitle_tracks(self, file_id: str, output_dir: Path = Path("output"), 
                          subtitle_language: str = "english") -> List[Dict]:
        """
        Get available subtitle tracks for a video
        
        Args:
            file_id: The file ID of the generated video
            output_dir: Directory where files are stored
            subtitle_language: Language of the subtitles
            
        Returns:
            List of subtitle track information
        """
        tracks = []
        lang_code = locale_utils.get_locale_code(subtitle_language)
        
        logger.info(f"Getting subtitle tracks for file_id={file_id}, language={subtitle_language}, lang_code={lang_code}")
        
        # Check for SRT subtitle track
        srt_path = output_dir / f"{file_id}_final.srt"
        logger.info(f"Checking SRT path: {srt_path}, exists: {srt_path.exists()}")
        if srt_path.exists():
            tracks.append({
                "kind": "subtitles",
                "label": f"Subtitles ({subtitle_language.title()})",
                "src": f"/api/subtitles/{file_id}/srt",
                "srclang": lang_code,
                "default": False
            })
            logger.info(f"Added SRT track: srclang={lang_code}")
        
        # Check for VTT subtitle track
        vtt_path = output_dir / f"{file_id}_final.vtt"
        logger.info(f"Checking VTT path: {vtt_path}, exists: {vtt_path.exists()}")
        if vtt_path.exists():
            tracks.append({
                "kind": "subtitles",
                "label": f"Subtitles ({subtitle_language.title()})",
                "src": f"/api/subtitles/{file_id}/vtt",
                "srclang": lang_code,
                "default": True
            })
            logger.info(f"Added VTT track: srclang={lang_code}")
            
        logger.info(f"Returning {len(tracks)} subtitle tracks")
        return tracks