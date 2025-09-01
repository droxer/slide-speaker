import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ScriptGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def _detect_language(self, text: str) -> str:
        """Detect the primary language of the slide content"""
        # Simple language detection based on character patterns
        if not text.strip():
            return "english"
        
        # Check for Chinese characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return "chinese"
        
        # Check for Japanese characters
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', text):
            return "japanese"
        
        # Check for Korean characters
        if re.search(r'[\uac00-\ud7a3]', text):
            return "korean"
        
        # Default to English for Latin script and others
        return "english"
    
    async def generate_script(self, slide_content: str, image_analysis: dict = None, language: str = "english") -> str:
        if not slide_content.strip() and not image_analysis:
            return "This slide contains visual content that will be presented."
        
        # Use image analysis if available, otherwise use text content
        content_to_use = slide_content
        if image_analysis and image_analysis.get('text_content'):
            content_to_use = image_analysis['text_content']
        
        # Language-specific prompts
        language_prompts = {
            "english": "Create a natural, engaging presentation script in English based on the following slide content analysis.",
            "chinese": "根据以下幻灯片内容分析，创建一个自然、吸引人的中文演示脚本。",
            "japanese": "以下のスライド内容分析に基づいて、自然で魅力的な日本語のプレゼンテーションスクリプトを作成してください。",
            "korean": "다음 슬라이드 내용 분석을 바탕으로 자연스럽고 매력적인 한국어 프레젠테이션 스크립트를 작성해 주세요."
        }
        
        # Enhanced prompt with image analysis context
        prompt_context = ""
        if image_analysis:
            prompt_context = f"""
Visual Analysis Context:
- Main Topic: {image_analysis.get('main_topic', 'Unknown')}
- Key Points: {', '.join(image_analysis.get('key_points', []))}
- Visual Elements: {', '.join(image_analysis.get('visual_elements', []))}
- Structure: {image_analysis.get('structure', 'standard')}
"""
        
        prompt = f"""
        {language_prompts.get(language, language_prompts['english'])}
        The script should be suitable for a professional AI avatar to deliver.
        Keep it concise (50-100 words), clear, and engaging.
        
        {prompt_context}
        
        Slide content:
        {content_to_use}
        
        Script:
        """
        
        # Language-specific system prompts
        system_prompts = {
            "english": "You are a professional presentation script writer. Create concise, engaging scripts for AI avatars based on slide content analysis.",
            "chinese": "你是一名专业的演示脚本撰写人。基于幻灯片内容分析为AI虚拟形象创建简洁、吸引人的中文脚本。",
            "japanese": "あなたはプロのプレゼンテーションスクリプトライターです。スライド内容分析に基づいてAIアバター用の簡潔で魅力的な日本語スクリプトを作成してください。",
            "korean": "당신은 전문 프레젠테이션 스크립트 작가입니다. 슬라이드 내용 분석을 바탕으로 AI 아바타를 위한 간결하고 매력적인 한국어 스크립트를 작성해 주세요."
        }
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use more capable model for better script generation
                messages=[
                    {"role": "system", "content": system_prompts.get(language, system_prompts['english'])},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            script = response.choices[0].message.content.strip()
            
            # Fallback scripts in different languages
            fallback_scripts = {
                "english": "Let me walk you through this important content.",
                "chinese": "让我为您介绍这一重要内容。",
                "japanese": "この重要な内容についてご説明します。",
                "korean": "이 중요한 내용을 설명해 드리겠습니다."
            }
            
            return script if script else fallback_scripts.get(language, "Let me walk you through this important content.")
            
        except Exception as e:
            print(f"Error generating script: {e}")
            # Fallback script based on detected language
            fallback_content = content_to_use[:100] if content_to_use else "visual content"
            fallback_scripts = {
                "english": f"In this slide, we'll discuss: {fallback_content}...",
                "chinese": f"在本幻灯片中，我们将讨论：{fallback_content[:50]}...",
                "japanese": f"このスライドでは、{fallback_content[:50]}...について説明します",
                "korean": f"이 슬라이드에서는 {fallback_content[:50]}...에 대해 논의하겠습니다"
            }
            return fallback_scripts.get(language, f"In this slide, we'll discuss: {fallback_content}...")