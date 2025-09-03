"""
Analyze slide images step for the presentation pipeline.
"""

from pathlib import Path

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.vision_service import VisionService

vision_service = VisionService()


async def analyze_slides_step(file_id: str) -> None:
    """Analyze slide images using vision service"""
    await state_manager.update_step_status(
        file_id, "analyze_slide_images", "processing"
    )
    state = await state_manager.get_state(file_id)

    # Get slide images for analysis
    slide_images = []
    if (
        state
        and "steps" in state
        and "convert_slides_to_images" in state["steps"]
        and state["steps"]["convert_slides_to_images"]["data"] is not None
    ):
        slide_images = state["steps"]["convert_slides_to_images"]["data"]

    if not slide_images:
        raise ValueError("No slide images available for analysis")

    # Analyze each slide image using vision service
    image_analyses = []
    for i, image_path in enumerate(slide_images):
        analysis = await vision_service.analyze_slide_image(Path(image_path))
        image_analyses.append({"slide_number": i + 1, "analysis": analysis})

    await state_manager.update_step_status(
        file_id, "analyze_slide_images", "completed", image_analyses
    )
