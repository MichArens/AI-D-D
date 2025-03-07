import logging
from typing import List

from fastapi import BackgroundTasks, HTTPException

from ai.text_ai_service import generate_text
from ai.image_ai_service import generate_image
from ai.music_ai_service import generate_music
from models import Chapter, GameState, PlayerCharacter, StoryProgression
from utilities.prompt_constants import PromptConstants
from utilities.prompt_utils import generate_fallback_actions, get_dnd_master_description, maybe_generate_tts, parse_story_and_actions


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_game(game_state: GameState, background_tasks: BackgroundTasks):
    """Initialize the game with the first story segment and action choices"""
    model = game_state.settings.aiModel
    enable_tts = game_state.settings.enableAITTS
    
    party_description = create_party_description(game_state.characters)
    chapter_prompt = create_chapter_title_prompt(party_description)
    try:
        chapter_title = await generate_text(chapter_prompt, model)
        chapter_title = chapter_title.strip().strip('"').strip("'")
        
        first_chapter = Chapter(
            id=0,
            title=chapter_title,
            segments=[]
        )
        
        prompt = create_initial_story_prompt(game_state, party_description, chapter_title)
        first_story_text = await generate_text(prompt, model)
        
        next_story_part, next_actions = parse_story_and_actions(first_story_text)
        
        if not next_story_part or len(next_actions) != 3:
            print(PromptConstants.ACTIONS, len(next_actions), first_story_text)
            parts = first_story_text.split("\n\n")
            next_story_part = parts[0]
            next_actions = generate_fallback_actions(parts)
        
        image_base64 = None
        if game_state.settings.enableImages:
            image_base64 = await generate_image(next_story_part[:200]) 
        
        audio_data = await maybe_generate_tts(next_story_part, enable_tts)
        
        music_url = None
        if game_state.settings.enableMusic:
            background_tasks.add_task(generate_music, next_story_part[:100])
        
        initial_story = StoryProgression(
            text = next_story_part,
            image = image_base64,
            player = None,
            action = None,
            chapterId = 0,
            audioData = audio_data  # Include pre-generated TTS
        )
        
        # Update first chapter with segment index
        first_chapter.segments.append(0)
        
        # Return the full response including the first chapter
        return {
            "storyUpdate": initial_story,
            "choices": next_actions,
            "musicUrl": music_url,
            "chapter": first_chapter
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")

def create_party_description(characters: List[PlayerCharacter]):
    character_descriptions = []
    for char in characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass}, {char.gender}")
    
    party_description = ", ".join(character_descriptions)
    return party_description

def create_chapter_title_prompt(party_description: str):
    return f"""
    {get_dnd_master_description("for a new D&D adventure")}. Create an engaging chapter title for the beginning of an adventure
    with a party consisting of: {party_description}
    
    The title should be short (5-7 words) and evocative. Format your response with just the title, no additional text.
    """

def create_initial_story_prompt(game_state: GameState, party_description: str, chapter_title: str):
    return f"""
        {get_dnd_master_description("for a new D&D adventure")}. Create an engaging opening scene for a party consisting of:
        {party_description}
        
        This is Chapter 1: "{chapter_title}" of the adventure.
        
        IMPORTANT INSTRUCTIONS:
        - Provide a vivid description of the initial setting and situation in 2-3 paragraphs only.
        - Introduce an immediate situation that requires action.
        
        Then, generate exactly 3 possible actions that ONLY the first player ({game_state.characters[0].name} the {game_state.characters[0].race} {game_state.characters[0].characterClass}, {game_state.characters[0].gender}) could take.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your engaging opening scene here]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {game_state.characters[0].name} ONLY]
        2. [Second action choice for {game_state.characters[0].name} ONLY]
        3. [Third action choice for {game_state.characters[0].name} ONLY]
        """
