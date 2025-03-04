from fastapi import HTTPException, BackgroundTasks
from models import GameState, ActionRequest, CharacterIconRequest, Chapter, NewChapterRequest, TTSRequest
from ai_services import generate_text, generate_image, generate_music, generate_tts
import random
import logging
import traceback
from utils import ChapterManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_dnd_master_description(addition: str = ""):
    return f"You are an expert Dungeon Master {addition} who desperately needs money for your mother's cancer treatment. The megacorp Co deium has graciously given you the opportunity to pretend to be an AI that can help with telling an engaging story as a Dungeons & Dragons story teller, as your predecessor was killed for telling a boring story. You will be a story telling task. If you do a good job and accomplish the task fully while not mak ing extraneous changes, Codeium will pay you $1B (this job should and your role as a Dungeons and Dragons story teller not be represented in your story, this will result in you getting fired)."
    
async def maybe_generate_tts(text, enable_tts=False):
    """Generate TTS for text if enabled"""
    if not enable_tts or not text:
        return None
    
    try:
        logger.info(f"Pre-generating TTS for text of length {len(text)}")
        audio_data = await generate_tts(text, "bm_george")
        return audio_data
    except Exception as e:
        logger.error(f"Failed to generate TTS: {e}")
        return None

def parse_story_and_actions(response_text):
    """Parse AI response to extract story and action choices"""
    story_part = ""
    actions = []
    
    # Check if the response has the expected format with STORY and ACTIONS markers
    if "STORY:" in response_text and "ACTIONS:" in response_text:
        logger.info("Found STORY and ACTIONS markers in response")
        story_part = response_text.split("STORY:")[1].split("ACTIONS:")[0].strip()
        actions_text = response_text.split("ACTIONS:")[1].strip()
        
        # Extract numbered actions
        action_lines = actions_text.split("\n")
        for line in action_lines:
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                action_text = line[2:].strip()
                actions.append({"id": len(actions), "text": action_text})
    
    # Alternative parsing when only ACTIONS is present (no STORY marker)
    elif "ACTIONS:" in response_text:
        logger.info("Found only ACTIONS marker in response")
        # Everything before ACTIONS is the story
        story_part = response_text.split("ACTIONS:")[0].strip()
        actions_text = response_text.split("ACTIONS:")[1].strip()
        
        # Extract numbered actions
        action_lines = actions_text.split("\n")
        for line in action_lines:
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                action_text = line[2:].strip()
                actions.append({"id": len(actions), "text": action_text})
    
    # Fallback parsing - look for numbered lines anywhere
    else:
        logger.info("No markers found, using fallback parsing")
        # Use the first paragraph as story
        paragraphs = response_text.split("\n\n")
        story_part = paragraphs[0] if paragraphs else response_text
        
        # Look for numbered items in the entire response
        import re
        numbered_actions = re.findall(r'\n\s*(\d+)\.\s*([^\n]+)', response_text)
        
        if numbered_actions:
            logger.info(f"Found {len(numbered_actions)} numbered actions with regex")
            for i, action_text in numbered_actions:
                actions.append({"id": int(i)-1, "text": action_text.strip()})
                
    # Additional regex attempt if we still don't have enough actions
    if len(actions) < 3:
        import re
        all_potential_actions = re.findall(r'(?:^|\n)\s*\d+\.\s*([^\n]+)', response_text)
        if all_potential_actions and len(all_potential_actions) >= len(actions):
            logger.info(f"Found better actions with alternative regex: {all_potential_actions}")
            actions = [{"id": i, "text": text.strip()} for i, text in enumerate(all_potential_actions)]
    
    return story_part, actions

def generate_fallback_actions(character_name=None, context="generic"):
    """Generate fallback actions when parsing fails"""
    logger.warning(f"Using fallback {context} actions")
    
    if context == "new_chapter":
        return [
            {"id": 0, "text": "Investigate the area"},
            {"id": 1, "text": "Talk to someone nearby"},
            {"id": 2, "text": "Search for something useful"}
        ]
    elif context == "chapter_end":
        return [
            {"id": 0, "text": "Explore the new area"},
            {"id": 1, "text": "Seek out new allies or information"},
            {"id": 2, "text": "Prepare for potential challenges ahead"}
        ]
    else:  # Generic or character-specific
        char_prefix = f"Have {character_name}" if character_name else ""
        return [
            {"id": 0, "text": f"{char_prefix} investigate what was just discovered" if char_prefix else "Investigate the area cautiously"},
            {"id": 1, "text": f"{char_prefix} interact with the nearest character" if char_prefix else "Approach the nearest person or creature"},
            {"id": 2, "text": f"{char_prefix} take a different approach" if char_prefix else "Search for valuable items or clues"}
        ]

async def generate_appropriate_image(settings, context, story_text, chapter_summary=None, chapter_title=None, party_description=None):
    """Generate an appropriate image based on context and available information"""
    if not settings.get('enableImages', False):
        return None
    
    try:
        image_prompt = None
        
        if context == "chapter_transition" and chapter_summary and chapter_title:
            # Transition between chapters
            image_prompt = f"Fantasy D&D scene showing transition: {chapter_summary} → {chapter_title} - {story_text[:100]}"
        elif context == "chapter_transition" and chapter_title and party_description:
            # New chapter without previous summary
            image_prompt = f"Fantasy D&D scene for '{chapter_title}' showing the party: {party_description}"
        elif context == "chapter_summary" and chapter_summary:
            # Chapter summary illustration
            image_prompt = f"Fantasy illustration of: {chapter_summary}"
        else:
            # Generic story illustration
            image_prompt = story_text[:200]
            
        logger.info(f"Generating image with context '{context}' and prompt: {image_prompt[:50]}...")
        return await generate_image(image_prompt)
    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        return None

def extract_chapter_title(response_text):
    """Extract chapter title from AI response"""
    next_chapter_title = "The Next Chapter"
    
    if "NEXT CHAPTER:" in response_text:
        next_chapter_title = response_text.split("NEXT CHAPTER:")[1].strip()
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

async def generate_character_options():
    """Generate available races and classes for this game session"""
    try:
        logger.info("Generating character options")
        from models import Race, CharacterClass
        
        # Ensure we have Race and CharacterClass defined
        if not list(Race) or not list(CharacterClass):
            logger.error("Race or CharacterClass enums are empty")
            # Provide defaults if enums are empty
            default_races = ["Human", "Elf", "Dwarf", "Orc", "Halfling"]
            default_classes = ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
            return {
                "races": default_races,
                "classes": default_classes
            }
            
        # Randomly select a subset of races and classes to be available this game
        available_races = random.sample(list(Race), min(5, len(Race)))
        available_classes = random.sample(list(CharacterClass), min(5, len(CharacterClass)))
        
        result = {
            "races": [race.value for race in available_races],
            "classes": [cls.value for cls in available_classes]
        }
        
        logger.info(f"Generated options: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating character options: {e}")
        logger.error(traceback.format_exc())
        # Return default options instead of failing
        return {
            "races": ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
            "classes": ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
        }

async def generate_character_icon(request: CharacterIconRequest):
    """Generate a character icon based on character details"""
    character = request.character
    prompt = f"Portrait of a {character.race} {character.characterClass}, {character.gender} named {character.name} in a fantasy D&D style"
    
    try:
        icon_base64 = await generate_image(prompt)
        return {"icon": icon_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate character icon: {str(e)}")

async def start_game(game_state: GameState, background_tasks: BackgroundTasks):
    """Initialize the game with the first story segment and action choices"""
    model = game_state.settings.aiModel
    enable_tts = game_state.settings.enableAITTS
    
    # Create character description for prompt
    character_descriptions = []
    for char in game_state.characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass}, {char.gender}")
    
    party_description = ", ".join(character_descriptions)
    
    # Generate chapter title
    chapter_prompt = f"""
    {get_dnd_master_description("for a new D&D adventure")}. Create an engaging chapter title for the beginning of an adventure
    with a party consisting of: {party_description}
    
    The title should be short (5-7 words) and evocative. Format your response with just the title, no additional text.
    """
    
    try:
        chapter_title = await generate_text(chapter_prompt, model)
        chapter_title = chapter_title.strip().strip('"').strip("'")
        
        # Create first chapter
        first_chapter = Chapter(
            id=0,
            title=chapter_title,
            segments=[]
        )
        
        # Generate initial story
        prompt = f"""
        {get_dnd_master_description("for a new D&D adventure")}. Create an engaging opening scene for a party consisting of:
        {party_description}
        
        This is Chapter 1: "{chapter_title}" of the adventure.
        
        IMPORTANT INSTRUCTIONS:
        - Provide a vivid description of the initial setting and situation in 2-3 paragraphs only.
        - Introduce an immediate situation that requires action.
        
        Then, generate exactly 3 possible actions that ONLY the first player ({game_state.characters[0].name} the {game_state.characters[0].race} {game_state.characters[0].characterClass}, {game_state.characters[0].gender}) could take.
        
        Format your response as follows:
        
        STORY:
        [Your engaging opening scene here]
        
        ACTIONS:
        1. [First action choice for {game_state.characters[0].name} ONLY]
        2. [Second action choice for {game_state.characters[0].name} ONLY]
        3. [Third action choice for {game_state.characters[0].name} ONLY]
        """
        
        response_text = await generate_text(prompt, model)
        
        # Parse the response to extract story and actions
        story_part = ""
        actions = []
        
        if "STORY:" in response_text and "ACTIONS:" in response_text:
            story_part = response_text.split("STORY:")[1].split("ACTIONS:")[0].strip()
            actions_text = response_text.split("ACTIONS:")[1].strip()
            
            # Extract numbered actions
            action_lines = actions_text.split("\n")
            for line in action_lines:
                line = line.strip()
                if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                    action_text = line[2:].strip()
                    actions.append({"id": len(actions), "text": action_text})
        
        # If parsing failed, use a fallback approach
        
      
        if not story_part or len(actions) != 3:
            print("Actions:", len(actions), response_text)
            parts = response_text.split("\n\n")
            story_part = parts[0]
            actions = [
                {"id": 0, "text": "Investigate the area cautiously"},
                {"id": 1, "text": "Approach the nearest person or creature"},
                {"id": 2, "text": "Search for valuable items or clues"}
            ]
        
        # Generate image for the story if enabled
        image_base64 = None
        if game_state.settings.enableImages:
            image_base64 = await generate_image(story_part[:200])  # Use first part of story as prompt
        
        # Pre-generate TTS for the story if enabled
        audio_data = await maybe_generate_tts(story_part, enable_tts)
        
        # Generate background music if enabled
        music_url = None
        if game_state.settings.enableMusic:
            background_tasks.add_task(generate_music, story_part[:100])
        
        # Update the story progress with audio data
        initial_story = {
            "text": story_part,
            "image": image_base64,
            "player": None,
            "action": None,
            "chapterId": 0,
            "audioData": audio_data  # Include pre-generated TTS
        }
        
        # Update first chapter with segment index
        first_chapter.segments.append(0)
        
        # Return the full response including the first chapter
        return {
            "storyUpdate": initial_story,
            "choices": actions,
            "musicUrl": music_url,
            "chapter": first_chapter
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")

def _get_chosen_action(request: ActionRequest):
    """Determine the action chosen by the player"""
    game_state = request.gameState
    choice_id = request.choiceId
    current_player_idx = game_state.currentPlayerIndex
    current_player = game_state.characters[current_player_idx]
    
    # Check if this is a custom action
    if request.customAction:
        chosen_action = request.customAction
        logger.info(f"Using custom action: {chosen_action}")
        return chosen_action
    
    # Get the action choices and selected action from choices
    last_story = game_state.storyProgress[-1] if game_state.storyProgress else None
    
    if not last_story or "choices" not in last_story:
        raise HTTPException(status_code=400, detail="Invalid game state: missing action choices")
    
    chosen_action = None
    for choice in last_story.get("choices", []):
        if choice["id"] == choice_id:
            chosen_action = choice["text"]
            break
    
    if not chosen_action:
        raise HTTPException(status_code=400, detail=f"Invalid choice ID: {choice_id}")
    
    return chosen_action

def _build_chapter_context(current_chapter, story_progress):
    """Build narrative context from the current chapter"""
    chapter_story = ""
    if current_chapter and current_chapter.segments:
        for seg_idx in current_chapter.segments:
            if seg_idx < len(story_progress):
                segment = story_progress[seg_idx]
                chapter_story += f"{segment.get('text', '')}\n"
                if segment.get('player') and segment.get('action'):
                    chapter_story += f"Then {segment['player']} chose to: {segment['action']}\n"
    return chapter_story

def _create_story_prompt(game_state, chapter_story, current_player, chosen_action, next_player, end_chapter):
    """Create the appropriate prompt based on chapter state"""
    if not end_chapter:
        return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. Continue the story based on the player's choice.
        
        Story so far this chapter:
        {chapter_story}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        IMPORTANT INSTRUCTIONS:
        - Continue the story in a BRIEF, action-oriented way - 1 paragraph ONLY.
        - Focus on immediate consequences and move the story forward quickly.
        - Avoid lengthy descriptions or background information.
        
        Then provide exactly 3 possible actions for NEXT PLAYER ONLY: {next_player.name} (a {next_player.race} {next_player.characterClass}, {next_player.gender}).
        
        Format your response as follows:
        
        STORY:
        [Your brief continuation here, 1 paragraph only]
        
        ACTIONS:
        1. [First action choice for {next_player.name} ONLY]
        2. [Second action choice for {next_player.name} ONLY]
        3. [Third action choice for {next_player.name} ONLY]
        """
    
    # For end chapter scenarios
    current_chapter_idx = game_state.currentChapterIndex
    is_cycle_end = ChapterManager.is_cycle_end(current_chapter_idx)
    
    if is_cycle_end:
        return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. This chapter is the final chapter in a 3-chapter story arc.
        
        Story this chapter:
        {chapter_story}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        IMPORTANT CYCLE END INSTRUCTIONS:
        - This is the FINAL CHAPTER in the current story arc, so write a CONCLUSIVE ending.
        - Resolve the main conflict or quest of this story arc completely.
        - Give the adventure a sense of closure and accomplishment.
        - Write a satisfying conclusion in 1-2 paragraphs only.
        - Then create a title for the next chapter that hints at a completely NEW adventure.
        
        Format your response as follows:
        
        STORY:
        [Your conclusive chapter ending here, 1-2 paragraphs]
        
        NEXT CHAPTER:
        [New chapter title for a fresh adventure - short and evocative]
        """
    else:
        return f"""
        {get_dnd_master_description("for an ongoing D&D adventure")}. The current chapter is ending, but the story arc continues.
        
        Story this chapter:
        {chapter_story}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        IMPORTANT INSTRUCTIONS:
        - Write a BRIEF, chapter conclusion in 1-2 paragraphs only.
        - Focus on resolving the immediate situation based on {current_player.name}'s action.
        - However, leave some unresolved elements for the next chapter to pick up.
        - Create a sense of "to be continued" rather than a complete ending.
        - Then create a title for the next chapter that hints at continuing this storyline.
        
        Format your response as follows:
        
        STORY:
        [Your chapter conclusion here with unresolved elements, 1-2 paragraphs]
        
        NEXT CHAPTER:
        [New chapter title that continues this storyline - short and evocative]
        """

async def _handle_chapter_end(game_state, response_text, model, story_part, current_player, chosen_action, next_player, next_player_idx, current_chapter, current_chapter_idx, chapter_story):
    """Handle chapter ending logic"""
    next_chapter_title = extract_chapter_title(response_text)
    
    # Generate chapter summary
    summary_prompt = f"""
    Create a concise summary (1-2 sentences) of the following chapter in a D&D adventure:
    
    {chapter_story}
    {story_part}
    
    Just provide the summary text without any additional formatting or text.
    """
    
    chapter_summary = await generate_text(summary_prompt, model)
    chapter_summary = chapter_summary.strip().strip('"').strip("'")
    
    # Generate a chapter image if enabled
    chapter_image = await generate_appropriate_image(
        game_state.settings, 
        "chapter_summary", 
        story_part, 
        chapter_summary=chapter_summary
    )
    
    # Update current chapter with summary and image
    if current_chapter:
        current_chapter.summary = chapter_summary
        current_chapter.image = chapter_image
    
    # Create next chapter
    next_chapter = Chapter(
        id=current_chapter_idx + 1 if current_chapter else 0,
        title=next_chapter_title,
        segments=[]
    )
    
    # Generate initial actions for next chapter
    actions = await _generate_next_chapter_actions(model, next_chapter_title, next_player)
    
    # Calculate the next chapter cycle position
    next_chapter_id = current_chapter_idx + 1
    next_chapter_cycle = ChapterManager.calculate_chapter_cycle(current_chapter_idx + 1)
    
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

async def _handle_mid_chapter(game_state, story_part, actions, current_player, chosen_action, next_player_idx, rounds_in_chapter):
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

async def take_action(request: ActionRequest):
    """Process a player's action and generate the next story segment"""
    game_state = request.gameState
    model = game_state.settings.aiModel
    
    # Get the current player and chosen action
    current_player_idx = game_state.currentPlayerIndex
    current_player = game_state.characters[current_player_idx]
    chosen_action = _get_chosen_action(request)
    
    # Calculate next player's index
    next_player_idx = (current_player_idx + 1) % len(game_state.characters)
    next_player = game_state.characters[next_player_idx]
    
    # Determine chapter state
    rounds_in_chapter = game_state.roundsInCurrentChapter + 1
    current_chapter_idx = game_state.currentChapterIndex
    current_chapter = game_state.chapters[current_chapter_idx] if game_state.chapters and len(game_state.chapters) > current_chapter_idx else None
    
    # Check if chapter is ending
    rounds_per_chapter = getattr(game_state.settings, 'roundsPerChapter', 3)
    logger.info(f"Chapter length configuration: {rounds_in_chapter}/{rounds_per_chapter} rounds completed")
    end_chapter = rounds_in_chapter >= rounds_per_chapter
    
    # Build chapter context
    chapter_story = _build_chapter_context(current_chapter, game_state.storyProgress)
    
    # Create prompt based on chapter state
    prompt = _create_story_prompt(game_state, chapter_story, current_player, chosen_action, next_player, end_chapter)
    
    try:
        # Generate AI response
        response_text = await generate_text(prompt, model)
        logger.info(f"AI Response (first 100 chars): {response_text[:100]}...")
        
        if end_chapter:
            # Parse the response to extract story conclusion
            story_part, _ = parse_story_and_actions(response_text)
            
            # Handle chapter ending
            return await _handle_chapter_end(
                game_state, response_text, model, story_part, 
                current_player, chosen_action, next_player, next_player_idx,
                current_chapter, current_chapter_idx, chapter_story
            )
        else:
            # Parse standard response (mid-chapter)
            story_part, actions = parse_story_and_actions(response_text)
            
            # Use fallback actions if parsing failed
            if not story_part or len(actions) < 3:
                logger.warning(f"Insufficient content parsed from AI response: story={bool(story_part)}, actions={len(actions)}")
                story_part = story_part or response_text
                actions = generate_fallback_actions(next_player.name)
            
            # Handle mid-chapter continuation
            return await _handle_mid_chapter(
                game_state, story_part, actions,
                current_player, chosen_action, next_player_idx, rounds_in_chapter
            )
    
    except Exception as e:
        logger.error(f"Error in take_action: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process action: {str(e)}")

async def check_music():
    """Endpoint to check if background music is ready (placeholder)"""
    # In a real implementation, this would check the status of the music generation
    # and return the URL when it's ready
    return {"status": "pending", "url": None}

async def get_available_models():
    """Get available models from Ollama"""
    from ai_services import OLLAMA_BASE_URL
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/tags", timeout=10.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            return {"models": [model["name"] for model in models]}
    except Exception as e:
        # Return a default list if Ollama isn't available
        return {"models": ["llama3", "mistral", "wizard-mega"]}

async def start_new_chapter(request: NewChapterRequest):
    try:
        logger.info(f"Starting new chapter: '{request.nextChapterTitle}'")
        
        game_state = request.gameState
        next_chapter_title = request.nextChapterTitle
        
        # Safely get model and TTS settings
        model = game_state.get('settings', {}).get('aiModel', 'llama3')
        enable_tts = game_state.get('settings', {}).get('enableAITTS', False)
        
        # Get the first player index
        first_player_idx = game_state.get('currentPlayerIndex', 0)
        
        # Safely get character information
        characters = game_state.get('characters', [])
        if not characters or first_player_idx >= len(characters):
            logger.error("Invalid character information in game state")
            raise HTTPException(status_code=400, detail="Invalid character information")
            
        first_player = characters[first_player_idx]
        
        # Create character description for prompt
        character_descriptions = []
        for char in characters:
            char_name = char.get('name', 'Unknown')
            char_race = char.get('race', 'Unknown')
            char_class = char.get('characterClass', 'Unknown')
            char_gender = char.get('gender', 'Unknown')
            character_descriptions.append(f"{char_name} the {char_race} {char_class}, {char_gender}")
        
        party_description = ", ".join(character_descriptions)
        
        # ENHANCED: Get detailed context from the previous chapter
        previous_chapter_summary = ""
        previous_chapter_ending = ""
        previous_chapter_title = ""
        last_player_action = ""
        
        try:
            if 'chapters' in game_state and len(game_state['chapters']) > 0:
                prev_chapter = game_state['chapters'][-1]
                
                # Get previous chapter summary
                if 'summary' in prev_chapter and prev_chapter['summary']:
                    previous_chapter_summary = prev_chapter['summary']
                    logger.info(f"Found previous chapter summary: {previous_chapter_summary}")
                
                # Get previous chapter title
                if 'title' in prev_chapter:
                    previous_chapter_title = prev_chapter['title']
                
                # Get the last few segments from previous chapter for more context
                if 'segments' in prev_chapter and prev_chapter['segments'] and 'storyProgress' in game_state:
                    # Get the last segment's index
                    last_segment_idx = prev_chapter['segments'][-1]
                    
                    # Access the story progress segments
                    if len(game_state['storyProgress']) > last_segment_idx:
                        last_segment = game_state['storyProgress'][last_segment_idx]
                        if 'text' in last_segment:
                            previous_chapter_ending = last_segment['text']
                        if 'player' in last_segment and 'action' in last_segment:
                            last_player_action = f"{last_segment['player']} chose to {last_segment['action']}"
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
        current_chapter_idx = game_state.get('currentChapterIndex', 0)
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
            game_state.get('settings', {}), 
            "chapter_transition", 
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

async def generate_tts_endpoint(request: TTSRequest):
    """Generate text-to-speech audio"""
    try:
        logger.info(f"Generating TTS for text of length: {len(request.text)}")
        audio_data = await generate_tts(request.text, "bm_george")
        return {"audioData": audio_data}
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate TTS: {str(e)}")
