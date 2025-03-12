import React, { use, useEffect, useState } from 'react';
import { GameScreens } from '../types/game-screens';
import { api } from '../utils/api-service';
import { IGameSettings, IGameState } from '../types/game-types';

interface SetupScreenProps {
  gameState: IGameState;
  updateSettings: (newSettings: IGameSettings) => void;
  setScreen: React.Dispatch<React.SetStateAction<GameScreens>>;
}

const SetupScreen: React.FC<SetupScreenProps> = ({
  gameState,
  updateSettings,
  setScreen,
}) => {
    const [customChapterLength, setCustomChapterLength] = useState(false);
    const [customLengthValue, setCustomLengthValue] = useState(3);
    const [availableModels, setAvailableModels] = useState(['llama3']);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    useEffect(() => {
        async function loadModels() {
            try {
              const { models } = await api.getModels();
              setAvailableModels(models);
              updateSettings({ ...gameState.settings, aiModel: models[0] });
            } catch (err) {
              console.error('Failed to load models:', err);
            }
          }
          
          loadModels();
    }, []);

    const handleSettingChange = (settingName: string, value: any) => {
        updateSettings({ ...gameState.settings, [settingName]: value });
    };

    const handleChapterLengthChange = (e: any) => {
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
        handleSettingChange('scenesPerChapter', parseInt(value));
        }
    };

    const handleCustomLengthChange = (e: any) => {
        let value = parseInt(e.target.value);
        
        // Ensure value is within reasonable limits (1-20)
        if (isNaN(value)) value = 3;
        if (value < 1) value = 1;
        if (value > 20) value = 20;
        
        setCustomLengthValue(value);
        handleSettingChange('scenesPerChapter', value);
    };

    const handleSubmit = (e: React.FormEvent) => {
        setLoading(true);
        e.preventDefault();
        setScreen('character');
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
                onChange={(e) => handleSettingChange('playerCount', parseInt(e.target.value))}
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
                onChange={(e) => handleSettingChange('chaptersPerArc', parseInt(e.target.value))}
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
                onChange={(e) => handleSettingChange('aiModel', e.target.value)}
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
                    onChange={(e) => handleSettingChange('enableImages', e.target.checked)}
                />
                <label htmlFor="enableImages">Generate Images</label>
                </div>
                
                <div className="feature-toggle">
                <input 
                    type="checkbox" 
                    id="enableAITTS" 
                    checked={gameState.settings?.enableAITTS !== false} 
                    onChange={(e) => handleSettingChange('enableAITTS', e.target.checked)}
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
                    onChange={(e) => handleSettingChange('enableMusic', e.target.checked)}
                />
                <label htmlFor="enableMusic">Background Music</label>
                </div>
            </div>
            </div>
            
            <div className="actions">
            <button 
                className="main-button" 
                onClick={handleSubmit}
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
