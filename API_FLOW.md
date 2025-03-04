# D&D AI Adventure - API Communication Flow

This document explains how the frontend React application communicates with the backend FastAPI server during a typical game progression.

## API Endpoint Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/models` | GET | Retrieve available AI models |
| `/api/generate-character-options` | POST | Get available races and classes |
| `/api/generate-character-icon` | POST | Generate character portraits |
| `/api/start-game` | POST | Initialize game with first story segment |
| `/api/take-action` | POST | Process player actions and continue story |
| `/api/start-new-chapter` | POST | Begin a new chapter after completing one |
| `/api/check-music` | GET | Check status of background music generation |
| `/api/generate-tts` | POST | Generate text-to-speech narration |

## Game Flow Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    
    %% Game Setup
    User->>Frontend: Open game
    Frontend->>Backend: GET /api/models
    Backend-->>Frontend: Available AI models
    User->>Frontend: Configure game settings
    User->>Frontend: Select number of players
    User->>Frontend: Toggle features (images, TTS, music)
    User->>Frontend: Proceed to character creation
    
    %% Character Creation
    Frontend->>Backend: POST /api/generate-character-options
    Backend-->>Frontend: Available races and classes
    User->>Frontend: Enter character details for each player
    User->>Frontend: Click "Start Adventure"
    
    alt Images Enabled
        Frontend->>Backend: POST /api/generate-character-icon (for each character)
        Backend-->>Frontend: Character portrait images
    end
    
    %% Game Start
    Frontend->>Backend: POST /api/start-game
    Backend-->>Frontend: Initial story, actions, chapter details
    
    alt Music Enabled
        Backend-->>Backend: Generate background music (async)
        Frontend->>Backend: GET /api/check-music
        Backend-->>Frontend: Music URL (when ready)
    end
    
    %% Game Loop
    loop Game Progression
        %% Player Actions
        Frontend->>User: Display story and action choices
        
        alt TTS Enabled
            User->>Frontend: Click TTS button
            Frontend->>Backend: POST /api/generate-tts (if not pre-generated)
            Backend-->>Frontend: Audio data
            Frontend->>User: Play audio narration
        end
        
        User->>Frontend: Select an action
        Frontend->>Backend: POST /api/take-action
        Backend-->>Frontend: Next story segment, next player, choices
        
        %% Chapter Transitions
        alt Chapter Ends
            Backend-->>Frontend: Chapter ending + next chapter info
            Frontend->>User: Display chapter complete message
            User->>Frontend: Click "Begin Next Chapter"
            Frontend->>Backend: POST /api/start-new-chapter
            Backend-->>Frontend: New chapter beginning and actions
        end
    end
```

## Detailed API Flow

### 1. Game Setup

- The frontend first retrieves available AI models (`GET /api/models`)
- The user configures game settings, including player count, AI model, and whether to enable features like images, TTS, and music
- After setup, the app transitions to character creation

### 2. Character Creation

- The frontend requests available races and classes (`POST /api/generate-character-options`)
- The user enters details for each character (name, race, class, gender)
- When "Start Adventure" is clicked, if image generation is enabled, the app requests character portraits (`POST /api/generate-character-icon`)

### 3. Game Start

- The frontend sends the game state to initialize the adventure (`POST /api/start-game`)
- The backend generates the initial story segment, action choices, and chapter info
- If music is enabled, the backend begins asynchronous music generation, and the frontend periodically checks for it (`GET /api/check-music`)

### 4. Game Loop

- For each turn:
  - The frontend displays the current story and action choices
  - If TTS is enabled, the user can click to hear narration
  - When the user selects an action, the frontend sends it to the backend (`POST /api/take-action`)
  - The backend generates the next story segment and returns it to the frontend
  - The process repeats for each player in rotation

### 5. Chapter Transitions

- After a certain number of rounds (typically 3), a chapter ends
- The backend includes chapter ending information and next chapter details in the response
- The frontend displays a "Chapter Complete" message and a button to start the next chapter
- When clicked, the frontend requests the new chapter (`POST /api/start-new-chapter`)
- The backend generates the beginning of the next chapter and returns it

## Data Flow for TTS

1. If AI TTS is enabled in settings (`enableAITTS`):
   - The backend pre-generates TTS for new story segments and includes it in the response as `audioData`
   - The frontend plays this audio when requested
   - For older segments without pre-generated audio, the frontend can request it on-demand (`POST /api/generate-tts`)

2. If AI TTS is disabled:
   - The frontend falls back to using the browser's built-in `speechSynthesis` API

This sequence ensures a seamless game experience where the AI-generated content (text, images, audio) is delivered to the player at the appropriate moments throughout their adventure.
