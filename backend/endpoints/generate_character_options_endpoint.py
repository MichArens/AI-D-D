import logging
import random
import traceback


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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