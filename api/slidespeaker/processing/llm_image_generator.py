"""LLM-based image generation module for SlideSpeaker.

This module generates presentation-style images using DALL-E based on slide content.
It can create both detailed presentation slides and simple background images.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

import requests
from loguru import logger
from openai import OpenAI

if TYPE_CHECKING:
    pass


# Style prompts for different presentation styles
STYLE_PROMPTS = {
    "professional": (
        "clean, modern, corporate presentation slide with subtle gradient background, "
        "minimalist design, professional typography, business aesthetic"
    ),
    "creative": (
        "creative, colorful presentation slide with abstract shapes, vibrant colors, "
        "modern design elements, inspirational aesthetic"
    ),
    "academic": (
        "academic presentation slide with clean layout, serif typography, "
        "research-oriented design, formal appearance"
    ),
    "tech": (
        "tech-focused presentation slide with futuristic elements, circuit board patterns, "
        "blue color scheme, modern technology aesthetic"
    ),
}

# Template for generating presentation slide images
IMAGE_PROMPT_TEMPLATE = """
Create a presentation slide image that visually represents the following content:
"{content}"

Style: {base_style}

Requirements:
- 16:9 aspect ratio (will be cropped to 1024x1024)
- No text on the image (purely visual)
- Professional presentation style
- Relevant imagery and metaphors for the content
- Clean, modern design
- Suitable for educational/business context
"""

# Simple background prompts for fallback options
SIMPLE_BACKGROUND_PROMPTS = {
    "gradient": (
        "A smooth, subtle gradient background in {color}, professional presentation style, "
        "no text, clean design"
    ),
    "solid": (
        "A clean, solid {color} background for presentation slides, minimalist design"
    ),
}


class LLMImageGenerator:
    """Generator for presentation-style images using DALL-E"""

    def __init__(self) -> None:
        """Initialize the image generator with OpenAI client"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_slide_image(
        self,
        title: str,
        description: str,
        key_points: list[str],
        output_path: Path,
        style: str = "professional",
    ) -> bool:
        """
        Generate a slide-like image with title, description, and key points using DALL-E.

        Args:
            title: The slide title
            description: The slide description/content
            key_points: List of key points to highlight
            output_path: Path where the generated image will be saved
            style: The presentation style (professional, creative, academic, tech)

        Returns:
            bool: True if image was generated successfully
        """
        try:
            # Create a structured prompt for slide generation
            slide_content = f"""
Title: {title}

Content: {description}

Key Points:
{chr(10).join(f"- {point}" for point in key_points)}
"""

            # Use a specialized prompt template for slide-like images
            slide_prompt_template = """
Create a professional presentation slide with the following elements:
"{slide_content}"

Style: {base_style}

Requirements:
- 16:9 aspect ratio suitable for presentations
- Visually represent the title and content appropriately
- Include visual metaphors that connect to the key points
- No text on the image (purely visual)
- Clean, modern design suitable for business/educational context
- Professional presentation aesthetics
"""

            base_style = STYLE_PROMPTS.get(style, STYLE_PROMPTS["professional"])
            prompt = slide_prompt_template.format(
                slide_content=slide_content, base_style=base_style
            ).strip()

            logger.info(f"Generating slide image with prompt: {prompt[:100]}...")

            image_model = os.getenv("IMAGE_GENERATION_MODEL", "dall-e-3")
            response = self.openai_client.images.generate(
                model=image_model,
                prompt=prompt,
                size="1792x1024",
                n=1,
            )

            # Download and save the generated image
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                if image_url:
                    await self._download_image(image_url, output_path)
                    logger.info(f"Slide image generated successfully: {output_path}")
                    return True
                else:
                    raise ValueError("No image URL returned from DALL-E")
            else:
                raise ValueError("No image data returned from DALL-E")

        except Exception as e:
            logger.error(f"DALL-E slide image generation error: {e}")
            raise

    async def _download_image(self, image_url: str, output_path: Path) -> None:
        """Download image from URL and save to output path."""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            logger.error(f"Image download error: {e}")
            raise
