import logging
import traceback
from typing import List, Literal, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel
from ai.text_ai_service import generate_text
from utilities.tts_generation_utils import maybe_generate_tts
from utilities.image_generation_utils import generate_appropriate_image
from utilities.image_context_enum import ImageContextEnum
from utilities.prompt_constants import PromptConstants
from utilities.prompt_utils import generate_fallback_actions, get_dnd_master_description, parse_story_and_actions
from models import GameSettings, GameState, PlayerCharacter, StoryChapter, StoryScene, StroyArc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionRequest(BaseModel):
    gameState: GameState
    customAction: Optional[str] = None  # Add field for custom action text

class TakeActionResponse(BaseModel):
    scene: StoryScene
    nextChapterTitle: Optional[str]
    chapterSummary: Optional[str]
    chapterSummaryImage: Optional[str]
    chapterSummaryAudioData: Optional[str]
    
async def take_action(request: ActionRequest)-> TakeActionResponse:
    """Process a player's action and generate the next story segment"""
    game_state: GameState = request.gameState
    model: str = game_state.settings.aiModel
    
    current_arc: StroyArc = game_state.arcs[-1]
    current_chapter: StoryChapter = current_arc.chapters[-1]
    previous_scene: StoryScene = current_chapter.scenes[-1]

    # Calculate next player
    prev_player_index = previous_scene.activeCharacterIndex
    next_player_idx: int = (prev_player_index + 1) % len(game_state.characters)
    
    # Build chapter context
    chapter_story_summary: str = _build_chapter_context(current_chapter, game_state.characters)
 
    # Create prompt based on chapter state
    prompt: str = _create_story_prompt(request.gameState.settings, request.gameState.characters, current_arc, current_chapter, chapter_story_summary, next_player_idx)
    
    try:
        # Generate AI response
        next_progression_text = await generate_text(prompt, model)
        logger.info(f"AI Response (first 20 chars):\n{next_progression_text[:20]}")
        
        next_story_part, next_actions = parse_story_and_actions(next_progression_text)
        if _is_chapter_ending(len(current_chapter.scenes), game_state.settings.scenesPerChapter):
            return await _handle_chapter_end(
                game_state.settings, next_progression_text, model, next_story_part, 
                next_player_idx,
                chapter_story_summary
            )
        else:
            if not next_story_part or len(next_actions) < 3:
                logger.warning(f"Insufficient content parsed from AI response: story={bool(next_story_part)}, actions={len(next_actions)}")
                next_story_part = next_story_part or next_progression_text
                next_actions = generate_fallback_actions(game_state.characters[next_player_idx].name)
            
            return await _handle_mid_chapter(
                game_state.settings, next_story_part, next_actions,
                next_player_idx
            )
    
    except Exception as e:
        logger.error(f"Error in take_action: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process action: {str(e)}")

def _is_chapter_ending(scenes_in_chapter: int, scenes_per_chapter: int)-> bool:
    """Check if the current chapter is ending"""
    logger.info(f"Chapter length configuration: {scenes_in_chapter}/{scenes_per_chapter} scenes completed")
    return scenes_in_chapter >= scenes_per_chapter

def _build_chapter_context(current_chapter: StoryChapter, characters: List[PlayerCharacter])-> str:
    """Build narrative context from the current chapter"""
    chapter_story = ""
    logger.debug(f"Building chapter context for {current_chapter.scenes}")
    for scene in current_chapter.scenes:
        active_character: PlayerCharacter = characters[scene.activeCharacterIndex]
        chapter_story += f"{scene.text}\n"
        chapter_story += f"Then {active_character.name} the {active_character.race} {active_character.characterClass} ({active_character.gender}) chose to: {scene.chosenAction}\n"
    return chapter_story

def _create_story_prompt(settings: GameSettings, characters: List[PlayerCharacter], current_arc: StroyArc, current_chapter: StoryChapter, chapter_story_summary: str, next_player_index: int):
    """Create the appropriate prompt based on chapter state"""
    should_generate_end_chapter: bool = _is_chapter_ending(len(current_chapter.scenes), settings.scenesPerChapter)
    previous_player_index: int = current_chapter.scenes[-1].activeCharacterIndex
    previous_player: PlayerCharacter = characters[previous_player_index]
    next_player: PlayerCharacter = characters[next_player_index]
    chosen_action: str = current_chapter.scenes[-1].chosenAction
    if not should_generate_end_chapter:
        return _generate_mid_chapter_prompt(chapter_story_summary, len(current_chapter.scenes), settings.scenesPerChapter, previous_player, chosen_action, next_player)
    
    is_arc_ending: bool = len(current_arc.chapters) >= settings.chaptersPerArc
    logger.info(f"is Arc ending: {is_arc_ending}")
    if is_arc_ending:
        return _generate_arc_end_prompt(chapter_story_summary, previous_player, chosen_action)
    else:
        return _generate_chapter_end_prompt(chapter_story_summary, previous_player, chosen_action)

def _generate_mid_chapter_prompt(chapter_story_summary: str, current_chapter_scene: int, scenes_per_chapter: int, previous_player: PlayerCharacter, chosen_action: str, next_player: PlayerCharacter)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. Continue the story based on the player's choice.
        
        Story so far this chapter:
        {chapter_story_summary}
        
        Previous player {previous_player.name} (a {previous_player.race} {previous_player.characterClass}, {previous_player.gender}) chose to: {chosen_action}
        The scene of the story that you need to generate is scene {current_chapter_scene}/{scenes_per_chapter}.

        IMPORTANT INSTRUCTIONS:
        - Continue the story in a BRIEF, action-oriented way - 1 paragraph ONLY.
        - Focus on immediate consequences and move the story forward quickly.
        - Avoid lengthy descriptions or background information.
        - Depending on the progress of the chapter, you may need to wrap up the chapter soon.
        
        Then provide exactly 3 possible actions for NEXT PLAYER ONLY: {next_player.name} (a {next_player.race} {next_player.characterClass}, {next_player.gender}).
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your brief continuation here, 1 paragraph only]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {next_player.name} ONLY]
        2. [Second action choice for {next_player.name} ONLY]
        3. [Third action choice for {next_player.name} ONLY]
        """

def _generate_arc_end_prompt(chapter_story_so_far: str, previous_player: int, chosen_action: str)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. This chapter is the final chapter in a story arc.
        
        Story this chapter:
        {chapter_story_so_far}
        
        Current player {previous_player.name} (a {previous_player.race} {previous_player.characterClass}, {previous_player.gender}) chose to: {chosen_action}
        
        IMPORTANT CYCLE END INSTRUCTIONS:
        - This is the FINAL CHAPTER in the current story arc, so write a CONCLUSIVE ending.
        - Resolve the main conflict or quest of this story arc completely.
        - Give the adventure a sense of closure and accomplishment.
        - Write a satisfying conclusion in 1-2 paragraphs only.
        - Then create a title for the next chapter that hints at a completely NEW adventure.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your conclusive chapter ending here, 1-2 paragraphs]
        
        {PromptConstants.NEXT_CHAPTER}
        [New chapter title for a fresh adventure - short and evocative]
        """

def _generate_chapter_end_prompt(chapter_story_so_far: str, previous_player: int, chosen_action: str)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. The current chapter is ending, but the story arc continues.
        
        Story this chapter:
        {chapter_story_so_far}
        
        Current player {previous_player.name} (a {previous_player.race} {previous_player.characterClass}, {previous_player.gender}) chose to: {chosen_action}
        
        IMPORTANT INSTRUCTIONS:
        - Write a BRIEF, chapter conclusion in 1-2 paragraphs only.
        - Focus on resolving the immediate situation based on {previous_player.name}'s action.
        - However, leave some unresolved elements for the next chapter to pick up.
        - Create a sense of "to be continued" rather than a complete ending.
        - Then create a title for the next chapter that hints at continuing this storyline.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your chapter conclusion here with unresolved elements, 1-2 paragraphs]
        
        {PromptConstants.NEXT_CHAPTER}
        [New chapter title that continues this storyline - short and evocative]
        """
    
async def _handle_chapter_end(
        settings: GameSettings, 
        next_progression_text: str,
        model: str, 
        next_story_part: str, 
        next_player_index: int, 
        chapter_story_summary: str
    ):
    next_chapter_title: str = _extract_chapter_title(next_progression_text)
    
    short_summary_prompt: str = _generate_chapter_summary_prompt(chapter_story_summary, next_story_part)
    short_chapter_summary: str = await generate_text(short_summary_prompt, model)
    short_chapter_summary: str = short_chapter_summary.strip().strip('"').strip("'")
    chapter_summary_audio_data: Optional[str] = await maybe_generate_tts(short_chapter_summary, settings.enableAITTS)
    chapter_summary_image = await generate_appropriate_image(
        settings, 
        ImageContextEnum.CHAPTER_SUMMARY, 
        short_chapter_summary
    )
    
    image_base64 = await generate_appropriate_image(
        settings, 
        ImageContextEnum.STORY_UPDATE, 
        next_story_part
    )
    next_scene_audio_data: Optional[str] = await maybe_generate_tts(next_story_part, settings.enableAITTS)
    
    response = TakeActionResponse(
        nextChapterTitle=next_chapter_title,
        chapterSummary=short_chapter_summary,
        chapterSummaryImage=chapter_summary_image,
        chapterSummaryAudioData=chapter_summary_audio_data,
        scene=StoryScene(
            text=next_story_part,
            image=image_base64,
            activeCharacterIndex=next_player_index,
            chosenAction=None,
            audioData=next_scene_audio_data,
            choices=[]
        )
    )
    return response

def _generate_chapter_summary_prompt(chapter_story: str, story_part: str)-> str:
    return f"""
    Create a concise summary (1-2 sentences) of the following chapter in a D&D adventure:
    
    {chapter_story}
    {story_part}
    
    Just provide the summary text without any additional formatting or text.
    """

def _extract_chapter_title(response_text)-> Union[str, Literal["The Next Chapter"]]:
    """Extract chapter title from AI response"""
    next_chapter_title: str = "The Next Chapter"
    if PromptConstants.NEXT_CHAPTER in response_text:
        next_chapter_title = response_text.split(PromptConstants.NEXT_CHAPTER)[1].strip()
        # Improved title cleaning
        next_chapter_title = next_chapter_title.split("\n")[0].strip()
        next_chapter_title = next_chapter_title.strip('"').strip("'")
        # Limit title length to avoid story content in title
        if len(next_chapter_title) > 50:  # Reasonable max length for a title
            next_chapter_title = next_chapter_title[:50].strip()
    else:
        # Fallback parsing
        parts: str = response_text.split("\n\n")
        if len(parts) > 1:
            # Use a more conservative approach for title extraction
            potential_title = parts[-1].strip().strip('"').strip("'")
            # If the potential title is too long, it's likely part of the story
            if len(potential_title) <= 50:
                next_chapter_title = potential_title
    
    # Additional safeguard to ensure title is reasonable
    if len(next_chapter_title) < 3 or len(next_chapter_title) > 50:
        next_chapter_title = "The Next Chapter"
    
    return next_chapter_title

async def _handle_mid_chapter(settings: GameSettings, story_part: str, actions: List[str], next_player_index: int):
    """Handle mid-chapter story continuation"""

    image_base64 = await generate_appropriate_image(
        settings, 
        ImageContextEnum.STORY_UPDATE, 
        story_part
    )
    
    audio_data = await maybe_generate_tts(story_part, settings.enableAITTS)
    
    response = TakeActionResponse(
        scene=StoryScene(
            text=story_part,
            image=image_base64,
            activeCharacterIndex=next_player_index,
            chosenAction=None,
            audioData=audio_data,
            choices=actions
        ),
        nextChapterTitle=None,
        chapterSummary=None,
        chapterSummaryImage=None
    )
    
    return response
