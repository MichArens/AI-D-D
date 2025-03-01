import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import SetupScreen from './components/SetupScreen';
import CharacterScreen from './components/CharacterScreen';
import GameScreen from './components/GameScreen';
import { api } from './services/api';
import { toggleTTS } from './utils/tts';
import { prepareChapterContent, addSegmentToChapter, deepCloneWithNewRefs } from './utils/chapter-manager';

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
  const [activeTTS, setActiveTTS] = useState(null); // Track which story segment is being spoken
  const storyRef = useRef(null);
  const [viewingChapterIndex, setViewingChapterIndex] = useState(0);
  
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
  
  // Clean up speech synthesis when component unmounts
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);
  
  // Handle setup screen settings
  const handleSettingsChange = (setting, value) => {
    setGameState(prev => ({
      ...prev,
      settings: { ...prev.settings, [setting]: value }
    }));
  };
  
  // Text-to-speech toggle function
  // Replace your existing toggleTTS function with this:
  const handleToggleTTS = (index) => {
    toggleTTS(index, activeTTS, setActiveTTS);
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
      char.name && char.race && char.characterClass && char.gender
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
        
        // Initialize chapter if it exists in response
        const chapters = gameResponse.chapter ? [gameResponse.chapter] : [];
        
        return {
          ...prev,
          storyProgress: newStoryProgress,
          musicUrl: gameResponse.musicUrl,
          chapters: chapters,
          currentChapterIndex: 0,
          roundsInCurrentChapter: 0,
          viewingChapterIndex: 0 // Initialize viewing to the first chapter
        };
      });
      
      // Initialize viewing chapter index
      setViewingChapterIndex(0);
      
      setScreen('game');
    } catch (err) {
      setError('Failed to start game. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle player action choice - completely rewritten
  const handleActionChoice = async (choiceId) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    setCurrentAction(choiceId);
    
    try {
      const response = await api.takeAction(gameState, choiceId);
      
      setGameState(prev => {
        // Create a new story segment with unique ID
        const newStory = {
          ...response.storyUpdate,
          choices: response.choices,
          _id: `segment-${Date.now()}-${Math.random()}`,
          timestamp: Date.now(),
          player: prev.characters[prev.currentPlayerIndex]?.name,
          action: prev.storyProgress[prev.storyProgress.length - 1]?.choices?.find(c => c.id === choiceId)?.text
        };
        
        let updatedChapters = deepCloneWithNewRefs(prev.chapters || []);
        let nextChapterIndex = prev.currentChapterIndex;
        let storyToShow = [];
        
        // Handle chapter transitions
        if (response.chapterEnded && response.nextChapter) {
          // Complete the current chapter
          if (updatedChapters[prev.currentChapterIndex]) {
            updatedChapters[prev.currentChapterIndex] = {
              ...updatedChapters[prev.currentChapterIndex],
              summary: response.chapterSummary || "",
              image: response.chapterImage
            };
          }
          
          // Create new chapter
          const newChapter = {
            id: updatedChapters.length,
            title: response.nextChapter.title,
            summary: "",
            segments: [0],  // Start with index 0 in this chapter
            storedSegments: { 0: newStory }  // Store segment directly in chapter
          };
          
          updatedChapters.push(newChapter);
          nextChapterIndex = updatedChapters.length - 1;
          
          // Show only the first segment of new chapter
          storyToShow = [deepCloneWithNewRefs(newStory)];
          
          // Update viewing chapter to new chapter
          setViewingChapterIndex(nextChapterIndex);
          
        } else {
          // Add segment to current chapter
          const result = addSegmentToChapter(updatedChapters, newStory, prev.currentChapterIndex);
          updatedChapters = result.chapters;
          
          // Add new segment to current display
          storyToShow = [...prev.storyProgress, deepCloneWithNewRefs(newStory)];
        }
        
        return {
          ...prev,
          storyProgress: storyToShow,
          currentPlayerIndex: response.nextPlayerIndex,
          chapters: updatedChapters,
          currentChapterIndex: nextChapterIndex,
          roundsInCurrentChapter: response.chapterEnded ? 0 : (response.roundsInChapter || 0)
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
  
  // Function to switch to a specific chapter view - completely rewritten
  const handleViewChapter = (chapterIndex) => {
    // Don't allow chapter changes while loading
    if (loading) return;
    
    setViewingChapterIndex(chapterIndex);
    
    setGameState(prev => {
      if (!prev.chapters || chapterIndex < 0 || chapterIndex >= prev.chapters.length) {
        return prev;
      }
      
      const targetChapter = prev.chapters[chapterIndex];
      
      // Completely rebuild the story progress for viewing this chapter
      let newStoryProgress;
      
      if (chapterIndex < prev.currentChapterIndex) {
        // Past chapter - show summary
        newStoryProgress = [{
          text: targetChapter.summary || "No summary available for this chapter.",
          image: targetChapter.image,
          chapterId: chapterIndex,
          isChapterSummary: true,
          _id: `summary-${chapterIndex}-${Date.now()}`
        }];
      } else {
        // Current chapter - rebuild from stored segments
        newStoryProgress = (targetChapter.segments || []).map(segIdx => {
          if (targetChapter.storedSegments && targetChapter.storedSegments[segIdx]) {
            return deepCloneWithNewRefs(targetChapter.storedSegments[segIdx]);
          }
          return null;
        }).filter(Boolean);
      }
      
      return {
        ...prev,
        // Replace storyProgress with completely fresh objects
        storyProgress: newStoryProgress
      };
    });
  };
  
  return (
    <div className={`dnd-app ${screen === 'game' ? 'dnd-app-fullscreen' : ''}`}>
      {screen === 'setup' && <SetupScreen 
        gameState={gameState} 
        setGameState={setGameState} 
        availableModels={availableModels} 
        handleStartSetup={handleStartSetup} 
        loading={loading} 
        error={error} 
        setScreen={setScreen} 
      />}
      {screen === 'character' && <CharacterScreen 
        gameState={gameState} 
        setGameState={setGameState} 
        characterOptions={characterOptions} 
        handleCharacterChange={handleCharacterChange} 
        handleStartGame={handleStartGame} 
        loading={loading} 
        error={error} 
        areCharactersComplete={areCharactersComplete} 
        setScreen={setScreen} 
      />}
      {screen === 'game' && <GameScreen 
        gameState={gameState} 
        setGameState={setGameState} 
        handleActionChoice={handleActionChoice} 
        handleViewChapter={handleViewChapter}
        viewingChapterIndex={viewingChapterIndex}
        loading={loading} 
        error={error} 
        currentAction={currentAction} 
        activeTTS={activeTTS} 
        toggleTTS={handleToggleTTS} 
        storyRef={storyRef} 
      />}
      
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