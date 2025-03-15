import { IGameState, IPlayerCharacter, IStoryChapter, IStoryScene } from "../types/game-types";

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Improve error handling in API calls
const callApi = async (endpoint: string, method: string = 'GET', body: any = null) => {
  try {
    console.log(`[API] Calling ${method} ${API_BASE_URL}/${endpoint}`, body);
    
    const headers = { 'Content-Type': 'application/json' };
    const config = {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    };
    
    const response = await fetch(`${API_BASE_URL}/${endpoint}`, config);
    
    // Log response status
    console.log(`[API] Response from ${endpoint}: status ${response.status}`);
    
    // Handle non-OK responses
    if (!response.ok) {
      let errorDetail = `HTTP error: ${response.status}`;
      let errorData: any = {};
      
      try {
        errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch (e) {
        // Unable to parse error as JSON
      }
      
      // Create better error message
      const error: any = new Error(`API Error: ${errorDetail}`);
      error.status = response.status;
      error.responseData = errorData;
      throw error;
    }
    
    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      console.warn(`[API] Non-JSON response from ${endpoint}`);
      return {};
    }
    
    const data = await response.json();
    console.log(`[API] Data received from ${endpoint}:`, data);
    return data;
  } catch (error) {
    console.error(`[API] Error in ${endpoint}:`, error);
    throw error;
  }
};

export const api = {
  async getCharacterOptions(): Promise<{races: string[], classes: string[]}> {
    try {
      console.log('[API] Getting character options');
      // Handle potential empty response
      const data = await callApi('generate-character-options', 'POST');
      if (!data || (!data.races && !data.classes)) {
        console.warn('[API] Received empty character options, using defaults');
        return {
          races: ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
          classes: ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
        };
      }
      return data;
    } catch (error) {
      console.error('[API] Failed to get character options:', error);
      // Return default options on error
      return {
        races: ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
        classes: ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
      };
    }
  },
  
  async generateCharacterIcon(character: IPlayerCharacter): Promise<{icon: string}> {
    return callApi('generate-character-icon', 'POST', { character });
  },

  async takeAction(gameState: IGameState, customAction?: string): Promise<{scene: IStoryScene, nextChapterTitle?: string, chapterSummary?: string, chapterSummaryImage?: string}> {
    return callApi('take-action', 'POST', { gameState, customAction });
  },
  
  async getModels(): Promise<{models: string[]}> {
    return callApi('models');
  },
  
  async startNewChapter(gameState: IGameState, newChapterTitle?: string): Promise<{newChapter: IStoryChapter}> {
    try {
      // Clean up gameState to make it more compatible with backend
      const cleanGameState = JSON.parse(JSON.stringify(gameState));
      
      // Make sure data matches the expected format for Pydantic model
      const requestData = {
        gameState: cleanGameState,
        newChapterTitle: newChapterTitle 
      };
      
      return await callApi('start-new-chapter', 'POST', requestData);
    } catch (error) {
      console.error('[API] Failed to start new chapter:', error);
      throw error;
    }
  },
  
  async checkMusic() {
    return callApi('check-music', 'GET');
  },
  
  async generateTTS(text: string, voice = 'bm_george'): Promise<string> {
    return callApi('generate-tts', 'POST', { text, voice });
  }
};
