import logging
from typing import Optional
from ai.image_ai_service import generate_image
from models import GameSettings
from utilities.image_context_enum import ImageContextEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_appropriate_image(settings: GameSettings, context: ImageContextEnum, story_text: str, chapter_summary: Optional[str]=None, chapter_title: Optional[str]=None, party_description: Optional[str]=None):
    """Generate an appropriate image based on context and available information"""
    if not settings.enableImages:
        return None
    
    try:
        image_prompt = None
        
        if context == ImageContextEnum.CHAPTER_TRANSITION and chapter_summary and chapter_title:
            # Transition between chapters
            image_prompt = f"Fantasy D&D scene showing transition: {chapter_summary} → {chapter_title} - {story_text[:100]}"
            image_prompt = _create_enhanced_image_prompt_for_chapter_transition(image_prompt)
        elif context == ImageContextEnum.CHAPTER_TRANSITION and chapter_title and party_description:
            # New chapter without previous summary
            image_prompt = f"Fantasy D&D scene for '{chapter_title}' showing the party: {party_description}"
            image_prompt = _create_enhanced_image_prompt_for_chapter_transition(image_prompt)
        elif context == ImageContextEnum.CHAPTER_SUMMARY and chapter_summary:
            image_prompt = f"Fantasy illustration of: {chapter_summary}"
            image_prompt = _create_enhanced_image_prompt_for_generic_story(image_prompt)
        else:
            # Generic story illustration
            image_prompt = story_text[:200]
            image_prompt = _create_enhanced_image_prompt_for_generic_story(image_prompt)
            
        logger.info(f"Generating image with context '{context}' and prompt: {image_prompt[:50]}...")
        return await generate_image(image_prompt)
    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        return None
    
def _create_enhanced_image_prompt_for_chapter_transition(prompt: str):
    enhanced_prompt = f"fantasy art, dungeons and dragons style, detailed, story transition, narrative continuity, same characters in new situation, {prompt}"
    enhanced_prompt += ", detailed background, dramatic lighting, seamless storytelling, character consistency"
    return enhanced_prompt

def _create_enhanced_image_prompt_for_generic_story(prompt: str):
    enhanced_prompt = f"fantasy art, dungeons and dragons style, detailed, dynamic scene, action shot, {prompt}"
    enhanced_prompt += ", vibrant lighting, dramatic composition, high quality, highly detailed"
    return enhanced_prompt