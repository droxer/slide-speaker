"""
Vision Service for Slide Analysis

This module provides image analysis capabilities using OpenAI's GPT-4 Vision model
to extract content from presentation slides. It analyzes both text and visual elements
to provide context for script generation.
"""

import base64
import os
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI

# Prompt for slide image analysis optimized for script generation
SLIDE_ANALYSIS_PROMPT = """
Analyze this presentation slide image specifically for creating an engaging presentation script.

Focus on these presentation-specific aspects:
1. **Slide Type**: Identify if this is a title slide, content slide, transition slide, or conclusion
2. **Speaking Points**: Extract key talking points in the order they should be presented
3. **Visual Emphasis**: Identify what's visually emphasized that should be verbally highlighted
4. **Slide Flow**: How does this slide connect to the overall presentation narrative?
5. **Audience Engagement**: What elements would benefit from explanation or elaboration?
6. **Context Clues**: What background context would help explain this slide's content?
7. **Transition Cues**: How should the speaker transition to/from this slide?

Text Content (extract exactly as shown):
- All visible text including titles, bullet points, labels, and captions
- Any code snippets or technical terms that need pronunciation guidance
- Numbers, statistics, and data labels

Visual Analysis:
- Charts/graphs: Describe the data story and key insights
- Diagrams: Explain the process or relationships shown
- Images: Describe what's shown and why it's relevant
- Layout: How visual hierarchy guides the presentation flow

Provide your analysis in a structured format that directly supports script generation,
focusing on what a presenter should say about each element.
"""

# System prompt for slide analysis
SLIDE_ANALYSIS_SYSTEM_PROMPT = (
    "You are an expert presentation coach and script writer. Analyze slide images to extract "
    "content that directly supports creating engaging presentation scripts. Focus on speaking points, "
    "narrative flow, and audience engagement strategies."
)


class VisionService:
    """Vision service for analyzing slide images using OpenAI GPT-4 Vision"""

    def __init__(self) -> None:
        """Initialize the vision service with OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for OpenAI API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def analyze_slide_image(
        self, image_path: Path, slide_text: str = ""
    ) -> dict[str, Any]:
        """
        Analyze slide image content using multi-model LLM (GPT-4 Vision)
        Returns structured analysis including text content, visual elements, and context

        Args:
            image_path: Path to the slide image
            slide_text: Optional extracted text content from the slide for enhanced context

        Returns:
            Structured analysis of the slide content optimized for script generation
        """
        try:
            # Encode the image
            base64_image = self._encode_image(image_path)

            # Build enhanced prompt with slide text context if provided
            enhanced_prompt = SLIDE_ANALYSIS_PROMPT
            if slide_text.strip():
                enhanced_prompt = f"""{SLIDE_ANALYSIS_PROMPT}

Additional Context from Slide Text Extraction:
{slide_text}

Use this extracted text to enhance your analysis and ensure consistency between visual and textual content."""

            model_name = os.getenv("VISION_MODEL", "gpt-4o-mini")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SLIDE_ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": enhanced_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=2000,
            )

            analysis_text = response.choices[0].message.content
            if analysis_text is None:
                analysis_text = "No analysis content available"

            analysis_text = analysis_text.strip()

            # Parse the analysis into structured format
            analysis = self._parse_analysis(analysis_text)

            # Add slide text context to the analysis if provided
            if slide_text.strip():
                analysis["content"]["extracted_text"] = slide_text
                # Ensure consistency between vision and text extraction
                if (
                    not analysis["content"]["text_content"]
                    or analysis["content"]["text_content"]
                    == "No text content available"
                ):
                    analysis["content"]["text_content"] = slide_text

            logger.info(
                f"Successfully analyzed slide image: {image_path.name} with text context: {bool(slide_text)}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Vision analysis error for {image_path}: {e}")
            import traceback

            logger.error(f"Vision analysis traceback: {traceback.format_exc()}")
            # Fallback: return basic analysis with file info
            return {
                "text_content": f"Slide image: {image_path.name}",
                "visual_elements": ["image"],
                "main_topic": "Presentation content",
                "key_points": ["Visual content to be presented"],
                "context": "Presentation slide",
                "numerical_data": [],
                "structure": "single_image",
            }

    def _parse_analysis(self, analysis_text: str) -> dict[str, Any]:
        """Parse the LLM analysis into structured format optimized for script generation"""
        return {
            "raw_analysis": analysis_text,
            "slide_metadata": {
                "type": self._extract_slide_type(analysis_text),
                "title": self._extract_slide_title(analysis_text),
                "estimated_duration_seconds": self._estimate_duration(analysis_text),
            },
            "content": {
                "text_content": self._extract_text_content(analysis_text),
                "speaking_points": self._extract_speaking_points(analysis_text),
                "visual_highlights": self._extract_visual_highlights(analysis_text),
                "transition_phrases": self._extract_transition_phrases(analysis_text),
            },
            "presentation_context": {
                "main_topic": self._extract_main_topic(analysis_text),
                "key_insights": self._extract_key_insights(analysis_text),
                "audience_focus": self._extract_audience_focus(analysis_text),
                "visual_elements": self._extract_visual_elements(analysis_text),
                "numerical_data": self._extract_numerical_data(analysis_text),
            },
            "script_guidance": {
                "opening_line": self._extract_opening_line(analysis_text),
                "emphasis_points": self._extract_emphasis_points(analysis_text),
                "explanation_needs": self._extract_explanation_needs(analysis_text),
                "closing_transition": self._extract_closing_transition(analysis_text),
            },
        }

    def _extract_text_content(self, analysis: str) -> str:
        """Extract text content from analysis"""
        lines = analysis.split("\n")
        text_lines = []
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["text:", "content:", "says:", "states:", "shows:"]
            ):
                text_lines.append(line)
        return "\n".join(text_lines) if text_lines else analysis[:500]

    def _extract_visual_elements(self, analysis: str) -> list[str]:
        """Extract visual elements from analysis"""
        elements = []
        if "chart" in analysis.lower():
            elements.append("chart")
        if "graph" in analysis.lower():
            elements.append("graph")
        if "image" in analysis.lower():
            elements.append("image")
        if "diagram" in analysis.lower():
            elements.append("diagram")
        return elements if elements else ["visual_content"]

    def _extract_main_topic(self, analysis: str) -> str:
        """Extract main topic from analysis"""
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["topic:", "theme:", "about:", "discusses:"]
            ):
                return line.strip()
        return "Presentation Content"

    def _extract_key_points(self, analysis: str) -> list[str]:
        """Extract key points from analysis"""
        points = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["point:", "key:", "important:", "bullet:"]
            ):
                points.append(line.strip())
        return points if points else ["Key information to be presented"]

    def _extract_slide_type(self, analysis: str) -> str:
        """Extract slide type from analysis"""
        analysis_lower = analysis.lower()
        if any(
            keyword in analysis_lower
            for keyword in ["title slide", "introduction", "welcome"]
        ):
            return "title"
        elif any(
            keyword in analysis_lower
            for keyword in ["conclusion", "summary", "thank you"]
        ):
            return "conclusion"
        elif any(
            keyword in analysis_lower for keyword in ["transition", "next", "moving on"]
        ):
            return "transition"
        else:
            return "content"

    def _extract_slide_title(self, analysis: str) -> str:
        """Extract slide title from analysis"""
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower() for keyword in ["title:", "topic:", "heading:"]
            ):
                return line.split(":", 1)[1].strip() if ":" in line else line.strip()
        return "Presentation Content"

    def _estimate_duration(self, analysis: str) -> int:
        """Estimate presentation duration based on content complexity"""
        word_count = len(analysis.split())
        # Rough estimate: 150 words per minute, converted to seconds
        return max(30, min(180, int((word_count / 150) * 60)))

    def _extract_speaking_points(self, analysis: str) -> list[str]:
        """Extract speaking points in presentation order"""
        points = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in [
                    "speaking point:",
                    "talk about:",
                    "explain:",
                    "discuss:",
                ]
            ):
                points.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return points if points else self._extract_key_points(analysis)

    def _extract_visual_highlights(self, analysis: str) -> list[str]:
        """Extract visual elements that should be verbally highlighted"""
        highlights = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["highlight:", "emphasis:", "focus on:", "notice:"]
            ):
                highlights.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return highlights if highlights else []

    def _extract_transition_phrases(self, analysis: str) -> list[str]:
        """Extract transition phrases for smooth presentation flow"""
        transitions = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["transition:", "next:", "moving on:", "now:"]
            ):
                transitions.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return transitions if transitions else ["Let's move to the next point"]

    def _extract_key_insights(self, analysis: str) -> list[str]:
        """Extract key insights for deeper explanation"""
        insights = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["insight:", "key insight:", "important:", "crucial:"]
            ):
                insights.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return insights if insights else []

    def _extract_audience_focus(self, analysis: str) -> str:
        """Extract audience focus guidance"""
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["audience:", "focus:", "attention:", "look at:"]
            ):
                return line.split(":", 1)[1].strip() if ":" in line else line.strip()
        return "General audience"

    def _extract_numerical_data(self, analysis: str) -> list[str]:
        """Extract numerical data and statistics"""
        import re

        numbers = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?(?:%|x|X|×)?\b", analysis)
        return list(set(numbers))  # Remove duplicates

    def _extract_opening_line(self, analysis: str) -> str:
        """Extract suggested opening line for the slide"""
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["opening:", "start with:", "begin:", "introduce:"]
            ):
                return line.split(":", 1)[1].strip() if ":" in line else line.strip()
        return "Let's look at this slide"

    def _extract_emphasis_points(self, analysis: str) -> list[str]:
        """Extract points that need emphasis during presentation"""
        emphasis = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["emphasize:", "stress:", "important:", "key:"]
            ):
                emphasis.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return emphasis if emphasis else []

    def _extract_explanation_needs(self, analysis: str) -> list[str]:
        """Extract content that needs additional explanation"""
        explanations = []
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["explain:", "clarify:", "describe:", "define:"]
            ):
                explanations.append(
                    line.split(":", 1)[1].strip() if ":" in line else line.strip()
                )
        return explanations if explanations else []

    def _extract_closing_transition(self, analysis: str) -> str:
        """Extract closing transition for moving to next slide"""
        lines = analysis.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in [
                    "closing:",
                    "transition out:",
                    "next slide:",
                    "conclude:",
                ]
            ):
                return line.split(":", 1)[1].strip() if ":" in line else line.strip()
        return "Let's continue to the next slide"

    async def batch_analyze_slides(
        self, image_paths: list[Path]
    ) -> list[dict[str, Any]]:
        """Analyze multiple slide images in batch"""
        analyses = []

        for image_path in image_paths:
            if image_path.exists():
                analysis = await self.analyze_slide_image(image_path)
                analyses.append(analysis)
            else:
                logger.warning(f"Image file not found: {image_path}")
                analyses.append(
                    {
                        "slide_metadata": {
                            "type": "missing",
                            "title": f"Missing: {image_path.name}",
                            "estimated_duration_seconds": 10,
                        },
                        "content": {
                            "text_content": f"Missing slide image: {image_path.name}",
                            "speaking_points": ["Content unavailable"],
                            "visual_highlights": [],
                            "transition_phrases": [
                                "Let's move to the next available slide"
                            ],
                            "extracted_text": "",
                        },
                        "presentation_context": {
                            "main_topic": "Unknown content",
                            "key_insights": [],
                            "audience_focus": "General audience",
                            "visual_elements": ["placeholder"],
                            "numerical_data": [],
                        },
                        "script_guidance": {
                            "opening_line": "Unfortunately, this slide is missing",
                            "emphasis_points": [],
                            "explanation_needs": ["Slide content unavailable"],
                            "closing_transition": "Let's continue to the next slide",
                        },
                    }
                )
        return analyses

    async def batch_analyze_slides_with_text(
        self, image_paths: list[Path], slide_texts: list[str]
    ) -> list[dict[str, Any]]:
        """Analyze multiple slide images with corresponding text content"""
        analyses = []

        # Ensure we have matching lengths
        min_length = min(len(image_paths), len(slide_texts))
        image_paths = image_paths[:min_length]
        slide_texts = slide_texts[:min_length]

        for image_path, slide_text in zip(image_paths, slide_texts, strict=False):
            if image_path.exists():
                analysis = await self.analyze_slide_image(image_path, slide_text)
                analyses.append(analysis)
            else:
                logger.warning(f"Image file not found: {image_path}")
                analyses.append(
                    {
                        "slide_metadata": {
                            "type": "missing",
                            "title": f"Missing: {image_path.name}",
                            "estimated_duration_seconds": 10,
                        },
                        "content": {
                            "text_content": f"Missing slide image: {image_path.name}",
                            "speaking_points": ["Content unavailable"],
                            "visual_highlights": [],
                            "transition_phrases": [
                                "Let's move to the next available slide"
                            ],
                            "extracted_text": slide_text,
                        },
                        "presentation_context": {
                            "main_topic": "Unknown content",
                            "key_insights": [],
                            "audience_focus": "General audience",
                            "visual_elements": ["placeholder"],
                            "numerical_data": [],
                        },
                        "script_guidance": {
                            "opening_line": "Unfortunately, this slide is missing",
                            "emphasis_points": [],
                            "explanation_needs": ["Slide content unavailable"],
                            "closing_transition": "Let's continue to the next slide",
                        },
                    }
                )

        return analyses
