"""
Transcript generation module for SlideSpeaker.

This module generates AI-powered presentation transcripts for each slide using OpenAI's GPT models.
It combines extracted slide content and visual analysis prompts to produce
engaging, natural-sounding transcripts suitable for AI avatar presentation.
"""

import os
from typing import Any

from loguru import logger
from openai import OpenAI

# Language-specific prompts for generating presentation transcripts
TRANSCRIPT_PROMPTS = {
    "english": "Create a detailed, comprehensive, and educational presentation transcript in English based on the following content analysis. Provide thorough explanations of topics and key points with relevant examples. Focus on depth of explanation rather than brevity to ensure complete understanding.",  # noqa: E501
}

SYSTEM_ROLES = {
    "english": "You are a professional presentation transcript writer and educator. "
    "Create detailed, comprehensive, and educational transcripts for AI avatars based on content analysis. "
    "Ensure clarity, flow, and appropriate pacing for spoken narration.",
}

# Fallback transcripts in different languages
DEFAULT_TRANSCRIPTS: dict[str, list[str]] = {
    "english": [
        "Welcome to our presentation. We'll explore the key ideas step by step.",
        "This section dives deeper into the core concepts with clear examples.",
        "Finally, we summarize the main points and discuss next steps.",
    ]
}


class TranscriptGenerator:
    """Generator for AI-powered presentation transcripts using OpenAI GPT models"""

    def __init__(self) -> None:
        """Initialize the transcript generator with OpenAI client"""
        # Get API key from environment (this is a special case that's not in config)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=api_key)
        self.model: str = os.getenv("SCRIPT_GENERATOR_MODEL", "gpt-4o-mini")

    async def generate_transcript(
        self,
        slide_content: dict[str, Any] | str,
        image_analysis: Any | None = None,
        language: str = "english",
    ) -> str:
        """Generate a presentation transcript for a slide using AI.

        This method creates a natural, engaging transcript suitable for AI avatar presentation
        based on analyzed slide content and any available image analysis.
        """
        try:
            system_prompt = SYSTEM_ROLES.get(language, SYSTEM_ROLES["english"])
            user_prompt = TRANSCRIPT_PROMPTS.get(
                language, TRANSCRIPT_PROMPTS["english"]
            )

            # Build context from slide content and optional image analysis
            content_text = (
                slide_content.get("text", "")
                if isinstance(slide_content, dict)
                else str(slide_content)
            )
            analysis_text = image_analysis or ""
            user_content = (
                f"Slide content:\n{content_text}\n\n"
                f"Image analysis (if any):\n{analysis_text}\n\n"
                f"{user_prompt}"
            )

            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            transcript = resp.choices[0].message.content or ""
            return transcript.strip()
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")
            # Fallback to a simple default transcript
            defaults = DEFAULT_TRANSCRIPTS.get(language, DEFAULT_TRANSCRIPTS["english"])
            return defaults[0]
