import React, { useState } from 'react';

const SetupScreen = ({ 
  gameState, 
  setGameState, 
  availableModels = ['llama3'], // Provide fallback default
  handleStartSetup, 
  loading, 
  error, 
  setScreen 
}) => {
  // Add state to track if custom chapter length is selected
  const [customChapterLength, setCustomChapterLength] = useState(false);
  const [customLengthValue, setCustomLengthValue] = useState(3); // Default value
  
  // Helper to safely handle settings changes
  const handleSettingsChange = (setting, value) => {
    setGameState(prev => ({
      ...prev,
      settings: { ...(prev.settings || {}), [setting]: value }
    }));
  };

  // Special handler for chapter length changes
  const handleChapterLengthChange = (e) => {
    const value = e.target.value;
    
    // Check if "custom" option is selected
    if (value === 'custom') {
      setCustomChapterLength(true);
      // Keep the current value or default to 3
      const currentValue = gameState.settings?.scenesPerChapter || 3;
      setCustomLengthValue(currentValue);
    } else {
      setCustomChapterLength(false);
      // Convert value to integer and update game state
      handleSettingsChange('scenesPerChapter', parseInt(value));
    }
  };
  
  // Handle custom length input changes with validation
  const handleCustomLengthChange = (e) => {
    let value = parseInt(e.target.value);
    
    // Ensure value is within reasonable limits (1-20)
    if (isNaN(value)) value = 3;
    if (value < 1) value = 1;
    if (value > 20) value = 20;
    
    setCustomLengthValue(value);
    handleSettingsChange('scenesPerChapter', value);
  };

  return (
    <div className="setup-screen">
      <h1>Dungeons & Dragons AI Game</h1>
      
      <div className="setup-form">
        <h2>Game Setup</h2>
        
        <div className="setup-section">
          <h3>Basic Settings</h3>
          
          <div className="form-group">
            <label>Number of Players:</label>
            <select 
              value={gameState.settings?.playerCount || 2} 
              onChange={(e) => handleSettingsChange('playerCount', parseInt(e.target.value))}
            >
              <option value="1">1 Player</option>
              <option value="2">2 Players</option>
              <option value="3">3 Players</option>
              <option value="4">4 Players</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Scenes per Chapter:</label>
            <select 
              value={customChapterLength ? 'custom' : (gameState.settings?.scenesPerChapter || 3)} 
              onChange={handleChapterLengthChange}
            >
              <option value="1">1 Round (Very Short)</option>
              <option value="2">2 Rounds (Short)</option>
              <option value="3">3 Rounds (Medium)</option>
              <option value="4">4 Rounds (Long)</option>
              <option value="5">5 Rounds (Very Long)</option>
              <option value="custom">Custom...</option>
            </select>
            
            {customChapterLength && (
              <div className="custom-length-input">
                <label htmlFor="customRounds">Custom rounds per chapter:</label>
                <input
                  id="customRounds"
                  type="number"
                  min="1"
                  max="20"
                  value={customLengthValue}
                  onChange={handleCustomLengthChange}
                  className="custom-number-input"
                />
              </div>
            )}
            
            <div className="setting-description">
              Controls how many player actions occur in each chapter
            </div>
          </div>
          
          <div className="form-group">
            <label>Chapters per Arc:</label>
            <select 
              value={gameState.settings?.chaptersPerArc || 3} 
              onChange={(e) => handleSettingsChange('chaptersPerArc', parseInt(e.target.value))}
            >
              <option value="1">1 Chapter (Very Short)</option>
              <option value="3">3 Chapters (Short)</option>
              <option value="5">5 Chapters (Medium)</option>
              <option value="7">7 Chapters (Long)</option>
              <option value="10">10 Chapters (Epic)</option>
            </select>
            <div className="setting-description">
              Controls how many chapters make up a complete story arc
            </div>
          </div>
          
          <div className="form-group">
            <label>AI Model:</label>
            <select 
              value={gameState.settings?.aiModel || 'llama3'} 
              onChange={(e) => handleSettingsChange('aiModel', e.target.value)}
            >
              {availableModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="setup-section">
          <h3>Features</h3>
          
          <div className="features-group">
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableImages" 
                checked={gameState.settings?.enableImages || false} 
                onChange={(e) => handleSettingsChange('enableImages', e.target.checked)}
              />
              <label htmlFor="enableImages">Generate Images</label>
            </div>
            
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableAITTS" 
                checked={gameState.settings?.enableAITTS !== false} 
                onChange={(e) => handleSettingsChange('enableAITTS', e.target.checked)}
              />
              <label htmlFor="enableAITTS">AI-powered Text-to-Speech Narration</label>
              <div className="feature-description">
                (When disabled, browser's native speech synthesis will be used)
              </div>
            </div>
            
            <div className="feature-toggle">
              <input 
                type="checkbox" 
                id="enableMusic" 
                checked={gameState.settings?.enableMusic || false} 
                onChange={(e) => handleSettingsChange('enableMusic', e.target.checked)}
              />
              <label htmlFor="enableMusic">Background Music</label>
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
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default SetupScreen;
