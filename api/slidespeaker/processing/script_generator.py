"""
Script generation module for SlideSpeaker.

This module generates AI-powered presentation scripts for each slide using OpenAI's GPT models.
It supports multiple languages and incorporates visual analysis context to create
engaging, natural-sounding scripts suitable for AI avatar presentation.
"""

import os
from typing import Any

from openai import OpenAI

# Language-specific prompts for generating presentation scripts
LANGUAGE_PROMPTS = {
    "english": "Create a natural, engaging presentation script in English based on the following slide content analysis.",  # noqa: E501
    "simplified_chinese": "根据以下幻灯片内容分析，创建一个自然、吸引人的简体中文演示脚本。",  # noqa: E501
    "traditional_chinese": "根據以下簡報內容分析，創建一個自然、吸引人的繁體中文演示腳本。",  # noqa: E501
    "japanese": "以下のスライド内容分析に基づいて、自然で魅力的な日本語のプレゼンテーションスクリプトを作成してください。",  # noqa: E501
    "korean": "다음 슬라이드 내용 분석을 바탕으로 자연스럽고 매력적인 한국어 프레젠테이션 스크립트를 작성해 주세요.",  # noqa: E501
    "thai": "สร้างสคริปต์การนำเสนอที่เป็นธรรมชาติและน่าสนใจเป็นภาษาไทยโดยอิงจากเนื้อหาสไลด์ดังกล่าว",  # noqa: E501
}

# Language-specific system prompts for AI
SYSTEM_PROMPTS = {
    "english": "You are a professional presentation script writer. "
    "Create concise, engaging scripts for AI avatars based on slide content analysis.",  # noqa: E501
    "simplified_chinese": "你是一名专业的演示脚本撰写人。基于幻灯片内容分析为AI虚拟形象创建简洁、吸引人的简体中文脚本。",  # noqa: E501
    "traditional_chinese": "你是一名專業的演示腳本撰寫人。基於簡報內容分析為AI虛擬形象創建簡潔、吸引人的繁體中文腳本。",  # noqa: E501
    "japanese": "あなたはプロのプレゼンテーションスクリプトライターです。スライド内容分析に基づいてAIアバター用の簡潔で魅力的な日本語スクリプトを作成してください。",  # noqa: E501
    "korean": "당신은 전문 프레젠테이션 스크립트 작가입니다. 슬라이드 내용 분석을 바탕으로 AI 아바타를 위한 간결하고 매력적인 한국어 스크립트를 작성해 주세요。",  # noqa: E501
    "thai": "คุณเป็นนักเขียนสคริปต์การนำเสนอระดับมืออาชีพ สร้างสคริปต์ที่กระชับและน่าสนใจสำหรับอวตาร AI โดยอิงจากเนื้อหาสไลด์",  # noqa: E501
}

# Fallback scripts in different languages
FALLBACK_SCRIPTS = {
    "english": "Let me walk you through this important content.",
    "simplified_chinese": "让我为您介绍这一重要内容。",
    "traditional_chinese": "讓我為您介紹這一重要內容。",
    "japanese": "この重要な内容についてご説明します。",
    "korean": "이 중요한 내용을 설명해 드리겠습니다.",
    "thai": "ให้ผมพาคุณไปดูเนื้อหาที่สำคัญนี้",
}

# Fallback scripts for error cases
ERROR_FALLBACK_SCRIPTS = {
    "english": "In this slide, we'll discuss: {content}...",
    "simplified_chinese": "在本幻灯片中，我们将讨论：{content}...",
    "traditional_chinese": "在本簡報中，我們將討論：{content}...",
    "japanese": "このスライドでは、{content}...について説明します",
    "korean": "이 슬라이드에서는 {content}...에 대해 논의하겠습니다",
    "thai": "ในสไลด์นี้ เราจะพูดถึง: {content}...",
}


class ScriptGenerator:
    """Generator for AI-powered presentation scripts using OpenAI GPT models"""

    def __init__(self) -> None:
        """Initialize the script generator with OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_script(
        self,
        slide_content: str,
        image_analysis: dict[str, Any] | None = None,
        language: str = "english",
    ) -> str:
        """
        Generate a presentation script for a slide using AI.

        This method creates a natural, engaging script suitable for AI avatar presentation
        by combining slide text content with visual analysis context. It supports multiple
        languages and includes comprehensive error handling with fallback mechanisms.
        """
        if not slide_content.strip() and not image_analysis:
            return "This slide contains visual content that will be presented."

        # Use image analysis if available, otherwise use text content
        content_to_use = slide_content
        if image_analysis and image_analysis.get("text_content"):
            content_to_use = image_analysis["text_content"]

        # Enhanced prompt with image analysis context
        prompt_context = ""
        if image_analysis:
            prompt_context = f"""
Visual Analysis Context:
- Main Topic: {image_analysis.get("main_topic", "Unknown")}
- Key Points: {", ".join(image_analysis.get("key_points", []))}
- Visual Elements: {", ".join(image_analysis.get("visual_elements", []))}
- Structure: {image_analysis.get("structure", "standard")}
"""

        prompt = f"""
        {LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["english"])}
        The script should be suitable for a professional AI avatar to deliver.
        Keep it concise (50-100 words), clear, and engaging.

        {prompt_context}

        Slide content:
        {content_to_use}

        Script:
        """

        try:
            model_name = os.getenv("SCRIPT_GENERATOR_MODEL", "gpt-4o")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPTS.get(
                            language, SYSTEM_PROMPTS["english"]
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
            )

            script_content = response.choices[0].message.content
            script = script_content.strip() if script_content else None

            return (
                script
                if script
                else FALLBACK_SCRIPTS.get(
                    language, "Let me walk you through this important content."
                )
            )

        except Exception as e:
            print(f"Error generating script: {e}")
            # Fallback script based on detected language
            fallback_content = (
                content_to_use[:100] if content_to_use else "visual content"
            )

            # If the content is just an image filename, provide a more meaningful fallback
            if fallback_content.startswith("Slide image:"):
                # This is likely from vision analysis fallback - create better content
                if language == "english":
                    return "Let me walk you through this important visual content."
                elif language in ["simplified_chinese", "traditional_chinese"]:
                    return "让我为您介绍这一重要视觉内容。"
                elif language == "japanese":
                    return "この重要なビジュアルコンテンツについてご説明します。"
                elif language == "korean":
                    return "이 중요한 시각적 콘텐츠를 설명해 드리겠습니다。"
                elif language == "thai":
                    return "ให้ผมพาคุณไปดูเนื้อหาภาพที่สำคัญนี้"

            fallback_template = ERROR_FALLBACK_SCRIPTS.get(
                language, ERROR_FALLBACK_SCRIPTS["english"]
            )
            return fallback_template.format(content=fallback_content[:50])
