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

class ActionChoice(BaseModel):
    id: int
    text: str

class StoryScene(BaseModel):
    text: str
    image: Optional[str] = None
    audioData: Optional[str] = None
    choices: List[ActionChoice] = Field(default_factory=list)
    activeCharacterIndex: Optional[int] = None
    chosenAction: Optional[str] = None

class StoryChapter(BaseModel):
    title: str
    summary: Optional[str] = None
    summaryImage: Optional[str] = None
    summaryAudioData: Optional[str] = None
    scenes: List[StoryScene]
    index: int

class StroyArc(BaseModel):
    chapters: List[StoryChapter]

class GameState(BaseModel):
    settings: GameSettings
    characters: List[PlayerCharacter] = Field(default_factory=list)
    arcs: List[StroyArc] = Field(default_factory=list)
    musicUrl: Optional[str] = None
