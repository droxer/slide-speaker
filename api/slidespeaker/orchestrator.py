from pathlib import Path
from loguru import logger

from slidespeaker.slide_processor import SlideProcessor
from slidespeaker.script_generator import ScriptGenerator
from slidespeaker.tts_service import TTSService
from slidespeaker.avatar_service_unified import UnifiedAvatarService
from slidespeaker.video_composer import VideoComposer
from slidespeaker.state_manager import state_manager
from slidespeaker.vision_service import VisionService

slide_processor = SlideProcessor()
script_generator = ScriptGenerator()
tts_service = TTSService()
avatar_service = UnifiedAvatarService()
video_composer = VideoComposer()
vision_service = VisionService()

async def process_presentation(file_id: str, file_path: Path, file_ext: str, language: str = "english"):
    """State-aware processing that can resume from any step"""
    logger.info(f"Initiating AI presentation generation for file: {file_id}, format: {file_ext}")
    
    # Initialize state
    state = await state_manager.get_state(file_id)
    if not state:
        await state_manager.create_state(file_id, file_path, file_ext)
        state = await state_manager.get_state(file_id)
    
    # Log initial state
    if state:
        logger.info(f"Current processing status: {state['status']}")
        for step_name, step_data in state["steps"].items():
            step_display_names = {
                "extract_slides": "Extracting presentation content",
                "convert_slides_to_images": "Converting slides to images",
                "analyze_slide_images": "Analyzing visual content",
                "generate_scripts": "Generating AI narratives",
                "review_scripts": "Reviewing and refining scripts",
                "generate_audio": "Synthesizing voice audio",
                "generate_avatar_videos": "Creating AI presenter videos",
                "compose_video": "Composing final presentation"
            }
            display_name = step_display_names.get(step_name, step_name)
            logger.info(f"Stage '{display_name}': {step_data['status']}")
    else:
        logger.info(f"No existing processing state found for {file_id}")
    
    # Define processing steps in order
    steps_order = [
        "extract_slides",
        "convert_slides_to_images",
        "analyze_slide_images",
        "generate_scripts", 
        "review_scripts",  # New step for script review
        "generate_audio",
        "generate_avatar_videos",
        "compose_video"
    ]
    
    try:
        # Process each step in order, skipping completed ones
        for step_name in steps_order:
            await _process_step(file_id, file_path, file_ext, step_name, language)
        
    except Exception as e:
        logger.error(f"AI presentation generation failed for file {file_id}: {e}")
        logger.error(f"Error category: {type(e).__name__}")
        import traceback
        logger.error(f"Technical details: {traceback.format_exc()}")
        
        # Update error state
        current_step = "unknown"
        state = await state_manager.get_state(file_id)
        if state and "current_step" in state:
            current_step = state["current_step"]
        
        try:
            await state_manager.update_step_status(file_id, current_step, "failed")
            await state_manager.add_error(file_id, str(e), current_step)
            await state_manager.mark_failed(file_id)
            logger.info(f"Processing marked as failed for file {file_id}")
        except Exception as inner_error:
            logger.error(f"Unable to update processing state: {inner_error}")
        
        # Don't cleanup on error - allow retry from last successful step


async def _process_step(file_id: str, file_path: Path, file_ext: str, step_name: str, language: str = "english"):
    """Process a single step in the presentation pipeline"""
    # Get fresh state
    state = await state_manager.get_state(file_id)
    
    # Skip completed steps
    if state and state["steps"][step_name]["status"] == "completed":
        step_display_names = {
            "extract_slides": "Extracting presentation content",
            "convert_slides_to_images": "Converting slides to images",
            "analyze_slide_images": "Analyzing visual content",
            "generate_scripts": "Generating AI narratives",
            "review_scripts": "Reviewing and refining scripts",
            "generate_audio": "Synthesizing voice audio",
            "generate_avatar_videos": "Creating AI presenter videos",
            "compose_video": "Composing final presentation"
        }
        display_name = step_display_names.get(step_name, step_name)
        logger.info(f"Stage already completed: {display_name}")
        return
    
    # Process pending, failed, or processing steps
    if state and state["steps"][step_name]["status"] in ["pending", "failed", "processing"]:
        step_display_names = {
            "extract_slides": "Extracting presentation content",
            "convert_slides_to_images": "Converting slides to images",
            "analyze_slide_images": "Analyzing visual content",
            "generate_scripts": "Generating AI narratives",
            "review_scripts": "Reviewing and refining scripts",
            "generate_audio": "Synthesizing voice audio",
            "generate_avatar_videos": "Creating AI presenter videos",
            "compose_video": "Composing final presentation"
        }
        display_name = step_display_names.get(step_name, step_name)
        logger.info(f"Executing stage: {display_name}")
        
        if step_name == "extract_slides":
            await extract_slides(file_id, file_path, file_ext)
        elif step_name == "analyze_slide_images":
            await analyze_slide_images(file_id)
        elif step_name == "generate_scripts":
            await generate_scripts(file_id, language)
        elif step_name == "review_scripts":
            await review_scripts(file_id, language)
        elif step_name == "generate_audio":
            await generate_audio(file_id, language)
        elif step_name == "generate_avatar_videos":
            await generate_avatar_videos(file_id)
        elif step_name == "convert_slides_to_images":
            await convert_slides_to_images(file_id, file_path, file_ext)
        elif step_name == "compose_video":
            await compose_video(file_id, file_path)


async def extract_slides(file_id: str, file_path: Path, file_ext: str):
    """Extract slides from the presentation file"""
    await state_manager.update_step_status(file_id, "extract_slides", "processing")
    logger.info(f"Extracting slides for file: {file_id}")
    slides = await slide_processor.extract_slides(file_path, file_ext)
    logger.info(f"Extracted {len(slides)} slides for file: {file_id}")
    await state_manager.update_step_status(file_id, "extract_slides", "completed", slides)
    
    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if updated_state and updated_state["steps"]["extract_slides"]["status"] == "completed":
        logger.info(f"Successfully updated extract_slides to completed for {file_id}")
    else:
        logger.error(f"Failed to update extract_slides state for {file_id}")


async def analyze_slide_images(file_id: str):
    """Analyze slide images using vision service"""
    await state_manager.update_step_status(file_id, "analyze_slide_images", "processing")
    state = await state_manager.get_state(file_id)
    
    # Get slide images for analysis
    slide_images = []
    if (state and 
        "steps" in state and 
        "convert_slides_to_images" in state["steps"] and 
        state["steps"]["convert_slides_to_images"]["data"] is not None):
        slide_images = state["steps"]["convert_slides_to_images"]["data"]
    
    if not slide_images:
        raise ValueError("No slide images available for analysis")
    
    # Analyze each slide image using vision service
    image_analyses = []
    for i, image_path in enumerate(slide_images):
        analysis = await vision_service.analyze_slide_image(Path(image_path))
        image_analyses.append({"slide_number": i + 1, "analysis": analysis})
    
    await state_manager.update_step_status(file_id, "analyze_slide_images", "completed", image_analyses)


async def generate_scripts(file_id: str, language: str = "english"):
    """Generate scripts for each slide"""
    await state_manager.update_step_status(file_id, "generate_scripts", "processing")
    state = await state_manager.get_state(file_id)
    
    # Comprehensive null checking for slides data
    slides = []
    if (state and 
        "steps" in state and 
        "extract_slides" in state["steps"] and 
        state["steps"]["extract_slides"]["data"] is not None):
        slides = state["steps"]["extract_slides"]["data"]
    
    # Get image analyses if available
    image_analyses = []
    if (state and 
        "steps" in state and 
        "analyze_slide_images" in state["steps"] and 
        state["steps"]["analyze_slide_images"]["data"] is not None):
        image_analyses = state["steps"]["analyze_slide_images"]["data"]
    
    if not slides:
        raise ValueError("No slides data available for script generation")
    
    scripts = []
    for i, slide_content in enumerate(slides):
        # Get image analysis for this slide if available
        image_analysis = None
        if image_analyses and i < len(image_analyses):
            image_analysis = image_analyses[i].get("analysis") if image_analyses[i] else None
        
        script = await script_generator.generate_script(slide_content, image_analysis, language)
        scripts.append({"slide_number": i + 1, "script": script})
    
    await state_manager.update_step_status(file_id, "generate_scripts", "completed", scripts)


async def review_scripts(file_id: str, language: str = "english"):
    """Review and refine all generated scripts for consistency and smooth flow"""
    await state_manager.update_step_status(file_id, "review_scripts", "processing")
    state = await state_manager.get_state(file_id)
    
    # Get generated scripts
    scripts = []
    if (state and 
        "steps" in state and 
        "generate_scripts" in state["steps"] and 
        state["steps"]["generate_scripts"]["data"] is not None):
        scripts = state["steps"]["generate_scripts"]["data"]
    
    if not scripts:
        raise ValueError("No scripts data available for review")
    
    # Review and refine scripts for consistency
    reviewed_scripts = await _review_and_refine_scripts(scripts, language)
    
    await state_manager.update_step_status(file_id, "review_scripts", "completed", reviewed_scripts)


async def _review_and_refine_scripts(scripts: list, language: str = "english") -> list:
    """Review and refine scripts for consistency, flow, and quality"""
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Prepare all scripts as a single context
    all_scripts_text = "\n\n".join([f"Slide {i+1}: {script_data.get('script', '')}" 
                                   for i, script_data in enumerate(scripts)])
    
    # Language-specific review prompts
    review_prompts = {
        "english": "Review and refine the following presentation scripts to ensure consistency in tone, style, and smooth transitions between slides. Make sure the language flows naturally and maintains a professional yet engaging presentation style.",
        "chinese": "审查并优化以下演示文稿脚本，确保语调、风格一致，幻灯片之间过渡自然。确保语言流畅自然，保持专业而引人入胜的演示风格。",
        "japanese": "次のプレゼンテーションスクリプトをレビューし、トーン、スタイルの一貫性、スライド間のスムーズな移行を確保してください。言語が自然に流れ、専門的で魅力的なプレゼンテーションスタイルを維持していることを確認してください。",
        "korean": "다음 프레젠테이션 스크립트를 검토하여 톤, 스타일의 일관성과 슬라이드 간의 원활한 전환을 보장하세요. 언어가 자연스럽게 흐르고 전문적이면서도 매력적인 프레젠테이션 스타일을 유지하는지 확인하세요.",
        "thai": "ตรวจสอบและปรับปรุงสคริปต์การนำเสนอต่อไปนี้เพื่อให้มีความสอดคล้องกันในด้านน้ำเสียง สไตล์ และการเปลี่ยนผ่านที่ราบรื่นระหว่างสไลด์ ตรวจสอบให้แน่ใจว่าภาษาไหลไปอย่างเป็นธรรมชาติและรักษารูปแบบการนำเสนอที่เป็นมืออาชีพและน่าสนใจ"
    }
    
    system_prompts = {
        "english": "You are a professional presentation editor. Your task is to review and refine presentation scripts for consistency, flow, and quality while preserving the core content and message of each slide.",
        "chinese": "您是一位专业的演示文稿编辑。您的任务是审查和优化演示文稿脚本的一致性、流畅性和质量，同时保持每张幻灯片的核心内容和信息。",
        "japanese": "あなたはプロのプレゼンテーションエディターです。各スライドの核心的な内容とメッセージを維持しながら、プレゼンテーションスクリプトの一貫性、流れ、品質をレビューし、改善することがあなたの任務です。",
        "korean": "귀하는 전문 프레젠테이션 편집자입니다. 각 슬라이드의 핵심 내용과 메시지를 유지하면서 프레젠테이션 스크립트의 일관성, 흐름, 품질을 검토하고 개선하는 것이 귀하의 임무입니다.",
        "thai": "คุณเป็นผู้แก้ไขการนำเสนอระดับมืออาชีพ งานของคุณคือการตรวจสอบและปรับปรุงสคริปต์การนำเสนอให้มีความสอดคล้อง ไหลลื่น และมีคุณภาพ พร้อมทั้งรักษาเนื้อหาหลักและข้อความของแต่ละสไลด์ไว้"
    }
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompts.get(language, system_prompts['english'])},
                {"role": "user", "content": f"""
                {review_prompts.get(language, review_prompts['english'])}
                
                Please provide refined versions of each script that improve:
                1. Consistency in tone and terminology
                2. Smooth transitions between slides
                3. Professional yet engaging language
                4. Appropriate length (50-100 words per slide)
                
                Original scripts:
                {all_scripts_text}
                
                Please return the refined scripts in the same format as the original, with each slide clearly labeled.
                """}
            ],
            max_tokens=2000
        )
        
        reviewed_content = response.choices[0].message.content.strip()
        
        # Parse the reviewed content back into structured format
        # This is a simple parsing approach - in production, you might want more robust parsing
        reviewed_scripts = []
        lines = reviewed_content.split('\n')
        
        current_slide = None
        current_script = []
        
        for line in lines:
            if line.startswith("Slide ") or line.startswith("幻灯片 ") or line.startswith("スライド ") or line.startswith("슬라이드 "):
                # Save previous slide if exists
                if current_slide is not None:
                    reviewed_scripts.append({
                        "slide_number": current_slide,
                        "script": '\n'.join(current_script).strip()
                    })
                
                # Start new slide
                # Extract slide number from various formats
                import re
                slide_match = re.search(r'(?:Slide|幻灯片|スライド|슬라이드)\s+(\d+)', line)
                if slide_match:
                    current_slide = int(slide_match.group(1))
                    current_script = []
                else:
                    current_slide = len(reviewed_scripts) + 1 if reviewed_scripts else 1
                    current_script = [line]
            elif current_slide is not None:
                current_script.append(line)
        
        # Save last slide
        if current_slide is not None:
            reviewed_scripts.append({
                "slide_number": current_slide,
                "script": '\n'.join(current_script).strip()
            })
        
        # If parsing failed, fall back to original scripts with minor improvements
        if not reviewed_scripts:
            # Simple fallback: just return original scripts
            return scripts
            
        # Merge with original structure preserving slide numbers
        final_scripts = []
        for i, original_script in enumerate(scripts):
            if i < len(reviewed_scripts):
                final_scripts.append({
                    "slide_number": original_script.get("slide_number", i + 1),
                    "script": reviewed_scripts[i].get("script", original_script.get("script", ""))
                })
            else:
                final_scripts.append(original_script)
        
        return final_scripts
        
    except Exception as e:
        logger.error(f"Error reviewing scripts: {e}")
        # Return original scripts if review fails
        return scripts


async def generate_audio(file_id: str, language: str = "english"):
    await state_manager.update_step_status(file_id, "generate_audio", "processing")
    state = await state_manager.get_state(file_id)
    
    # Comprehensive null checking for scripts data
    scripts = []
    if (state and 
        "steps" in state and 
        "review_scripts" in state["steps"] and 
        state["steps"]["review_scripts"]["data"] is not None):
        scripts = state["steps"]["review_scripts"]["data"]
    
    if not scripts:
        raise ValueError("No scripts data available for audio generation")
    
    audio_files = []
    for i, script_data in enumerate(scripts):
        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            audio_path = Path("output") / f"{file_id}_slide_{i+1}.mp3"
            try:
                # Try OpenAI first
                await tts_service.generate_speech(script_data["script"], audio_path, provider="openai", language=language)
                audio_files.append(str(audio_path))
                logger.info(f"Generated audio for slide {i+1}: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to generate audio with OpenAI for slide {i+1}: {e}")
                # Try ElevenLabs as fallback
                try:
                    await tts_service.generate_speech(script_data["script"], audio_path, provider="elevenlabs", language=language)
                    audio_files.append(str(audio_path))
                    logger.info(f"Generated audio with ElevenLabs fallback for slide {i+1}: {audio_path}")
                except Exception as fallback_e:
                    logger.error(f"Fallback to ElevenLabs also failed for slide {i+1}: {fallback_e}")
                    raise Exception(f"Failed to generate audio for slide {i+1} with both providers: {e}")
    
    await state_manager.update_step_status(file_id, "generate_audio", "completed", audio_files)
    
    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if updated_state and updated_state["steps"]["generate_audio"]["status"] == "completed":
        logger.info(f"Successfully updated generate_audio to completed for {file_id}")
        logger.info(f"Audio files: {audio_files}")
    else:
        logger.error(f"Failed to update generate_audio state for {file_id}")


async def generate_avatar_videos(file_id: str):
    """Generate avatar videos from scripts"""
    await state_manager.update_step_status(file_id, "generate_avatar_videos", "processing")
    state = await state_manager.get_state(file_id)
    
    # Comprehensive null checking for scripts data
    scripts = []
    if (state and 
        "steps" in state and 
        "review_scripts" in state["steps"] and 
        state["steps"]["review_scripts"]["data"] is not None):
        scripts = state["steps"]["review_scripts"]["data"]
    
    if not scripts:
        raise ValueError("No scripts data available for avatar video generation")
    
    avatar_videos = []
    for i, script_data in enumerate(scripts):
        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            video_path = Path("output") / f"{file_id}_avatar_{i+1}.mp4"
            try:
                await avatar_service.generate_avatar_video(
                    script_data["script"], video_path, 
                    provider="heygen",  # Use HeyGen as primary
                    fallback_to_alternative=True  # Fallback to alternative if HeyGen fails
                )
                avatar_videos.append(str(video_path))
                logger.info(f"Generated avatar video for slide {i+1}: {video_path}")
            except Exception as e:
                logger.error(f"Failed to generate avatar video for slide {i+1}: {e}")
                raise
    
    await state_manager.update_step_status(file_id, "generate_avatar_videos", "completed", avatar_videos)
    
    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if updated_state and updated_state["steps"]["generate_avatar_videos"]["status"] == "completed":
        logger.info(f"Successfully updated generate_avatar_videos to completed for {file_id}")
        logger.info(f"Avatar videos: {avatar_videos}")
    else:
        logger.error(f"Failed to update generate_avatar_videos state for {file_id}")


async def convert_slides_to_images(file_id: str, file_path: Path, file_ext: str):
    """Convert slides to images"""
    await state_manager.update_step_status(file_id, "convert_slides_to_images", "processing")
    slide_images = []
    state = await state_manager.get_state(file_id)
    
    # Safely get slides data with comprehensive null checking
    slides = []
    if (state and 
        "steps" in state and 
        "extract_slides" in state["steps"] and 
        state["steps"]["extract_slides"]["data"] is not None):
        slides = state["steps"]["extract_slides"]["data"]
    
    if not slides:
        raise ValueError("No slides data available for conversion to images")
    
    for i in range(len(slides)):
        image_path = Path("output") / f"{file_id}_slide_{i+1}.png"
        await slide_processor.convert_to_image(Path(file_path), file_ext, i, image_path)
        slide_images.append(str(image_path))
    
    await state_manager.update_step_status(file_id, "convert_slides_to_images", "completed", slide_images)


async def compose_video(file_id: str, file_path: Path):
    """Compose the final video from all components"""
    await state_manager.update_step_status(file_id, "compose_video", "processing")
    state = await state_manager.get_state(file_id)
    
    # Comprehensive null checking for all required data
    slide_images_data = []
    avatar_videos_data = []
    audio_files_data = []
    
    if (state and 
        "steps" in state and 
        "convert_slides_to_images" in state["steps"] and 
        state["steps"]["convert_slides_to_images"]["data"] is not None):
        slide_images_data = state["steps"]["convert_slides_to_images"]["data"]
    
    if (state and 
        "steps" in state and 
        "generate_avatar_videos" in state["steps"] and 
        state["steps"]["generate_avatar_videos"]["data"] is not None):
        avatar_videos_data = state["steps"]["generate_avatar_videos"]["data"]
    
    if (state and 
        "steps" in state and 
        "generate_audio" in state["steps"] and 
        state["steps"]["generate_audio"]["data"] is not None):
        audio_files_data = state["steps"]["generate_audio"]["data"]
    
    # Validate all required data exists
    if not slide_images_data:
        raise ValueError("No slide images data available for video composition")
    if not audio_files_data:
        raise ValueError("No audio files data available for video composition")
    
    slide_images = [Path(p) for p in slide_images_data]
    audio_files = [Path(p) for p in audio_files_data]
    
    final_video_path = Path("output") / f"{file_id}_final.mp4"
    
    # Use avatar videos if available, otherwise create simple video
    if avatar_videos_data:
        logger.info("Avatar videos found, creating full presentation with avatars")
        avatar_videos = [Path(p) for p in avatar_videos_data]
        await video_composer.compose_video(slide_images, avatar_videos, audio_files, final_video_path)
    else:
        logger.warning("No avatar videos available, creating simple presentation without avatars")
        await video_composer.create_simple_video(slide_images, audio_files, final_video_path)
    
    await state_manager.update_step_status(file_id, "compose_video", "completed", str(final_video_path))
    await state_manager.mark_completed(file_id)
    
    # Cleanup temporary files
    temp_files = audio_files + slide_images
    if avatar_videos_data:
        avatar_videos = [Path(p) for p in avatar_videos_data]
        temp_files += avatar_videos
        
    for temp_file in temp_files:
        if Path(temp_file).exists():
            Path(temp_file).unlink()
    
    if Path(file_path).exists():
        Path(file_path).unlink()