"""
Generate a 2-person conversation script (podcast) from PDF chapters.

Uses the segmented PDF content to create a host/guest style dialogue
focused on content (no visual/UI mentions).
"""

import re
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.core.state_manager import state_manager
from slidespeaker.llm import chat_completion

PODCAST_SYSTEM_PROMPT = """You are an expert podcast writer and interviewer.
Create a natural, informative two-person conversation (Host and Guest) that
explains complex ideas clearly and engagingly. Avoid references to slides,
visuals, or UI. Keep the flow coherent across chapters and include brief
transitions woven into the host/guest dialogue (no explicit labels). Tone is
professional, friendly, and insightful.

Rules:
- Only output lines that start with "Host:" or "Guest:".
- Do NOT include any standalone labels like "Transition:", "Scene:", etc.
- If you want a transition, write it as part of a Host/Guest line."""


def _build_user_prompt(chapters: list[dict[str, Any]], language: str) -> str:
    parts: list[str] = []
    parts.append(
        """Write a two-person conversation (Host and Guest) based on these chapters.
For each chapter, include a short transition from the prior topic, then a back-and-forth dialogue
that covers the chapter’s key points with clear explanations, examples, and definitions as needed.
Do not mention or describe visuals. Focus on the ideas. Target 90–150 spoken words per chapter.

Chapters:"""
    )
    for i, ch in enumerate(chapters, start=1):
        title = (ch.get("title") or "").strip()
        desc = (ch.get("description") or "").strip()
        kps = ch.get("key_points") or []
        parts.append(f"\n{i}. {title}\nDescription: {desc}")
        if kps:
            pts = "\n".join([f"- {p}" for p in kps])
            parts.append(f"Key points:\n{pts}")

    parts.append(
        """
FORMAT:
- Return the dialogue as alternating paragraphs prefixed with "Host:" or "Guest:".
- Separate chapters with a blank line.
- No numbering, no extra labels (e.g., no "Transition:"), no headers. Plain text only.
"""
    )
    return "\n".join(parts)


async def generate_podcast_script_step(file_id: str, language: str = "english") -> None:
    await state_manager.update_step_status(
        file_id, "generate_podcast_script", "processing"
    )
    logger.info(f"Generating podcast conversation script for file {file_id}")

    st = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []
    if (
        st
        and st.get("steps")
        and st["steps"].get("segment_pdf_content")
        and st["steps"]["segment_pdf_content"].get("data")
    ):
        chapters = st["steps"]["segment_pdf_content"]["data"] or []

    if not chapters:
        logger.warning(
            "No chapters available for podcast script; producing empty result"
        )
        await state_manager.update_step_status(
            file_id, "generate_podcast_script", "completed", []
        )
        return

    try:
        # Always generate the podcast script in English first
        user_prompt = _build_user_prompt(chapters, "english")
        content = chat_completion(
            model=config.script_generate_model,
            messages=[
                {"role": "system", "content": PODCAST_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        # Convert to a simple list of dialogue lines
        lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
        dialogue: list[dict[str, str]] = []
        for ln in lines:
            role = (
                "Host"
                if ln.lower().startswith("host:")
                else ("Guest" if ln.lower().startswith("guest:") else None)
            )
            text = ln.split(":", 1)[1].strip() if ":" in ln else ln
            text = _strip_transition_label(text)
            if role and text:
                dialogue.append({"speaker": role, "text": text})

        await state_manager.update_step_status(
            file_id, "generate_podcast_script", "completed", dialogue
        )
    except Exception as e:
        logger.error(f"Podcast script generation failed: {e}")
        await state_manager.update_step_status(
            file_id, "generate_podcast_script", "failed", {"error": str(e)}
        )
        raise


def _strip_transition_label(text: str) -> str:
    t = text.strip()
    # Remove leading "Transition:" (or with dashes) case-insensitively
    t = re.sub(r"^(transition)\s*[:\-—–]\s*", "", t, flags=re.IGNORECASE)
    return t.strip()
