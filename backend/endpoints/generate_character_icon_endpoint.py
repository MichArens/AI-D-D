import logging

from fastapi import HTTPException

from ai_services import generate_image
from models import CharacterIconRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_character_icon(request: CharacterIconRequest):
    """Generate a character icon based on character details"""
    character = request.character
    prompt = f"Portrait of a {character.race} {character.characterClass}, {character.gender} named {character.name} in a fantasy D&D style"
    
    try:
        icon_base64 = await generate_image(prompt)
        return {"icon": icon_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate character icon: {str(e)}")
