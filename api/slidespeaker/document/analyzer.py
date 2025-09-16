"""
PDF content analyzer for SlideSpeaker.

This module provides deep analysis of PDF content and segmentation into chapters.
It uses AI to understand the content structure and create meaningful segments
for presentation generation.
"""

from typing import Any

from loguru import logger
from PyPDF2 import PdfReader

from slidespeaker.configs.config import config
from slidespeaker.llm import chat_completion

# Import the shared transcript generator
from slidespeaker.transcript import TranscriptGenerator

# Language-specific prompts for PDF analysis
LANGUAGE_PROMPTS = {
    "english": {
        "system": """You are an expert content analyzer and presentation designer.
Your task is to carefully analyze the entire document content and segment it into
logical chapters for presentation purposes. Focus on identifying key themes,
concepts, and logical breakpoints in the content to create meaningful, coherent chapters.""",
        "prompt": """
                Carefully analyze the following document titled "{doc_title}" and segment it into
                less than {max_num_of_segments} logical chapters that would work well for a presentation.
                Your analysis should cover
        the entire document content to ensure comprehensive coverage.

        For each chapter, provide:
        1. A clear, concise title (3-8 words) that captures the main theme - NO subtitles or colons
        2. 3-5 key points as bullet items that highlight the most important concepts
        3. A presentation script (80-150 words) that explains the key points in an
           engaging, educational way suitable for a presentation

        IMPORTANT: Chapter titles should be clean and concise - DO NOT include subtitles,
        colons, or additional descriptive text in the title itself.

        Examples of GOOD titles:
        - "Introduction to Machine Learning"
        - "Data Analysis Techniques"
        - "Project Implementation"

        Examples of BAD titles:
        - "Chapter 1: Introduction to Machine Learning"
        - "Data Analysis Techniques: Methods and Applications"
        - "Project Implementation - Steps and Best Practices"

        Document content:
        {full_text}

        Respond in JSON format with the following structure:
        {{
            "chapters": [
                {{
                    "title": "Clean Chapter Title",
                    "description": "Brief description of chapter content",
                    "key_points": [
                        "Key point 1",
                        "Key point 2",
                        "Key point 3"
                    ],
                    "script": "Comprehensive presentation script for this chapter that covers "
                    "the key points in an engaging way"
                }}
            ]
        }}
        """,
    },
    "simplified_chinese": {
        "system": """您是一位专业的文档内容分析师和演示文稿设计师。您的任务是仔细分析整个文档内容
并将其分割成适合演示的逻辑章节。重点是识别关键主题、概念和内容中的逻辑断点，
以创建有意义、连贯的章节。""",
        "prompt": """
        请仔细分析以下名为"{doc_title}"的文档，并将其分割成不超过{max_num_of_segments}个适合演示的逻辑章节。您的分析应涵盖整个文档内容以确保全面覆盖。

        每个章节需要提供：
        1. 清晰简洁的标题（3-8个字）概括主要主题 - 不要包含副标题或冒号
        2. 3-5个要点条目，突出最重要的概念
        3. 演示文稿脚本（80-150个字）以引人入胜、教育性的方式解释要点，适合演示使用

        重要提示：章节标题应简洁明了 - 标题本身不要包含副标题、冒号或其他描述性文字。

        良好标题示例：
        - "机器学习简介"
        - "数据分析技术"
        - "项目实施"

        不良标题示例：
        - "第1章：机器学习简介"
        - "数据分析技术：方法与应用"
        - "项目实施 - 步骤与最佳实践"

        文档内容：
        {full_text}

        请以以下JSON格式回复：
        {{
            "chapters": [
                {{
                    "title": "简洁的章节标题",
                    "description": "章节内容简述",
                    "key_points": [
                        "要点1",
                        "要点2",
                        "要点3"
                    ],
                    "script": "本章节的综合性演示文稿脚本，以引人入胜的方式涵盖要点"
                }}
            ]
        }}
        """,
    },
    "traditional_chinese": {
        "system": """您是一位專業的文件內容分析師和簡報設計師。您的任務是仔細分析整個文件內容
並將其分割成適合簡報的邏輯章節。重點是識別關鍵主題、概念和內容中的邏輯斷點，
以創建有意義、連貫的章節。""",
        "prompt": """
        請仔細分析以下名為"{doc_title}"的文件，並將其分割成不超過{max_num_of_segments}個適合簡報的邏輯章節。您的分析應涵蓋整個文件內容以確保全面覆蓋。

        每個章節需要提供：
        1. 清晰簡潔的標題（3-8個字）概括主要主題 - 不要包含副標題或冒號
        2. 3-5個要點條目，突出最重要的概念
        3. 簡報腳本（80-150個字）以引人入勝、教育性的方式解釋要點，適合簡報使用

        重要提示：章節標題應簡潔明瞭 - 標題本身不要包含副標題、冒號或其他描述性文字。

        良好標題示例：
        - "機器學習簡介"
        - "數據分析技術"
        - "項目實施"

        不良標題示例：
        - "第1章：機器學習簡介"
        - "數據分析技術：方法與應用"
        - "項目實施 - 步驟與最佳實踐"

        文件內容：
        {full_text}

        請以以下JSON格式回覆：
        {{
            "chapters": [
                {{
                    "title": "簡潔的章節標題",
                    "description": "章節內容簡述",
                    "key_points": [
                        "要點1",
                        "要點2",
                        "要點3"
                    ],
                    "script": "本章節的綜合性簡報腳本，以引人入勝的方式涵蓋要點"
                }}
            ]
        }}
        """,
    },
}

# Default chapters for fallback
DEFAULT_CHAPTERS = {
    "english": [
        {
            "title": "Introduction",
            "description": "Overview of the document content and main topics covered.",
            "key_points": [
                "Document purpose and scope",
                "Main topics to be covered",
                "Expected outcomes",
            ],
        },
        {
            "title": "Core Concepts",
            "description": "Detailed analysis of the core document content.",
            "key_points": [
                "Key concepts and principles",
                "Important findings and data",
                "Practical applications",
            ],
        },
        {
            "title": "Conclusion",
            "description": "Summary of key takeaways and final thoughts.",
            "key_points": [
                "Main insights and conclusions",
                "Recommendations for action",
                "Future considerations",
            ],
        },
    ],
    "simplified_chinese": [
        {
            "title": "简介",
            "description": "文档内容概述和涵盖的主要主题。",
            "key_points": ["文档目的和范围", "涵盖的主要主题", "预期成果"],
        },
        {
            "title": "核心概念",
            "description": "文档核心内容的详细分析。",
            "key_points": ["关键概念和原理", "重要发现和数据", "实际应用"],
        },
        {
            "title": "总结",
            "description": "关键要点总结和最终思考。",
            "key_points": ["主要见解和结论", "行动建议", "未来考虑"],
        },
    ],
    "traditional_chinese": [
        {
            "title": "簡介",
            "description": "文件內容概述和涵蓋的主要主題。",
            "key_points": ["文件目的和範圍", "涵蓋的主要主題", "預期成果"],
        },
        {
            "title": "核心概念",
            "description": "文件核心內容的詳細分析。",
            "key_points": ["關鍵概念和原理", "重要發現和數據", "實際應用"],
        },
        {
            "title": "總結",
            "description": "關鍵要點總結和最終思考。",
            "key_points": ["主要見解和結論", "行動建議", "未來考慮"],
        },
    ],
}


class PDFAnalyzer:
    """Analyzer for PDF content that segments content into chapters"""

    def __init__(self) -> None:
        """Initialize the PDF analyzer with configured provider"""
        # Use OpenAI exclusively for PDF analysis in this module
        self.model: str = config.pdf_analyzer_model
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.model = config.pdf_analyzer_model
        self.transcript_generator = TranscriptGenerator()

    async def analyze_and_segment(
        self, file_path: str, language: str = "english", max_num_of_segments: int = 10
    ) -> list[dict[str, Any]]:
        """
        Analyze PDF content and segment into chapters.

        This method reads the entire PDF content, understands the main topics,
        and segments the content into logical chapters with titles, descriptions, and scripts.

        Args:
            file_path: Path to the PDF file
            language: Target language for chapter content
            max_num_of_segments: Maximum number of segments/chapters to create (default: 10)

        Returns:
            List of chapters with title, description, and script for each
        """
        # Read the entire PDF content
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"

        # Clean and prepare the text
        full_text = full_text.strip()

        if not full_text:
            # Log more details about the PDF for debugging
            page_count = len(pdf_reader.pages) if pdf_reader else 0
            logger.warning(
                f"PDF file appears to be empty or unreadable. Pages: {page_count}, File: {file_path}"
            )
            raise ValueError(
                f"PDF file appears to be empty or unreadable. Pages: {page_count}"
            )

        # Extract document title from first few lines
        lines = full_text.split("\n")
        doc_title = ""
        for line in lines[:5]:  # Check first 5 lines for title
            line = line.strip()
            if line and len(line) > 10 and len(line) < 100:  # Reasonable title length
                doc_title = line
                break

        if not doc_title:
            doc_title = "Document Content"

        # Use AI to analyze content and create chapters
        chapters = await self._generate_chapters(
            full_text, doc_title, language, max_num_of_segments
        )
        return chapters

    async def _generate_chapters(
        self,
        full_text: str,
        doc_title: str,
        language: str,
        max_num_of_segments: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Use AI to segment PDF content into chapters.

        Args:
            full_text: Complete text content of the PDF
            doc_title: Extracted title of the document
            language: Target language for chapter content
            max_num_of_segments: Maximum number of segments/chapters to create (default: 5)

        Returns:
            List of chapters with title, description, key_points, and script
        """
        # Use the global LANGUAGE_PROMPTS
        prompts = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["english"])

        try:
            formatted_prompt = prompts["prompt"].format(
                doc_title=doc_title,
                full_text=full_text,
                max_num_of_segments=max_num_of_segments,
            )

            content = chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": formatted_prompt},
                ],
            )
            # Parse the response
            if content:
                import json

                # Extract JSON from response
                start = content.find("{")
                end = content.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = content[start:end]
                    result = json.loads(json_str)
                    base_chapters = result.get("chapters", [])

                    # Process chapters to ensure they have all required fields
                    chapters_with_scripts = []
                    for chapter in base_chapters:
                        # Ensure key_points exists
                        if "key_points" not in chapter:
                            chapter["key_points"] = []

                        # If the model already provided a script, keep it as-is
                        provided_script = str(chapter.get("script", "") or "").strip()
                        if provided_script:
                            chapter["script"] = provided_script
                        else:
                            # Otherwise, generate a comprehensive script using the shared script generator
                            # Combine title, description, and key points for comprehensive script generation
                            content_for_script = f"""Chapter Topic: {chapter.get("title", "")}
Chapter Description: {chapter.get("description", "")}
"""
                            if chapter.get("key_points"):
                                key_points_text = "\n".join(
                                    [f"- {point}" for point in chapter["key_points"]]
                                )
                                content_for_script += f"""

Key Points to Cover in Detail:
{key_points_text}
"""
                            content_for_script += """
Please provide a detailed, comprehensive explanation of this chapter topic,
thoroughly covering all key points with relevant examples where appropriate.
"""

                            script = (
                                await self.transcript_generator.generate_transcript(
                                    content_for_script, language=language
                                )
                            )
                            chapter["script"] = script

                        chapters_with_scripts.append(chapter)

                    return chapters_with_scripts

            # Fallback if parsing fails
            return await self._create_default_chapters(
                full_text, language, max_num_of_segments
            )

        except Exception as e:
            print(f"Error generating chapters: {e}")
            # Fallback to default chapters
            return await self._create_default_chapters(
                full_text, language, max_num_of_segments
            )

    async def _create_default_chapters(
        self, full_text: str, language: str, max_num_of_segments: int = 5
    ) -> list[dict[str, Any]]:
        """
        Create default chapters if AI analysis fails.

        Args:
            full_text: Complete text content of the PDF
            language: Target language for chapter content
            max_num_of_segments: Maximum number of segments/chapters to create (default: 5)

        Returns:
            List of default chapters with title, description, key_points, and script
        """
        # Extract first few lines as title

        # Use the global DEFAULT_CHAPTERS
        base_chapters = DEFAULT_CHAPTERS.get(language, DEFAULT_CHAPTERS["english"])

        # Limit the number of chapters to max_num_of_segments
        if len(base_chapters) > max_num_of_segments:
            base_chapters = base_chapters[:max_num_of_segments]
        elif len(base_chapters) < max_num_of_segments:
            # If we need more chapters, duplicate the existing ones
            while len(base_chapters) < max_num_of_segments:
                for chapter in DEFAULT_CHAPTERS.get(
                    language, DEFAULT_CHAPTERS["english"]
                ):
                    if len(base_chapters) >= max_num_of_segments:
                        break
                    # Create a copy with modified title to differentiate
                    new_chapter = chapter.copy()
                    new_chapter["title"] = (
                        f"{chapter['title']} (Part {len(base_chapters) + 1})"
                    )
                    base_chapters.append(new_chapter)

        # Generate comprehensive scripts using the shared script generator
        # to ensure detailed explanations of the topic and key points
        chapters_with_scripts = []
        for chapter in base_chapters:
            # Combine title, description, and key points for comprehensive script generation
            content_for_script = f"""Chapter Topic: {chapter["title"]}
Chapter Description: {chapter["description"]}
"""
            if chapter.get("key_points"):
                key_points_text = "\n".join(
                    [f"- {point}" for point in chapter["key_points"]]
                )
                content_for_script += f"""

Key Points to Cover in Detail:
{key_points_text}
"""
            content_for_script += """
Please provide a detailed, comprehensive explanation of this chapter topic,
thoroughly covering all key points with relevant examples where appropriate.
"""

            script = await self.transcript_generator.generate_transcript(
                content_for_script, language=language
            )

            # Add script to chapter
            chapter_with_script = chapter.copy()
            chapter_with_script["script"] = script
            chapters_with_scripts.append(chapter_with_script)

        return chapters_with_scripts
