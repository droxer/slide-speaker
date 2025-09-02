import os
import base64
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Prompt for slide image analysis
SLIDE_ANALYSIS_PROMPT = """
Analyze this presentation slide image and provide a comprehensive understanding of its content.

Please provide:
1. All text content visible on the slide (extract exactly as shown)
2. Visual elements and their arrangement (charts, graphs, images, diagrams)
3. The main topic/theme of the slide
4. Key points being communicated
5. Context and purpose of the content
6. Any numerical data or statistics present
7. The overall structure and layout

Format your response as a structured analysis that can be used to generate a presentation script.
"""

# System prompt for slide analysis
SLIDE_ANALYSIS_SYSTEM_PROMPT = "You are an expert presentation analyst. Analyze slide images and extract comprehensive content understanding for script generation."

class VisionService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for OpenAI API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def analyze_slide_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Analyze slide image content using multi-model LLM (GPT-4 Vision)
        Returns structured analysis including text content, visual elements, and context
        """
        try:
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": SLIDE_ANALYSIS_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": SLIDE_ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Parse the analysis into structured format
            analysis = self._parse_analysis(analysis_text)
            
            logger.info(f"Successfully analyzed slide image: {image_path.name}")
            return analysis
            
        except Exception as e:
            logger.error(f"Vision analysis error for {image_path}: {e}")
            # Fallback: return basic analysis with file info
            return {
                "text_content": f"Slide image: {image_path.name}",
                "visual_elements": ["image"],
                "main_topic": "Presentation content",
                "key_points": ["Visual content to be presented"],
                "context": "Presentation slide",
                "numerical_data": [],
                "structure": "single_image"
            }
    
    def _parse_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the LLM analysis into structured format"""
        # This is a basic parser - you might want to enhance this based on your needs
        return {
            "raw_analysis": analysis_text,
            "text_content": self._extract_text_content(analysis_text),
            "visual_elements": self._extract_visual_elements(analysis_text),
            "main_topic": self._extract_main_topic(analysis_text),
            "key_points": self._extract_key_points(analysis_text),
            "context": "presentation_slide",
            "numerical_data": [],
            "structure": "analyzed_content"
        }
    
    def _extract_text_content(self, analysis: str) -> str:
        """Extract text content from analysis"""
        lines = analysis.split('\n')
        text_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['text:', 'content:', 'says:', 'states:', 'shows:']):
                text_lines.append(line)
        return '\n'.join(text_lines) if text_lines else analysis[:500]
    
    def _extract_visual_elements(self, analysis: str) -> List[str]:
        """Extract visual elements from analysis"""
        elements = []
        if 'chart' in analysis.lower():
            elements.append('chart')
        if 'graph' in analysis.lower():
            elements.append('graph')
        if 'image' in analysis.lower():
            elements.append('image')
        if 'diagram' in analysis.lower():
            elements.append('diagram')
        return elements if elements else ['visual_content']
    
    def _extract_main_topic(self, analysis: str) -> str:
        """Extract main topic from analysis"""
        lines = analysis.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['topic:', 'theme:', 'about:', 'discusses:']):
                return line.strip()
        return "Presentation Content"
    
    def _extract_key_points(self, analysis: str) -> List[str]:
        """Extract key points from analysis"""
        points = []
        lines = analysis.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['point:', 'key:', 'important:', 'bullet:']):
                points.append(line.strip())
        return points if points else ["Key information to be presented"]
    
    async def batch_analyze_slides(self, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """Analyze multiple slide images in batch"""
        analyses = []
        
        for image_path in image_paths:
            if image_path.exists():
                analysis = await self.analyze_slide_image(image_path)
                analyses.append(analysis)
            else:
                logger.warning(f"Image file not found: {image_path}")
                analyses.append({
                    "text_content": f"Missing slide image: {image_path.name}",
                    "visual_elements": ["placeholder"],
                    "main_topic": "Unknown content",
                    "key_points": ["Content unavailable"],
                    "context": "missing_slide",
                    "numerical_data": [],
                    "structure": "unknown"
                })
        
        return analyses