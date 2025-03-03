from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class Race(str, Enum):
    HUMAN = "Human"
    ELF = "Elf"
    DWARF = "Dwarf"
    ORC = "Orc"
    HALFLING = "Halfling"
    GNOME = "Gnome"
    DRAGONBORN = "Dragonborn"
    TIEFLING = "Tiefling"

class CharacterClass(str, Enum):
    WARRIOR = "Warrior"
    MAGE = "Mage"
    ROGUE = "Rogue"
    CLERIC = "Cleric"
    BARD = "Bard"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    DRUID = "Druid"

class GameSettings(BaseModel):
    playerCount: int
    enableImages: bool = False
    enableAITTS: bool = False  # Changed from enableTTS to enableAITTS
    enableMusic: bool = False
    aiModel: str = "llama3"

class PlayerCharacter(BaseModel):
    name: str
    race: Race
    characterClass: CharacterClass
    gender: str
    playerIndex: int
    icon: Optional[str] = None  # Base64 encoded image

class Chapter(BaseModel):
    id: int
    title: str
    summary: str = ""
    image: Optional[str] = None  # Base64 encoded image
    segments: List[int] = []  # Indices of story segments in this chapter

class GameState(BaseModel):
    settings: GameSettings
    characters: List[PlayerCharacter] = []
    storyProgress: List[Dict[str, Any]] = []
    currentPlayerIndex: int = 0
    musicUrl: Optional[str] = None
    chapters: List[Chapter] = []
    currentChapterIndex: int = 0
    roundsInCurrentChapter: int = 0
    chapterCycle: int = 0  # Track which chapter in the cycle (0, 1, 2)

class ActionChoice(BaseModel):
    id: int
    text: str

class ActionRequest(BaseModel):
    gameState: GameState
    choiceId: int
    customAction: Optional[str] = None  # Add field for custom action text

class StoryResponse(BaseModel):
    text: str
    image: Optional[str] = None
    choices: List[ActionChoice]

class CharacterIconRequest(BaseModel):
    character: PlayerCharacter
    
class NewChapterRequest(BaseModel):
    gameState: Dict[str, Any]
    nextChapterTitle: str
    
    class Config:
        # Make the model more permissive with extra fields
        extra = "ignore"
        # Allow coercing types when possible
        arbitrary_types_allowed = True
