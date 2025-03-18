import asyncio
import json
import random
import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Set

from models import PlayerCharacter, StoryScene

logger = logging.getLogger(__name__)

class GameSessionManager:
    """Manages active game sessions and connected WebSocket clients"""
    
    def __init__(self):
        # Map of session_code -> GameSession
        self.active_sessions: Dict[str, 'GameSession'] = {}
        # Set of used session codes to avoid duplicates
        self.used_codes: Set[str] = set()
    
    def generate_session_code(self) -> str:
        """Generate a unique 4-digit session code"""
        while True:
            # Generate a random 4-digit code
            code = f"{random.randint(0, 9999):04d}"
            if code not in self.used_codes:
                self.used_codes.add(code)
                return code
    
    def create_session(self, host_websocket: WebSocket) -> str:
        """Create a new game session with a unique code"""
        session_code = self.generate_session_code()
        self.active_sessions[session_code] = GameSession(session_code, host_websocket)
        logger.info(f"Created new game session with code: {session_code}")
        return session_code
    
    def get_session(self, session_code: str) -> Optional['GameSession']:
        """Get a game session by its code"""
        return self.active_sessions.get(session_code)
    
    def remove_session(self, session_code: str) -> None:
        """Remove a game session when it ends"""
        if session_code in self.active_sessions:
            del self.active_sessions[session_code]
            logger.info(f"Removed game session with code: {session_code}")
            
    def set_session_characters(self, session_code: str, characters: List[PlayerCharacter]) -> None:
        """Set the available characters for a session"""
        session = self.get_session(session_code)
        if session:
            session.characters = characters

class GameSession:
    """Represents an active game session with connected clients"""
    
    def __init__(self, session_code: str, host_websocket: WebSocket):
        self.session_code = session_code
        self.host_websocket = host_websocket
        # List of connected player WebSockets (excluding host)
        self.player_connections: List[WebSocket] = []
        # Current game state information relevant to connected clients
        self.current_scene: StoryScene = None
        # Character information
        self.characters: List[PlayerCharacter] = []
        self.assigned_characters: Dict[WebSocket, int] = {}  # Map websockets to character indices
    
    async def connect_player(self, websocket: WebSocket) -> None:
        """Connect a new player to this session"""
        self.player_connections.append(websocket)
        # Send the current state and available characters to the new player
        await self.send_available_characters(websocket)
        logger.info(f"Player joined session {self.session_code}, total players: {len(self.player_connections)}")
    
    async def send_available_characters(self, websocket: WebSocket) -> None:
        """Send available characters to the player for selection"""
        try:
            logger.info(f"Sending available characters to player {self.assigned_characters}")
            assigned_indices = set(self.assigned_characters.values())
            available_characters = []
            
            # Create a list of available characters with their assignment status
            for idx, char in enumerate(self.characters):
                available_characters.append({
                    **char,
                    "assigned": idx in assigned_indices
                })
            
            await websocket.send_json({
                "type": "available_characters",
                "data": {
                    "characters": available_characters
                }
            })
        except Exception as e:
            logger.error(f"Error sending available characters: {e}")
    
    async def assign_character(self, websocket: WebSocket, character_index: int) -> bool:
        """Assign a character to a player"""
        # Check if character is already assigned
        if character_index in self.assigned_characters.values():
            await websocket.send_json({
                "type": "error",
                "message": "This character is already taken by another player"
            })
            return False
        
        # Check if index is valid
        if character_index < 0 or character_index >= len(self.characters):
            await websocket.send_json({
                "type": "error",
                "message": "Invalid character selection"
            })
            return False
            
        # Assign the character
        self.assigned_characters[websocket] = character_index
        
        # Confirm assignment to player
        await websocket.send_json({
            "type": "character_assigned",
            "data": {
                "character": self.characters[character_index]
            }
        })
        
        # Send game state now that character is assigned
        await self.send_game_state_to_player(websocket)
        
        # Notify host of character assignment
        try:
            await self.host_websocket.send_json({
                "type": "player_character_assigned",
                "data": {
                    "player_index": self.player_connections.index(websocket),
                    "character_index": character_index,
                    "character_name": self.characters[character_index]["name"]
                }
            })
        except Exception as e:
            logger.error(f"Error notifying host of character assignment: {e}")
            
        return True
    
    async def disconnect_player(self, websocket: WebSocket) -> None:
        """Remove a player connection"""
        if websocket in self.player_connections:
            self.player_connections.remove(websocket)
            
            # Free up the assigned character if any
            if websocket in self.assigned_characters:
                del self.assigned_characters[websocket]
                
            logger.info(f"Player left session {self.session_code}, remaining players: {len(self.player_connections)}")
    
    async def send_game_state_to_player(self, websocket: WebSocket) -> None:
        """Send current game state to a specific player"""
        try:
            logger.info(f"Sending game state to player \n{self.current_scene}")
            
            if websocket in self.assigned_characters:
                await websocket.send_json({
                    "type": "game_state_update",
                    "data": {
                        "newScene": self.current_scene.model_dump()
                    }
                })
        except Exception as e:
            logger.error(f"Error sending game state to player: {e}")
    
    async def update_game_state(self, new_scene: StoryScene) -> None:
        """Update the current game state and broadcast to all players"""        
        # Broadcast to all players who have selected characters
        self.current_scene = new_scene.model_copy()
        logger.info(f"Updated game state for session {self.session_code}")
        for player_ws in self.player_connections:
            if player_ws in self.assigned_characters:
                try:
                    await self.send_game_state_to_player(player_ws)
                except Exception as e:
                    logger.error(f"Error updating game state for player: {e}")
    
    async def update_characters(self, characters: List[Dict]) -> None:
        """Update the character list when the host provides new information"""
        self.characters = characters
        
        # Notify all connected players about updated character list
        for player_ws in self.player_connections:
            if player_ws not in self.assigned_characters:
                await self.send_available_characters(player_ws)
    
    async def handle_player_action(self, player_index: int, action: str) -> None:
        """Process a player action and send it to the host"""
        # Find the websocket for this player
        if player_index < len(self.player_connections):
            player_ws = self.player_connections[player_index]
            
            # Check if this player has a character assigned
            if player_ws not in self.assigned_characters:
                return  # Player hasn't selected a character yet
                
            character_index = self.assigned_characters[player_ws]
            
            # Only process if it's this character's turn
            if character_index != self.current_scene.activeCharacterIndex:
                return  # Not this player's character's turn
                
            try:
                # Forward the action to the host
                await self.host_websocket.send_json({
                    "type": "player_action",
                    "data": {
                        "player_index": character_index,  # Use character index instead of connection index
                        "action": action
                    }
                })
            except Exception as e:
                logger.error(f"Error sending player action to host: {e}")

# Singleton instance of the session manager
game_session_manager = GameSessionManager()

async def handle_websocket_connection(websocket: WebSocket):
    """Handle a new WebSocket connection"""
    # IMPORTANT: Always accept the WebSocket connection first
    await websocket.accept()
    
    session: Optional[GameSession] = None
    is_host = False
    
    try:
        data = await websocket.receive_json()
        
        if data["type"] == "create_session":
            session_code = game_session_manager.create_session(websocket)
            session = game_session_manager.get_session(session_code)
            is_host = True
            
            await websocket.send_json({
                "type": "session_created",
                "session_code": session_code
            })
            
            logger.info(f"Host created new session: {session_code}")
            
        elif data["type"] == "join_session":
            logger.info(f"Player joining session {data}")
            session_code = data["data"]["sessionCode"]
            session = game_session_manager.get_session(session_code)
            
            if not session:
                await websocket.send_json({
                    "type": "join_session_error",
                    "message": "Invalid session code"
                })
                return
            
            await session.connect_player(websocket)
            
            try:
                await session.host_websocket.send_json({
                    "type": "player_joined",
                    "player_count": len(session.player_connections)
                })
            except Exception as e:
                logger.error(f"Error notifying host of new player: {e}")
        
        # Main message loop
        while True:
            message = await websocket.receive_json()
            
            if is_host:
                if message["type"] == "update_game_state":
                    await session.update_game_state(StoryScene(**message["data"]['scene']))
                elif message["type"] == "update_characters":
                    await session.update_characters(message["data"]["characters"])
            else:
                if message["type"] == "player_action":
                    player_index = session.player_connections.index(websocket)
                    await session.handle_player_action(player_index, message["data"]["action"])
                elif message["type"] == "select_character":
                    character_index = message["data"]["character_index"]
                    await session.assign_character(websocket, character_index)
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        if session:
            if is_host:
                game_session_manager.remove_session(session.session_code)
            else:
                await session.disconnect_player(websocket)
    
                try:
                    await session.host_websocket.send_json({
                        "type": "player_left",
                        "player_count": len(session.player_connections)
                    })
                except:
                    pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if session and is_host:
            game_session_manager.remove_session(session.session_code)
