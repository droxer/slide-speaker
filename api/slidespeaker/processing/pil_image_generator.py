"""PIL-based image generation module for SlideSpeaker.

This module generates presentation-style images using PIL (Python Imaging Library)
for creating chapter slides and simple backgrounds programmatically.
"""

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    pass


class PILImageGenerator:
    """Generator for presentation-style images using PIL"""

    async def generate_slide_image(
        self, chapter: dict[str, Any], output_path: Path
    ) -> None:
        """
        Create a slide-like image for a chapter with title, description, and key points.

        Args:
            chapter: Chapter dictionary with title, description, and key_points
            output_path: Path to save the generated image
        """
        try:
            from PIL import Image, ImageDraw

            # Create a 16:9 slide image (1920x1080)
            width, height = 1920, 1080
            img = Image.new("RGB", (width, height), "#ffffff")
            draw = ImageDraw.Draw(img)

            # Load fonts with fallback
            title_font, desc_font, keypoint_font = self._load_fonts()

            # Add gradient background
            self._add_gradient_background(img, draw, width, height)

            # Add decorative elements
            self._add_decorative_elements(draw, width, height)

            # Add content
            self._add_slide_content(
                draw, chapter, title_font, desc_font, keypoint_font, width, height
            )

            # Save the image
            img.convert("RGB").save(output_path)
            logger.info(f"Created chapter slide: {output_path}")

        except ImportError:
            logger.warning("PIL not available for slide generation, using fallback")
            await self._create_programmatic_background(output_path, "#4287f5")
        except Exception as e:
            logger.error(f"Error creating chapter slide: {e}")
            await self._create_programmatic_background(output_path, "#4287f5")

    async def _create_programmatic_background(
        self, output_path: Path, color: str
    ) -> None:
        """Create a simple background programmatically using PIL."""
        try:
            from PIL import Image

            # Create a simple solid color image
            img = Image.new("RGB", (1024, 1024), color)
            img.save(output_path)
            logger.info(f"Created programmatic background: {output_path}")

        except ImportError:
            logger.warning("PIL not available for background generation")
            raise Exception(
                "Image generation requires PIL for background creation"
            ) from None

    def _load_fonts(self) -> tuple[Any, Any, Any]:
        """Load fonts with fallback to default if system fonts are not available."""
        title_font: Any
        desc_font: Any
        keypoint_font: Any

        try:
            from PIL import ImageFont

            # Try common system fonts
            title_font = ImageFont.truetype("Arial.ttf", 60)
            desc_font = ImageFont.truetype("Arial.ttf", 36)
            keypoint_font = ImageFont.truetype("Arial.ttf", 28)
        except Exception:
            try:
                from PIL import ImageFont

                # Try alternative font names
                title_font = ImageFont.truetype("DejaVuSans.ttf", 60)
                desc_font = ImageFont.truetype("DejaVuSans.ttf", 36)
                keypoint_font = ImageFont.truetype("DejaVuSans.ttf", 28)
            except Exception:
                from PIL import ImageFont

                # Fallback to default font
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
                keypoint_font = ImageFont.load_default()

        return title_font, desc_font, keypoint_font

    def _add_gradient_background(
        self, img: Any, draw: Any, width: int, height: int
    ) -> None:
        """Add a subtle gradient background to the slide."""
        from PIL import Image, ImageDraw

        gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)

        # Create a vertical gradient from light blue to white
        for y in range(height):
            intensity = int(200 * (y / height))
            color = (240, 245, 255, 255 - intensity)  # Light blue to transparent
            gradient_draw.line([(0, y), (width, y)], fill=color)

        img.paste(Image.alpha_composite(img.convert("RGBA"), gradient))

    def _add_decorative_elements(self, draw: Any, width: int, height: int) -> None:
        """Add decorative elements to the slide."""
        # Draw a subtle horizontal line
        draw.line([(100, 200), (width - 100, 200)], fill="#4287f5", width=3)

        # Draw a small circle in bottom right corner
        circle_x, circle_y = width - 50, height - 50
        draw.ellipse(
            [circle_x - 20, circle_y - 20, circle_x + 20, circle_y + 20],
            fill="#4287f5",
            outline="#2c3e50",
            width=2,
        )

    def _add_slide_content(
        self,
        draw: Any,
        chapter: dict[str, Any],
        title_font: Any,
        desc_font: Any,
        keypoint_font: Any,
        width: int,
        height: int,
    ) -> None:
        """Add chapter content (title, description, key points) to the slide with improved layout."""
        margin = 100

        # Add chapter title
        title = chapter.get("title", f"Chapter {chapter.get('slide_number', 1)}")
        title_lines = textwrap.wrap(
            title, width=50
        )  # Adjusted width for better wrapping

        title_y = 170
        # Increase title line spacing for readability
        title_line_height = 80

        # Move the title higher by reducing title_y
        title_y = 110  # Was 170, now moved up by 60px

        for i, line in enumerate(title_lines):
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = title_y + i * title_line_height
            draw.text((x, y), line, fill="#2c3e50", font=title_font)

        # Calculate total title height for proper spacing
        total_title_height = len(title_lines) * title_line_height

        # Add chapter description
        description = chapter.get("description", "")
        # Increase spacing between title and description
        desc_y = title_y + total_title_height + 90

        # Increase font size for description and keypoints
        # We'll create larger fonts based on the originals
        from PIL import ImageFont

        # Try to get the font path and size from the original font objects
        def get_larger_font(
            orig_font: ImageFont.ImageFont, scale: float = 1.25
        ) -> ImageFont.ImageFont:
            try:
                # Try to get the font size (this is a more reliable approach)
                # We'll try to get the size by checking the font's attributes
                if hasattr(orig_font, "size"):
                    orig_size = orig_font.size
                    # Since we can't easily get the font path, we'll try to create a new font
                    # with the same size scaled up. This is a best-effort approach.
                    from PIL import ImageFont

                    # Try to create a new default font with larger size
                    new_font = ImageFont.load_default(size=int(orig_size * scale))
                    return new_font  # type: ignore[return-value]
                else:
                    # If we can't determine the size, return the original font
                    return orig_font
            except Exception:
                # Fallback: just use the original font if we can't get path/size
                return orig_font

        larger_desc_font = get_larger_font(desc_font, scale=1.25)
        larger_keypoint_font = get_larger_font(keypoint_font, scale=1.25)

        if description:
            # Use smaller width for better line control
            desc_lines = textwrap.wrap(description, width=80)
            # Increase description line height for better line spacing
            desc_line_height = 68

            for i, line in enumerate(desc_lines[:4]):  # Limit to 4 lines for better fit
                bbox = draw.textbbox((0, 0), line, font=larger_desc_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = desc_y + i * desc_line_height
                draw.text((x, y), line, fill="#34495e", font=larger_desc_font)

            # Update description height for key points positioning
            desc_content_height = len(desc_lines[:4]) * desc_line_height
        else:
            desc_content_height = 0

        # Add key points
        key_points = chapter.get("key_points", [])
        if key_points:
            # Increase spacing between description and key points
            keypoints_start_y = desc_y + desc_content_height + 80

            # Draw "Key Points:" header
            header_text = "Key Points:"
            draw.text(
                (margin, keypoints_start_y),
                header_text,
                fill="#2c3e50",
                font=larger_desc_font,
            )

            # Draw each key point with increased line spacing
            keypoint_line_height = 68
            keypoint_y = (
                keypoints_start_y + 60
            )  # More space after header for larger font

            for i, point in enumerate(key_points[:6]):  # Limit to 6 key points
                # Compute starting y for this keypoint
                current_y = keypoint_y + i * keypoint_line_height

                # Stop if near the bottom
                if current_y > height - 150:
                    break

                # Wrap only the text (without bullet) for a clean hanging indent
                wrapped_lines = textwrap.wrap(str(point), width=90)
                if not wrapped_lines:
                    continue

                # Draw a bullet sized to the current font line height
                # Support styles: 'dot' (default), 'large_dot', 'square', 'hyphen'
                bullet_style = str(chapter.get("bullet_style", "dot")).lower()
                line_bbox = draw.textbbox(
                    (0, 0), wrapped_lines[0], font=larger_keypoint_font
                )
                line_h = max(1, line_bbox[3] - line_bbox[1])
                cy = current_y + line_h // 2
                cx = margin
                indent_x: int

                if bullet_style in ("square", "box"):
                    side = max(4, int(line_h * 0.22))
                    half = side // 2
                    draw.rectangle(
                        [cx - half, cy - half, cx + half, cy + half],
                        fill="#34495e",
                        outline=None,
                    )
                    indent_x = margin + side + 12
                elif bullet_style in ("hyphen", "dash"):
                    hy_w = max(8, int(line_h * 0.5))
                    hy_h = max(2, int(line_h * 0.08))
                    draw.rectangle(
                        [cx, cy - hy_h // 2, cx + hy_w, cy + hy_h // 2],
                        fill="#34495e",
                        outline=None,
                    )
                    indent_x = margin + hy_w + 12
                else:  # dot / large_dot default
                    radius_factor = (
                        0.18 if bullet_style in ("dot", "•", "bullet") else 0.28
                    )
                    r = max(3, int(line_h * radius_factor))
                    draw.ellipse(
                        [cx - r, cy - r, cx + r, cy + r],
                        fill="#34495e",
                        outline=None,
                    )
                    indent_x = margin + (r * 2) + 12

                # First line
                if current_y <= height - 120:
                    draw.text(
                        (indent_x, current_y),
                        wrapped_lines[0],
                        fill="#34495e",
                        font=larger_keypoint_font,
                    )

                # Continuation lines (hanging indent)
                # Increase continuation line spacing as well
                continuation_step = 48
                for j, cont_line in enumerate(wrapped_lines[1:], start=1):
                    line_y = current_y + j * continuation_step
                    if line_y <= height - 120:
                        draw.text(
                            (indent_x, line_y),
                            cont_line,
                            fill="#34495e",
                            font=larger_keypoint_font,
                        )

                # If wrapping occurred, increase spacing for the next bullet accordingly
                if len(wrapped_lines) > 1:
                    keypoint_line_height = max(
                        keypoint_line_height,
                        len(wrapped_lines) * continuation_step + 16,
                    )
