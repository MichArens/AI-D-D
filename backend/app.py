from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import json
import random
import os
import asyncio
import base64
from enum import Enum

app = FastAPI(title="D&D AI Game Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
OLLAMA_BASE_URL = "http://localhost:11434/api"
SD_BASE_URL = "http://localhost:7860/sdapi/v1"
SUNO_API_URL = "https://api.suno.ai/v1"
SUNO_API_KEY = os.environ.get("SUNO_API_KEY", "")  # Get from environment variables

# Game data structures
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

# Pydantic models for requests and responses
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
    playerIndex: int
    icon: Optional[str] = None  # Base64 encoded image

class GameState(BaseModel):
    settings: GameSettings
    characters: List[PlayerCharacter] = []
    storyProgress: List[Dict[str, Any]] = []
    currentPlayerIndex: int = 0
    musicUrl: Optional[str] = None
    
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

# ----- AI Service Functions -----

async def generate_text(prompt: str, model: str = "llama3"):
    """Generate text using Ollama API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()["response"]
    except Exception as e:
        print(f"Error generating text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

async def generate_image(prompt: str):
    """Generate image using Stable Diffusion API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SD_BASE_URL}/txt2img",
                json={
                    "prompt": f"fantasy art, dungeons and dragons style, detailed, {prompt}",
                    "negative_prompt": "nsfw, poor quality, deformed",
                    "width": 512,
                    "height": 512,
                    "steps": 30
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data["images"][0]  # Base64 encoded image
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

async def generate_music(prompt: str):
    """Generate background music using Suno AI API"""
    if not SUNO_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {SUNO_API_KEY}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{SUNO_API_URL}/generate",
                headers=headers,
                json={
                    "prompt": f"Fantasy adventure music for a D&D game: {prompt}",
                    "duration": 120  # 2 minutes
                },
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("url")
    except Exception as e:
        print(f"Error generating music: {str(e)}")
        return None

# ----- Game Logic Endpoints -----

@app.post("/api/generate-character-options")
async def generate_character_options():
    """Generate available races and classes for this game session"""
    # Randomly select a subset of races and classes to be available this game
    available_races = random.sample(list(Race), min(5, len(Race)))
    available_classes = random.sample(list(CharacterClass), min(5, len(CharacterClass)))
    
    return {
        "races": [race.value for race in available_races],
        "classes": [cls.value for cls in available_classes]
    }

@app.post("/api/generate-character-icon")
async def generate_character_icon(request: CharacterIconRequest):
    """Generate a character icon based on character details"""
    character = request.character
    prompt = f"Portrait of a {character.race} {character.characterClass} named {character.name} in a fantasy D&D style"
    
    try:
        icon_base64 = await generate_image(prompt)
        return {"icon": icon_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate character icon: {str(e)}")

@app.post("/api/start-game")
async def start_game(game_state: GameState, background_tasks: BackgroundTasks):
    """Initialize the game with the first story segment and action choices"""
    model = game_state.settings.aiModel
    
    # Create character description for prompt
    character_descriptions = []
    for char in game_state.characters:
        character_descriptions.append(f"{char.name} the {char.race} {char.characterClass}")
    
    party_description = ", ".join(character_descriptions)
    
    # Generate initial story
    prompt = f"""
    You are the Dungeon Master for a new D&D adventure. Create an engaging opening scene for a party consisting of:
    {party_description}
    
    Provide a vivid description of the initial setting and situation in 3-4 paragraphs.
    Then, generate exactly 3 possible actions that the first player ({game_state.characters[0].name}) could take.
    Format your response as follows:
    
    STORY:
    [Your engaging opening scene here]
    
    ACTIONS:
    1. [First action choice]
    2. [Second action choice]
    3. [Third action choice]
    """
    
    try:
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
            # We don't wait for music to be ready - it will be fetched on subsequent requests
        
        # Update the story progress
        initial_story = {
            "text": story_part,
            "image": image_base64,
            "player": None,
            "action": None
        }
        
        # Return the full response
        return {
            "storyUpdate": initial_story,
            "choices": actions,
            "musicUrl": music_url
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")

@app.post("/api/take-action")
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
    
    # Create prompt for generating the next story segment
    # Include full story history for context
    story_history = ""
    for i, segment in enumerate(game_state.storyProgress):
        story_history += f"Scene {i+1}: {segment.get('text', '')}\n"
        if segment.get('player') and segment.get('action'):
            story_history += f"Then {segment['player']} chose to: {segment['action']}\n"
    
    prompt = f"""
    You are the Dungeon Master for an ongoing D&D adventure. Continue the story based on the player's choice.
    
    Story so far:
    {story_history}
    
    Current player {current_player.name} (a {current_player.race} {current_player.characterClass}) chose to: {chosen_action}
    
    Continue the story with what happens next, then provide exactly 3 possible actions for the next player, {next_player.name} (a {next_player.race} {next_player.characterClass}).
    
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
            story_part = parts[0] if parts else response_text
            actions = [
                {"id": 0, "text": "Investigate further"},
                {"id": 1, "text": "Talk to someone nearby"},
                {"id": 2, "text": "Take a different approach"}
            ]
        
        # Generate image for the story if enabled
        image_base64 = None
        if game_state.settings.enableImages:
            image_base64 = await generate_image(story_part[:200])  # Use first part of story as prompt
        
        # Update the story progress with the player's choice and the next segment
        story_update = {
            "text": story_part,
            "image": image_base64,
            "player": current_player.name,
            "action": chosen_action,
            "choices": actions
        }
        
        # Return the full response
        return {
            "storyUpdate": story_update,
            "choices": actions,
            "nextPlayerIndex": next_player_idx
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process action: {str(e)}")

@app.get("/api/check-music")
async def check_music():
    """Endpoint to check if background music is ready (placeholder)"""
    # In a real implementation, this would check the status of the music generation
    # and return the URL when it's ready
    return {"status": "pending", "url": None}

@app.get("/api/models")
async def get_available_models():
    """Get available models from Ollama"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/tags", timeout=10.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            return {"models": [model["name"] for model in models]}
    except Exception as e:
        # Return a default list if Ollama isn't available
        return {"models": ["llama3", "mistral", "wizard-mega"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)