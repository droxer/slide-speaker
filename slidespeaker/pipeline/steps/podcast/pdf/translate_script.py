"""
Translate the podcast script from English to the selected voice language.

Preserves speaker labels (Host/Guest) and returns the same structured list
of dialogue items: [{"speaker": "Host|Guest", "text": "..."}].
"""

import re
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.state_manager import state_manager
from slidespeaker.llm import chat_completion

SYSTEM_PROMPT = (
    "You are a precise translator for podcast dialogues. "
    "Translate the text to the target language while strictly "
    "preserving speaker labels and structure. Output only lines that start with "
    "'Host:' or 'Guest:'. Do not add notes or labels; return only the translated "
    "dialogue lines. Avoid any references to visuals or slides; focus purely on "
    "content. Do NOT include any standalone labels like 'Transition:'; if present "
    "in the source, incorporate the idea into the Host/Guest line without the label."
)


def _build_translate_prompt(
    dialogue: list[dict[str, Any]], target_language: str
) -> str:
    lines = []
    lines.append(
        f"Translate the following Host/Guest dialogue into {target_language}.\n"
        "Keep each line on its own, prefixing with 'Host:' or 'Guest:' exactly as given.\n"
        "Return plain text lines only, one per line, no numbering or extra text.\n"
    )
    lines.append("\nDialogue:\n")
    for item in dialogue:
        sp = (item.get("speaker") or "Host").strip()
        tx = (item.get("text") or "").strip()
        if tx:
            lines.append(f"{sp}: {tx}")
    return "\n".join(lines)


def _strip_transition_label(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^(transition)\s*[:\-—–]\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


async def translate_podcast_script_step(
    file_id: str, source_language: str = "english", target_language: str = "english"
) -> None:
    normalized_source = locale_utils.normalize_language(source_language)
    normalized_target = locale_utils.normalize_language(target_language)
    target_display = locale_utils.get_display_name(normalized_target)

    await state_manager.update_step_status(
        file_id, "translate_podcast_script", "processing"
    )
    logger.info(
        "Translating podcast script for file %s -> %s",
        file_id,
        target_display or normalized_target,
    )

    st = await state_manager.get_state(file_id)
    dialogue: list[dict[str, Any]] = []
    if st and st.get("steps") and st["steps"].get("generate_podcast_script"):
        dialogue = st["steps"]["generate_podcast_script"].get("data") or []

    if not dialogue:
        logger.warning(
            "No dialogue to translate; marking step completed with empty data"
        )
        await state_manager.update_step_status(
            file_id, "translate_podcast_script", "completed", []
        )
        return

    if normalized_target == normalized_source:
        logger.info(
            "Source and target languages are the same (%s); copying input dialogue",
            normalized_target,
        )
        await state_manager.update_step_status(
            file_id, "translate_podcast_script", "completed", dialogue
        )
        return

    try:
        prompt = _build_translate_prompt(dialogue, target_display)
        content = chat_completion(
            model=config.translation_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
        out: list[dict[str, str]] = []
        for ln in lines:
            role = (
                "Host"
                if ln.lower().startswith("host:")
                else ("Guest" if ln.lower().startswith("guest:") else None)
            )
            text = ln.split(":", 1)[1].strip() if ":" in ln else ln
            text = _strip_transition_label(text)
            if role and text:
                out.append({"speaker": role, "text": text})
        await state_manager.update_step_status(
            file_id, "translate_podcast_script", "completed", out
        )
    except Exception as e:
        logger.error(f"Podcast script translation failed: {e}")
        await state_manager.update_step_status(
            file_id, "translate_podcast_script", "failed", {"error": str(e)}
        )
        raise
