import React from 'react';

const SetupScreen = ({ gameState, setGameState, availableModels, handleStartSetup, loading, error, setScreen }) => {
  const handleSettingsChange = (setting, value) => {
    setGameState(prev => ({
      ...prev,
      settings: { ...prev.settings, [setting]: value }
    }));
  };

  return (
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
};

export default SetupScreen;
