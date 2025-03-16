import React, { useState, useRef, useEffect } from 'react';
import { GameScreens } from '../types/game-screens';
import { IPlayerCharacter, IStoryScene } from '../types/game-types';
import PlayerWebsocketService from '../utils/websocket/player/player-websocket-service';
import { PlayerMessageType } from '../utils/websocket/player/player-message-types';

interface JoinGameScreenProps {
  setScreen: React.Dispatch<React.SetStateAction<GameScreens>>;
}

interface IRemoteCharacter extends IPlayerCharacter {
  assigned?: boolean;
}

const JoinGameScreen: React.FC<JoinGameScreenProps> = ({ setScreen }) => {
  const [code, setCode] = useState<string[]>(['', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [connected, setConnected] = useState<boolean>(false);
  const [currentScene, setCurrentScene] = useState<IStoryScene | null>(null);

  const [customAction, setCustomAction] = useState<string>('');
  const [showCustomActionForm, setShowCustomActionForm] = useState<boolean>(false);
  
  // New state variables for character selection
  const [selectingCharacter, setSelectingCharacter] = useState<boolean>(false);
  const [availableCharacters, setAvailableCharacters] = useState<IRemoteCharacter[]>([]);
  const [selectedCharacterIndex, setSelectedCharacterIndex] = useState<number | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<IRemoteCharacter | null>(null);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([null, null, null, null]);

  useEffect(() => {
    PlayerWebsocketService.getInstance().onOpen = () => {
        console.log('Player WebSocket connected');
    }
    PlayerWebsocketService.getInstance().on(PlayerMessageType.GAME_STATE_UPDATE, handleGameStateUpdate);
    PlayerWebsocketService.getInstance().on(PlayerMessageType.HOST_DISCONNECTED, handleHostDisconnected);
    PlayerWebsocketService.getInstance().on(PlayerMessageType.JOIN_SESSION_ERROR, handleError);
    PlayerWebsocketService.getInstance().on(PlayerMessageType.AVVAILABLE_CHARACTERS, handleAvailableCharacters);
    PlayerWebsocketService.getInstance().on(PlayerMessageType.CHARACTER_ASSIGNED, handleCharacterAssigned);
    PlayerWebsocketService.getInstance().connect();
    return () => {
        PlayerWebsocketService.getInstance().off(PlayerMessageType.GAME_STATE_UPDATE, handleGameStateUpdate);
        PlayerWebsocketService.getInstance().off(PlayerMessageType.HOST_DISCONNECTED, handleHostDisconnected);
        PlayerWebsocketService.getInstance().off(PlayerMessageType.JOIN_SESSION_ERROR, handleError);
        PlayerWebsocketService.getInstance().off(PlayerMessageType.AVVAILABLE_CHARACTERS, handleAvailableCharacters);
        PlayerWebsocketService.getInstance().off(PlayerMessageType.CHARACTER_ASSIGNED, handleCharacterAssigned);
        PlayerWebsocketService.getInstance().disconnect();
    };
  }, []);

  const handleGameStateUpdate = (data: {data: {type: string, newScene: IStoryScene}}) => {
    console.log('Game state updated:', data);
    setCurrentScene(data.data.newScene);
    setLoading(false);
  };

  useEffect(() => {
    console.log('Current scene update:', typeof(currentScene));
  }, [currentScene]);

  const handleHostDisconnected = () => {
    setError('Game host has disconnected. Please go back to the main menu.');
    setConnected(false);
  };

  const handleError = (data: any) => {
    setError(data.message || 'An error occurred');
    setLoading(false);
  };

  const handleAvailableCharacters = (data: {data: {characters: IPlayerCharacter[]}}) => {
    setAvailableCharacters(data.data.characters);
    setConnected(true);
    setSelectingCharacter(true);
    setLoading(false);
  };

  const handleCharacterAssigned = (data: any) => {
    setSelectedCharacter(data.data.character);
    setSelectingCharacter(false);
  };

  const handleInputChange = (index: number, value: string) => {
    if (value.length <= 1 && /^\d*$/.test(value)) {
      const newCode = [...code];
      newCode[index] = value;
      setCode(newCode);
      
      // Auto-advance to next input
      if (value && index < 3) {
        inputRefs.current[index + 1]?.focus();
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Handle backspace to go to previous input
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleJoinGame = async () => {
    const sessionCode = code.join('');
    if (sessionCode.length !== 4) {
      setError('Please enter a valid 4-digit code');
      return;
    }

    setLoading(true);
    setError(null);

    try {
        PlayerWebsocketService.getInstance().joinSession(sessionCode);
        // Connection established, now waiting for character data
        // The server will send available_characters message
    } catch (err: any) {
      setError(err.message || 'Failed to join game');
      setLoading(false);
    }
  };

  const handleCharacterSelect = (index: number) => {
    if (availableCharacters[index]?.assigned) {
      setError('This character is already taken by another player');
      return;
    }
    setSelectedCharacterIndex(index);
  };

  const handleConfirmCharacter = () => {
    if (selectedCharacterIndex !== null) {
      setLoading(true);
      setError(null);
      
      PlayerWebsocketService.getInstance().selectCharacter(selectedCharacterIndex);
    }
  };

  const handleActionSelect = (action: string) => {
    if (action === 'custom') {
        setShowCustomActionForm(true);
    } else {
        PlayerWebsocketService.getInstance().sendPlayerAction(action);
        setLoading(true);
    }
  };

  const handleCustomActionSubmit = () => {
    if (customAction.trim()) {
        PlayerWebsocketService.getInstance().sendPlayerAction(customAction);
        setCustomAction('');
        setShowCustomActionForm(false);
        setLoading(true);
    }
  };

  const handleCancel = () => {
    setShowCustomActionForm(false);
    setCustomAction('');
  };

  // Render based on the current state in the flow
  if (!connected) {
    // Code entry screen
    return (
      <div className="join-game-screen">
        <h1>Join Game</h1>
        
        <div className="join-form">
          <p>Enter the 4-digit game code provided by the game host:</p>
          
          <div className="code-input-container">
            {[0, 1, 2, 3].map((index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el; }}
                type="text"
                className="code-input"
                value={code[index]}
                onChange={(e) => handleInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                maxLength={1}
                autoFocus={index === 0}
              />
            ))}
          </div>
          
          <div className="actions">
            <button 
              className="secondary-button" 
              onClick={() => setScreen('setup')}
              disabled={loading}
            >
              Back
            </button>
            <button 
              className="main-button" 
              onClick={handleJoinGame}
              disabled={loading || code.join('').length !== 4}
            >
              {loading ? 'Connecting...' : 'Join Game'}
            </button>
          </div>
          
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
    );
  } else if (selectingCharacter) {
    // Character selection screen
    return (
      <div className="join-game-screen">
        <h1>Select Your Character</h1>
        
        <div className="character-selection-container">
          <p>Choose a character to play as:</p>
          
          <div className="available-characters">
            {availableCharacters.map((character, index) => (
              <div 
                key={index}
                className={`character-option ${character.assigned ? 'character-taken' : ''} ${selectedCharacterIndex === index ? 'character-selected' : ''}`}
                onClick={() => !character.assigned && handleCharacterSelect(index)}
              >
                <div className="character-avatar">
                  {character.icon ? (
                    <img 
                      src={`data:image/png;base64,${character.icon}`}
                      alt={character.name}
                      className="character-icon"
                    />
                  ) : (
                    <div className="character-placeholder">
                      {character.name.charAt(0)}
                    </div>
                  )}
                </div>
                <div className="character-details">
                  <h3>{character.name}</h3>
                  <p>{character.race} {character.characterClass}</p>
                  <p>{character.gender}</p>
                  {character.assigned && <span className="taken-badge">Already taken</span>}
                </div>
              </div>
            ))}
          </div>
          
          <div className="actions">
            <button 
              className="secondary-button" 
              onClick={() => {
                setConnected(false);
              }}
              disabled={loading}
            >
              Cancel
            </button>
            <button 
              className="main-button" 
              onClick={handleConfirmCharacter}
              disabled={loading || selectedCharacterIndex === null || availableCharacters[selectedCharacterIndex]?.assigned}
            >
              {loading ? 'Selecting...' : 'Choose This Character'}
            </button>
          </div>
          
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
    );
  } else {
    // Game view - after character selection
    return (
      <div className="join-game-screen">
        <h1>Game Session</h1>
        
        {selectedCharacter && (
          <div className="player-character-info">
            <h2>Playing as: {selectedCharacter.name}</h2>
            <p>{selectedCharacter.race} {selectedCharacter.characterClass}</p>
          </div>
        )}
        
        <div className="player-view">

          <div className="story-container player-story">
            <div className="story-text">
              {currentScene?.text || "Waiting for the game to start..."}
            </div>
          </div>
          
          {currentScene && currentScene.activeCharacterIndex == selectedCharacter?.playerIndex && currentScene.choices.length > 0 ? (
            <div className="player-actions">
              <h3>Your Turn - Choose an Action</h3>
              
              <div className="action-choices">
                {currentScene?.choices.map(choice => (
                  <button
                    key={choice.id}
                    className="action-button"
                    onClick={() => handleActionSelect(choice.text)}
                  >
                    {choice.text}
                  </button>
                ))}
                <button 
                  className="action-button custom-action-button" 
                  onClick={() => handleActionSelect('custom')}
                >
                  Custom Action...
                </button>
              </div>
            </div>
          ) : (
            <div className="waiting-message">
              <p>{currentScene && currentScene.choices.length == 0 ? "Waiting for new chapter to begin..." : "Waiting for your turn..."}</p>
            </div>
          )}
          
          {showCustomActionForm && (
            <div className="custom-action-modal">
              <div className="modal-content">
                <h3>Custom Action</h3>
                <p>Describe what you want to do:</p>
                <textarea
                  value={customAction}
                  onChange={(e) => setCustomAction(e.target.value)}
                  rows={4}
                  placeholder="I want to..."
                />
                <div className="custom-action-buttons">
                  <button className="secondary-button" onClick={handleCancel}>
                    Cancel
                  </button>
                  <button
                    className="main-button"
                    onClick={handleCustomActionSubmit}
                    disabled={!customAction.trim()}
                  >
                    Submit
                  </button>
                </div>
              </div>
            </div>
          )}
          
          <div className="actions">
            <button 
              className="secondary-button" 
              onClick={() => {
                setScreen('setup');
              }}
            >
              Leave Game
            </button>
          </div>
        </div>
      </div>
    );
  }
};

export default JoinGameScreen;
