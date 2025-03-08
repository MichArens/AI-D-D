import logging
import traceback
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel

from ai.text_ai_service import generate_text
from utilities.prompt_constants import PromptConstants
from models import GameSettings, GameState, PlayerCharacter, StoryChapter, StoryScene, StroyArc
from utilities.image_generation_utils import generate_appropriate_image
from utilities.image_context_enum import ImageContextEnum
from utilities.prompt_utils import generate_fallback_actions, get_dnd_master_description, maybe_generate_tts, parse_story_and_actions


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewChapterRequest(BaseModel):
    gameState: GameState
    
    class Config:
        # Make the model more permissive with extra fields
        extra = "ignore"

class NewChapterResponse(BaseModel):
    newChapter: StoryChapter
        
async def start_new_chapter(request: NewChapterRequest)-> NewChapterResponse:
    try:
        is_game_start: bool = len(request.gameState.arcs[-1].chapters) == 0
        is_arc_start: bool = is_game_start or len(request.gameState.arcs[-1].chapters) == 1
        next_player: PlayerCharacter = request.gameState.characters[0] if is_game_start else request.gameState.arcs[-1].chapters[-2].scenes[-1].activePlayer
        logger.info(f"Starting new chapter is game start: {is_game_start}, is arc start: {is_arc_start}")
        if is_arc_start:
            generated_chapter_title: Optional[str] = None if is_game_start else request.gameState.arcs[-1].chapters[-1].title
            return await _create_arc_start_chapter(request.gameState.settings, request.gameState.characters, next_player, generated_chapter_title)

        return await _create_mid_arc_chapter(request.gameState.settings, request.gameState.arcs[-1], request.gameState.characters, next_player, request.gameState.arcs[-1].chapters[-1].title)
    except Exception as e:
        logger.error(f"Error in start_new_chapter: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to start new chapter: {str(e)}")

async def _create_arc_start_chapter(settings: GameSettings, characters: List[PlayerCharacter], next_player: PlayerCharacter, generated_chapter_title: Optional[str] = None):
    party_description: str = _create_party_description(characters)
    chapter_title: str = generated_chapter_title
    if not chapter_title:
        chapter_title = await _create_chapter_title(settings.aiModel, party_description)
 
    initial_story_prompt = _create_initial_story_prompt(next_player, party_description, chapter_title)
    initial_story_text = await generate_text(initial_story_prompt, settings.aiModel)
    
    initial_story_part, initial_story_actions = parse_story_and_actions(initial_story_text)
    
    if not initial_story_part or len(initial_story_actions) != 3:
        print(PromptConstants.ACTIONS, len(initial_story_actions), initial_story_text)
        parts = initial_story_text.split("\n\n")
        initial_story_part = parts[0]
        initial_story_actions = generate_fallback_actions(parts)
    
    image_base64 = await generate_appropriate_image(
            settings,
            ImageContextEnum.CHAPTER_TRANSITION, 
            initial_story_part,
            None,
            chapter_title=chapter_title,
            party_description=party_description
    )
    
    audio_data = await maybe_generate_tts(initial_story_part, settings.enableAITTS)
    
    initial_scene = StoryScene(
        text=initial_story_part,
        image=image_base64,
        choices=initial_story_actions,
        audioData=audio_data,
        activePlayer=next_player,
        chosenAction=None
    )
    
    return NewChapterResponse(
            newChapter=StoryChapter(
            title=chapter_title,
            summary=None,
            summaryImage=None,
            scenes=[initial_scene]
        )
    )

def _create_party_description(characters: List[PlayerCharacter]):
    character_descriptions = []
    for char in characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass} ({char.gender})")
    
    party_description = ", ".join(character_descriptions)
    return party_description

async def _create_chapter_title(model: str, party_description: str)-> str:
    chapter_title_prompt: str = _create_chapter_title_prompt(party_description)
    chapter_title = await generate_text(chapter_title_prompt, model)
    chapter_title = chapter_title.strip().strip('"').strip("'")
    return chapter_title

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
        
        This is Chapter titled: "{chapter_title}" of the adventure.
        
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

async def _create_mid_arc_chapter(settings: GameSettings, current_arc: StroyArc, characters: List[PlayerCharacter], next_player: PlayerCharacter, generated_chapter_title: str):
    party_description: str = _create_party_description(characters)
    mid_chapter_prompt: str = _create_mid_arc_new_chapter_prompt(current_arc, party_description, next_player, generated_chapter_title)
    logger.info(f"Mid Chapter Prompt: {mid_chapter_prompt}")
    response_text = await generate_text(mid_chapter_prompt, settings.aiModel)
    logger.info(f"Mid Chapter Prompt Response: {response_text}")
    story_part, actions = parse_story_and_actions(response_text)
    if not story_part or len(actions) != 3:
        logger.warning(f"New Chapter Actions: {len(actions)}, using fallback")
        story_part = story_part or (response_text.split("\n\n")[0] if "\n\n" in response_text else response_text)
        actions = generate_fallback_actions(context="new_chapter")

    image_base64 = await generate_appropriate_image(
            settings,
            ImageContextEnum.CHAPTER_TRANSITION, 
            story_part,
            None,
            chapter_title=generated_chapter_title,
            party_description=party_description
    )
    
    audio_data = await maybe_generate_tts(story_part, settings.enableAITTS)

    initial_scene = StoryScene(
        text=story_part,
        image=image_base64,
        choices=actions,
        audioData=audio_data,
        activePlayer=next_player,
        chosenAction=None
    )
    
    return NewChapterResponse(
            newChapter=StoryChapter(
            title=generated_chapter_title,
            scenes=[initial_scene]
        )
    )

def _create_mid_arc_new_chapter_prompt(current_arc: StroyArc, party_description: str, next_player: PlayerCharacter, generated_chapter_title: str):
     return f"""
        {get_dnd_master_description("for an ongoing arc and a new chapter of a D&D adventure")} The party is continuing their current adventure in a chapter titled:
        "{generated_chapter_title}"
        
        The party consists of: {party_description}
        
        {_create_continuity_prompt(_create_current_arc_summary(current_arc), current_arc.chapters[-2].scenes[-1].text, None, None, generated_chapter_title)}
        
        Then, provide exactly 3 possible actions that ONLY {next_player.name} could take 
        in direct response to the situation that was unfolding at the end of the previous chapter.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your brief opening scene that continues from the previous chapter but not simmilar]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {next_player.name} ONLY]
        2. [Second action choice for {next_player.name} ONLY]
        3. [Third action choice for {next_player.name} ONLY]
        """

def _create_current_arc_summary(current_arc: StroyArc):
    #TODO maybe reference the whole previous chapter text and not only the summary
    chapters_summary: str = ""
    previous_chapters: List[StoryChapter] = current_arc.chapters[:len(current_arc.chapters) - 1]
    for index, chapter in enumerate(previous_chapters):
        chapters_summary += f"* Chapter No.{index+1} \"{chapter.title}\": "
        if chapter.summary:
            chapters_summary += f" {chapter.summary}\n"

    return f"""
        The party is currently in an adventure arc with {len(previous_chapters)} previous chapters.
        Their summary is as follows:
        {chapters_summary}
        """

def _create_continuity_prompt(current_arc_summary: str, previous_chapter_ending: str, location: Optional[str], key_characters: Optional[List[str]], next_chapter_title: str) -> str:
    """Create a prompt section that ensures continuity between chapters"""
    
    continuity_text = "IMPORTANT CONTINUITY INSTRUCTIONS:\n"
    continuity_text += "- This chapter MUST be a direct continuation of the previous events in the current arc, not a separate story.\n"
    continuity_text += f"- {current_arc_summary}"
    continuity_text += "- Reference specific events or elements from the end of the previous chapter.\n"
    continuity_text += "- Pick up where the previous chapter left off, with the same characters in the same situation but ADVANCE the story.\n"
    continuity_text += f"- Build new situation from: \"{previous_chapter_ending}\"\n"
    
    if location is not None: #TODO add location extraction
        continuity_text += f"- The party should still be in or near {location} unless they explicitly left\n"
    
    if key_characters is not None and len(key_characters) > 0: #TODO add key characters
        chars = ", ".join(key_characters[:3])  # Limit to 3 characters
        continuity_text += f"- Remember to include relevant NPCs from the previous chapter, such as: {chars}\n"
    
    # Connect to the new chapter title
    continuity_text += f"- Show clearly how the new chapter title \"{next_chapter_title}\" follows from previous events\n"
    continuity_text += "- Create a BRIEF opening scene for this new chapter in 2-3 paragraphs only.\n"
    
    return continuity_text