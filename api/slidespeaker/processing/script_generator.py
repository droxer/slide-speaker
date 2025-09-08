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
    "english": "Create a detailed, comprehensive, and educational presentation script in English based on the following content analysis. Provide thorough explanations of topics and key points with relevant examples. Focus on depth of explanation rather than brevity to ensure complete understanding.",  # noqa: E501
    "simplified_chinese": "根据以下内容分析，创建一个详细、全面且具有教育意义的简体中文演示脚本。对主题和要点提供详尽解释和相关示例。重点是深度解释而非简洁，以确保完全理解。",  # noqa: E501
    "traditional_chinese": "根據以下內容分析，創建一個詳細、全面且具有教育意義的繁體中文演示腳本。對主題和要點提供詳盡解釋和相關示例。重點是深度解釋而非簡潔，以確保完全理解。",  # noqa: E501
    "japanese": "以下の内容分析に基づいて、詳細で包括的かつ教育的な日本語のプレゼンテーションスクリプトを作成してください。トピックと要点の詳細な説明と関連する例を提供してください。完全な理解を確保するために、簡潔さよりも説明の深さに重点を置いてください。",  # noqa: E501
    "korean": "다음 내용 분석을 바탕으로 자세하고 포괄적이며 교육적인 한국어 프레젠테이션 스크립트를 작성해 주세요。주제와 핵심 포인트에 대한 철저한 설명과 관련 예시를 제공하세요。완전한 이해를 보장하기 위해 간결함보다는 설명의 깊이에 중점을 두세요。",  # noqa: E501
    "thai": "สร้างสคริปต์การนำเสนอที่ละเอียด ครอบคลุม และมีคุณค่าทางการศึกษาเป็นภาษาไทยโดยอิงจากเนื้อหา ให้คำอธิบายอย่างละเอียดเกี่ยวกับหัวข้อและประเด็นสำคัญพร้อมตัวอย่างที่เกี่ยวข้อง ให้ความสำคัญกับความลึกของการอธิบายมากกว่าความกระชับเพื่อให้มั่นใจว่าเข้าใจอย่างสมบูรณ์",  # noqa: E501
}

# Language-specific system prompts for AI
SYSTEM_PROMPTS = {
    "english": "You are a professional presentation script writer and educator. "
    "Create detailed, comprehensive, and educational scripts for AI avatars based on content analysis. "
    "Provide thorough explanations of topics and key points, include relevant examples where appropriate, "
    "and ensure complex concepts are fully understood by the audience. "
    "Focus on depth of explanation rather than brevity.",  # noqa: E501
    "simplified_chinese": "你是一名专业的演示脚本撰写人和教育专家。基于内容分析为AI虚拟形象创建详细、全面且具有教育意义的简体中文脚本。提供对主题和要点的详尽解释，适当包含相关示例，并确保观众充分理解复杂概念。重点是深度解释而非简洁。",  # noqa: E501
    "traditional_chinese": "你是一名專業的演示腳本撰寫人和教育專家。基於內容分析為AI虛擬形象創建詳細、全面且具有教育意義的繁體中文腳本。提供對主題和要點的詳盡解釋，適當包含相關示例，並確保觀眾充分理解複雜概念。重點是深度解釋而非簡潔。",  # noqa: E501
    "japanese": "あなたはプロのプレゼンテーションスクリプトライター兼教育者です。内容分析に基づいてAIアバター用の詳細で包括的かつ教育的な日本語スクリプトを作成してください。トピックと要点の詳細な説明を提供し、適切な例を含め、複雑な概念が聴衆に十分に理解されるようにしてください。簡潔さよりも説明の深さに重点を置いてください。",  # noqa: E501
    "korean": "당신은 전문 프레젠테이션 스크립트 작가이자 교육자입니다. 내용 분석을 바탕으로 AI 아바타를 위한 자세하고 포괄적이며 교육적인 한국어 스크립트를 작성해 주세요。주제와 핵심 포인트에 대한 철저한 설명을 제공하고, 적절한 예시를 포함하며, 복잡한 개념이 청중에게 충분히 이해되도록 하세요。간결함보다는 설명의 깊이에 중점을 두세요。",  # noqa: E501
    "thai": "คุณเป็นนักเขียนสคริปต์การนำเสนอและนักการศึกษา สร้างสคริปต์ที่ละเอียด ครอบคลุม และมีคุณค่าทางการศึกษาสำหรับอวตาร AI โดยอิงจากเนื้อหา ให้คำอธิบายอย่างละเอียดเกี่ยวกับหัวข้อและประเด็นสำคัญ รวมถึงตัวอย่างที่เกี่ยวข้องเมื่อเหมาะสม และให้แน่ใจว่าแนวคิดที่ซับซ้อนจะถูกเข้าใจอย่างเต็มที่โดยผู้ชม ให้ความสำคัญกับความลึกของการอธิบายมากกว่าความกระชับ",  # noqa: E501
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
        Create a detailed, comprehensive explanation that thoroughly covers the topic and key points.
        The script should be educational, engaging, and provide in-depth analysis of the content.
        Focus on explaining concepts clearly, providing examples where relevant, and ensuring
        the audience fully understands the material.
        Length: 150-300 words to ensure comprehensive coverage.

        {prompt_context}

        Content to convert into a detailed presentation script:
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
                max_tokens=500,  # Increased for more detailed explanations
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
