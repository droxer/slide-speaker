"""Translation service for SlideSpeaker (translation package)."""

import os
from typing import Any

from loguru import logger
from openai import OpenAI

# Language mapping for translation
LANGUAGE_CODES = {
    "english": "en",
    "simplified_chinese": "zh-CN",
    "traditional_chinese": "zh-TW",
    "japanese": "ja",
    "korean": "ko",
    "thai": "th",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "arabic": "ar",
    "hindi": "hi",
    "vietnamese": "vi",
}

# Translation prompts for different languages
TRANSLATION_PROMPTS = {
    "english": "Translate the following presentation scripts to English while maintaining the original meaning, tone, and context. Ensure the translations are professional and suitable for presentation purposes. Return only the translated content without any additional markers, prefixes, or explanations. DO NOT add any prefixes like '[Translated to English]:' or 'Slide 1:'. Each slide should be separated by double newlines. Return only the pure translated text content.",  # noqa: E501
    "simplified_chinese": "将以下演示文稿脚本翻译成简体中文，保持原文的含义、语调和上下文。确保翻译专业且适合演示用途。仅返回翻译后的内容，不要添加任何额外的标记、前缀或说明。不要添加'[Translated to simplified_chinese]:'或'Slide 1:'等前缀。每个幻灯片之间用双换行符分隔。仅返回纯翻译文本内容。",  # noqa: E501
    "traditional_chinese": "將以下簡報文稿腳本翻譯成繁體中文，保持原文的含義、語調和上下文。確保翻譯專業且適合簡報用途。僅返回翻譯後的內容，不要添加任何額外的標記、前綴或說明。不要添加'[Translated to traditional_chinese]:'或'Slide 1:'等前綴。每個簡報之間用雙換行符分隔。僅返回純翻譯文本內容。",  # noqa: E501
    "japanese": "以下のプレゼンテーションスクリプトを日本語に翻訳し、元の意味、トーン、文脈を維持してください。翻訳は専門的でプレゼンテーションに適したものを確保してください。追加のマーカー、プレフィックス、説明なしで翻訳されたコンテンツのみを返してください。'[Translated to japanese]:'や'Slide 1:'などのプレフィックスを追加しないでください。各スライドは二重改行で区切ってください。純粋な翻訳テキストコンテンツのみを返してください。",  # noqa: E501
    "korean": "다음 프레젠테이션 스크립트를 한국어로 번역하면서 원래 의미, 톤, 문맥을 유지하세요. 번역은 전문적이고 프레젠테이션에 적합하도록 하세요. 추가 마커, 접두사, 설명 없이 번역된 콘텐츠만 반환하세요. '[Translated to korean]:'이나 'Slide 1:' 등의 접두사를 추가하지 마세요. 각 슬라이드는 이중 줄바꿈으로 구분되어야 합니다. 순수한 번역 텍스트 콘텐츠만 반환하세요.",  # noqa: E501
    "thai": "แปลสคริปต์การนำเสนอต่อไปนี้เป็นภาษาไทยโดยคงความหมาย น้ำเสียง และบริบทต้นฉบับ ตรวจสอบให้แน่ใจว่าการแปลมีความเป็นมืออาชีพและเหมาะสมสำหรับการนำเสนอ คืนเฉพาะเนื้อหาที่แปลแล้วโดยไม่มีเครื่องหมายเพิ่มเติม คำนำหน้า หรือคำอธิบาย อย่าเพิ่มคำนำหน้าเช่น '[Translated to thai]:' หรือ 'Slide 1:' แยกแต่ละสไลด์ด้วยบรรทัดว่างสองบรรทัด คืนเฉพาะเนื้อหาข้อความที่แปลแล้วเท่านั้น",  # noqa: E501
}

# System prompts for translation (trimmed for brevity in this copy)
SYSTEM_PROMPTS = dict(TRANSLATION_PROMPTS)


class TranslationService:
    """Service for translating presentation scripts using AI models"""

    def __init__(self) -> None:
        self.client: OpenAI | None = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    def translate_scripts(
        self,
        scripts: list[dict[str, Any]],
        source_language: str,
        target_language: str,
    ) -> list[dict[str, Any]]:
        """Translate a list of scripts into target language"""
        try:
            if not scripts:
                return []

            if source_language.lower() == target_language.lower():
                return scripts

            system_prompt = SYSTEM_PROMPTS.get(
                target_language.lower(), SYSTEM_PROMPTS["english"]
            )
            user_prompt = TRANSLATION_PROMPTS.get(
                target_language.lower(), TRANSLATION_PROMPTS["english"]
            )
            text_blocks = [s.get("script", "").strip() for s in scripts]
            joined = "\n\n".join(text_blocks)

            if not self.client:
                logger.warning(
                    "Translation client not initialized; returning originals"
                )
                return scripts

            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_prompt}\n\n{joined}"},
                ],
                temperature=0.2,
            )
            translated_content = response.choices[0].message.content or ""
            if not translated_content.strip():
                return scripts

            return self._parse_translated_content(translated_content, scripts)

        except Exception as e:
            logger.error(f"Error translating scripts: {e}")
            return scripts

    def _parse_translated_content(
        self, translated_content: str, original_scripts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        try:
            translated_content = translated_content.strip()
            if translated_content.startswith("```"):
                lines = translated_content.split("\n")
                if len(lines) > 2:
                    translated_content = "\n".join(lines[1:-1])

            lines = translated_content.split("\n")
            cleaned_lines = []
            for line in lines:
                if line.startswith("[Translated to"):
                    continue
                import re

                cleaned_line = re.sub(r"^Slide\s+\d+\s*:\s*", "", line)
                cleaned_line = re.sub(r"^\d+\.\s*", "", cleaned_line)
                cleaned_line = re.sub(r"^\[[^\]]+\]:\s*", "", cleaned_line)
                if cleaned_line.strip():
                    cleaned_lines.append(cleaned_line.strip())

            translated_content = "\n".join(cleaned_lines)
            paragraphs = [
                p.strip() for p in translated_content.split("\n\n") if p.strip()
            ]

            if len(paragraphs) == len(original_scripts):
                result: list[dict[str, Any]] = []
                for i, paragraph in enumerate(paragraphs):
                    result.append(
                        {
                            "slide_number": original_scripts[i].get(
                                "slide_number", str(i + 1)
                            ),
                            "script": paragraph,
                        }
                    )
                return result

            # Fallback to per-line mapping
            lines = [
                line.strip() for line in translated_content.split("\n") if line.strip()
            ]
            if len(lines) >= len(original_scripts):
                result = []
                for i, original_script in enumerate(original_scripts):
                    if i < len(lines):
                        result.append(
                            {
                                "slide_number": original_script.get(
                                    "slide_number", str(i + 1)
                                ),
                                "script": lines[i],
                            }
                        )
                return result

            # Return original if parsing fails
            return original_scripts
        except Exception as e:
            logger.warning(f"Failed to parse translated content: {e}")
            return original_scripts
