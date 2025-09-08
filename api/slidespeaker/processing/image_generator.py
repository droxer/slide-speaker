"""
Image generation module for SlideSpeaker.

This module generates presentation-style images using DALL-E based on slide content.
It can create both detailed presentation slides and simple background images.
"""

import os
import textwrap
from pathlib import Path
from typing import Any

import requests
from loguru import logger
from openai import OpenAI

STYLE_PROMPTS = {
    "professional": "clean, modern, corporate presentation slide with subtle gradient background, "
    "minimalist design, professional typography, business aesthetic",
    "creative": "creative, colorful presentation slide with abstract shapes, vibrant colors, "
    "modern design elements, inspirational aesthetic",
    "academic": "academic presentation slide with clean layout, serif typography, research-oriented design, formal appearance",  # noqa: E501
    "tech": "tech-focused presentation slide with futuristic elements, circuit board patterns, blue color scheme, modern technology aesthetic",  # noqa: E501
}

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

SIMPLE_BACKGROUND_PROMPTS = {
    "gradient": "A smooth, subtle gradient background in {color}, "
    "professional presentation style, no text, clean design",
    "solid": "A clean, solid {color} background for presentation slides, minimalist design",
}


class ImageGenerator:
    """Generator for presentation-style images using DALL-E"""

    def __init__(self) -> None:
        """Initialize the image generator with OpenAI client"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_presentation_image(
        self, content: str, output_path: Path, style: str = "professional"
    ) -> bool:
        """
        Generate a presentation-style image using DALL-E based on slide content

        This method creates visually appealing presentation slides by converting
        slide content into descriptive prompts for DALL-E image generation.
        """
        try:
            # Create a prompt for presentation image
            prompt = self._create_image_prompt(content, style)
            logger.info(f"Generating image with prompt: {prompt[:100]}...")

            # Get model from environment variable, default to "gpt-image-1"
            image_model = os.getenv("IMAGE_GENERATION_MODEL", "gpt-image-1")

            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model=image_model,
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

            # Get model from environment variable, default to "gpt-image-1"
            image_model = os.getenv("IMAGE_GENERATION_MODEL", "gpt-image-1")

            response = self.openai_client.images.generate(
                model=image_model,
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

    async def generate_chapter_images(
        self,
        chapters: list[dict[str, Any]],
        output_dir: Path,
        language: str = "english",
    ) -> list[Path]:
        """
        Generate slide-like images for PDF chapters.

        Args:
            chapters: List of chapter dictionaries with title, description, and script
            output_dir: Directory to save the generated images
            language: Language for image generation (used for style selection)

        Returns:
            List of paths to the generated images
        """
        image_paths = []

        # Create output directory if it doesn't exist
        output_dir.mkdir(exist_ok=True, parents=True)

        # Generate a slide-like image for each chapter
        for i, chapter in enumerate(chapters):
            image_path = output_dir / f"chapter_{i + 1}.png"

            # Create a slide-like image with chapter title and description
            try:
                await self._create_slide_image(chapter, image_path)
                image_paths.append(image_path)
                logger.info(f"Generated slide image for chapter {i + 1}: {image_path}")
            except Exception as e:
                logger.error(f"Failed to generate slide image for chapter {i + 1}: {e}")
                # Create a fallback background if slide creation fails
                try:
                    await self._create_fallback_background(image_path, "#4287f5")
                    image_paths.append(image_path)
                    logger.info(
                        f"Generated fallback background image for chapter {i + 1}: {image_path}"
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"Failed to generate fallback image for chapter {i + 1}: {fallback_error}"
                    )

        return image_paths

    async def _create_slide_image(
        self, chapter: dict[str, Any], output_path: Path
    ) -> None:
        """
        Create a slide-like image for a chapter with title, description, and key points.

        Args:
            chapter: Chapter dictionary with title, description, and key_points
            output_path: Path to save the generated image
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create a 16:9 slide image (1920x1080) - standard video resolution
            width, height = 1920, 1080
            img = Image.new("RGB", (width, height), "#ffffff")
            draw = ImageDraw.Draw(img)

            # Try to load system fonts, fallback to default if not available
            title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont
            desc_font: ImageFont.FreeTypeFont | ImageFont.ImageFont
            keypoint_font: ImageFont.FreeTypeFont | ImageFont.ImageFont
            try:
                # Try common system fonts
                title_font = ImageFont.truetype("Arial.ttf", 60)
                desc_font = ImageFont.truetype("Arial.ttf", 36)
                keypoint_font = ImageFont.truetype("Arial.ttf", 28)
            except Exception:
                try:
                    # Try alternative font names
                    title_font = ImageFont.truetype("DejaVuSans.ttf", 60)
                    desc_font = ImageFont.truetype("DejaVuSans.ttf", 36)
                    keypoint_font = ImageFont.truetype("DejaVuSans.ttf", 28)
                except Exception:
                    # Fallback to default font
                    title_font = ImageFont.load_default()
                    desc_font = ImageFont.load_default()
                    keypoint_font = ImageFont.load_default()

            # Add a subtle gradient background
            gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)

            # Create a vertical gradient from light blue to white
            for y in range(height):
                # Calculate color intensity (0 at top, 255 at bottom)
                intensity = int(200 * (y / height))
                color = (240, 245, 255, 255 - intensity)  # Light blue to transparent
                gradient_draw.line([(0, y), (width, y)], fill=color)

            img = Image.alpha_composite(img.convert("RGBA"), gradient)
            draw = ImageDraw.Draw(img)

            # Add decorative elements
            # Draw a subtle horizontal line
            draw.line([(100, 200), (width - 100, 200)], fill="#4287f5", width=3)

            # Add chapter title
            title = chapter.get("title", f"Chapter {chapter.get('slide_number', 1)}")
            # Ensure title is clean and concise (should already be from the analyzer)
            title_lines = textwrap.wrap(title, width=40)  # Wrap text to fit

            # Calculate vertical position for title (top of the slide)
            title_y = 150
            line_height = 70
            total_title_height = len(title_lines) * line_height

            for i, line in enumerate(title_lines):
                # Get text dimensions for centering
                bbox = draw.textbbox((0, 0), line, font=title_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = title_y + i * line_height
                draw.text((x, y), line, fill="#2c3e50", font=title_font)

            # Add chapter description
            description = chapter.get("description", "")
            if description:
                desc_lines = textwrap.wrap(description, width=60)  # Wrap text to fit

                # Start description below title
                desc_y = title_y + total_title_height + 30

                for i, line in enumerate(desc_lines[:3]):  # Limit to 3 lines
                    # Get text dimensions for centering
                    bbox = draw.textbbox((0, 0), line, font=desc_font)
                    text_width = bbox[2] - bbox[0]
                    x = (width - text_width) // 2
                    y = desc_y + i * 45
                    draw.text((x, y), line, fill="#34495e", font=desc_font)

            # Add key points
            key_points = chapter.get("key_points", [])
            if key_points:
                # Start key points below description
                keypoints_y = desc_y + min(3, len(desc_lines)) * 45 + 40

                # Draw "Key Points:" header
                draw.text(
                    (150, keypoints_y), "Key Points:", fill="#2c3e50", font=desc_font
                )

                # Draw each key point
                for i, point in enumerate(key_points[:5]):  # Limit to 5 key points
                    y_position = keypoints_y + 60 + i * 40
                    if y_position < height - 100:  # Don't go beyond image bounds
                        # Add bullet point and wrap text
                        bullet_point = f"• {point}"
                        wrapped_lines = textwrap.wrap(bullet_point, width=70)

                        # Draw wrapped lines
                        for j, line in enumerate(wrapped_lines):
                            line_y = y_position + j * 35
                            if line_y < height - 100:  # Don't go beyond image bounds
                                draw.text(
                                    (200, line_y),
                                    line,
                                    fill="#34495e",
                                    font=keypoint_font,
                                )

            # Add a subtle decorative element in the corner
            # Draw a small circle in bottom right corner
            circle_x, circle_y = width - 50, height - 50
            draw.ellipse(
                [circle_x - 20, circle_y - 20, circle_x + 20, circle_y + 20],
                fill="#4287f5",
                outline="#2c3e50",
                width=2,
            )

            # Save the image
            img.convert("RGB").save(output_path)
            logger.info(f"Created slide image: {output_path}")

        except ImportError:
            logger.warning(
                "PIL not available for slide image generation, using fallback"
            )
            # Fallback to simple background
            await self._create_fallback_background(output_path, "#4287f5")
        except Exception as e:
            logger.error(f"Error creating slide image: {e}")
            # Fallback to simple background
            await self._create_fallback_background(output_path, "#4287f5")

    async def convert_slides_to_images(
        self, file_path: str, file_ext: str, output_dir: Path
    ) -> list[Path]:
        """
        Convert presentation slides to images.

        This is a stub implementation to satisfy type checking.
        """
        # This would be implemented with actual slide conversion logic
        return []

    async def analyze_slide_images(self, file_id: str) -> None:
        """
        Analyze slide images for content understanding.

        This is a stub implementation to satisfy type checking.
        """
        # This would be implemented with actual image analysis logic
        pass
