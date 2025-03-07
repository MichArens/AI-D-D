import logging
import traceback

from fastapi import HTTPException

from ai_services import generate_text
from models import NewChapterRequest
from utilities.image_context_enum import ImageContextEnum
from utilities.prompt_utils import generate_appropriate_image, generate_fallback_actions, maybe_generate_tts, parse_story_and_actions
from utils import ChapterManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_new_chapter(request: NewChapterRequest):
    try:
        logger.info(f"Starting new chapter: '{request.nextChapterTitle}'")
        
        game_state = request.gameState
        next_chapter_title = request.nextChapterTitle
        
        # Safely get model and TTS settings
        model = game_state.settings.aiModel
        enable_tts = game_state.settings.enableAITTS
        
        # Get the first player index
        first_player_idx = game_state.currentPlayerIndex
        
        # Safely get character information
        characters = game_state.characters
        if not characters or first_player_idx >= len(characters):
            logger.error("Invalid character information in game state")
            raise HTTPException(status_code=400, detail="Invalid character information")
            
        first_player = characters[first_player_idx]
        
        # Create character description for prompt
        character_descriptions = []
        for char in characters:
            char_name = char.name
            char_race = char.race
            char_class = char.characterClass
            char_gender = char.gender
            character_descriptions.append(f"{char_name} the {char_race} {char_class}, {char_gender}")
        
        party_description = ", ".join(character_descriptions)
        
        # ENHANCED: Get detailed context from the previous chapter
        previous_chapter_summary = ""
        previous_chapter_ending = ""
        previous_chapter_title = ""
        last_player_action = ""
        
        try:
            if len(game_state.chapters) > 0:
                prev_chapter = game_state.chapters[-1]
                
                # Get previous chapter summary
                if prev_chapter.summary:
                    previous_chapter_summary = prev_chapter.summary
                    logger.info(f"Found previous chapter summary: {previous_chapter_summary}")
                
                # Get previous chapter title
                if prev_chapter.title:
                    previous_chapter_title = prev_chapter.title
                
                # Get the last few segments from previous chapter for more context
                if prev_chapter.segments and game_state.storyProgress:
                    # Get the last segment's index
                    last_segment_idx = prev_chapter.segments[-1]
                    
                    # Access the story progress segments
                    if len(game_state.storyProgress) > last_segment_idx:
                        last_segment = game_state.storyProgress[last_segment_idx]
                        if last_segment.text:
                            previous_chapter_ending = last_segment.text
                        if last_segment.player and last_segment.action:
                            last_player_action = f"{last_segment.player} chose to {last_segment.action}"
        except Exception as e:
            logger.error(f"Error getting previous chapter context: {e}")
            # Continue without context if there's an error
        
        # Build a comprehensive context from previous chapter
        chapter_transition_context = ""
        if previous_chapter_title:
            chapter_transition_context += f"Previous chapter was titled '{previous_chapter_title}'. "
        
        if previous_chapter_summary:
            chapter_transition_context += f"\nSummary of previous chapter: {previous_chapter_summary}\n"
        
        if previous_chapter_ending:
            chapter_transition_context += f"\nThe previous chapter ended with: {previous_chapter_ending}\n"
            
        if last_player_action:
            chapter_transition_context += f"\nThe last action was: {last_player_action}\n"
            
        # Check if this chapter should be a fresh start (after 3-chapter cycle)
        current_chapter_idx = game_state.currentChapterIndex
        previous_chapter_idx = current_chapter_idx - 1
        is_fresh_start = ChapterManager.is_cycle_end(previous_chapter_idx)
        
        # Use ChapterManager to generate appropriate prompt based on cycle
        prompt = ChapterManager.create_chapter_transition_prompt(game_state, next_chapter_title)
        
        # Generate response
        response_text = await generate_text(prompt, model)
        
        # Parse response for story and actions
        story_part, actions = parse_story_and_actions(response_text)
        
        # If parsing failed, use fallback
        if not story_part or len(actions) != 3:
            logger.warning(f"New Chapter Actions: {len(actions)}, using fallback")
            story_part = story_part or (response_text.split("\n\n")[0] if "\n\n" in response_text else response_text)
            actions = generate_fallback_actions(context="new_chapter")
        
        # Pre-generate TTS for the story
        audio_data = await maybe_generate_tts(story_part, enable_tts)
        
        # Generate image if enabled
        image_base64 = await generate_appropriate_image(
            game_state.settings,
            ImageContextEnum.CHAPTER_TRANSITION, 
            story_part, 
            chapter_summary=previous_chapter_summary,
            chapter_title=next_chapter_title,
            party_description=party_description
        )
        
        # Return response with the cycle information
        next_chapter_cycle = ChapterManager.calculate_chapter_cycle(current_chapter_idx)
        
        logger.info("Successfully generated new chapter opening")
        return {
            "storyUpdate": {
                "text": story_part,
                "image": image_base64,
                "choices": actions,
                "audioData": audio_data,  # Include pre-generated TTS
                "isFreshStart": is_fresh_start  # Flag if this is a fresh start chapter
            },
            "choices": actions,
            "chapterCycle": next_chapter_cycle  # Include cycle position
        }
        
    except Exception as e:
        logger.error(f"Error in start_new_chapter: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to start new chapter: {str(e)}")

