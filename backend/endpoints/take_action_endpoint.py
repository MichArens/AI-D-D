import logging
import traceback
from typing import List, Literal, Union

from fastapi import HTTPException
from ai.text_ai_service import generate_text
from utilities.image_generation_utils import generate_appropriate_image
from utilities.image_context_enum import ImageContextEnum
from utilities.prompt_constants import PromptConstants
from utils import ChapterManager
from utilities.prompt_utils import generate_fallback_actions, get_dnd_master_description, maybe_generate_tts, parse_story_and_actions
from models import ActionRequest, Chapter, GameState, PlayerCharacter, StoryProgression

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def take_action(request: ActionRequest):
    """Process a player's action and generate the next story segment"""
    game_state: GameState = request.gameState
    model: str = game_state.settings.aiModel
    
    # Get the current player and chosen action
    current_player_idx: int = game_state.currentPlayerIndex
    current_player: PlayerCharacter = game_state.characters[current_player_idx]
    chosen_action: str = _get_chosen_action(request)
    
    # Calculate next player's index
    next_player_idx = (current_player_idx + 1) % len(game_state.characters)
    next_player = game_state.characters[next_player_idx]
    
    # Determine chapter state
    current_chapter_idx: int = game_state.currentChapterIndex
    # current_chapter: Chapter = game_state.chapters[current_chapter_idx] if game_state.chapters and len(game_state.chapters) > current_chapter_idx else None
    current_chapter: Chapter = game_state.chapters[current_chapter_idx]
    
    rounds_in_chapter: int = game_state.roundsInCurrentChapter + 1
    should_generate_end_chapter: bool = _is_chapter_ending(rounds_in_chapter, game_state.settings.scenesPerChapter)
    
    # Build chapter context
    chapter_story_so_far = _build_chapter_context(current_chapter, game_state.storyProgress)
 
    # Create prompt based on chapter state
    prompt = _create_story_prompt(game_state, chapter_story_so_far, current_player, chosen_action, next_player, should_generate_end_chapter)
    
    try:
        # Generate AI response
        next_progression_text = await generate_text(prompt, model)
        logger.info(f"AI Response (first 100 chars):\n{next_progression_text}")
        
        next_story_part, next_actions = parse_story_and_actions(next_progression_text)
        if should_generate_end_chapter:
            return await _handle_chapter_end(
                game_state, next_progression_text, model, next_story_part, 
                current_player, chosen_action, next_player, next_player_idx,
                current_chapter, current_chapter_idx, chapter_story_so_far
            )
        else:
            if not next_story_part or len(next_actions) < 3:
                logger.warning(f"Insufficient content parsed from AI response: story={bool(next_story_part)}, actions={len(next_actions)}")
                next_story_part = next_story_part or next_progression_text
                next_actions = generate_fallback_actions(next_player.name)
            
            return await _handle_mid_chapter(
                game_state, next_story_part, next_actions,
                current_player, chosen_action, next_player_idx, rounds_in_chapter
            )
    
    except Exception as e:
        logger.error(f"Error in take_action: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process action: {str(e)}")

def _is_chapter_ending(rounds_in_chapter: int, rounds_per_chapter: int)-> bool:
    """Check if the current chapter is ending"""
    logger.info(f"Chapter length configuration: {rounds_in_chapter}/{rounds_per_chapter} rounds completed")
    return rounds_in_chapter >= rounds_per_chapter

def _get_chosen_action(request: ActionRequest)-> str:
    """Determine the action chosen by the player"""
    game_state: GameState = request.gameState
    choice_id: int = request.choiceId
    
    # Check if this is a custom action
    if request.customAction:
        chosen_action = request.customAction
        logger.info(f"Using custom action: {chosen_action}")
        return chosen_action
    
    # Get the action choices and selected action from choices
    last_story = game_state.storyProgress[-1] if game_state.storyProgress else None
    logger.debug(f"Last story segment: {last_story.choices} {len(last_story.choices)}")
    if last_story.choices is None or len(last_story.choices) == 0:
        raise HTTPException(status_code=400, detail="Invalid game state: missing action choices")
    
    chosen_action = None
    for choice in last_story.choices:
        if choice.id == choice_id:
            chosen_action = choice.text
            break
    
    if not chosen_action:
        raise HTTPException(status_code=400, detail=f"Invalid choice ID: {choice_id}")
    
    return chosen_action

def _build_chapter_context(current_chapter: Chapter, story_progress: List[StoryProgression])-> str:
    """Build narrative context from the current chapter"""
    chapter_story = ""
    logger.debug(f"Building chapter context for {story_progress}")
    if current_chapter and current_chapter.segments:
        for seg_idx in current_chapter.segments:
            if seg_idx < len(story_progress):
                segment = story_progress[seg_idx]
                chapter_story += f"{segment.text if segment.text is not None else ''}\n"
                if segment.player and segment.action:
                    chapter_story += f"Then {segment.player} chose to: {segment.action}\n"
    return chapter_story

def _create_story_prompt(game_state: GameState, chapter_story_so_far: str, current_player: PlayerCharacter, chosen_action: str, next_player: PlayerCharacter, should_generate_end_chapter: bool):
    """Create the appropriate prompt based on chapter state"""
    if not should_generate_end_chapter:
        return _generate_mid_chapter_prompt(chapter_story_so_far, current_player, chosen_action, next_player)
    
    # For end chapter scenarios
    current_chapter_idx = game_state.currentChapterIndex
    is_cycle_end = ChapterManager.is_cycle_end(current_chapter_idx)
    
    if is_cycle_end:
        return _generate_cycle_end_prompt(chapter_story_so_far, current_player, chosen_action)
    else:
        return _generate_chapter_end_prompt(chapter_story_so_far, current_player, chosen_action)

def _generate_mid_chapter_prompt(chapter_story_so_far: str, current_player: PlayerCharacter, chosen_action: str, next_player: PlayerCharacter)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. Continue the story based on the player's choice.
        
        Story so far this chapter:
        {chapter_story_so_far}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        IMPORTANT INSTRUCTIONS:
        - Continue the story in a BRIEF, action-oriented way - 1 paragraph ONLY.
        - Focus on immediate consequences and move the story forward quickly.
        - Avoid lengthy descriptions or background information.
        
        Then provide exactly 3 possible actions for NEXT PLAYER ONLY: {next_player.name} (a {next_player.race} {next_player.characterClass}, {next_player.gender}).
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your brief continuation here, 1 paragraph only]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {next_player.name} ONLY]
        2. [Second action choice for {next_player.name} ONLY]
        3. [Third action choice for {next_player.name} ONLY]
        """

def _generate_cycle_end_prompt(chapter_story_so_far: str, current_player: PlayerCharacter, chosen_action: str)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. This chapter is the final chapter in a 3-chapter story arc.
        
        Story this chapter:
        {chapter_story_so_far}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
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

def _generate_chapter_end_prompt(chapter_story_so_far: str, current_player: PlayerCharacter, chosen_action: str)-> str:
    return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. The current chapter is ending, but the story arc continues.
        
        Story this chapter:
        {chapter_story_so_far}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        IMPORTANT INSTRUCTIONS:
        - Write a BRIEF, chapter conclusion in 1-2 paragraphs only.
        - Focus on resolving the immediate situation based on {current_player.name}'s action.
        - However, leave some unresolved elements for the next chapter to pick up.
        - Create a sense of "to be continued" rather than a complete ending.
        - Then create a title for the next chapter that hints at continuing this storyline.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your chapter conclusion here with unresolved elements, 1-2 paragraphs]
        
        {PromptConstants.NEXT_CHAPTER}
        [New chapter title that continues this storyline - short and evocative]
        """
    
async def _handle_chapter_end(game_state: GameState, next_progression_text: str, model: str, next_story_part: str, current_player: PlayerCharacter, chosen_action: str, next_player: PlayerCharacter, next_player_idx: int, current_chapter: Chapter, current_chapter_idx: int, chapter_story_so_far: str):
    next_chapter_title = _extract_chapter_title(next_progression_text)
    
    summary_prompt = _generate_chapter_summary_prompt(chapter_story_so_far, next_story_part)
    chapter_summary = await generate_text(summary_prompt, model)
    chapter_summary = chapter_summary.strip().strip('"').strip("'")
    
    chapter_image = await generate_appropriate_image(
        game_state.settings, 
        ImageContextEnum.CHAPTER_SUMMARY, 
        next_story_part, 
        chapter_summary=chapter_summary
    )
    
    current_chapter.summary = chapter_summary
    current_chapter.image = chapter_image
    
    actions = await _generate_next_chapter_actions(model, next_chapter_title, next_player)
    
    next_chapter_id = current_chapter_idx + 1
    next_chapter_cycle = ChapterManager.calculate_chapter_cycle(current_chapter_idx + 1)
    
    image_base64 = await generate_appropriate_image(
        game_state.settings, 
        ImageContextEnum.STORY_UPDATE, 
        next_story_part
    )
    audio_data = await maybe_generate_tts(next_story_part, game_state.settings.enableAITTS)
    
    # Create the story update
    story_update = {
        "text": next_story_part,
        "image": image_base64,
        "player": current_player.name,
        "action": chosen_action,
        "chapterId": next_chapter_id,
        "audioData": audio_data
    }
    
    return {
        "storyUpdate": story_update,
        "choices": actions,
        "nextPlayerIndex": next_player_idx,
        "chapterEnded": True,
        "chapterSummary": chapter_summary,
        "chapterImage": chapter_image,
        "nextChapterTitle": next_chapter_title,
        "nextChapter": {
            "id": next_chapter_id,
            "title": next_chapter_title
        },
        "roundsInChapter": 0,  # Reset for new chapter
        "chapterCycle": next_chapter_cycle,  # Include the cycle position for the next chapter
        "isFreshStart": ChapterManager.is_cycle_end(current_chapter_idx)  # Flag if next chapter is fresh start
    }

def _generate_chapter_summary_prompt(chapter_story: str, story_part: str)-> str:
    return f"""
    Create a concise summary (1-2 sentences) of the following chapter in a D&D adventure:
    
    {chapter_story}
    {story_part}
    
    Just provide the summary text without any additional formatting or text.
    """

def _extract_chapter_title(response_text)-> Union[str, Literal["The Next Chapter"]]:
    """Extract chapter title from AI response"""
    next_chapter_title = "The Next Chapter"
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
        parts = response_text.split("\n\n")
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

async def _generate_next_chapter_actions(model, next_chapter_title, next_player):
    """Generate actions for the beginning of a new chapter"""
    next_chapter_prompt = f"""
    {get_dnd_master_description("for a D&D adventure")}. The party has just started a new chapter titled "{next_chapter_title}".
    
    IMPORTANT: Provide exactly 3 possible actions that ONLY {next_player.name} (a {next_player.race} {next_player.characterClass}) could take.
    No other character should be referenced in these actions.
    
    Format your response as:
    
    1. [First action choice for {next_player.name} ONLY]
    2. [Second action choice for {next_player.name} ONLY]
    3. [Third action choice for {next_player.name} ONLY]
    """
    
    actions_response = await generate_text(next_chapter_prompt, model)
    
    # Extract actions
    actions = []
    action_lines = actions_response.split("\n")
    for line in action_lines:
        line = line.strip()
        if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
            action_text = line[2:].strip()
            actions.append({"id": len(actions), "text": action_text})
    
    # Fallback if parsing failed
    if len(actions) < 3:
        logger.warning(f"Failed to parse chapter actions: {len(actions)}")
        actions = generate_fallback_actions(context="chapter_end")
    
    return actions

async def _handle_mid_chapter(game_state: GameState, story_part: str, actions: List[str], current_player: PlayerCharacter, chosen_action: str, next_player_idx: int, rounds_in_chapter: int):
    """Handle mid-chapter story continuation"""
    current_chapter_idx = game_state.currentChapterIndex
    
    # Generate image and audio
    image_base64 = await generate_appropriate_image(
        game_state.settings, 
        "story_update", 
        story_part
    )
    
    audio_data = await maybe_generate_tts(story_part, game_state.settings.enableAITTS)
    
    # Create the story update
    story_update = {
        "text": story_part,
        "image": image_base64,
        "player": current_player.name,
        "action": chosen_action,
        "chapterId": current_chapter_idx,
        "audioData": audio_data
    }
    
    return {
        "storyUpdate": story_update,
        "choices": actions,
        "nextPlayerIndex": next_player_idx,
        "chapterEnded": False,
        "roundsInChapter": rounds_in_chapter
    }
