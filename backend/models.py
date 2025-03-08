from pydantic import BaseModel, Field
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
    scenesPerChapter: int = 3  # Add new setting for chapter length, default to 3
    chaptersPerArc: int = 3  # Add new setting for arc length, default to 3

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

class ActionChoice(BaseModel):
    id: int
    text: str

class StoryProgression(BaseModel):
    text: str
    image: Optional[str] = None
    player: Optional[str] = None
    action: Optional[str] = None
    chapterId: int
    audioData: Optional[str] = None
    choices: List[ActionChoice] = []

class StoryScene(BaseModel):
    text: str
    image: Optional[str] = None
    choices: List[ActionChoice] = Field(default_factory=list)

class StoryChapter(BaseModel):
    title: str
    summary: Optional[str] = None
    summaryImage: Optional[str] = None
    scenes: List[StoryScene]

class StroyArc(BaseModel):
    chapters: List[Chapter]

class GameState(BaseModel):
    settings: GameSettings
    characters: List[PlayerCharacter] = Field(default_factory=list)
    storyProgress: List[StoryProgression] = Field(default_factory=list)
    currentPlayerIndex: int = 0
    musicUrl: Optional[str] = None
    chapters: List[Chapter] = Field(default_factory=list)
    currentChapterIndex: int = 0
    roundsInCurrentChapter: int = 0
    chapterCycle: int = 0  # Track which chapter in the cycle (0, 1, 2)

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
    gameState: GameState
    nextChapterTitle: str
    
    class Config:
        # Make the model more permissive with extra fields
        extra = "ignore"

class TTSRequest(BaseModel):
    text: str
    voice: str = "bm_george"  # Default voice
