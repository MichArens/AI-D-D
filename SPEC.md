**I want to create a full-stack AI-generated Dungeons & Dragons-style game with the following features:**
**Gameplay Flow:**
**1. The game starts by generating an initial story setting and presenting the current player with three action choices.**
**2. Once a player chooses an action, the AI generates the next part of the story based on their choice (+image if enabled ) and rotates to the next player, who gets three new action choices.**
**3. The game continues this way, allowing all players to see past choices and story progression.**
**Game Screens:**
**1. Game Setup Screen:**
**• Choose number of players**
**• Configure optional settings (detailed below)**
**2. Character Creation Screen:**
**• Players select a race (Elf, Human, Orc, etc.)**
**• Players select a class (Mage, Warrior, Rogue, etc.)**
**• Available races and classes will change each game**
**• Players choose a name**
**3. Main Game Screen:**
**• Displays a story progression box showing the full narrative (and AI image related to the story if enabled).**
**• Shows the current active player with their AI-generated icon.**
**• Displays three action choices for the current player.**
**• When a player chooses an action, their icon and choice appear in the story box.**
**Additional Features:**
**• After character creation (Screen 2), the game will only transition to Screen 3 after:**
**• The first story progression is generated**
**• Player icons (if enabled) are created**
**• Background music (if enabled) starts playing**
**• In Screen 3, the follow-up story text should appear immediately after an action is chosen, while the AI-generated scene image loads separately.**
**Game Setup Options (Screen 1):**
**• Enable image generation (default: off)**
**• Enable text-to-speech narration (front side tts) (default: on)**
**• Enable background music generation (default: off)**
**• Choose AI model options (retrieved from Ollama)**
**Tech Stack:**
**• Frontend: React**
**• Backend: FastAPI (Python)**
**• Text Generation: Local Ollama server**
**• Image Generation: Local Stable Diffusion server**
**• Background Music: Suno AI API calls**
**Code Requirements:**
**• Generate all necessary game files (full backend & frontend)**
**• Backend: One FastAPI file handling AI requests (text, images, music)**
**• Frontend: One React file with complete UI and styling**
**• Provide setup & installation guides (package.json, requirements.txt)**
**UI Theme:**
**• Dungeons & Dragons style**
**• Vintage red & black theme**