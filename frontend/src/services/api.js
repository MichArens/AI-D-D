const API_BASE_URL = 'http://localhost:8000/api';

export const api = {
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
