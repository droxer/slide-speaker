"""Module for reviewing and refining presentation transcripts.

This module uses OpenAI to review and improve generated presentation transcripts
for consistency, flow, and quality. It ensures appropriate formatting for AI avatar delivery
and handles proper positioning of opening/closing statements.
"""

from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

# Language-specific review prompts
REVIEW_PROMPTS = {
    "english": "Review and refine the following presentation transcripts to ensure consistency in tone, style, and smooth transitions between slides. CRITICAL: Ensure opening statements (greetings, introductions) appear ONLY on the first slide, and closing statements (summaries, thank-yous, calls-to-action) appear ONLY on the last slide. Middle slides should start directly with content and use smooth transitions without greetings or closings.",  # noqa: E501
    "simplified_chinese": "审查并优化以下演示文稿，确保语调、风格一致，幻灯片之间过渡自然。关键要求：开场白（问候、介绍）只出现在第一张幻灯片，结尾语（总结、感谢、行动号召）只出现在最后一张幻灯片。中间幻灯片应直接进入内容，使用平滑过渡，避免重复问候或结尾。",  # noqa: E501
    "traditional_chinese": "審閱並優化以下簡報文稿，確保語調、風格一致，簡報之間過渡自然。關鍵要求：開場白（問候、介紹）只出現在第一張簡報，結尾語（總結、感謝、行動號召）只出現在最後一張簡報。中間簡報應直接進入內容，使用平滑過渡，避免重複問候或結尾。",  # noqa: E501
    "japanese": "次のプレゼンテーショントランスクリプトをレビューし、トーン、スタイルの一貫性、スライド間のスムーズな移行を確保してください。重要：オープニングステートメント（挨拶、紹介）は最初のスライドにのみ、クロージングステートメント（要約、感謝、アクションコール）は最後のスライドにのみ表示してください。中間スライドは直接コンテンツから始め、挨拶や締めくくりを避けてスムーズに移行してください。",  # noqa: E501
    "korean": "다음 프레젠테이션 트랜스크립트를 검토하여 톤, 스타일의 일관성과 슬라이드 간의 원활한 전환을 보장하세요. 중요: 오프닝 문장(인사, 소개)은 첫 번째 슬라이드에만, 클로징 문장(요약, 감사, 행동 촉구)은 마지막 슬라이드에만 표시하세요. 중간 슬라이드는 직접 콘텐츠로 시작하고, 인사나 마무리를 피하면서 부드럽게 전환하세요.",  # noqa: E501
    "thai": "ตรวจสอบและปรับปรุงทรานสคริปต์การนำเสนอต่อไปนี้เพื่อให้มีความสอดคล้องกันในด้านน้ำเสียง สไตล์ และการเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์ สิ่งสำคัญ: ให้ข้อความเปิด (คำทักทาย การแนะนำ) ปรากฏเฉพาะในสไลด์แรกเท่านั้น และข้อความปิด (สรุป ขอบคุณ การเรียกร้องให้ดำเนินการ) ปรากฏเฉพาะในสไลด์สุดท้ายเท่านั้น สไลด์กลางควรเริ่มต้นโดยตรงด้วยเนื้อหาและใช้การเปลี่ยนผ่านที่ราบรื่นโดยไม่มีคำทักทายหรือการปิดท้าย",  # noqa: E501
}

# Language-specific instruction prompts
INSTRUCTION_PROMPTS = {
    "english": "Please provide refined versions of each transcript that improve:\n1. Consistency in tone and terminology\n2. Smooth transitions between slides\n3. Professional yet engaging language\n4. Appropriate length (50-100 words per slide)\n5. CRITICAL POSITIONING:\n   - Slide 1 (First): Include engaging opening (greeting, topic introduction)\n   - Slides 2 to N-1 (Middle): Start directly with content, use smooth transitions like 'Next, we'll explore...', 'Moving on to...', 'Building on this...'\n   - Slide N (Last): Include closing summary and call-to-action\n6. ELIMINATE: Remove any duplicate greetings, introductions, or closings from middle slides\n7. FORMAT: Return each transcript as clean, standalone content WITHOUT any \"Slide X:\" prefixes or labels\n\nPlease return the refined transcripts as plain text content only, with each slide's content on its own. Do not include any slide numbers or labels in the output text.",  # noqa: E501
    "simplified_chinese": "请提供每个演示文稿的精炼版本，改进以下方面：\n1. 语调和术语的一致性\n2. 幻灯片之间的平滑过渡\n3. 专业而又有吸引力的语言\n4. 合适的长度（每张幻灯片50-100字）\n5. 关键位置：\n   - 第一页：包含有吸引力的开场（问候、主题介绍）\n   - 中间页：直接进入内容，使用像“接下来我们将探讨…”，“继续…”，“在此基础上…”等平滑过渡\n   - 最后一页：包含结尾总结和行动号召\n6. 删除：从中间页移除任何重复的问候、介绍或结尾\n7. 格式：只返回纯文本，每张幻灯片的内容单独呈现，不要包含“第X页：”之类的前缀或标签",  # noqa: E501
}


class TranscriptReviewer:
    """Reviewer for AI-generated presentation transcripts (OpenAI only)"""

    def __init__(self) -> None:
        """Initialize OpenAI reviewer"""
        # Force OpenAI usage; Qwen support removed for transcript review
        self.provider = "openai"
        self.model: str = config.openai_reviewer_model
        if not config.openai_api_key:
            logger.error("OPENAI_API_KEY not set; reviewer will fallback to originals")

    async def revise_transcripts(
        self, transcripts: list[dict[str, Any]], language: str = "english"
    ) -> list[dict[str, Any]]:
        """Revise transcripts to improve flow and consistency"""
        if not transcripts:
            return []

        # Build prompts in target language
        system_prompt = REVIEW_PROMPTS.get(language, REVIEW_PROMPTS["english"])
        instruction_prompt = INSTRUCTION_PROMPTS.get(
            language, INSTRUCTION_PROMPTS["english"]
        )

        # Concatenate transcripts for the model
        content = "\n\n".join([t.get("script", "") for t in transcripts])

        try:
            reviewed_content = chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": instruction_prompt + "\n\n" + content},
                ],
            )
        except Exception as e:
            logger.error(f"Transcript review failed: {e}")
            # If the model call fails, return original transcripts
            return transcripts

        # Simple splitting logic; real implementation may be more advanced
        paragraphs = [p.strip() for p in reviewed_content.split("\n\n") if p.strip()]
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
