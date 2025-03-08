import logging
import traceback
from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel

from ai.text_ai_service import generate_text
from ai.image_ai_service import generate_image
from ai.music_ai_service import generate_music
from models import GameSettings, PlayerCharacter, StoryChapter, StoryScene
from utilities.prompt_constants import PromptConstants
from utilities.prompt_utils import generate_fallback_actions, get_dnd_master_description, maybe_generate_tts, parse_story_and_actions


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StartGameRequest(BaseModel):
    settings: GameSettings
    characters: List[PlayerCharacter]

class StartGameResponse(BaseModel):
    initialChapter: StoryChapter
    musicUrl: Optional[str] = None
    
async def start_game(request: StartGameRequest, background_tasks: BackgroundTasks):
    """Initialize the game with the first story segment and action choices"""
    logger.info(f"Starting game with settings: {request.settings} and characters: {request.characters}")
    model = request.settings.aiModel
    enable_tts = request.settings.enableAITTS
    
    party_description = _create_party_description(request.characters)
    chapter_prompt = _create_chapter_title_prompt(party_description)
    try:
        chapter_title = await generate_text(chapter_prompt, model)
        chapter_title = chapter_title.strip().strip('"').strip("'")
        
        first_chapter = StoryChapter(
            title=chapter_title,
            scenes=[]
        )
        
        prompt = _create_initial_story_prompt(request.characters[0], party_description, chapter_title)
        first_story_text = await generate_text(prompt, model)
        
        next_story_part, next_actions = parse_story_and_actions(first_story_text)
        
        if not next_story_part or len(next_actions) != 3:
            print(PromptConstants.ACTIONS, len(next_actions), first_story_text)
            parts = first_story_text.split("\n\n")
            next_story_part = parts[0]
            next_actions = generate_fallback_actions(parts)
        
        image_base64 = await _generate_image_for_starT_game(request.settings.enableImages, next_story_part)
        
        audio_data = await maybe_generate_tts(next_story_part, enable_tts)
        
        music_url = None
        if request.settings.enableMusic:
            background_tasks.add_task(generate_music, next_story_part[:100])
        
        initial_scene = StoryScene(
            text=next_story_part,
            image=image_base64,
            choices=next_actions,
            audioData = audio_data,
            choosingPlayer=request.characters[0]
        )
        
        # Update first chapter with segment index
        first_chapter.scenes.append(initial_scene)
        
        return StartGameResponse(
            initialChapter = first_chapter,
            musicUrl =music_url,
        )
    
    except Exception as e:
        logger.error(traceback.print_exc())
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")

def _create_party_description(characters: List[PlayerCharacter]):
    character_descriptions = []
    for char in characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass}, {char.gender}")
    
    party_description = ", ".join(character_descriptions)
    return party_description

def _create_chapter_title_prompt(party_description: str):
    return f"""
    {get_dnd_master_description("for a new D&D adventure")}. Create an engaging chapter title for the beginning of an adventure
    with a party consisting of: {party_description}
    
    The title should be short (5-7 words) and evocative. Format your response with just the title, no additional text.
    """

def _create_initial_story_prompt(first_character: PlayerCharacter, party_description: str, chapter_title: str):
    return f"""
        {get_dnd_master_description("for a new D&D adventure")}. Create an engaging opening scene for a party consisting of:
        {party_description}
        
        This is Chapter 1: "{chapter_title}" of the adventure.
        
        IMPORTANT INSTRUCTIONS:
        - Provide a vivid description of the initial setting and situation in 2-3 paragraphs only.
        - Introduce an immediate situation that requires action.
        
        Then, generate exactly 3 possible actions that ONLY the first player ({first_character.name} the {first_character.race} {first_character.characterClass}, {first_character.gender}) could take.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your engaging opening scene here]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {first_character.name} ONLY]
        2. [Second action choice for {first_character.name} ONLY]
        3. [Third action choice for {first_character.name} ONLY]
        """

async def _generate_image_for_starT_game(enableImages: bool, next_story_part: str):
    image_base64 = None
    if enableImages:
        prompt = next_story_part[:200]
        enhanced_prompt = f"fantasy art, dungeons and dragons style, establishing shot, new adventure beginning, fresh start, {prompt}"
        enhanced_prompt += ", vibrant colors, wide landscape view, new horizon, detailed environment, adventure awaits"
        image_base64 = await generate_image(enhanced_prompt) 
    return image_base64
