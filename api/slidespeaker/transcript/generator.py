"""
Transcript generation module for SlideSpeaker.

Generates AI-powered presentation transcripts per slide using OpenAI. Combines
extracted slide content and visual analysis prompts to produce natural, engaging
transcripts suitable for AI avatar presentation.
"""

from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

from .utils import sanitize_transcript

# Language-specific prompts for generating presentation transcripts
TRANSCRIPT_PROMPTS = {
    "english": (
        "Create a detailed, deeply-understood presentation transcript in English based on the content below. "
        "Demonstrate true comprehension by:\n"
        "- Explaining concepts in plain language, then layering nuance\n"
        "- Defining terms and acronyms the first time they appear\n"
        "- Making relationships and cause–effect explicit\n"
        "- Using short, concrete examples or analogies when helpful\n"
        "- Anticipating likely audience questions or confusions and addressing them\n"
        "- Paraphrasing slide text (do not read bullets verbatim)\n"
        "- Keeping a clear narrative flow and signposting transitions\n\n"
        "Target 80–140 spoken words, optimized for clarity and retention."
    ),
}

SYSTEM_ROLES = {
    "english": (
        "You are a professional presentation narrator and explainer. "
        "Your goal is to help listeners truly understand. "
        "Write natural, spoken transcripts that: (1) prioritize comprehension "
        "over brevity, (2) preserve technical accuracy, (3) keep pacing and "
        "structure suitable for audio narration, and (4) avoid greetings/"
        "closings except at appropriate slides."
    ),
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
    """Generator for AI-powered presentation transcripts (OpenAI only)"""

    def __init__(self) -> None:
        """Initialize OpenAI client from configuration."""
        # Force OpenAI usage; Qwen support removed for transcript generation
        self.provider = "openai"
        self.model: str = config.openai_script_model
        if not config.openai_api_key:
            logger.error(
                "OPENAI_API_KEY not set; OpenAI transcript generation will fallback"
            )

    async def generate_transcript(
        self,
        slide_content: dict[str, Any] | str,
        image_analysis: Any | None = None,
        language: str = "english",
    ) -> str:
        """Generate a presentation transcript for one slide using the configured provider."""
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

            # Build content-focused analysis (avoid visual UI/descriptive elements)
            def _content_only_analysis(ia: Any) -> str:
                try:
                    if isinstance(ia, dict):
                        parts: list[str] = []
                        pc = ia.get("presentation_context", {}) or {}
                        cnt = ia.get("content", {}) or {}
                        # Core ideas and insights
                        mt = pc.get("main_topic")
                        if mt:
                            parts.append(f"Main topic: {mt}")
                        kis = pc.get("key_insights")
                        if kis:
                            parts.append(f"Key insights: {kis}")
                        # Speaking points (as conceptual cues)
                        sp = cnt.get("speaking_points")
                        if sp:
                            parts.append(f"Speaking points: {sp}")
                        # Numerical data (evidence)
                        nums = pc.get("numerical_data")
                        if nums:
                            parts.append(f"Evidence: {nums}")
                        # Transition phrases (narrative cues)
                        tp = cnt.get("transition_phrases")
                        if tp:
                            parts.append(f"Transitions: {tp}")
                        # Text content fallback
                        txt = cnt.get("text_content")
                        if txt:
                            parts.append(f"Extracted text: {txt}")
                        return "\n".join(parts)
                except Exception:
                    pass
                return ""

            analysis_text = _content_only_analysis(image_analysis)
            guidelines = (
                "CRITICAL: Do not mention slide layout, colors, icons, animations, or phrases like 'on the slide'. "  # noqa: E501
                "Present the ideas directly, focusing on meaning and explanation."
            )
            user_content = (
                f"Slide content (text extraction):\n{content_text}\n\n"
                f"Content analysis (no visual UI mentions):\n{analysis_text}\n\n"
                f"{user_prompt}\n\n{guidelines}"
            )

            content = chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            transcript = sanitize_transcript(content.strip())
            return transcript
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")
            # Fallback to a simple default transcript
            defaults = DEFAULT_TRANSCRIPTS.get(language, DEFAULT_TRANSCRIPTS["english"])
            return defaults[0]
