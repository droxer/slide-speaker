"""
Transcript generation module for SlideSpeaker.

Generates AI-powered presentation transcripts per slide using the configured
provider (OpenAI or Qwen). Combines extracted slide content and visual
analysis prompts to produce natural, engaging transcripts suitable for
AI avatar presentation.
"""

from typing import Any

import requests
from loguru import logger
from openai import OpenAI

from slidespeaker.configs.config import config

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
    """Generator for AI-powered presentation transcripts (OpenAI or Qwen)"""

    def __init__(self) -> None:
        """Initialize client based on configured provider."""
        self.provider = config.script_provider
        self.client: OpenAI | None = None
        self.model: str = config.script_generator_model  # OpenAI model by default
        self.qwen_api_key: str | None = None
        self.qwen_model: str | None = None
        if self.provider == "qwen":
            self.qwen_api_key = config.qwen_api_key
            self.qwen_model = config.qwen_script_model or "qwen-turbo"
            if not self.qwen_api_key:
                # Defer failure to call time to avoid import-time crashes
                logger.error(
                    "QWEN_API_KEY not set; Qwen transcript generation will fallback"
                )
        else:
            api_key = config.openai_api_key
            if api_key:
                try:
                    self.client = OpenAI(api_key=api_key)
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI client: {e}")
            else:
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
            analysis_text = image_analysis or ""
            user_content = (
                f"Slide content:\n{content_text}\n\n"
                f"Image analysis (if any):\n{analysis_text}\n\n"
                f"{user_prompt}"
            )

            if self.provider == "qwen":
                content = self._generate_with_qwen(
                    system_prompt, user_prompt, content_text, analysis_text
                )
            else:
                if not self.client:
                    raise RuntimeError("OpenAI client not configured")
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                )
                content = resp.choices[0].message.content or ""
            transcript = content.strip()
            return transcript
        except Exception as e:
            logger.error(f"Transcript generation failed: {e}")
            # Fallback to a simple default transcript
            defaults = DEFAULT_TRANSCRIPTS.get(language, DEFAULT_TRANSCRIPTS["english"])
            return defaults[0]

    def _generate_with_qwen(
        self,
        system_prompt: str,
        user_prompt: str,
        content_text: str,
        analysis_text: str,
    ) -> str:
        if not self.qwen_api_key:
            raise RuntimeError("Qwen API key not configured")
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.qwen_api_key}",
            "Content-Type": "application/json",
        }
        user_content = (
            f"Slide content:\n{content_text}\n\n"
            f"Image analysis (if any):\n{analysis_text}\n\n"
            f"{user_prompt}"
        )
        payload = {
            "model": self.qwen_model or "qwen-turbo",
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            },
            "parameters": {"result_format": "message"},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Qwen HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        content = str(
            ((data.get("output") or {}).get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if content:
            return content
        alt = str((data.get("output") or {}).get("text") or "")
        return alt
