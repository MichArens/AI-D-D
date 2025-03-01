const API_BASE_URL = 'http://localhost:8000/api';

export const api = {
  // Get available character options
  async getCharacterOptions() {
    const response = await fetch(`${API_BASE_URL}/generate-character-options`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get character options');
    }
    
    return response.json();
  },
  
  // Generate character icon
  async generateCharacterIcon(character) {
    const response = await fetch(`${API_BASE_URL}/generate-character-icon`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate character icon');
    }
    
    return response.json();
  },
  
  // Start a new game
  async startGame(gameState) {
    const response = await fetch(`${API_BASE_URL}/start-game`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gameState)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start game');
    }
    
    const data = await response.json();
    
    // Initialize chapters if missing from response
    if (data.chapter) {
      gameState.chapters = [data.chapter];
      gameState.currentChapterIndex = 0;
      gameState.roundsInCurrentChapter = 0;
    }
    
    return data;
  },
  
  // Take a player action
  async takeAction(gameState, choiceId) {
    const response = await fetch(`${API_BASE_URL}/take-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gameState, choiceId })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to process action');
    }
    
    return response.json();
  },
  
  // Get available models
  async getModels() {
    const response = await fetch(`${API_BASE_URL}/models`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get models');
    }
    
    return response.json();
  }
};
