"""Module for reviewing and refining presentation scripts."""

import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from ..utils.config import config

# Language-specific review prompts
REVIEW_PROMPTS = {
    "english": "Review and refine the following presentation scripts to ensure consistency in tone, style, and smooth transitions between slides. Make sure the language flows naturally and maintains a professional yet engaging presentation style.",  # noqa: E501
    "simplified_chinese": "审查并优化以下演示文稿脚本，确保语调、风格一致，幻灯片之间过渡自然。确保语言流畅自然，保持专业而引人入胜的演示风格。",  # noqa: E501
    "traditional_chinese": "審閱並優化以下簡報文稿腳本，確保語調、風格一致，簡報之間過渡自然。確保語言流暢自然，保持專業且引人入勝的簡報風格。",  # noqa: E501
    "japanese": "次のプレゼンテーションスクリプトをレビューし、トーン、スタイルの一貫性、スライド間のスムーズな移行を確保してください。言語が自然に流れ、専門的で魅力的なプレゼンテーションスタイルを維持していることを確認してください。",  # noqa: E501
    "korean": "다음 프레젠테이션 스크립트를 검토하여 톤, 스타일의 일관성과 슬라이드 간의 원활한 전환을 보장하세요. 언어가 자연스럽게 흐르고 전문적이면서도 매력적인 프레젠테이션 스타일을 유지하는지 확인하세요.",  # noqa: E501
    "thai": "ตรวจสอบและปรับปรุงสคริปต์การนำเสนอต่อไปนี้เพื่อให้มีความสอดคล้องกันในด้านน้ำเสียง สไตล์ และการเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์ ตรวจสอบให้แน่ใจว่าภาษาไหลไปอย่างเป็นธรรมชาติและรักษารูปแบบการนำเสนอที่เป็นมืออาชีพและน่าสนใจ",  # noqa: E501
}

# Language-specific instruction prompts
INSTRUCTION_PROMPTS = {
    "english": "Please provide refined versions of each script that improve:\n1. Consistency in tone and terminology\n2. Smooth transitions between slides\n3. Professional yet engaging language\n4. Appropriate length (50-100 words per slide)\n\nPlease return the refined scripts in the same format as the original, with each slide clearly labeled.",
    "simplified_chinese": "请提供每个脚本的精炼版本，改进以下方面：\n1. 语调和术语的一致性\n2. 幻灯片之间的平滑过渡\n3. 专业且引人入胜的语言\n4. 适当的长度（每张幻灯片50-100字）\n\n请以与原始格式相同的格式返回精炼后的脚本，每张幻灯片都清晰标注。",
    "traditional_chinese": "請提供每個腳本的精煉版本，改進以下方面：\n1. 語調和術語的一致性\n2. 簡報之間的平滑過渡\n3. 專業且引人入勝的語言\n4. 適當的長度（每張簡報50-100字）\n\n請以與原始格式相同的格式返回精煉後的腳本，每張簡報都清晰標註。",
    "japanese": "各スクリプトの洗練されたバージョンを提供してください。以下の点を改善してください：\n1. トーンと用語の一貫性\n2. スライド間のスムーズな移行\n3. 専門的で魅力的な言語\n4. 適切な長さ（スライドごとに50〜100語）\n\n元の形式と同じ形式で洗練されたスクリプトを返してください。各スライドを明確にラベル付けしてください。",
    "korean": "각 스크립트의 정제된 버전을 제공해 주세요. 다음 사항을 개선하세요：\n1. 톤과 용어의 일관성\n2. 슬라이드 간의 원활한 전환\n3. 전문적이고 매력적인 언어\n4. 적절한 길이(슬라이드당 50~100단어)\n\n원본 형식과 동일한 형식으로 정제된 스크립트를 반환해 주세요. 각 슬라이드를 명확하게 레이블링하세요。",
    "thai": "โปรดให้เวอร์ชันที่ปรับปรุงแล้วของแต่ละสคริปต์ซึ่งปรับปรุงด้านต่อไปนี้：\n1. ความสอดคล้องในน้ำเสียงและคำศัพท์\n2. การเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์\n3. ภาษาที่เป็นมืออาชีพและน่าสนใจ\n4. ความยาวที่เหมาะสม (50-100 คำต่อสไลด์)\n\nโปรดส่งคืนสคริปต์ที่ปรับปรุงแล้วในรูปแบบเดียวกับต้นฉบับ โดยติดป้ายกำกับแต่ละสไลด์อย่างชัดเจน"
}

# Language-specific system prompts
SYSTEM_PROMPTS = {
    "english": "You are a professional presentation editor. Your task is to review and refine presentation scripts for consistency, flow, and quality while preserving the core content and message of each slide.",  # noqa: E501
    "simplified_chinese": "您是一位专业的演示文稿编辑。您的任务是审查和优化演示文稿脚本的一致性、流畅性和质量，同时保持每张幻灯片的核心内容和信息。",  # noqa: E501
    "traditional_chinese": "您是一位專業的簡報文稿編輯。您的任務是審閱和優化簡報文稿腳本的一致性、流暢性和質量，同時保持每張簡報的核心內容和信息。",  # noqa: E501
    "japanese": "あなたはプロのプレゼンテーションエディターです。各スライドの核心的な内容とメッセージを維持しながら、プレゼンテーションスクリプトの一貫性、流れ、品質をレビューし、改善することがあなたの任務です。",  # noqa: E501
    "korean": "귀하는 전문 프레젠테이션 편집자입니다. 각 슬라이드의 핵심 내용과 메시지를 유지하면서 프레젠테이션 스크립트의 일관성, 흐름, 품질을 검토하고 개선하는 것이 귀하의 임무입니다.",  # noqa: E501
    "thai": "คุณเป็นผู้แก้ไขการนำเสนอระดับมืออาชีพ งานของคุณคือการตรวจสอบและปรับปรุงสคริปต์การนำเสนอให้มีความสอดคล้อง ไหลลื่น และมีคุณภาพ พร้อมทั้งรักษาเนื้อหาหลักและข้อความของแต่ละสไลด์ไว้",  # noqa: E501
}  # noqa: E501


load_dotenv()


class ScriptReviewer:
    """Review and refine presentation scripts for consistency and quality."""

    def __init__(self) -> None:
        """Initialize the script reviewer with OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def review_and_refine_scripts(
        self, scripts: list[dict[str, Any]], language: str = "english"
    ) -> list[dict[str, Any]]:
        """
        Review and refine scripts for consistency, flow, and quality.
        
        Args:
            scripts: List of script dictionaries with slide_number and script content
            language: Language of the scripts
            
        Returns:
            List of refined script dictionaries
        """
        # Prepare all scripts as a single context
        all_scripts_text = "\n\n".join(
            [
                f"Slide {i + 1}: {script_data.get('script', '')}"
                for i, script_data in enumerate(scripts)
            ]
        )

        try:
            model_name = os.getenv("SCRIPT_REVIEWER_MODEL", "gpt-4o")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["english"]),
                    },
                    {
                        "role": "user",
                        "content": f"""
                    {REVIEW_PROMPTS.get(language, REVIEW_PROMPTS["english"])}

                    {INSTRUCTION_PROMPTS.get(language, INSTRUCTION_PROMPTS["english"])}

                    Original scripts:
                    {all_scripts_text}
                    """,
                    },
                ],
                max_tokens=2000,
            )

            reviewed_content_response = response.choices[0].message.content
            reviewed_content = reviewed_content_response.strip() if reviewed_content_response else ""
            logger.info(f"Script review response received for language '{language}': {reviewed_content[:200]}...")
            
            # Debug: log the first few lines to see if parsing will work
            lines = reviewed_content.split("\n")
            if lines:
                logger.info(f"First few lines of reviewed content: {lines[:3]}")

            # Parse the reviewed content back into structured format
            # This is a simple parsing approach - in production, you might want
            # more robust parsing
            reviewed_scripts = []
            lines = reviewed_content.split("\n")

            current_slide: int | None = None
            current_script: list[str] = []

            for line in lines:
                if (
                    line.startswith("Slide ")
                    or line.startswith("幻灯片 ")
                    or line.startswith("スライド ")
                    or line.startswith("슬라이드 ")
                    or line.startswith("สไลด์ ")
                ):
                    # Save previous slide if exists
                    if current_slide is not None:
                        reviewed_scripts.append(
                            {
                                "slide_number": str(current_slide),
                                "script": "\n".join(current_script).strip(),
                            }
                        )

                    # Start new slide
                    # Extract slide number from various formats
                    import re

                    slide_match = re.search(
                        r"(?:Slide|幻灯片|スライド|슬라이드|สไลด์)\s+(\d+)", line
                    )
                    if slide_match:
                        current_slide = int(slide_match.group(1))
                        current_script = []
                    else:
                        current_slide = len(reviewed_scripts) + 1 if reviewed_scripts else 1
                        current_script = [line]
                elif current_slide is not None:
                    current_script.append(line)

            # Save last slide
            if current_slide is not None:
                reviewed_scripts.append(
                    {
                        "slide_number": str(current_slide),
                        "script": "\n".join(current_script).strip(),
                    }
                )

            # If parsing failed or resulted in empty scripts, fall back to
            # original scripts with minor improvements
            if not reviewed_scripts or all(
                not script.get("script", "") for script in reviewed_scripts
            ):
                # Simple fallback: just return original scripts
                logger.info(
                    "Script review parsing failed or resulted in empty scripts, "
                    "returning original scripts"
                )
                return scripts

            # Merge with original structure preserving slide numbers
            final_scripts = []
            for i, original_script in enumerate(scripts):
                if i < len(reviewed_scripts):
                    # Make sure we have content, if not fall back to original
                    reviewed_script_content = reviewed_scripts[i].get("script", "")
                    if reviewed_script_content:
                        final_scripts.append(
                            {
                                "slide_number": original_script.get("slide_number", i + 1),
                                "script": reviewed_script_content,
                            }
                        )
                    else:
                        # If reviewed script is empty, use original
                        final_scripts.append(
                            {
                                "slide_number": original_script.get("slide_number", i + 1),
                                "script": original_script.get("script", ""),
                            }
                        )
                else:
                    final_scripts.append(original_script)

            logger.info(f"Final reviewed scripts: {final_scripts}")
            return final_scripts

        except Exception as e:
            logger.error(f"Error reviewing scripts: {e}")
            # Return original scripts if review fails
            return scripts