import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

load_dotenv()

# Style prompts for DALL-E image generation
STYLE_PROMPTS = {
    "professional": "clean, modern, corporate presentation slide with subtle gradient background, "
    "minimalist design, professional typography, business aesthetic",
    "creative": "creative, colorful presentation slide with abstract shapes, vibrant colors, "
    "modern design elements, inspirational aesthetic",
    "academic": "academic presentation slide with clean layout, serif typography, "
    "research-oriented design, formal appearance",
    "tech": "tech-focused presentation slide with futuristic elements, circuit board patterns, "
    "blue color scheme, modern technology aesthetic",
}

# Base prompt template for DALL-E image generation
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

# Simple background prompts
SIMPLE_BACKGROUND_PROMPTS = {
    "gradient": "A smooth, subtle gradient background in {color}, "
    "professional presentation style, no text, clean design",
    "solid": "A clean, solid {color} background for presentation slides, minimalist design",
}


class ImageGenerator:
    def __init__(self) -> None:
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_presentation_image(
        self, content: str, output_path: Path, style: str = "professional"
    ) -> bool:
        """
        Generate a presentation-style image using DALL-E based on slide content
        """
        try:
            # Create a prompt for presentation image
            prompt = self._create_image_prompt(content, style)
            logger.info(f"Generating image with prompt: {prompt[:100]}...")

            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            # Download the image
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                if image_url:
                    await self._download_image(image_url, output_path)
                else:
                    raise ValueError("No image URL returned from DALL-E")
            else:
                raise ValueError("No image data returned from DALL-E")

            logger.info(f"Image generated successfully: {output_path}")
            return True

        except Exception as e:
            logger.error(f"DALL-E image generation error: {e}")
            raise

    def _create_image_prompt(self, content: str, style: str) -> str:
        """Create a detailed prompt for presentation image generation"""

        base_style = STYLE_PROMPTS.get(style, STYLE_PROMPTS["professional"])

        prompt = IMAGE_PROMPT_TEMPLATE.format(content=content, base_style=base_style)

        return prompt.strip()

    async def _download_image(self, image_url: str, output_path: Path) -> None:
        """Download image from URL"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            logger.error(f"Image download error: {e}")
            raise

    async def generate_simple_background(
        self, output_path: Path, color: str = "#f0f4f8", style: str = "gradient"
    ) -> None:
        """Generate a simple background image (fallback option)"""
        try:
            # For simple backgrounds, we can create programmatic images
            # or use very simple DALL-E prompts

            prompt_template = SIMPLE_BACKGROUND_PROMPTS.get(
                style, SIMPLE_BACKGROUND_PROMPTS["gradient"]
            )
            prompt = prompt_template.format(color=color)

            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            if response.data and len(response.data) > 0:
                image_url = response.data[0].url
                if image_url:
                    await self._download_image(image_url, output_path)
                else:
                    raise ValueError("No image URL returned from DALL-E")
            else:
                raise ValueError("No image data returned from DALL-E")

            logger.info(f"Background image generated: {output_path}")

        except Exception as e:
            logger.error(f"Background generation error: {e}")
            # Fallback: create a simple colored background programmatically
            await self._create_fallback_background(output_path, color)

    async def _create_fallback_background(self, output_path: Path, color: str) -> None:
        """Create a simple fallback background using PIL"""
        try:
            from PIL import Image

            # Create a simple solid color image
            img = Image.new("RGB", (1024, 1024), color)
            img.save(output_path)
            logger.info(f"Created fallback background: {output_path}")

        except ImportError:
            logger.warning("PIL not available for fallback backgrounds")
            raise Exception(
                "Image generation requires PIL for fallback backgrounds"
            ) from None
