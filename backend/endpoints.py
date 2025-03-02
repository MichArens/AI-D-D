from fastapi import HTTPException, BackgroundTasks
from models import GameState, ActionRequest, CharacterIconRequest, Chapter, NewChapterRequest
from ai_services import generate_text, generate_image, generate_music
import random
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix the character options endpoint with better error handling
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
    
    # Create character description for prompt
    character_descriptions = []
    for char in game_state.characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass}, {char.gender}")
    
    party_description = ", ".join(character_descriptions)
    
    # Generate chapter title
    chapter_prompt = f"""
    You are the Dungeon Master for a new D&D adventure. Create an engaging chapter title for the beginning of an adventure
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
        You are the Dungeon Master for a new D&D adventure. Create an engaging opening scene for a party consisting of:
        {party_description}
        
        This is Chapter 1: "{chapter_title}" of the adventure.
        Provide a vivid description of the initial setting and situation in 3-4 paragraphs, making sure to include their genders.
        Then, generate exactly 3 possible actions that the first player ({game_state.characters[0].name}) could take.
        Format your response as follows:
        
        STORY:
        [Your engaging opening scene here]
        
        ACTIONS:
        1. [First action choice]
        2. [Second action choice]
        3. [Third action choice]
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
            # Simple fallback parsing
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
        
        # Generate background music if enabled
        music_url = None
        if game_state.settings.enableMusic:
            background_tasks.add_task(generate_music, story_part[:100])
        
        # Update the story progress
        initial_story = {
            "text": story_part,
            "image": image_base64,
            "player": None,
            "action": None,
            "chapterId": 0
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

async def take_action(request: ActionRequest):
    """Process a player's action and generate the next story segment"""
    game_state = request.gameState
    choice_id = request.choiceId
    model = game_state.settings.aiModel
    
    # Get the current player and their chosen action
    current_player_idx = game_state.currentPlayerIndex
    current_player = game_state.characters[current_player_idx]
    
    # Get the action choices and selected action
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
    
    # Calculate next player's index
    next_player_idx = (current_player_idx + 1) % len(game_state.characters)
    next_player = game_state.characters[next_player_idx]
    
    # Increment the rounds in current chapter counter - make sure this is used correctly
    rounds_in_chapter = game_state.roundsInCurrentChapter + 1
    current_chapter_idx = game_state.currentChapterIndex
    current_chapter = game_state.chapters[current_chapter_idx] if game_state.chapters and len(game_state.chapters) > current_chapter_idx else None
    
    # Fixed: Ensure chapter ends precisely after 3 rounds
    end_chapter = rounds_in_chapter >= 3
    
    # Create prompt for generating the next story segment
    # Include story history from this chapter only
    chapter_story = ""
    if current_chapter and current_chapter.segments:
        for seg_idx in current_chapter.segments:
            if seg_idx < len(game_state.storyProgress):
                segment = game_state.storyProgress[seg_idx]
                chapter_story += f"{segment.get('text', '')}\n"
                if segment.get('player') and segment.get('action'):
                    chapter_story += f"Then {segment['player']} chose to: {segment['action']}\n"
    
    # Create prompt based on whether the chapter is ending
    if end_chapter:
        prompt = f"""
        You are the Dungeon Master for an ongoing D&D adventure. The current chapter is ending.
        
        Story this chapter:
        {chapter_story}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        Write a satisfying conclusion to this chapter that resolves the immediate situation, based on {current_player.name}'s action.
        Then create a title for the next chapter that hints at a new development or location.
        
        Format your response as follows:
        
        STORY:
        [Your engaging chapter conclusion here, 2-3 paragraphs]
        
        NEXT CHAPTER:
        [New chapter title - short and evocative]
        """
    else:
        prompt = f"""
        You are the Dungeon Master for an ongoing D&D adventure. Continue the story based on the player's choice.
        
        Story so far this chapter:
        {chapter_story}
        
        Current player {current_player.name} (a {current_player.race} {current_player.characterClass}, {current_player.gender}) chose to: {chosen_action}
        
        Continue the story with what happens next according to the current player's choice, then provide exactly 3 possible actions for the next player, {next_player.name} (a {next_player.race} {next_player.characterClass}, {next_player.gender}).
        
        Format your response as follows:
        
        STORY:
        [Your engaging continuation here, 2-3 paragraphs]
        
        ACTIONS:
        1. [First action choice]
        2. [Second action choice]
        3. [Third action choice]
        """
    
    try:
        response_text = await generate_text(prompt, model)
        
        if end_chapter:
            # Parse the response to extract story conclusion and next chapter title
            story_part = ""
            next_chapter_title = "The Next Chapter"
            
            if "STORY:" in response_text and "NEXT CHAPTER:" in response_text:
                story_part = response_text.split("STORY:")[1].split("NEXT CHAPTER:")[0].strip()
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
                story_part = parts[0] if parts else response_text
                if len(parts) > 1:
                    # Use a more conservative approach for title extraction
                    potential_title = parts[-1].strip().strip('"').strip("'")
                    # If the potential title is too long, it's likely part of the story
                    if len(potential_title) <= 50:
                        next_chapter_title = potential_title
                    else:
                        # Generate a generic title
                        next_chapter_title = f"Chapter {current_chapter_idx + 2}"
            
            # Additional safeguard to ensure title is reasonable
            if len(next_chapter_title) < 3 or len(next_chapter_title) > 50:
                next_chapter_title = f"Chapter {current_chapter_idx + 2}"
            
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
            chapter_image = None
            if game_state.settings.enableImages:
                image_prompt = f"Fantasy illustration of: {chapter_summary}"
                chapter_image = await generate_image(image_prompt)
            
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
            next_chapter_prompt = f"""
            You are the Dungeon Master for a D&D adventure. The party has just started a new chapter titled "{next_chapter_title}".
            Provide exactly 3 possible actions that {next_player.name} (a {next_player.race} {next_player.characterClass}) could take in this new situation.
            
            Format your response as:
            
            1. [First action choice]
            2. [Second action choice]
            3. [Third action choice]
            """
            
            actions_response = await generate_text(next_chapter_prompt, model)
            actions = []
            action_lines = actions_response.split("\n")
            for line in action_lines:
                line = line.strip()
                if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                    action_text = line[2:].strip()
                    actions.append({"id": len(actions), "text": action_text})
            
            # Fallback if parsing failed
            if len(actions) < 3:
                actions = [
                    {"id": 0, "text": "Explore the new area"},
                    {"id": 1, "text": "Seek out new allies or information"},
                    {"id": 2, "text": "Prepare for potential challenges ahead"}
                ]
                
        else:
            # Parse standard response (mid-chapter)
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
            
            # Fallback parsing
            if not story_part or len(actions) != 3:
                parts = response_text.split("\n\n")
                story_part = parts[0] if parts else response_text
                actions = [
                    {"id": 0, "text": "Investigate further"},
                    {"id": 1, "text": "Talk to someone nearby"},
                    {"id": 2, "text": "Take a different approach"}
                ]
        
        # Generate image for the story if enabled
        image_base64 = None
        if game_state.settings.enableImages:
            image_base64 = await generate_image(story_part[:200])
        
        # Create the story update
        next_chapter_id = current_chapter_idx + 1 if end_chapter else current_chapter_idx
        story_update = {
            "text": story_part,
            "image": image_base64,
            "player": current_player.name,
            "action": chosen_action,
            "chapterId": next_chapter_id
        }
        
        # Return different response structures based on whether chapter ended
        if end_chapter:
            return {
                "storyUpdate": story_update,
                "choices": actions,
                "nextPlayerIndex": next_player_idx,
                "chapterEnded": True,
                "chapterSummary": chapter_summary,
                "chapterImage": chapter_image,
                "nextChapterTitle": next_chapter_title, # Explicitly include title
                "nextChapter": {
                    "id": next_chapter_id,
                    "title": next_chapter_title
                },
                "roundsInChapter": 0  # Reset for new chapter
            }
        else:
            return {
                "storyUpdate": story_update,
                "choices": actions,
                "nextPlayerIndex": next_player_idx,
                "chapterEnded": False,
                "roundsInChapter": rounds_in_chapter
            }
        
    except Exception as e:
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
    """Generate the first segment of a new chapter"""
    try:
        logger.info(f"Starting new chapter: '{request.nextChapterTitle}'")
        
        game_state = request.gameState
        next_chapter_title = request.nextChapterTitle
        
        # Safely get model from game state
        model = game_state.get('settings', {}).get('aiModel', 'llama3')
        logger.info(f"Using AI model: {model}")
        
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
        
        # Create prompt for new chapter start
        prompt = f"""
        You are the Dungeon Master for an ongoing D&D adventure. The party is beginning a new chapter titled:
        "{next_chapter_title}"
        
        The party consists of: {party_description}
        
        Create an engaging opening scene for this new chapter in 3-4 paragraphs.
        Then, provide exactly 3 possible actions that {first_player.get('name', 'the player')} could take.
        
        Format your response as follows:
        
        STORY:
        [Your engaging opening scene here]
        
        ACTIONS:
        1. [First action choice]
        2. [Second action choice]
        3. [Third action choice]
        """
        
        # Generate response
        response_text = await generate_text(prompt, model)
        
        # Rest of your parsing logic...
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
        
        # If parsing failed, use fallback
        if not story_part or len(actions) != 3:
            story_part = response_text.split("\n\n")[0] if "\n\n" in response_text else response_text
            actions = [
                {"id": 0, "text": "Investigate the area"},
                {"id": 1, "text": "Talk to someone nearby"},
                {"id": 2, "text": "Search for something useful"}
            ]
        
        # Generate image if enabled
        image_base64 = None
        enable_images = game_state.get('settings', {}).get('enableImages', False)
        if enable_images:
            image_prompt = f"Fantasy scene: {story_part[:200]}"
            image_base64 = await generate_image(image_prompt)
        
        logger.info("Successfully generated new chapter opening")
        return {
            "storyUpdate": {
                "text": story_part,
                "image": image_base64,
                "choices": actions
            },
            "choices": actions
        }
        
    except Exception as e:
        logger.error(f"Error in start_new_chapter: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to start new chapter: {str(e)}")
