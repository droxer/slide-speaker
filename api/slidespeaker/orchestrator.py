from pathlib import Path
from loguru import logger

from slidespeaker.slide_processor import SlideProcessor
from slidespeaker.script_generator import ScriptGenerator
from slidespeaker.tts_service import TTSService
from slidespeaker.avatar_service_unified import UnifiedAvatarService
from slidespeaker.video_composer import VideoComposer
from slidespeaker.subtitle_generator import SubtitleGenerator
from slidespeaker.video_previewer import VideoPreviewer
from slidespeaker.state_manager import state_manager
from slidespeaker.vision_service import VisionService

slide_processor = SlideProcessor()
script_generator = ScriptGenerator()
tts_service = TTSService()
avatar_service = UnifiedAvatarService()
video_composer = VideoComposer()
subtitle_generator = SubtitleGenerator()
video_previewer = VideoPreviewer()
vision_service = VisionService()

async def process_presentation(file_id: str, file_path: Path, file_ext: str, language: str = "english", 
                             subtitle_language: str = None, generate_avatar: bool = True, 
                             generate_subtitles: bool = True, task_id: str = None):
    """State-aware processing that can resume from any step"""
    # Don't default subtitle language to audio language - preserve user selection
    # subtitle_language remains as provided (could be None)
    
    logger.info(f"Initiating AI presentation generation for file: {file_id}, format: {file_ext}")
    logger.info(f"Audio language: {language}, Subtitle language: {subtitle_language}")
    logger.info(f"Generate avatar: {generate_avatar}, Generate subtitles: {generate_subtitles}")
    
    # Check if task has been cancelled before starting (if task_id provided)
    if task_id:
        task_status = await state_manager.get_state(f"task_{task_id}")
        if task_status and task_status.get("status") == "cancelled":
            logger.info(f"Task {task_id} was cancelled before processing started")
            await state_manager.mark_failed(file_id)
            return


    # Initialize state
    state = await state_manager.get_state(file_id)
    if not state:
        await state_manager.create_state(file_id, file_path, file_ext, language, subtitle_language, generate_avatar, generate_subtitles)
        state = await state_manager.get_state(file_id)
    else:
        # Update existing state with new parameters (in case they've changed)
        state["audio_language"] = language
        state["subtitle_language"] = subtitle_language
        state["generate_avatar"] = generate_avatar
        state["generate_subtitles"] = generate_subtitles
        await state_manager._save_state(file_id, state)
    
    # Log initial state
    if state:
        logger.info(f"Current processing status: {state['status']}")
        for step_name, step_data in state["steps"].items():
            step_display_names = {
                "extract_slides": "Extracting presentation content",
                "convert_slides_to_images": "Converting slides to images",
                "analyze_slide_images": "Analyzing visual content",
                "generate_scripts": "Generating AI narratives",
                "generate_subtitle_scripts": "Generating subtitle narratives",
                "review_scripts": "Reviewing and refining scripts",
                "review_subtitle_scripts": "Reviewing subtitle scripts",
                "generate_audio": "Synthesizing voice audio",
                "generate_avatar_videos": "Creating AI presenter videos",
                "compose_video": "Composing final presentation"
            }
            display_name = step_display_names.get(step_name, step_name)
            status_text = step_data['status']
            if status_text == "skipped":
                status_text = "Skipped (disabled)"
            logger.info(f"Stage '{display_name}': {status_text}")
    else:
        logger.info(f"No existing processing state found for {file_id}")
    
    # Define processing steps in order
    steps_order = [
        "extract_slides",
        "convert_slides_to_images",
        "analyze_slide_images",
        "generate_scripts", 
        "review_scripts"  # Review scripts for audio language
    ]
    
    # Add subtitle script generation steps only if languages are different
    if language != subtitle_language:
        steps_order.extend([
            "generate_subtitle_scripts",
            "review_subtitle_scripts"
        ])
    
    # Continue with audio and video generation
    steps_order.extend([
        "generate_audio"
    ])
    
    # Add avatar generation step only if enabled
    if generate_avatar:
        steps_order.append("generate_avatar_videos")
    
    # Always add compose video step
    steps_order.append("compose_video")
    
    try:
        # Process each step in order, skipping completed ones
        for step_name in steps_order:
            # Check for cancellation before processing each step
            if task_id:
                task_status = await state_manager.get_state(f"task_{task_id}")
                if task_status and task_status.get("status") == "cancelled":
                    logger.info(f"Task {task_id} was cancelled during processing")
                    await state_manager.mark_failed(file_id)
                    return
                
            await _process_step(file_id, file_path, file_ext, step_name, language, task_id=task_id)
        
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


async def _process_step(file_id: str, file_path: Path, file_ext: str, step_name: str, language: str = "english", task_id: str = None):
    """Process a single step in the presentation pipeline"""
    # Check for cancellation before processing the step
    if task_id:
        task_status = await state_manager.get_state(f"task_{task_id}")
        if task_status and task_status.get("status") == "cancelled":
            logger.info(f"Task {task_id} was cancelled during step {step_name}")
            await state_manager.mark_failed(file_id)
            return
        
    # Get fresh state
    state = await state_manager.get_state(file_id)
    
    # Get subtitle language from state
    subtitle_language = None
    if state and "subtitle_language" in state:
        subtitle_language = state["subtitle_language"]
    # Default to audio language if subtitle language not specified
    if subtitle_language is None:
        subtitle_language = language
    
    # Skip completed steps
    if state and state["steps"][step_name]["status"] == "completed":
        step_display_names = {
            "extract_slides": "Extracting presentation content",
            "convert_slides_to_images": "Converting slides to images",
            "analyze_slide_images": "Analyzing visual content",
            "generate_scripts": "Generating AI narratives",
            "generate_subtitle_scripts": "Generating subtitle narratives",
            "review_scripts": "Reviewing and refining scripts",
            "review_subtitle_scripts": "Reviewing subtitle scripts",
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
            "generate_subtitle_scripts": "Generating subtitle narratives",
            "review_scripts": "Reviewing and refining scripts",
            "review_subtitle_scripts": "Reviewing subtitle scripts",
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
        elif step_name == "generate_subtitle_scripts":
            await generate_scripts(file_id, subtitle_language, is_subtitle=True)
        elif step_name == "review_scripts":
            await review_scripts(file_id, language)
        elif step_name == "review_subtitle_scripts":
            await review_scripts(file_id, subtitle_language, is_subtitle=True)
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


async def generate_scripts(file_id: str, language: str = "english", is_subtitle: bool = False):
    """Generate scripts for each slide"""
    step_name = "generate_subtitle_scripts" if is_subtitle else "generate_scripts"
    await state_manager.update_step_status(file_id, step_name, "processing")
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
    
    await state_manager.update_step_status(file_id, step_name, "completed", scripts)


async def review_scripts(file_id: str, language: str = "english", is_subtitle: bool = False):
    """Review and refine all generated scripts for consistency and smooth flow"""
    step_name = "review_subtitle_scripts" if is_subtitle else "review_scripts"
    await state_manager.update_step_status(file_id, step_name, "processing")
    state = await state_manager.get_state(file_id)
    
    # Get generated scripts from the appropriate step
    source_step = "generate_subtitle_scripts" if is_subtitle else "generate_scripts"
    scripts = []
    if (state and 
        "steps" in state and 
        source_step in state["steps"] and 
        state["steps"][source_step]["data"] is not None):
        scripts = state["steps"][source_step]["data"]
    
    if not scripts:
        raise ValueError("No scripts data available for review")
    
    # Review and refine scripts for consistency
    reviewed_scripts = await _review_and_refine_scripts(scripts, language)
    
    await state_manager.update_step_status(file_id, step_name, "completed", reviewed_scripts)


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
        logger.info(f"Script review response received: {reviewed_content}")
        
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
        
        # If parsing failed or resulted in empty scripts, fall back to original scripts with minor improvements
        if not reviewed_scripts or all(not script.get("script", "") for script in reviewed_scripts):
            # Simple fallback: just return original scripts
            logger.info("Script review parsing failed or resulted in empty scripts, returning original scripts")
            return scripts
            
        # Merge with original structure preserving slide numbers
        final_scripts = []
        for i, original_script in enumerate(scripts):
            if i < len(reviewed_scripts):
                # Make sure we have content, if not fall back to original
                reviewed_script_content = reviewed_scripts[i].get("script", "")
                if reviewed_script_content:
                    final_scripts.append({
                        "slide_number": original_script.get("slide_number", i + 1),
                        "script": reviewed_script_content
                    })
                else:
                    # If reviewed script is empty, use original
                    final_scripts.append({
                        "slide_number": original_script.get("slide_number", i + 1),
                        "script": original_script.get("script", "")
                    })
            else:
                final_scripts.append(original_script)
        
        logger.info(f"Final reviewed scripts: {final_scripts}")
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
            script_text = script_data["script"].strip()
            if script_text:  # Only generate audio if script is not empty
                audio_path = Path(__file__).parent.parent / "output" / f"{file_id}_slide_{i+1}.mp3"
                try:
                    # Try OpenAI first
                    await tts_service.generate_speech(script_text, audio_path, provider="openai", language=language)
                    audio_files.append(str(audio_path))
                    logger.info(f"Generated audio for slide {i+1}: {audio_path}")
                except Exception as e:
                    logger.error(f"Failed to generate audio with OpenAI for slide {i+1}: {e}")
                    # Try ElevenLabs as fallback
                    try:
                        await tts_service.generate_speech(script_text, audio_path, provider="elevenlabs", language=language)
                        audio_files.append(str(audio_path))
                        logger.info(f"Generated audio with ElevenLabs fallback for slide {i+1}: {audio_path}")
                    except Exception as fallback_e:
                        logger.error(f"Fallback to ElevenLabs also failed for slide {i+1}: {fallback_e}")
                        raise Exception(f"Failed to generate audio for slide {i+1} with both providers: {e}")
            else:
                logger.warning(f"Skipping audio generation for slide {i+1} due to empty script")
        else:
            logger.warning(f"Skipping audio generation for slide {i+1} due to missing or empty script data")
    
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
    
    # Check if avatar generation is enabled
    generate_avatar = True
    if state and "generate_avatar" in state:
        generate_avatar = state["generate_avatar"]
    
    # If avatar generation is disabled, skip this step
    if not generate_avatar:
        logger.info("Avatar generation disabled, skipping avatar video generation")
        await state_manager.update_step_status(file_id, "generate_avatar_videos", "completed", [])
        return
    
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
    failed_slides = []
    
    for i, script_data in enumerate(scripts):
        # Additional null check for individual script data
        if script_data and "script" in script_data and script_data["script"]:
            video_path = Path(__file__).parent.parent / "output" / f"{file_id}_avatar_{i+1}.mp4"
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
                failed_slides.append(i+1)
                # Continue with other slides instead of failing completely
                continue
    
    # If all slides failed, raise an error
    if len(failed_slides) == len(scripts):
        raise Exception(f"Failed to generate avatar videos for all slides: {failed_slides}")
    
    # Log partial failures
    if failed_slides:
        logger.warning(f"Failed to generate avatar videos for slides: {failed_slides}. Continuing with remaining slides.")
    
    await state_manager.update_step_status(file_id, "generate_avatar_videos", "completed", avatar_videos)
    
    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if updated_state and updated_state["steps"]["generate_avatar_videos"]["status"] == "completed":
        logger.info(f"Successfully updated generate_avatar_videos to completed for {file_id}")
        logger.info(f"Avatar videos: {avatar_videos}")
        if failed_slides:
            logger.info(f"Failed slides: {failed_slides}")
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
        image_path = Path(__file__).parent.parent / "output" / f"{file_id}_slide_{i+1}.png"
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
    scripts_data = []
    
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
    
    # Get scripts for subtitle generation
    # Use subtitle-specific scripts if they exist (when languages differ), otherwise use regular scripts
    scripts_data = []
    if (state and "steps" in state):
        # Check if subtitle scripts exist (languages are different)
        if ("review_subtitle_scripts" in state["steps"] and 
            state["steps"]["review_subtitle_scripts"]["data"] is not None):
            scripts_data = state["steps"]["review_subtitle_scripts"]["data"]
            logger.info("Using subtitle-specific scripts for subtitle generation")
        # Fall back to regular scripts if subtitle scripts don't exist
        elif ("review_scripts" in state["steps"] and 
              state["steps"]["review_scripts"]["data"] is not None):
            scripts_data = state["steps"]["review_scripts"]["data"]
            logger.info("Using regular scripts for subtitle generation")
    
    # Get subtitle language and generation flag from state
    subtitle_language = None
    generate_subtitles = True
    if state and "subtitle_language" in state:
        subtitle_language = state["subtitle_language"]  # Preserve user selection
    # Default to audio language if subtitle language not specified
    if subtitle_language is None:
        subtitle_language = language
    if state and "generate_subtitles" in state:
        generate_subtitles = state["generate_subtitles"]
    
    logger.info(f"Subtitle settings - Language: {subtitle_language}, Generate: {generate_subtitles}")
    
    # Validate all required data exists
    if not slide_images_data:
        raise ValueError("No slide images data available for video composition")
    # Audio files are optional - we can create a video without them
    
    slide_images = [Path(p) for p in slide_images_data]
    audio_files = [Path(p) for p in audio_files_data]
    
    # Use absolute path to ensure consistency with main.py
    final_video_path = Path(__file__).parent.parent / "output" / f"{file_id}_final.mp4"
    
    # Generate subtitles before composing video (if enabled)
    if scripts_data and generate_subtitles:
        try:
            logger.info(f"Generating subtitles for {len(scripts_data)} scripts in language: {subtitle_language}")
            logger.info(f"Final video path: {final_video_path}")
            
            # If we have no audio files, we need to provide estimated durations
            if not audio_files_data:
                logger.info("No audio files available, using estimated durations for subtitles")
                # Create a list of dummy paths for estimated durations (5 seconds each)
                # The subtitle generator will handle non-existent files by using default durations
                estimated_audio_files = [Path(f"/tmp/dummy_audio_{i}.mp3") for i in range(len(scripts_data))]
                srt_path, vtt_path = subtitle_generator.generate_subtitles(scripts_data, estimated_audio_files, final_video_path, subtitle_language)
            else:
                srt_path, vtt_path = subtitle_generator.generate_subtitles(scripts_data, audio_files, final_video_path, subtitle_language)
            logger.info(f"Generated subtitles: {srt_path}, {vtt_path}")
            
            # Verify files were created
            import os
            if os.path.exists(srt_path):
                srt_size = os.path.getsize(srt_path)
                logger.info(f"SRT file created successfully: {srt_path}, size: {srt_size} bytes")
                # Log first few lines for debugging
                try:
                    with open(srt_path, 'r', encoding='utf-8') as f:
                        first_lines = f.read(500)
                        logger.info(f"SRT file first 500 chars: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading SRT file: {e}")
            else:
                logger.error(f"SRT file not found: {srt_path}")
                
            if os.path.exists(vtt_path):
                vtt_size = os.path.getsize(vtt_path)
                logger.info(f"VTT file created successfully: {vtt_path}, size: {vtt_size} bytes")
                # Log first few lines for debugging
                try:
                    with open(vtt_path, 'r', encoding='utf-8') as f:
                        first_lines = f.read(500)
                        logger.info(f"VTT file first 500 chars: {first_lines}")
                except Exception as e:
                    logger.error(f"Error reading VTT file: {e}")
            else:
                logger.error(f"VTT file not found: {vtt_path}")
        except Exception as e:
            logger.error(f"Failed to generate subtitles: {e}")
            import traceback
            logger.error(f"Subtitle generation traceback: {traceback.format_exc()}")
            # If subtitles are required and generation fails, we should raise an exception
            # to prevent continuing with the video composition
            if generate_subtitles:
                raise Exception(f"Failed to generate subtitles: {e}")
    elif not generate_subtitles:
        logger.info("Subtitle generation disabled, skipping subtitle generation")
    
    # Check if avatar generation was enabled and completed
    avatar_generation_enabled = True
    if state and "generate_avatar" in state:
        avatar_generation_enabled = state["generate_avatar"]
    
    # Use avatar videos if available and enabled, otherwise create simple video
    if avatar_videos_data and avatar_generation_enabled:
        logger.info("Avatar videos found, creating full presentation with avatars")
        avatar_videos = [Path(p) for p in avatar_videos_data]
        await video_composer.compose_video(slide_images, avatar_videos, audio_files, final_video_path)
    else:
        if avatar_generation_enabled:
            logger.warning("No avatar videos available, creating simple presentation without avatars")
        else:
            logger.info("Avatar generation disabled, creating simple presentation without avatars")
        
        # Create video based on whether we have audio files or not
        if audio_files_data:
            await video_composer.create_simple_video(slide_images, audio_files, final_video_path)
        else:
            logger.info("No audio files available, creating images-only video")
            await video_composer.create_images_only_video(slide_images, final_video_path)
    
    await state_manager.update_step_status(file_id, "compose_video", "completed", str(final_video_path))
    await state_manager.mark_completed(file_id)
    
    # Generate preview data
    try:
        preview_data = video_previewer.generate_preview_data(file_id, Path(__file__).parent.parent / "output", subtitle_language)
        logger.info(f"Generated preview data: {preview_data}")
    except Exception as e:
        logger.error(f"Failed to generate preview data: {e}")
    
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