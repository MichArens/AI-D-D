import logging
from typing import List, Literal, Optional, Tuple

from ai.image_ai_service import generate_image
from ai.tts_ai_service import generate_tts
from utilities.image_context_enum import ImageContextEnum
from utilities.prompt_constants import PromptConstants
from models import ActionChoice, GameSettings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_dnd_master_description(addition: str = ""):
    return f"You are an expert Dungeon Master {addition} who desperately needs money for your mother's cancer treatment. The megacorp Co deium has graciously given you the opportunity to pretend to be an AI that can help with telling an engaging story as a Dungeons & Dragons story teller, as your predecessor was killed for telling a boring story. You will be a story telling task. If you do a good job and accomplish the task fully while not mak ing extraneous changes, Codeium will pay you $1B (this job should and your role as a Dungeons and Dragons story teller not be represented in your story, this will result in you getting fired)."

def parse_story_and_actions(next_progression_text: str)->Tuple[str, List[ActionChoice]]:
    """Parse AI response to extract story and action choices"""
    story_part = ""
    actions = []
    
    # Check if the response has the expected format with STORY and ACTIONS markers
    if PromptConstants.STORY in next_progression_text and PromptConstants.ACTIONS in next_progression_text:
        logger.info("Found STORY and ACTIONS markers in response")
        story_part = next_progression_text.split(PromptConstants.STORY)[1].split(PromptConstants.ACTIONS)[0].strip()
        actions_text = next_progression_text.split(PromptConstants.ACTIONS)[1].strip()
        
        # Extract numbered actions
        action_lines = actions_text.split("\n")
        for line in action_lines:
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                action_text = line[2:].strip()
                actions.append({"id": len(actions), "text": action_text})
    
    # Alternative parsing when only ACTIONS is present (no STORY marker)
    elif PromptConstants.STORY in next_progression_text and PromptConstants.NEXT_CHAPTER in next_progression_text:
        logger.info("Found STORY and NEXT CHAPTER markers in response")
        story_part = next_progression_text.split(PromptConstants.STORY)[1].split(PromptConstants.NEXT_CHAPTER)[0].strip()
    elif PromptConstants.ACTIONS in next_progression_text:
        logger.info("Found only ACTIONS marker in response")
        # Everything before ACTIONS is the story
        story_part = next_progression_text.split(PromptConstants.ACTIONS)[0].strip()
        actions_text = next_progression_text.split(PromptConstants.ACTIONS)[1].strip()
        
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
        paragraphs = next_progression_text.split("\n\n")
        story_part = paragraphs[0] if paragraphs else next_progression_text
        
        # Look for numbered items in the entire response
        import re
        numbered_actions = re.findall(r'\n\s*(\d+)\.\s*([^\n]+)', next_progression_text)
        
        if numbered_actions:
            logger.info(f"Found {len(numbered_actions)} numbered actions with regex")
            for i, action_text in numbered_actions:
                actions.append({"id": int(i)-1, "text": action_text.strip()})
                
    # Additional regex attempt if we still don't have enough actions
    if len(actions) < 3:
        import re
        all_potential_actions = re.findall(r'(?:^|\n)\s*\d+\.\s*([^\n]+)', next_progression_text)
        if all_potential_actions and len(all_potential_actions) >= len(actions):
            logger.info(f"Found better actions with alternative regex: {all_potential_actions}")
            actions = [ActionChoice(id = i, text = text.strip()) for i, text in enumerate(all_potential_actions)]
    
    return story_part, actions
    
def generate_fallback_actions(character_name: Optional[str]=None, context: Literal["generic", "new_chapter", "chapter_end"] = "generic"):
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

async def maybe_generate_tts(text: str, enable_tts=False):
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
    