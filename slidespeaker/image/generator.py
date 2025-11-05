"""Unified image generation (image package)."""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.configs.config import config

from .llm import LLMImageGenerator
from .pil import PILImageGenerator


class ImageGenerator:
    def __init__(self) -> None:
        self.llm_generator = LLMImageGenerator()
        self.pil_generator = PILImageGenerator()

    async def generate_images(
        self, chapters: list[dict[str, Any]], output_dir: Path
    ) -> list[Path]:
        if config.slide_image_provider.lower() == "llm":
            return await self._generate_slide_images_by_llm(chapters, output_dir)
        else:
            return await self._generate_slide_images_by_pil(chapters, output_dir)

    async def _generate_slide_images_by_pil(
        self, chapters: list[dict[str, Any]], output_dir: Path
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
        self, chapters: list[dict[str, Any]], output_dir: Path
    ) -> list[Path]:
        output_dir.mkdir(exist_ok=True, parents=True)
        image_paths: list[Path] = []
        style = "professional"
        for i, chapter in enumerate(chapters):
            image_path = output_dir / f"chapter_{i + 1}.png"
            title = chapter.get("title", f"Chapter {i + 1}")
            description = chapter.get("description", "")
            key_points = chapter.get("key_points", [])
            await self.llm_generator.generate_slide_image(
                title=title,
                description=description,
                key_points=key_points,
                output_path=image_path,
                style=style,
            )
            image_paths.append(image_path)
            logger.info(f"Generated slide image for chapter {i + 1}: {image_path}")
        return image_paths


__all__ = ["ImageGenerator"]
