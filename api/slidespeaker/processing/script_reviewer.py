"""Module for reviewing and refining presentation scripts."""

import os
from typing import Any

from loguru import logger
from openai import OpenAI

# Language-specific review prompts
REVIEW_PROMPTS = {
    "english": "Review and refine the following presentation scripts to ensure consistency in tone, style, and smooth transitions between slides. CRITICAL: Ensure opening statements (greetings, introductions) appear ONLY on the first slide, and closing statements (summaries, thank-yous, calls-to-action) appear ONLY on the last slide. Middle slides should start directly with content and use smooth transitions without greetings or closings.",  # noqa: E501
    "simplified_chinese": "审查并优化以下演示文稿脚本，确保语调、风格一致，幻灯片之间过渡自然。关键要求：开场白（问候、介绍）只出现在第一张幻灯片，结尾语（总结、感谢、行动号召）只出现在最后一张幻灯片。中间幻灯片应直接进入内容，使用平滑过渡，避免重复问候或结尾。",  # noqa: E501
    "traditional_chinese": "審閱並優化以下簡報文稿腳本，確保語調、風格一致，簡報之間過渡自然。關鍵要求：開場白（問候、介紹）只出現在第一張簡報，結尾語（總結、感謝、行動號召）只出現在最後一張簡報。中間簡報應直接進入內容，使用平滑過渡，避免重複問候或結尾。",  # noqa: E501
    "japanese": "次のプレゼンテーションスクリプトをレビューし、トーン、スタイルの一貫性、スライド間のスムーズな移行を確保してください。重要：オープニングステートメント（挨拶、紹介）は最初のスライドにのみ、クロージングステートメント（要約、感謝、アクションコール）は最後のスライドにのみ表示してください。中間スライドは直接コンテンツから始め、挨拶や締めくくりを避けてスムーズに移行してください。",  # noqa: E501
    "korean": "다음 프레젠테이션 스크립트를 검토하여 톤, 스타일의 일관성과 슬라이드 간의 원활한 전환을 보장하세요. 중요: 오프닝 문장(인사, 소개)은 첫 번째 슬라이드에만, 클로징 문장(요약, 감사, 행동 촉구)은 마지막 슬라이드에만 표시하세요. 중간 슬라이드는 직접 콘텐츠로 시작하고, 인사나 마무리를 피하면서 부드럽게 전환하세요.",  # noqa: E501
    "thai": "ตรวจสอบและปรับปรุงสคริปต์การนำเสนอต่อไปนี้เพื่อให้มีความสอดคล้องกันในด้านน้ำเสียง สไตล์ และการเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์ สิ่งสำคัญ: ให้ข้อความเปิด (คำทักทาย การแนะนำ) ปรากฏเฉพาะในสไลด์แรกเท่านั้น และข้อความปิด (สรุป ขอบคุณ การเรียกร้องให้ดำเนินการ) ปรากฏเฉพาะในสไลด์สุดท้ายเท่านั้น สไลด์กลางควรเริ่มต้นโดยตรงด้วยเนื้อหาและใช้การเปลี่ยนผ่านที่ราบรื่นโดยไม่มีคำทักทายหรือการปิดท้าย",  # noqa: E501
}

# Language-specific instruction prompts
INSTRUCTION_PROMPTS = {
    "english": "Please provide refined versions of each script that improve:\n1. Consistency in tone and terminology\n2. Smooth transitions between slides\n3. Professional yet engaging language\n4. Appropriate length (50-100 words per slide)\n5. CRITICAL POSITIONING:\n   - Slide 1 (First): Include engaging opening (greeting, topic introduction)\n   - Slides 2 to N-1 (Middle): Start directly with content, use smooth transitions like 'Next, we'll explore...', 'Moving on to...', 'Building on this...'\n   - Slide N (Last): Include closing summary and call-to-action\n6. ELIMINATE: Remove any duplicate greetings, introductions, or closings from middle slides\n7. FORMAT: Return each script as clean, standalone content WITHOUT any \"Slide X:\" prefixes or labels\n\nPlease return the refined scripts as plain text content only, with each slide's content on its own. Do not include any slide numbers or labels in the output text.",  # noqa: E501
    "simplified_chinese": '请提供每个脚本的精炼版本，改进以下方面：\n1. 语调和术语的一致性\n2. 幻灯片之间的平滑过渡\n3. 专业且引人入胜的语言\n4. 适当的长度（每张幻灯片50-100字）\n5. 关键定位：\n   - 第1张幻灯片：包含引人入胜的开场（问候、主题介绍）\n   - 第2到N-1张幻灯片：直接进入内容，使用平滑过渡如"接下来我们将探讨..."、"继续来看..."、"在此基础上..."\n   - 第N张幻灯片：包含总结和行动号召\n6. 消除重复：删除中间幻灯片的重复问候、介绍或结尾\n7. 格式：返回每个脚本为干净的独立内容，不包含任何"幻灯片 X："前缀或标签\n\n请将精炼后的脚本作为纯文本内容返回，每个幻灯片的内容独立呈现。不要在输出文本中包含任何幻灯片编号或标签。',  # noqa: E501
    "traditional_chinese": '請提供每個腳本的精煉版本，改進以下方面：\n1. 語調和術語的一致性\n2. 簡報之間的平滑過渡\n3. 專業且引人入勝的語言\n4. 適當的長度（每張簡報50-100字）\n5. 關鍵定位：\n   - 第1張簡報：包含引人入勝的開場（問候、主題介紹）\n   - 第2到N-1張簡報：直接進入內容，使用平滑過渡如"接下來我們將探討..."、"繼續來看..."、"在此基礎上..."\n   - 第N張簡報：包含總結和行動號召\n6. 消除重複：刪除中間簡報的重複問候、介紹或結尾\n7. 格式：返回每個腳本為乾淨的獨立內容，不包含任何"簡報 X："前綴或標籤\n\n請將精煉後的腳本作為純文本內容返回，每個簡報的內容獨立呈現。不要在輸出文本中包含任何簡報編號或標籤。',  # noqa: E501
    "japanese": '各スクリプトの洗練されたバージョンを提供してください。以下の点を改善してください：\n1. トーンと用語の一貫性\n2. スライド間のスムーズな移行\n3. 専門的で魅力的な言語\n4. 適切な長さ（スライドごとに50〜100語）\n5. 重要な配置：\n   - スライド1：魅力的なオープニング（挨拶、トピック紹介）を含む\n   - スライド2〜N-1：直接コンテンツから始め、スムーズな移行を使用\n   - スライドN：クロージングサマリーとアクションコールを含む\n6. 重複排除：中間スライドの重複挨拶、紹介、締めくくりを削除\n7. フォーマット：各スクリプトをクリーンなスタンドアロンコンテンツとして返し、"スライド X："のプレフィックスやラベルを含まない\n\n洗練されたスクリプトをプレーンテキストコンテンツとして返してください。各スライドのコンテンツを個別に提示し、出力テキストにスライド番号やラベルを含めないでください。',  # noqa: E501
    "korean": "각 스크립트의 정제된 버전을 제공해 주세요. 다음 사항을 개선하세요：\n1. 톤과 용어의 일관성\n2. 슬라이드 간의 원활한 전환\n3. 전문적이고 매력적인 언어\n4. 적절한 길이(슬라이드당 50~100단어)\n5. 핵심 위치 지정：\n   - 슬라이드 1: 매력적인 오프닝(인사말, 주제 소개) 포함\n   - 슬라이드 2~N-1: 직접 콘텐츠로 시작, '다음으로 살펴 보겠습니다...', '이어서...', '이를 바탕으로...' 등의 원활한 전환 사용\n   - 슬라이드 N: 마무리 요약과 행동 촉구 포함\n6. 중복 제거: 중간 슬라이드의 중복 인사말, 소개, 마무리 제거\n7. 형식: 각 스크립트를 깨끗한 독립 콘텐츠로 반환하고, \"슬라이드 X:\" 접두사나 라벨을 포함하지 않음\n\n정제된 스크립트를 일반 텍스트 콘텐츠로 반환해 주세요. 각 슬라이드의 콘텐츠를 개별적으로 제공하고, 출력 텍스트에 슬라이드 번호나 라벨을 포함하지 마세요。",  # noqa: E501
    "thai": "โปรดให้เวอร์ชันที่ปรับปรุงแล้วของแต่ละสคริปต์ซึ่งปรับปรุงด้านต่อไปนี้：\n1. ความสอดคล้องในน้ำเสียงและคำศัพท์\n2. การเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์\n3. ภาษาที่เป็นมืออาชีพและน่าสนใจ\n4. ความยาวที่เหมาะสม (50-100 คำต่อสไลด์)\n5. การกำหนดตำแหน่งสำคัญ：\n   - สไลด์ที่ 1: รวมการเปิดที่น่าสนใจ (การทักทาย การแนะนำหัวข้อ)\n   - สไลด์ที่ 2 ถึง N-1: เริ่มต้นโดยตรงด้วยเนื้อหา ใช้การเปลี่ยนผ่านที่ราบรื่นเช่น 'ต่อไปเราจะสำรวจ...' 'ไปยัง...' 'จากจุดนี้...'\n   - สไลด์ที่ N: รวมสรุปการปิดและการเรียกร้องให้ดำเนินการ\n6. การกำจัดข้อความซ้ำ: ลบการทักทาย การแนะนำ หรือการปิดท้ายที่ซ้ำกันออกจากสไลด์กลาง\n7. รูปแบบ: ส่งคืนแต่ละสคริปต์เป็นเนื้อหาสแตนด์อโลนที่สะอาดโดยไม่มีคำนำหน้าหรือป้ายกำกับ \"สไลด์ X:\"\n\nโปรดส่งคืนสคริปต์ที่ปรับปรุงแล้วเป็นเนื้อหาข้อความล้วน โดยไม่ต้องระบุหมายเลขสไลด์หรือป้ายกำกับใดๆ ในเนื้อหาที่ส่งคืน",  # noqa: E501
}

# Language-specific system prompts
SYSTEM_PROMPTS = {
    "english": "You are a professional presentation editor. Your task is to review and refine presentation scripts for consistency, flow, and quality while preserving the core content and message of each slide.",  # noqa: E501
    "simplified_chinese": "您是一位专业的演示文稿编辑。您的任务是审查和优化演示文稿脚本的一致性、流畅性和质量，同时保持每张幻灯片的核心内容和信息。",  # noqa: E501
    "traditional_chinese": "您是一位專業的簡報文稿編輯。您的任務是審閱和優化簡報文稿腳本的一致性、流暢性和質量，同時保持每張簡報的核心內容和信息。",  # noqa: E501
    "japanese": "あなたはプロのプレゼンテーションエディターです。各スライドの核心的な内容とメッセージを維持しながら、プレゼンテーションスクリプトの一貫性、流れ、品質をレビューし、改善することがあなたの任務です。",  # noqa: E501
    "korean": "귀하는 전문 프레젠테이션 편집자입니다. 각 슬라이드의 핵심 내용과 메시지를 유지하면서 프레젠테이션 스크립트의 일관성, 흐름, 품질을 검토하고 개선하는 것이 귀하의 임무입니다.",  # noqa: E501
    "thai": "คุณเป็นผู้แก้ไขการนำเสนอระดับมืออาชีพ งานของคุณคือการตรวจสอบและปรับปรุงสคริปต์การนำเสนอให้มีความสอดคล้อง ไหลลื่น และมีคุณภาพ พร้อมทั้งรักษาเนื้อหาหลักและข้อความของแต่ละสไลด์ไว้",  # noqa: E501
}


class ScriptReviewer:
    def __init__(self) -> None:
        """Initialize the script reviewer with OpenAI client."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def revise_scripts(
        self, scripts: list[dict[str, Any]], language: str = "english"
    ) -> list[dict[str, Any]]:
        all_scripts_text = "\n\n".join(
            [
                f"Slide {i + 1}: {script_data.get('script', '')}"
                for i, script_data in enumerate(scripts)
            ]
        )

        logger.info(f"All scripts text: {all_scripts_text}")

        try:
            model_name = os.getenv("SCRIPT_REVIEWER_MODEL", "gpt-4o")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPTS.get(
                            language, SYSTEM_PROMPTS["english"]
                        ),
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
            )

            reviewed_content_response = response.choices[0].message.content
            reviewed_content = (
                reviewed_content_response.strip() if reviewed_content_response else ""
            )
            logger.info(
                f"Script review response received for language '{language}': {reviewed_content[:200]}..."
            )

            # Debug: log the first few lines to see if parsing will work
            lines = reviewed_content.split("\n")
            if lines:
                logger.info(f"First few lines of reviewed content: {lines[:3]}")

            # Parse the reviewed content back into structured format
            reviewed_scripts = []

            # Since the AI now returns clean content without slide labels,
            # we need to split the content into the correct number of slides
            num_slides = len(scripts)

            if not reviewed_content.strip():
                # If no content returned, fall back to original scripts
                return scripts

            # Clean the content
            reviewed_content = reviewed_content.strip()

            # Split into paragraphs by double newlines
            paragraphs = [
                p.strip() for p in reviewed_content.split("\n\n") if p.strip()
            ]

            if len(paragraphs) == num_slides:
                # Perfect match - each paragraph is a slide
                for i, paragraph in enumerate(paragraphs):
                    reviewed_scripts.append(
                        {"slide_number": str(i + 1), "script": paragraph.strip()}
                    )
            elif len(paragraphs) > 0:
                # Try to distribute paragraphs across slides
                slides = []
                if len(paragraphs) == 1:
                    # Single paragraph - split into sentences
                    sentences = [
                        s.strip() for s in paragraphs[0].split(". ") if s.strip()
                    ]
                    sentences = [
                        s + "." if not s.endswith(".") else s for s in sentences
                    ]

                    # Distribute sentences across slides
                    sentences_per_slide = max(1, len(sentences) // num_slides)
                    for i in range(num_slides):
                        start_idx = i * sentences_per_slide
                        if i == num_slides - 1:
                            # Last slide gets remaining sentences
                            slide_sentences = sentences[start_idx:]
                        else:
                            slide_sentences = sentences[
                                start_idx : start_idx + sentences_per_slide
                            ]

                        if slide_sentences:
                            slides.append(" ".join(slide_sentences))
                        else:
                            # Fallback to original if no sentences
                            slides.append(scripts[i].get("script", ""))
                else:
                    # Multiple paragraphs - distribute across slides
                    # Map paragraphs to slides proportionally
                    for i in range(num_slides):
                        start_idx = int(i * len(paragraphs) / num_slides)
                        end_idx = int((i + 1) * len(paragraphs) / num_slides)

                        if start_idx < len(paragraphs):
                            slide_paragraphs = paragraphs[start_idx:end_idx]
                            slide_content = " ".join(slide_paragraphs)
                            slides.append(slide_content)
                        else:
                            slides.append(scripts[i].get("script", ""))

                # Build reviewed scripts
                for i, content in enumerate(slides):
                    if content.strip():
                        reviewed_scripts.append(
                            {"slide_number": str(i + 1), "script": content.strip()}
                        )
                    else:
                        # Fallback to original if empty
                        reviewed_scripts.append(
                            {
                                "slide_number": str(i + 1),
                                "script": scripts[i].get("script", ""),
                            }
                        )
            else:
                # Single block of text - split by character count
                total_chars = len(reviewed_content)
                chars_per_slide = total_chars // num_slides

                for i in range(num_slides):
                    if i == num_slides - 1:
                        # Last slide gets remaining content
                        slide_content = reviewed_content[i * chars_per_slide :].strip()
                    else:
                        slide_content = reviewed_content[
                            i * chars_per_slide : (i + 1) * chars_per_slide
                        ].strip()

                    # Clean up the split
                    slide_content = slide_content.strip()
                    if not slide_content:
                        slide_content = scripts[i].get("script", "")

                    reviewed_scripts.append(
                        {"slide_number": str(i + 1), "script": slide_content}
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
            logger.info(f"Successfully parsed {len(reviewed_scripts)} reviewed scripts")

            # Ensure we have the right number of scripts
            for i, original_script in enumerate(scripts):
                if i < len(reviewed_scripts):
                    reviewed_script_content = reviewed_scripts[i].get("script", "")
                    if reviewed_script_content:
                        final_scripts.append(
                            {
                                "slide_number": original_script.get(
                                    "slide_number", i + 1
                                ),
                                "script": reviewed_script_content,
                            }
                        )
                        logger.info(f"Using reviewed script for slide {i + 1}")
                    else:
                        # If reviewed script is empty, use original
                        final_scripts.append(
                            {
                                "slide_number": original_script.get(
                                    "slide_number", i + 1
                                ),
                                "script": original_script.get("script", ""),
                            }
                        )
                        logger.warning(
                            f"Using original script for slide {i + 1} (empty review)"
                        )
                else:
                    # Handle case where we have more original scripts than reviewed ones
                    final_scripts.append(original_script)
                    logger.warning(
                        f"Using original script for slide {i + 1} (no review)"
                    )

            logger.info(f"Final reviewed scripts: {final_scripts}")
            return final_scripts

        except Exception as e:
            logger.error(f"Error reviewing scripts: {e}")
            # Return original scripts if review fails
            return scripts
