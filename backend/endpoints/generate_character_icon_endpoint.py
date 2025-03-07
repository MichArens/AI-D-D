import logging

from fastapi import HTTPException


from ai.image_ai_service import generate_image
from models import CharacterIconRequest, PlayerCharacter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_character_icon(request: CharacterIconRequest):
    """Generate a character icon based on character details"""
    character = request.character
    prompt = _create_character_icon_prompt(character)
    
    try:
        icon_base64 = await _generate_character_icon_for_game(prompt)
        return {"icon": icon_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate character icon: {str(e)}")

def _create_character_icon_prompt(character: PlayerCharacter):
    return f"Portrait of a {character.race} {character.characterClass}, {character.gender} named {character.name} in a fantasy D&D style"

async def _generate_character_icon_for_game(prompt: str):
    enhanced_prompt = f"fantasy art, dungeons and dragons style, detailed, dynamic scene, action shot, {prompt}"
    enhanced_prompt += ", vibrant lighting, dramatic composition, high quality, highly detailed"
    return await generate_image(enhanced_prompt)
