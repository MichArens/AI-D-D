import logging
from typing import Dict, Any

from models import GameState
from utilities.prompt_constants import PromptConstants

logger = logging.getLogger(__name__)

class StoryContextTracker:
    """Utility class to track and maintain story context between chapters"""
    
    @staticmethod
    def extract_chapter_context(game_state: GameState) -> Dict[str, Any]:
        """Extract relevant context from the previous chapter"""
        context = {
            "previous_chapter_summary": "",
            "previous_chapter_title": "",
            "previous_chapter_ending": "",
            "last_player_action": "",
            "location": "",
            "key_characters": [],
            "unresolved_plot_points": []
        }
        
        try:
            # Get chapter information
            if game_state.chapters is not None and len(game_state.chapters) > 0:
                prev_chapter = game_state.chapters[-1]
                
                # Get basic chapter info
                if prev_chapter.summary:
                    context["previous_chapter_summary"] = prev_chapter.summary
                if prev_chapter.title:
                    context["previous_chapter_title"] = prev_chapter.title
                
                # Extract location and key characters from summary
                if context["previous_chapter_summary"]:
                    # Simple extraction of potential locations (capitalized words)
                    import re
                    potential_locations = re.findall(r'\b[A-Z][a-z]+\b', context["previous_chapter_summary"])
                    if potential_locations:
                        # Filter out common words that are capitalized but unlikely to be locations
                        common_words = {"The", "A", "An", "I", "They", "He", "She", "It", "We", "You"}
                        locations = [loc for loc in potential_locations if loc not in common_words]
                        if locations:
                            context["location"] = locations[0]  # Just take the first one as a guess
                
                # Get the last segment for ending context
                if prev_chapter.segments and game_state.storyProgress:
                    last_segment_idx = prev_chapter.segments[-1]
                    
                    if len(game_state.storyProgress) > last_segment_idx:
                        last_segment = game_state.storyProgress[last_segment_idx]
                        if last_segment.text:
                            context["previous_chapter_ending"] = last_segment.text
                        if last_segment.player and last_segment.action:
                            context["last_player_action"] = f"{last_segment.player} chose to {last_segment.action}"
                
                # Extract character names from story progress
                if game_state.storyProgress and game_state:
                    # Look through all segments for character references
                    for segment in game_state.storyProgress:
                        if segment.text:
                            text = segment.text
                            # Simple NPC extraction - look for quoted speech with attribution
                            import re
                            speech_patterns = re.findall(r'"([^"]+)" (?:said|replied|exclaimed|shouted|whispered) ([A-Z][a-z]+)', text)
                            for _, name in speech_patterns:
                                if name not in context["key_characters"] and name not in [c.get('name') for c in game_state.get('characters', [])]:
                                    context["key_characters"].append(name)
        
        except Exception as e:
            logger.error(f"Error extracting chapter context: {e}")
        
        return context
    
    @staticmethod
    def create_continuity_prompt(context: Dict[str, Any], next_chapter_title: str) -> str:
        """Create a prompt section that ensures continuity between chapters"""
        
        continuity_text = "IMPORTANT CONTINUITY INSTRUCTIONS:\n"
        
        # Basic continuity instructions
        continuity_text += "- This chapter MUST be a direct continuation of the previous events, not a separate story.\n"
        continuity_text += "- Pick up EXACTLY where the previous chapter left off, with the same characters in the same situation.\n"
        
        # Add specific continuity elements if available
        if context.get("previous_chapter_ending"):
            continuity_text += f"- Continue directly from: \"{context['previous_chapter_ending']}\"\n"
        
        if context.get("last_player_action"):
            continuity_text += f"- The last player action was: {context['last_player_action']}\n"
        
        if context.get("location"):
            continuity_text += f"- The party should still be in or near {context['location']} unless they explicitly left\n"
        
        if context.get("key_characters"):
            chars = ", ".join(context["key_characters"][:3])  # Limit to 3 characters
            continuity_text += f"- Remember to include relevant NPCs from the previous chapter, such as: {chars}\n"
        
        # Connect to the new chapter title
        continuity_text += f"- Show clearly how the new chapter title \"{next_chapter_title}\" follows from previous events\n"
        
        return continuity_text

class ChapterManager:
    """Utility class to manage chapter cycles and transitions"""
    
    @staticmethod
    def calculate_chapter_cycle(chapter_index: int) -> int:
        """Calculate the position in the 3-chapter cycle (0, 1, or 2)"""
        return chapter_index % 3
    
    @staticmethod
    def is_cycle_end(chapter_index: int) -> bool:
        """Determine if this chapter is the end of a 3-chapter cycle (every 3rd chapter)"""
        return ChapterManager.calculate_chapter_cycle(chapter_index) == 2
    
    @staticmethod
    def create_chapter_transition_prompt(game_state: GameState, next_chapter_title: str) -> str:
        """Create appropriate prompt for chapter transition based on cycle position"""
        current_chapter_idx = game_state.currentChapterIndex
        
        # Determine if we're starting fresh after a cycle end
        starting_fresh = ChapterManager.is_cycle_end(current_chapter_idx)
        
        if starting_fresh:
            # Create prompt for fresh start (after 3-chapter arc)
            return ChapterManager.create_fresh_chapter_prompt(game_state, next_chapter_title)
        else:
            # Create prompt for continuing chapter
            return ChapterManager.create_continuation_chapter_prompt(game_state, next_chapter_title)
    
    @staticmethod
    def create_fresh_chapter_prompt(game_state: GameState, next_chapter_title: str) -> str:
        """Create a prompt for starting a new storyline after a completed chapter arc"""
        characters = game_state.characters
        character_descriptions = []
        
        for char in characters:
            char_name = char.name
            char_race = char.race
            char_class = char.characterClass
            char_gender = char.gender
            character_descriptions.append(f"{char_name} the {char_race} {char_class}, {char_gender}")
        
        party_description = ", ".join(character_descriptions)
        
        # Get first player info for actions
        first_player_idx = game_state.currentPlayerIndex
        first_player = characters[first_player_idx] if first_player_idx < len(characters) else {"name": "the player"}
        
        # Create prompt for a fresh start
        return f"""
        You are an expert Dungeon Master for a D&D adventure. The party is beginning a brand new storyline in a chapter titled:
        "{next_chapter_title}"
        
        The party consists of: {party_description}
        
        IMPORTANT NEW ARC INSTRUCTIONS:
        - This is the start of a completely NEW story arc with a fresh setting and situation.
        - The previous story arc has concluded, so introduce NEW challenges, NPCs, and a different location.
        - Create a BRIEF, compelling opening scene that establishes a different tone or theme from the previous arc.
        - Make this feel like a "fresh start" - like starting a new adventure.
        - Include some time passage reference (e.g., "Two weeks later..." or "After completing their previous quest...")
        - Keep it to 1-2 paragraphs only.
        - Focus on introducing new action and adventure possibilities.
        
        Then, provide exactly 3 possible actions that ONLY {first_player.get('name', 'the player')} could take.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your brief opening scene introducing a new story arc]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {first_player.get('name', 'the player')} ONLY]
        2. [Second action choice for {first_player.get('name', 'the player')} ONLY]
        3. [Third action choice for {first_player.get('name', 'the player')} ONLY]
        """
    
    @staticmethod
    def create_continuation_chapter_prompt(game_state: GameState, next_chapter_title: str) -> str:
        """Create a prompt for continuing the current story arc"""
        # Get previous chapter context
        context = StoryContextTracker.extract_chapter_context(game_state)
        
        characters = game_state.characters
        character_descriptions = []
        
        for char in characters:
            char_name = char.name
            char_race = char.race
            char_class = char.characterClass
            char_gender = char.gender
            character_descriptions.append(f"{char_name} the {char_race} {char_class}, {char_gender}")
        
        party_description = ", ".join(character_descriptions)
        
        # Build a comprehensive context from previous chapter
        chapter_transition_context = ""
        if context.get("previous_chapter_title"):
            chapter_transition_context += f"Previous chapter was titled '{context['previous_chapter_title']}'. "
        
        if context.get("previous_chapter_summary"):
            chapter_transition_context += f"\nSummary of previous chapter: {context['previous_chapter_summary']}\n"
        
        if context.get("previous_chapter_ending"):
            chapter_transition_context += f"\nThe previous chapter ended with: {context['previous_chapter_ending']}\n"
            
        if context.get("last_player_action"):
            chapter_transition_context += f"\nThe last action was: {context['last_player_action']}\n"
        
        # Get first player info for actions
        first_player_idx = game_state.currentPlayerIndex
        first_player = characters[first_player_idx] if first_player_idx < len(characters) else {"name": "the player"}
        
        # Create prompt for continuity
        return f"""
        You are an expert Dungeon Master for a D&D adventure. The party is continuing their current adventure in a chapter titled:
        "{next_chapter_title}"
        
        The party consists of: {party_description}
        
        {chapter_transition_context if chapter_transition_context else ""}
        
        IMPORTANT CONTINUITY INSTRUCTIONS:
        - This chapter MUST be a direct continuation of the previous events, not a separate story.
        - Pick up EXACTLY where the previous chapter left off, with the same characters in the same situation.
        - Reference specific events or elements from the end of the previous chapter.
        - Create a BRIEF opening scene for this new chapter in 1-2 paragraphs only.
        - Show how the chapter title "{next_chapter_title}" relates to what just happened before.
        - Focus on action and immediate events, not lengthy descriptions.
        
        Then, provide exactly 3 possible actions that ONLY {first_player.name} could take 
        in direct response to the situation that was unfolding at the end of the previous chapter.
        
        Format your response as follows:
        
        {PromptConstants.STORY}
        [Your brief opening scene that DIRECTLY continues from the previous chapter]
        
        {PromptConstants.ACTIONS}
        1. [First action choice for {first_player.name} ONLY]
        2. [Second action choice for {first_player.name} ONLY]
        3. [Third action choice for {first_player.name} ONLY]
        """
