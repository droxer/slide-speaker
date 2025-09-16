"""Module for reviewing and refining presentation transcripts.

This module uses OpenAI to review and improve generated presentation transcripts
for consistency, flow, and quality. It ensures appropriate formatting for AI avatar delivery
and handles proper positioning of opening/closing statements.
"""

from typing import Any

from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

from .utils import sanitize_transcript

# Language-specific review prompts
REVIEW_PROMPTS = {
    "english": (
        "Review and refine the following presentation transcripts to ensure "
        "consistency in tone, style, and smooth transitions. "
        "CRITICAL: Remove mentions of slide visuals (layout, colors, icons, "
        "animations, 'on the slide', 'as shown here'). "
        "Focus on explaining the content itself. Ensure opening appears only "
        "on the first slide and closing only on the last."
    ),  # noqa: E501
    "simplified_chinese": "审查并优化以下演示文稿，确保语调、风格一致，幻灯片之间过渡自然。避免提及任何可视化界面元素（布局、颜色、图标、动画、‘在幻灯片上’等），专注于内容本身。关键要求：开场白只出现在首页，结尾语只出现在末页。",  # noqa: E501
    "traditional_chinese": "審閱並優化以下簡報文稿，確保語調、風格一致，簡報之間過渡自然。避免提及任何視覺化介面元素（版面、顏色、圖示、動畫、‘在投影片上’等），專注於內容本身。關鍵要求：開場白僅在首頁，結語僅在末頁。",  # noqa: E501
    "japanese": "次のトランスクリプトをレビューし、トーンと流れの一貫性を高めてください。UI/視覚要素（レイアウト、色、アイコン、アニメーション、「スライド上で」等）への言及は避け、内容の説明に集中してください。冒頭は最初のスライドのみ、締めは最後のみ。",  # noqa: E501
    "korean": "다음 트랜스크립트를 검토하여 일관성과 흐름을 개선하세요. UI/시각 요소(레이아웃, 색상, 아이콘, 애니메이션, ‘슬라이드에서’ 등)에 대한 언급을 피하고 내용 설명에 집중하세요. 도입은 첫 슬라이드, 마무리는 마지막 슬라이드에만 포함합니다.",  # noqa: E501
    "thai": "ตรวจสอบและปรับปรุงสคริปต์โดยหลีกเลี่ยงการกล่าวถึงองค์ประกอบ UI/ภาพ (เลย์เอาต์ สี ไอคอน แอนิเมชัน ‘บนสไลด์’ ฯลฯ) ให้เน้นอธิบายเนื้อหาเท่านั้น ข้อความเปิดเฉพาะสไลด์แรก และปิดเฉพาะสไลด์สุดท้าย",  # noqa: E501
}

# Language-specific instruction prompts
INSTRUCTION_PROMPTS = {
    "english": (
        "Please provide refined versions that: (1) keep tone/terminology consistent, (2) use smooth transitions, (3) are engaging yet precise, "  # noqa: E501
        "(4) target 80–140 words per slide, and (5) eliminate any references to visual UI (layout, colors, icons, animations, 'on the slide').\n\n"  # noqa: E501
        "CRITICAL POSITIONING:\n- Slide 1: opening only\n- Slides 2..N-1: direct content, smooth transitions\n- Slide N: closing summary and call-to-action\n\n"  # noqa: E501
        "FORMAT: Return plain text for each slide’s content only, no labels or numbering."  # noqa: E501
    ),  # noqa: E501
    "simplified_chinese": "请提供每页精炼版本：保持术语一致、过渡顺滑、语言专业；每页目标80–140字；禁止提及UI/视觉元素（布局、颜色、图标、动画、“在幻灯片上”等），只解释内容本身。开场仅在第一页，结语仅在最后一页。格式：只返回每页纯文本，无编号标签。",  # noqa: E501
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
