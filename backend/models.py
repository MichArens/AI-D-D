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
    enableTTS: bool = True
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

class ActionChoice(BaseModel):
    id: int
    text: str

class ActionRequest(BaseModel):
    gameState: GameState
    choiceId: int

class StoryResponse(BaseModel):
    text: str
    image: Optional[str] = None
    choices: List[ActionChoice]

class CharacterIconRequest(BaseModel):
    character: PlayerCharacter
