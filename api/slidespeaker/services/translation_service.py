"""Translation service for SlideSpeaker.

This module provides translation capabilities for scripts using AI language models.
It supports translation between multiple languages and maintains context for
coherent translations across presentation slides.
"""

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

# System prompts for translation
SYSTEM_PROMPTS = {
    "english": "You are a professional translator specializing in presentation content. Your task is to accurately translate presentation scripts while preserving their meaning, tone, and professional quality. Return only the translated content without any additional markers, prefixes, or explanations. DO NOT add any prefixes like '[Translated to English]:' or 'Slide 1:'. Each slide should be separated by double newlines. Return only the pure translated text content.",  # noqa: E501
    "simplified_chinese": "您是一位专业的演示文稿内容翻译员。您的任务是在保持演示文稿脚本含义、语调和专业质量的同时准确翻译。仅返回翻译后的内容，不要添加任何额外的标记、前缀或说明。不要添加'[Translated to simplified_chinese]:'或'Slide 1:'等前缀。每个幻灯片之间用双换行符分隔。仅返回纯翻译文本内容。",  # noqa: E501
    "traditional_chinese": "您是一位專業的簡報內容翻譯員。您的任務是在保持簡報腳本含義、語調和專業品質的同時準確翻譯。僅返回翻譯後的內容，不要添加任何額外的標記、前綴或說明。不要添加'[Translated to traditional_chinese]:'或'Slide 1:'等前綴。每個簡報之間用雙換行符分隔。僅返回純翻譯文本內容。",  # noqa: E501
    "japanese": "あなたはプレゼンテーションコンテンツの専門翻訳者です。プレゼンテーションスクリプトの意味、トーン、プロの品質を維持しながら正確に翻訳することがあなたの任務です。追加のマーカー、プレフィックス、説明なしで翻訳されたコンテンツのみを返してください。'[Translated to japanese]:'や'Slide 1:'などのプレフィックスを追加しないでください。各スライドは二重改行で区切ってください。純粋な翻訳テキストコンテンツのみを返してください。",  # noqa: E501
    "korean": "귀하는 프레젠테이션 콘텐츠 전문 번역가입니다. 프레젠테이션 스크립트의 의미, 톤, 전문 품질을 유지하면서 정확하게 번역하는 것이 귀하의 임무입니다。추가 마커, 접두사, 설명 없이 번역된 콘텐츠만 반환하세요。'[Translated to korean]:'이나 'Slide 1:' 등의 접두사를 추가하지 마세요。각 슬라이드는 이중 줄바꿈으로 구분되어야 합니다。순수한 번역 텍스트 콘텐츠만 반환하세요。",  # noqa: E501
    "thai": "คุณเป็นนักแปลผู้เชี่ยวชาญด้านเนื้อหาการนำเสนอ งานของคุณคือการแปลสคริปต์การนำเสนออย่างถูกต้องโดยรักษาความหมาย น้ำเสียง และคุณภาพระดับมืออาชีพไว้ คืนเฉพาะเนื้อหาที่แปลแล้วโดยไม่มีเครื่องหมายเพิ่มเติม คำนำหน้า หรือคำอธิบาย อย่าเพิ่มคำนำหน้าเช่น '[Translated to thai]:' หรือ 'Slide 1:' แยกแต่ละสไลด์ด้วยบรรทัดว่างสองบรรทัด คืนเฉพาะเนื้อหาข้อความที่แปลแล้วเท่านั้น",  # noqa: E501
}


class TranslationService:
    """Service for translating presentation scripts using AI language models"""

    def __init__(self) -> None:
        """Initialize the translation service with OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def translate_scripts(
        self,
        scripts: list[dict[str, Any]],
        source_language: str = "english",
        target_language: str = "english",
    ) -> list[dict[str, Any]]:
        """
        Translate presentation scripts from source language to target language.

        Args:
            scripts: List of script dictionaries with slide_number and script content
            source_language: Source language of the scripts (default: english)
            target_language: Target language for translation

        Returns:
            List of translated script dictionaries
        """
        if not scripts:
            logger.warning("No scripts provided for translation")
            return scripts

        if target_language == source_language:
            logger.info(
                f"Source and target languages are the same ({target_language}), returning original scripts"
            )
            return scripts

        logger.info(
            f"Translating {len(scripts)} scripts from {source_language} to {target_language}"
        )

        all_scripts_text = "\n\n".join(
            [
                f"Slide {script_data.get('slide_number', i + 1)}: {script_data.get('script', '')}"
                for i, script_data in enumerate(scripts)
            ]
        )

        try:
            model_name = os.getenv("TRANSLATION_MODEL", "gpt-4o")
            logger.info(f"Using translation model: {model_name}")

            system_prompt = SYSTEM_PROMPTS.get(
                target_language, SYSTEM_PROMPTS["english"]
            )
            user_prompt = f"""
                        {TRANSLATION_PROMPTS.get(target_language, TRANSLATION_PROMPTS["english"])}

                        Original scripts:
                        {all_scripts_text}
                        """

            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            translated_content_response = response.choices[0].message.content
            translated_content = (
                translated_content_response.strip()
                if translated_content_response
                else ""
            )
            logger.info(
                f"Translation response received for {target_language}: {translated_content[:500]}..."
            )

            if not translated_content.strip():
                logger.warning(
                    "Translation returned empty content, returning original scripts"
                )
                return scripts

            # Parse the translated content back into structured format
            translated_scripts = self._parse_translated_content(
                translated_content, scripts
            )

            if not translated_scripts:
                logger.warning(
                    "Failed to parse translated content, returning original scripts"
                )
                return scripts

            logger.info(f"Successfully translated {len(translated_scripts)} scripts")
            return translated_scripts

        except Exception as e:
            logger.error(f"Error translating scripts: {e}")
            # Return original scripts if translation fails
            return scripts

    def _parse_translated_content(
        self, translated_content: str, original_scripts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Parse translated content back into structured script format.

        Args:
            translated_content: Raw translated text from AI model
            original_scripts: Original script structure to maintain slide numbers

        Returns:
            List of parsed translated script dictionaries
        """
        try:
            logger.debug(f"Parsing translated content: {translated_content[:500]}...")

            # Clean the content
            translated_content = translated_content.strip()

            # Handle case where AI returns markdown or other formatting
            if translated_content.startswith("```"):
                # Extract content from code block
                lines = translated_content.split("\n")
                if len(lines) > 2:
                    translated_content = "\n".join(lines[1:-1])

            # Remove common prefixes that AI might add
            lines = translated_content.split("\n")
            cleaned_lines = []
            for line in lines:
                # Remove translation markers like "[Translated to simplified_chinese]:"
                if line.startswith("[Translated to"):
                    continue
                # Remove slide number prefixes like "Slide 1:" or "1."
                cleaned_line = line
                # Check for various slide prefix formats
                import re

                # Remove "Slide X:" prefix
                cleaned_line = re.sub(r"^Slide\s+\d+\s*:\s*", "", cleaned_line)
                # Remove "X." prefix
                cleaned_line = re.sub(r"^\d+\.\s*", "", cleaned_line)
                # Remove any remaining bracketed translation markers
                cleaned_line = re.sub(r"^\[[^\]]+\]:\s*", "", cleaned_line)

                if cleaned_line.strip():
                    cleaned_lines.append(cleaned_line.strip())

            # Rejoin cleaned lines
            translated_content = "\n".join(cleaned_lines)
            logger.debug(f"Cleaned content: {translated_content[:500]}...")

            # Split into paragraphs by double newlines
            paragraphs = [
                p.strip() for p in translated_content.split("\n\n") if p.strip()
            ]

            logger.debug(
                f"Found {len(paragraphs)} paragraphs, expected {len(original_scripts)}"
            )

            # If we have the right number of paragraphs, map them to slides
            if len(paragraphs) == len(original_scripts):
                translated_scripts = []
                for i, paragraph in enumerate(paragraphs):
                    translated_scripts.append(
                        {
                            "slide_number": original_scripts[i].get(
                                "slide_number", str(i + 1)
                            ),
                            "script": paragraph,
                        }
                    )
                logger.debug(
                    f"Successfully parsed {len(translated_scripts)} translated scripts"
                )
                return translated_scripts
            else:
                # Try to split by single newlines if double newlines didn't work
                lines = [
                    line.strip()
                    for line in translated_content.split("\n")
                    if line.strip()
                ]
                logger.debug(
                    f"Trying single line split: {len(lines)} lines, expected {len(original_scripts)}"
                )
                if len(lines) >= len(original_scripts):
                    # Assume each line is a slide (or we have more lines than needed)
                    translated_scripts = []
                    for i, original_script in enumerate(original_scripts):
                        if i < len(lines):
                            translated_scripts.append(
                                {
                                    "slide_number": original_script.get(
                                        "slide_number", str(i + 1)
                                    ),
                                    "script": lines[i],
                                }
                            )
                        else:
                            # Fallback to original if we don't have enough translated content
                            translated_scripts.append(original_script)
                    logger.debug(
                        f"Successfully parsed {len(translated_scripts)} translated scripts (line split)"
                    )
                    return translated_scripts
                else:
                    # Not enough content, return original scripts
                    logger.warning(
                        f"Translation parsing failed: expected {len(original_scripts)} "
                        f"paragraphs, got {len(paragraphs)}"
                    )
                    return original_scripts

        except Exception as e:
            logger.error(f"Error parsing translated content: {e}")
            return original_scripts
