"""Module for reviewing and refining presentation transcripts.

Supports whichever LLM provider is configured (OpenAI or Gemini) to refine the
generated presentation transcripts for consistency, flow, and quality. It
ensures appropriate formatting for AI avatar delivery and handles proper
positioning of opening/closing statements.
"""

from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

from .utils import sanitize_transcript

REVIEW_PROMPT = """Review and refine the following presentation transcripts to ensure
consistency in tone, style, and smooth transitions. CRITICAL: Remove mentions of
slide visuals (layout, colors, icons, animations, 'on the slide', 'as shown here').
Focus on explaining the content itself. Ensure opening appears only on the first
slide and closing only on the last."""

INSTRUCTION_PROMPT = """Please provide refined versions that:
(1) keep tone/terminology consistent,
(2) use smooth transitions,
(3) are engaging yet precise,
(4) target 80–140 words per slide, and
(5) eliminate any references to visual UI (layout, colors, icons, animations, 'on the slide').

CRITICAL POSITIONING:
- Slide 1: opening only
- Slides 2..N-1: direct content, smooth transitions
- Slide N: closing summary and call-to-action

FORMAT: Return plain text for each slide’s content only, no labels or numbering."""


class TranscriptReviewer:
    """Reviewer for AI-generated presentation transcripts."""

    def __init__(self) -> None:
        """Initialize reviewer with configured provider."""
        self.model = config.script_review_model or config.openai_model

    async def revise_transcripts(
        self, transcripts: list[dict[str, Any]], language: str = "english"
    ) -> list[dict[str, Any]]:
        """Revise transcripts to improve flow and consistency"""
        if not transcripts:
            return []

        # Use English-only prompts regardless of requested language
        system_prompt = REVIEW_PROMPT
        instruction_prompt = INSTRUCTION_PROMPT

        # Concatenate transcripts for the model
        content = "\n\n".join([t.get("script", "") for t in transcripts])

        try:
            reviewed_content = chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"""{instruction_prompt}

{content}""",
                    },
                ],
            )
        except Exception as e:
            logger.error(f"Transcript review failed: {e}")
            # If the model call fails, return original transcripts
            return transcripts

        # Simple splitting logic; real implementation may be more advanced
        paragraphs = [
            sanitize_transcript(p.strip())
            for p in reviewed_content.split("\n\n")
            if p.strip()
        ]
        num_slides = len(transcripts)
        reviewed_transcripts: list[dict[str, Any]] = []

        if len(paragraphs) == num_slides:
            # Perfect match - each paragraph is a slide
            for i, paragraph in enumerate(paragraphs):
                reviewed_transcripts.append(
                    {"slide_number": str(i + 1), "script": paragraph.strip()}
                )
        elif len(paragraphs) > 0:
            # Fallback distribute across slides
            for i in range(num_slides):
                text = paragraphs[i % len(paragraphs)]
                reviewed_transcripts.append(
                    {"slide_number": str(i + 1), "script": text}
                )
        else:
            # No better content; return original
            return transcripts

        # Ensure every slide has content; fallback to original if needed
        result: list[dict[str, Any]] = []
        for i in range(num_slides):
            if i < len(reviewed_transcripts) and reviewed_transcripts[i].get("script"):
                result.append(reviewed_transcripts[i])
            else:
                result.append(transcripts[i])
        return result

    # Qwen review support removed
