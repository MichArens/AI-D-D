import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// API service
const API_BASE_URL = 'http://localhost:8000/api';

const api = {
  async getModels() {
    const response = await fetch(`${API_BASE_URL}/models`);
    return response.json();
  },
  
  async getCharacterOptions() {
    const response = await fetch(`${API_BASE_URL}/generate-character-options`, {
      method: 'POST'
    });
    return response.json();
  },
  
  async generateCharacterIcon(character) {
    const response = await fetch(`${API_BASE_URL}/generate-character-icon`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character })
    });
    return response.json();
  },
  
  async startGame(gameState) {
    const response = await fetch(`${API_BASE_URL}/start-game`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gameState)
    });
    return response.json();
  },
  
  async takeAction(gameState, choiceId) {
    const response = await fetch(`${API_BASE_URL}/take-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gameState, choiceId })
    });
    return response.json();
  }
};

// App Component
function App() {
  // Game state
  const [screen, setScreen] = useState('setup'); // 'setup', 'character', 'game'
  const [availableModels, setAvailableModels] = useState(['llama3']);
  const [characterOptions, setCharacterOptions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [gameState, setGameState] = useState({
    settings: {
      playerCount: 2,
      enableImages: false,
      enableTTS: true,
      enableMusic: false,
      aiModel: 'llama3'
    },
    characters: [],
    storyProgress: [],
    currentPlayerIndex: 0,
    musicUrl: null
  });
  const [currentAction, setCurrentAction] = useState(null);
  const storyRef = useRef(null);
  const speechSynthesisRef = useRef(null);
  
  // Load available models on startup
  useEffect(() => {
    async function loadModels() {
      try {
        const { models } = await api.getModels();
        setAvailableModels(models);
        setGameState(prev => ({
          ...prev,
          settings: { ...prev.settings, aiModel: models[0] }
        }));
      } catch (err) {
        console.error('Failed to load models:', err);
      }
    }
    
    loadModels();
  }, []);
  
  // Scroll to bottom of story container when content updates
  useEffect(() => {
    if (storyRef.current) {
      storyRef.current.scrollTop = storyRef.current.scrollHeight;
    }
  }, [gameState.storyProgress]);
  
  // Text-to-speech for new story segments
  useEffect(() => {
    if (gameState.settings.enableTTS && gameState.storyProgress.length > 0) {
      const lastStory = gameState.storyProgress[gameState.storyProgress.length - 1];
      if (lastStory && lastStory.text && !lastStory.spoken) {
        // Mark as spoken to prevent multiple readings
        setGameState(prev => {
          const newProgress = [...prev.storyProgress];
          newProgress[newProgress.length - 1] = { ...newProgress[newProgress.length - 1], spoken: true };
          return { ...prev, storyProgress: newProgress };
        });
        
        if (window.speechSynthesis) {
          // Cancel any ongoing speech
          window.speechSynthesis.cancel();
          
          // Create new utterance
          const utterance = new SpeechSynthesisUtterance(lastStory.text);
          utterance.rate = 0.9; // Slightly slower for clarity
          speechSynthesisRef.current = utterance;
          window.speechSynthesis.speak(utterance);
        }
      }
    }
    
    return () => {
      if (window.speechSynthesis && speechSynthesisRef.current) {
        window.speechSynthesis.cancel();
      }
    };
  }, [gameState.storyProgress, gameState.settings.enableTTS]);
  
  // Handle setup screen settings
  const handleSettingsChange = (setting, value) => {
    setGameState(prev => ({
      ...prev,
      settings: { ...prev.settings, [setting]: value }
    }));
  };
  
  // Navigate to character creation
  const handleStartSetup = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const options = await api.getCharacterOptions();
      setCharacterOptions(options);
      
      // Initialize character slots based on player count
      const initialCharacters = Array(gameState.settings.playerCount).fill(null).map((_, idx) => ({
        name: '',
        race: null,
        characterClass: null,
        playerIndex: idx,
        icon: null
      }));
      
      setGameState(prev => ({
        ...prev,
        characters: initialCharacters
      }));
      
      setScreen('character');
    } catch (err) {
      setError('Failed to initialize character creation. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Update character data
  const handleCharacterChange = (index, field, value) => {
    setGameState(prev => {
      const newCharacters = [...prev.characters];
      newCharacters[index] = { ...newCharacters[index], [field]: value };
      return { ...prev, characters: newCharacters };
    });
  };
  
  // Check if all characters are complete
  const areCharactersComplete = () => {
    return gameState.characters.every(char => 
      char.name && char.race && char.characterClass
    );
  };
  
  // Start the game
  const handleStartGame = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Generate icons for all characters if images are enabled
      if (gameState.settings.enableImages) {
        const updatedCharacters = [...gameState.characters];
        
        for (let i = 0; i < updatedCharacters.length; i++) {
          const character = updatedCharacters[i];
          const { icon } = await api.generateCharacterIcon(character);
          updatedCharacters[i] = { ...character, icon };
        }
        
        setGameState(prev => ({
          ...prev,
          characters: updatedCharacters
        }));
      }
      
      // Initialize the game with the first story segment
      const gameResponse = await api.startGame(gameState);
      
      setGameState(prev => {
        // Add initial story to progress
        const newStoryProgress = [...prev.storyProgress];
        const initialStory = { 
          ...gameResponse.storyUpdate,
          choices: gameResponse.choices
        };
        newStoryProgress.push(initialStory);
        
        return {
          ...prev,
          storyProgress: newStoryProgress,
          musicUrl: gameResponse.musicUrl
        };
      });
      
      setScreen('game');
    } catch (err) {
      setError('Failed to start game. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle player action choice
  const handleActionChoice = async (choiceId) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    setCurrentAction(choiceId);
    
    try {
      const response = await api.takeAction(gameState, choiceId);
      
      setGameState(prev => {
        // Add new story segment to progress
        const newStoryProgress = [...prev.storyProgress];
        const newStory = { 
          ...response.storyUpdate,
          choices: response.choices
        };
        newStoryProgress.push(newStory);
        
        return {
          ...prev,
          storyProgress: newStoryProgress,
          currentPlayerIndex: response.nextPlayerIndex
        };
      });
      
      setCurrentAction(null);
    } catch (err) {
      setError('Failed to process action. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Render Setup Screen
  const renderSetupScreen = () => (
    <div className="setup-screen">
      <h1>D&D AI Adventure</h1>
      <div className="setup-form">
        <div className="setup-section">
          <h2>Game Settings</h2>
          
          <div className="form-group">
            <label>Number of Players:</label>
            <select 
              value={gameState.settings.playerCount}
              onChange={(e) => handleSettingsChange('playerCount', parseInt(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6].map(num => (
                <option key={num} value={num}>{num}</option>
              ))}
            </select>
          </div>
          
          <div className="form-group">
            <label>AI Model:</label>
            <select 
              value={gameState.settings.aiModel}
              onChange={(e) => handleSettingsChange('aiModel', e.target.value)}
            >
              {availableModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>
          
          <div className="features-group">
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableImages" 
                checked={gameState.settings.enableImages}
                onChange={(e) => handleSettingsChange('enableImages', e.target.checked)}
              />
              <label htmlFor="enableImages">Enable Image Generation</label>
            </div>
            
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableTTS" 
                checked={gameState.settings.enableTTS}
                onChange={(e) => handleSettingsChange('enableTTS', e.target.checked)}
              />
              <label htmlFor="enableTTS">Enable Text-to-Speech Narration</label>
            </div>
            
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableMusic" 
                checked={gameState.settings.enableMusic}
                onChange={(e) => handleSettingsChange('enableMusic', e.target.checked)}
              />
              <label htmlFor="enableMusic">Enable Background Music</label>
            </div>
          </div>
        </div>
      </div>
      
      <div className="actions">
        <button 
          className="main-button" 
          onClick={handleStartSetup}
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Continue to Character Creation'}
        </button>
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
  
  // Render Character Creation Screen
  const renderCharacterScreen = () => (
    <div className="character-screen">
      <h1>Character Creation</h1>
      
      <div className="character-form">
        {gameState.characters.map((character, index) => (
          <div key={index} className="character-card">
            <h3>Player {index + 1}</h3>
            
            <div className="form-group">
              <label>Character Name:</label>
              <input 
                type="text" 
                value={character.name || ''}
                onChange={(e) => handleCharacterChange(index, 'name', e.target.value)}
                placeholder="Enter name"
              />
            </div>
            
            <div className="form-group">
              <label>Race:</label>
              <select 
                value={character.race || ''}
                onChange={(e) => handleCharacterChange(index, 'race', e.target.value)}
              >
                <option value="">Select Race</option>
                {characterOptions?.races?.map(race => (
                  <option key={race} value={race}>{race}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label>Class:</label>
              <select 
                value={character.characterClass || ''}
                onChange={(e) => handleCharacterChange(index, 'characterClass', e.target.value)}
              >
                <option value="">Select Class</option>
                {characterOptions?.classes?.map(cls => (
                  <option key={cls} value={cls}>{cls}</option>
                ))}
              </select>
            </div>
          </div>
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
          onClick={handleStartGame}
          disabled={loading || !areCharactersComplete()}
        >
          {loading ? 'Creating Adventure...' : 'Start Adventure!'}
        </button>
      </div>
      
      {error && <div className="error-message">{error}</div>}
      {!areCharactersComplete() && (
        <div className="info-message">All characters must have a name, race, and class.</div>
      )}
    </div>
  );
  
  // Render Main Game Screen
  const renderGameScreen = () => (
    <div className="game-screen">
      <div className="game-layout">
        <div className="story-container" ref={storyRef}>
          {gameState.storyProgress.map((segment, index) => (
            <div key={index} className="story-segment">
              {segment.image && (
                <div className="story-image">
                  <img src={`data:image/png;base64,${segment.image}`} alt="Scene" />
                </div>
              )}
              
              <div className="story-text">
                <p>{segment.text}</p>
                
                {segment.player && segment.action && (
                  <div className="player-action">
                    <div className="player-icon">
                      {gameState.characters.find(c => c.name === segment.player)?.icon ? (
                        <img 
                          src={`data:image/png;base64,${gameState.characters.find(c => c.name === segment.player)?.icon}`} 
                          alt={segment.player} 
                        />
                      ) : (
                        <div className="icon-placeholder">{segment.player[0]}</div>
                      )}
                    </div>
                    <p><strong>{segment.player}</strong> chose to {segment.action}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
          {/* End of story segments mapping */}
        </div>
        
        <div className="action-panel">
          <div className="current-player">
            {gameState.characters[gameState.currentPlayerIndex] && (
              <>
                <h3>Current Player: 
                  <span className="player-name">{gameState.characters[gameState.currentPlayerIndex].name}</span>
                </h3>
                <div className="player-info">
                  {gameState.characters[gameState.currentPlayerIndex].icon ? (
                    <img 
                      src={`data:image/png;base64,${gameState.characters[gameState.currentPlayerIndex].icon}`} 
                      alt={gameState.characters[gameState.currentPlayerIndex].name} 
                      className="active-player-icon"
                    />
                  ) : (
                    <div className="icon-placeholder active">
                      {gameState.characters[gameState.currentPlayerIndex].name[0]}
                    </div>
                  )}
                  <div className="player-details">
                    <p>{gameState.characters[gameState.currentPlayerIndex].race} {gameState.characters[gameState.currentPlayerIndex].characterClass}</p>
                  </div>
                </div>
              </>
            )}
          </div>
          
          <div className="action-choices">
            <h3>Choose Your Action:</h3>
            
            {gameState.storyProgress.length > 0 && 
             gameState.storyProgress[gameState.storyProgress.length - 1].choices && 
             gameState.storyProgress[gameState.storyProgress.length - 1].choices.map(choice => (
              <button 
                key={choice.id} 
                className={`action-button ${currentAction === choice.id ? 'selected' : ''}`}
                onClick={() => handleActionChoice(choice.id)}
                disabled={loading}
              >
                {choice.text}
              </button>
            ))}
            
            {loading && <div className="loading-message">Generating story...</div>}
          </div>
        </div>
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
  
  return (
    <div className="dnd-app">
      {screen === 'setup' && renderSetupScreen()}
      {screen === 'character' && renderCharacterScreen()}
      {screen === 'game' && renderGameScreen()}
      
      {/* Background music player (hidden) */}
      {gameState.musicUrl && gameState.settings.enableMusic && (
        <audio 
          src={gameState.musicUrl} 
          autoPlay 
          loop 
          style={{ display: 'none' }} 
        />
      )}
    </div>
  );
}

export default App;