"""
PDF content analyzer for SlideSpeaker.

This module provides deep analysis of PDF content and segmentation into chapters.
It uses AI to understand the content structure and create meaningful segments
for presentation generation.
"""

import os
from typing import Any

from openai import OpenAI
from PyPDF2 import PdfReader

# Import the shared script generator
from slidespeaker.processing.script_generator import ScriptGenerator

# Language-specific prompts for PDF analysis
LANGUAGE_PROMPTS = {
    "english": {
        "system": "You are an expert content analyzer and presentation designer. "
        + "Your task is to analyze a document and segment it into logical "
        + "chapters for presentation purposes.",
        "prompt": """
        Analyze the following document titled "{doc_title}" and segment it into 3-7
        logical chapters that would work well for a presentation.
        For each chapter, provide:
        1. A clear, concise title (5-10 words)
        2. A brief description (1-2 sentences) that summarizes the chapter content
        3. A presentation script (50-100 words) that explains the key points in an
           engaging way

        Document content:
        {full_text}  # Limit to first 4000 characters to avoid token limits

        Respond in JSON format with the following structure:
        {{
            "chapters": [
                {{
                    "title": "Chapter Title",
                    "description": "Brief description of chapter content",
                    "script": "Presentation script for this chapter"
                }}
            ]
        }}
        """,
    },
    "simplified_chinese": {
        "system": "您是一位专业的文档内容分析师和演示文稿设计师。您的任务是分析文档并将其分割成适合演示的逻辑章节。",
        "prompt": """
        请分析以下名为"{doc_title}"的文档，并将其分割成3-7个适合演示的逻辑章节。
        每个章节需要提供：
        1. 清晰简洁的标题（5-10个字）
        2. 简短描述（1-2句话）总结章节内容
        3. 演示文稿脚本（50-100个字）以吸引人的方式解释要点

        文档内容：
        {full_text}

        请以以下JSON格式回复：
        {{
            "chapters": [
                {{
                    "title": "章节标题",
                    "description": "章节内容简述",
                    "script": "本章节的演示文稿脚本"
                }}
            ]
        }}
        """,
    },
    "traditional_chinese": {
        "system": "您是一位專業的文件內容分析師和簡報設計師。您的任務是分析文件並將其分割成適合簡報的邏輯章節。",
        "prompt": """
        請分析以下名為"{doc_title}"的文件，並將其分割成3-7個適合簡報的邏輯章節。
        每個章節需要提供：
        1. 清晰簡潔的標題（5-10個字）
        2. 簡短描述（1-2句話）總結章節內容
        3. 簡報腳本（50-100個字）以吸引人的方式解釋要點

        文件內容：
        {full_text}

        請以以下JSON格式回覆：
        {{
            "chapters": [
                {{
                    "title": "章節標題",
                    "description": "章節內容簡述",
                    "script": "本章節的簡報腳本"
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
        },
        {
            "title": "Main Content",
            "description": "Detailed analysis of the core document content.",
        },
        {
            "title": "Conclusion",
            "description": "Summary of key takeaways and final thoughts.",
        },
    ],
    "simplified_chinese": [
        {
            "title": "介绍",
            "description": "文档内容概述和涵盖的主要主题。",
        },
        {
            "title": "主要内容",
            "description": "文档核心内容的详细分析。",
        },
        {
            "title": "结论",
            "description": "关键要点总结和最终思考。",
        },
    ],
    "traditional_chinese": [
        {
            "title": "介紹",
            "description": "文件內容概述和涵蓋的主要主題。",
        },
        {
            "title": "主要內容",
            "description": "文件核心內容的詳細分析。",
        },
        {
            "title": "結論",
            "description": "關鍵要點總結和最終思考。",
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
            raise ValueError("PDF file appears to be empty or unreadable")

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
            List of chapters with title, description, and script
        """
        # Use the global LANGUAGE_PROMPTS
        prompts = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["english"])

        try:
            # Format the prompt with the document title and text
            formatted_prompt = prompts["prompt"].format(
                doc_title=doc_title,
                full_text=full_text[
                    :4000
                ],  # Limit to first 4000 characters to avoid token limits
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": formatted_prompt},
                ],
                temperature=0.3,
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

                    # Generate scripts for each chapter using the shared script generator
                    chapters_with_scripts = []
                    for chapter in base_chapters:
                        # Combine title and description for script generation
                        content_for_script = f"{chapter.get('title', '')}: {chapter.get('description', '')}"
                        script = await self.script_generator.generate_script(
                            content_for_script, language=language
                        )

                        # Add script to chapter
                        chapter_with_script = chapter.copy()
                        chapter_with_script["script"] = script
                        chapters_with_scripts.append(chapter_with_script)

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
            List of default chapters
        """
        # Extract first few lines as title

        # Use the global DEFAULT_CHAPTERS
        base_chapters = DEFAULT_CHAPTERS.get(language, DEFAULT_CHAPTERS["english"])

        # Generate scripts using the shared script generator
        chapters_with_scripts = []
        for chapter in base_chapters:
            # Combine title and description for script generation
            content_for_script = f"{chapter['title']}: {chapter['description']}"
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
            chapters: List of chapter dictionaries with title, description, and script
            language: Target language for analysis

        Returns:
            Dictionary with analysis results including content summary, key topics, etc.
        """
        try:
            # Extract all content from chapters for analysis
            all_titles = [chapter.get("title", "") for chapter in chapters]
            all_descriptions = [chapter.get("description", "") for chapter in chapters]
            all_scripts = [chapter.get("script", "") for chapter in chapters]

            # Combine content for overall analysis
            combined_content = "\n".join(all_titles + all_descriptions + all_scripts)

            # Estimate reading time (average reading speed: 200 words per minute)
            word_count = len(combined_content.split())
            estimated_reading_time = max(1, word_count // 200)  # At least 1 minute

            # Analyze content structure
            chapter_analysis = []
            for i, chapter in enumerate(chapters):
                chapter_content = (
                    f"{chapter.get('title', '')} {chapter.get('description', '')} "
                    f"{chapter.get('script', '')}"
                )
                chapter_word_count = len(chapter_content.split())
                chapter_reading_time = max(1, chapter_word_count // 200)

                chapter_analysis.append(
                    {
                        "chapter_index": i + 1,
                        "title": chapter.get("title", ""),
                        "word_count": chapter_word_count,
                        "estimated_reading_time": chapter_reading_time,
                    }
                )

            # Create content summary
            content_summary = (
                f"This document contains {len(chapters)} chapters with approximately "
                f"{word_count} words and an estimated reading time of "
                f"{estimated_reading_time} minutes."
            )

            analysis_results = {
                "total_chapters": len(chapters),
                "total_word_count": word_count,
                "estimated_reading_time": estimated_reading_time,
                "content_summary": content_summary,
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
                "chapters": [
                    {
                        "chapter_index": i + 1,
                        "title": chapter.get("title", ""),
                        "word_count": 0,
                        "estimated_reading_time": 0,
                    }
                    for i, chapter in enumerate(chapters)
                ],
            }
