"""
PDF content analyzer for SlideSpeaker.

This module provides deep analysis of PDF content and segmentation into chapters.
It uses AI to understand the content structure and create meaningful segments
for presentation generation.
"""

import os
from typing import Any

from loguru import logger
from openai import OpenAI
from PyPDF2 import PdfReader

# Import the shared script generator
from slidespeaker.processing.script_generator import ScriptGenerator

# Language-specific prompts for PDF analysis
LANGUAGE_PROMPTS = {
    "english": {
        "system": "You are an expert content analyzer and presentation designer. "
        + "Your task is to carefully analyze the entire document content and segment it into logical "
        + "chapters for presentation purposes. Focus on identifying key themes, concepts, and logical "
        + "breakpoints in the content to create meaningful, coherent chapters.",
        "prompt": """
                Carefully analyze the following document titled "{doc_title}" and segment it into 3-7
        logical chapters that would work well for a presentation. Your analysis should cover
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
        "system": "您是一位专业的文档内容分析师和演示文稿设计师。您的任务是仔细分析整个文档内容并将其分割成适合演示的逻辑章节。重点是识别关键主题、概念和内容中的逻辑断点，以创建有意义、连贯的章节。",  # noqa: E501
        "prompt": """
        请仔细分析以下名为"{doc_title}"的文档，并将其分割成3-7个适合演示的逻辑章节。您的分析应涵盖整个文档内容以确保全面覆盖。

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
        "system": "您是一位專業的文件內容分析師和簡報設計師。您的任務是仔細分析整個文件內容並將其分割成適合簡報的邏輯章節。重點是識別關鍵主題、概念和內容中的邏輯斷點，以創建有意義、連貫的章節。",  # noqa: E501
        "prompt": """
        請仔細分析以下名為"{doc_title}"的文件，並將其分割成3-7個適合簡報的邏輯章節。您的分析應涵蓋整個文件內容以確保全面覆蓋。

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
        """Initialize the PDF analyzer with OpenAI client and script generator"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model: str = os.getenv("PDF_ANALYZER_MODEL", "gpt-4o-mini")
        self.script_generator = ScriptGenerator()

    async def analyze_and_segment_pdf(
        self, file_path: str, language: str = "english"
    ) -> list[dict[str, Any]]:
        """
        Analyze PDF content and segment into chapters.

        This method reads the entire PDF content, understands the main topics,
        and segments the content into logical chapters with titles, descriptions, and scripts.

        Args:
            file_path: Path to the PDF file
            language: Target language for chapter content

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
        chapters = await self._generate_chapters(full_text, doc_title, language)
        return chapters

    async def _generate_chapters(
        self, full_text: str, doc_title: str, language: str
    ) -> list[dict[str, Any]]:
        """
        Use AI to segment PDF content into chapters.

        Args:
            full_text: Complete text content of the PDF
            doc_title: Extracted title of the document
            language: Target language for chapter content

        Returns:
            List of chapters with title, description, key_points, and script
        """
        # Use the global LANGUAGE_PROMPTS
        prompts = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["english"])

        try:
            formatted_prompt = prompts["prompt"].format(
                doc_title=doc_title,
                full_text=full_text,
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": formatted_prompt},
                ],
            )

            # Parse the response
            content = response.choices[0].message.content
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

                        # Always generate a comprehensive script using the shared script generator
                        # to ensure detailed explanations of the topic and key points
                        # Combine title, description, and key points for comprehensive script generation
                        content_for_script = (
                            f"Chapter Topic: {chapter.get('title', '')}\n"
                        )
                        content_for_script += (
                            f"Chapter Description: {chapter.get('description', '')}\n"
                        )
                        if chapter.get("key_points"):
                            key_points_text = "\n".join(
                                [f"- {point}" for point in chapter["key_points"]]
                            )
                            content_for_script += (
                                f"\nKey Points to Cover in Detail:\n{key_points_text}\n"
                            )
                            content_for_script += (
                                "\nPlease provide a detailed, comprehensive explanation of this chapter topic, "
                                "thoroughly covering all key points with relevant examples where appropriate."
                            )

                            script = await self.script_generator.generate_script(
                                content_for_script, language=language
                            )
                        chapter["script"] = script

                        chapters_with_scripts.append(chapter)

                    return chapters_with_scripts

            # Fallback if parsing fails
            return await self._create_default_chapters(full_text, language)

        except Exception as e:
            print(f"Error generating chapters: {e}")
            # Fallback to default chapters
            return await self._create_default_chapters(full_text, language)

    async def _create_default_chapters(
        self, full_text: str, language: str
    ) -> list[dict[str, Any]]:
        """
        Create default chapters if AI analysis fails.

        Args:
            full_text: Complete text content of the PDF
            language: Target language for chapter content

        Returns:
            List of default chapters with title, description, key_points, and script
        """
        # Extract first few lines as title

        # Use the global DEFAULT_CHAPTERS
        base_chapters = DEFAULT_CHAPTERS.get(language, DEFAULT_CHAPTERS["english"])

        # Generate comprehensive scripts using the shared script generator
        # to ensure detailed explanations of the topic and key points
        chapters_with_scripts = []
        for chapter in base_chapters:
            # Combine title, description, and key points for comprehensive script generation
            content_for_script = f"Chapter Topic: {chapter['title']}\n"
            content_for_script += f"Chapter Description: {chapter['description']}\n"
            if chapter.get("key_points"):
                key_points_text = "\n".join(
                    [f"- {point}" for point in chapter["key_points"]]
                )
                content_for_script += (
                    f"\nKey Points to Cover in Detail:\n{key_points_text}\n"
                )
            content_for_script += (
                "\nPlease provide a detailed, comprehensive explanation of this chapter topic, "
                "thoroughly covering all key points with relevant examples where appropriate."
            )

            script = await self.script_generator.generate_script(
                content_for_script, language=language
            )

            # Add script to chapter
            chapter_with_script = chapter.copy()
            chapter_with_script["script"] = script
            chapters_with_scripts.append(chapter_with_script)

        return chapters_with_scripts

    async def analyze_chapters(
        self, chapters: list[dict[str, Any]], language: str = "english"
    ) -> dict[str, Any]:
        """
        Perform additional analysis on already segmented chapters.

        This method analyzes the structure and content of chapters to provide
        insights like content summary, key topics, reading time estimation, etc.

        Args:
            chapters: List of chapter dictionaries with title, description, key_points, and script
            language: Target language for analysis

        Returns:
            Dictionary with analysis results including content summary, key topics, etc.
        """
        try:
            # Extract all content from chapters for analysis
            all_titles = [chapter.get("title", "") for chapter in chapters]
            all_descriptions = [chapter.get("description", "") for chapter in chapters]
            all_key_points = []
            for chapter in chapters:
                key_points = chapter.get("key_points", [])
                if key_points:
                    all_key_points.extend(key_points)
            all_scripts = [chapter.get("script", "") for chapter in chapters]

            # Combine content for overall analysis
            combined_content = "\n".join(
                all_titles + all_descriptions + all_key_points + all_scripts
            )

            # Estimate reading time (average reading speed: 200 words per minute)
            word_count = len(combined_content.split())
            estimated_reading_time = max(1, word_count // 200)  # At least 1 minute

            # Analyze content structure
            chapter_analysis = []
            for i, chapter in enumerate(chapters):
                chapter_content = (
                    f"{chapter.get('title', '')} {chapter.get('description', '')} "
                    f"{' '.join(chapter.get('key_points', []))} {chapter.get('script', '')}"
                )
                chapter_word_count = len(chapter_content.split())
                chapter_reading_time = max(1, chapter_word_count // 200)

                chapter_analysis.append(
                    {
                        "chapter_index": i + 1,
                        "title": chapter.get("title", ""),
                        "word_count": chapter_word_count,
                        "estimated_reading_time": chapter_reading_time,
                        "key_points_count": len(chapter.get("key_points", [])),
                    }
                )

            # Extract key topics from key points
            all_key_points_text = " ".join(all_key_points)
            # Simple approach: extract potential key topics from key points
            import re

            # Extract words that appear to be key topics (simple heuristic)
            potential_topics = re.findall(r"\b[A-Z][a-z]+\b", all_key_points_text)
            key_topics = list(set(potential_topics))[
                :10
            ]  # Limit to top 10 unique topics

            # Create content summary
            content_summary = (
                f"This document contains {len(chapters)} chapters with approximately "
                f"{word_count} words and an estimated reading time of "
                f"{estimated_reading_time} minutes. It covers {len(key_topics)} key topics."
            )

            analysis_results = {
                "total_chapters": len(chapters),
                "total_word_count": word_count,
                "estimated_reading_time": estimated_reading_time,
                "content_summary": content_summary,
                "key_topics": key_topics,
                "chapters": chapter_analysis,
            }

            return analysis_results

        except Exception as e:
            print(f"Error analyzing chapters: {e}")
            # Return basic analysis if detailed analysis fails
            return {
                "total_chapters": len(chapters),
                "total_word_count": 0,
                "estimated_reading_time": 0,
                "content_summary": "Basic chapter analysis",
                "key_topics": [],
                "chapters": [
                    {
                        "chapter_index": i + 1,
                        "title": chapter.get("title", ""),
                        "word_count": 0,
                        "estimated_reading_time": 0,
                        "key_points_count": len(chapter.get("key_points", [])),
                    }
                    for i, chapter in enumerate(chapters)
                ],
            }
