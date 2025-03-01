import React from 'react';

const SetupScreen = ({ 
  gameState, 
  setGameState, 
  availableModels = ['llama3'], // Provide fallback default
  handleStartSetup, 
  loading, 
  error, 
  setScreen 
}) => {
  // Helper to safely handle settings changes
  const handleSettingsChange = (setting, value) => {
    setGameState(prev => ({
      ...prev,
      settings: { ...(prev.settings || {}), [setting]: value }
    }));
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
                id="enableTTS" 
                checked={gameState.settings?.enableTTS !== false} 
                onChange={(e) => handleSettingsChange('enableTTS', e.target.checked)}
              />
              <label htmlFor="enableTTS">Text-to-Speech Narration</label>
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
