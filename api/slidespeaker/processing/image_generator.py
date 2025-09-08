"""Unified image generation module for SlideSpeaker.

This module provides a unified interface for generating presentation-style images
using both LLM-based (DALL-E) and PIL-based approaches.
"""

import os
from pathlib import Path
from typing import Any

from loguru import logger

from .llm_image_generator import LLMImageGenerator
from .pil_image_generator import PILImageGenerator


class ImageGenerator:
    """Unified generator for presentation-style images using both LLM and PIL approaches"""

    def __init__(self) -> None:
        """Initialize the image generator with both LLM and PIL backends"""
        self.llm_generator = LLMImageGenerator()
        self.pil_generator = PILImageGenerator()

    async def generate_images(
        self,
        chapters: list[dict[str, Any]],
        output_dir: Path,
    ) -> list[Path]:
        if os.getenv("SLIDE_IMAGE_PROVIDER") == "llm":
            return await self._generate_slide_images_by_llm(chapters, output_dir)
        else:
            return await self._generate_slide_images_by_pil(chapters, output_dir)

    async def _generate_slide_images_by_pil(
        self,
        chapters: list[dict[str, Any]],
        output_dir: Path,
    ) -> list[Path]:
        output_dir.mkdir(exist_ok=True, parents=True)
        image_paths: list[Path] = []

        for i, chapter in enumerate(chapters):
            image_path = output_dir / f"chapter_{i + 1}.png"

            await self.pil_generator.generate_slide_image(chapter, image_path)
            image_paths.append(image_path)
            logger.info(f"Generated slide image for chapter {i + 1}: {image_path}")

        return image_paths

    async def _generate_slide_images_by_llm(
        self,
        chapters: list[dict[str, Any]],
        output_dir: Path,
    ) -> list[Path]:
        """
        Generate slide-like images for PDF chapters using LLM-based image generation.

        Args:
            chapters: List of chapter dictionaries with title, description, and script
            output_dir: Directory to save the generated images
            language: Language for image generation (used for style selection)

        Returns:
            List of paths to the generated images
        """
        output_dir.mkdir(exist_ok=True, parents=True)
        image_paths: list[Path] = []

        # Determine style based on language
        style = "professional"  # Default style
        for i, chapter in enumerate(chapters):
            image_path = output_dir / f"chapter_{i + 1}.png"

            title = chapter.get("title", f"Chapter {i + 1}")
            description = chapter.get("description", "")
            key_points = chapter.get("key_points", [])

            # Generate slide image using LLM-based approach
            await self.llm_generator.generate_slide_image(
                title=title,
                description=description,
                key_points=key_points,
                output_path=image_path,
                style=style,
            )

        return image_paths
