import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import SetupScreen from './components/SetupScreen';
import CharacterScreen from './components/CharacterScreen';
import GameScreen from './components/GameScreen';
import { api } from './services/api';
// Conditionally import chapter manager to avoid errors if file doesn't exist
const chapterManager = (() => {
  try {
    return require('./utils/chapter-manager');
  } catch (e) {
    console.warn("Chapter manager not found, using fallbacks");
    return {
      deepCloneWithNewRefs: obj => JSON.parse(JSON.stringify(obj)),
      addSegmentToChapter: (chapters, segment, idx) => ({ chapters, allSegments: [] })
    };
  }
})();

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
      enableAITTS: false,
      enableMusic: false,
      aiModel: 'llama3',
      scenesPerChapter: 3,
      chaptersPerArc: 3
    },
    arcs: [
      {
        chapters: []
      }
    ],
    characters: [],
    musicUrl: null
  });
  const [activeTTS, setActiveTTS] = useState(null); // Track which story segment is being spoken
  const audioRef = useRef(null); // Reference to the audio element
  const storyRef = useRef(null);
  const [viewingChapterIndex, setViewingChapterIndex] = useState(0);
  const [nextChapter, setNextChapter] = useState(null);
  
  // Add error timeout ref to clear error messages
  const errorTimeoutRef = useRef(null);
  
  // Clear error messages after a timeout
  const clearErrorAfterDelay = (message = null) => {
    // Clear any existing timeout
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
    }
    
    if (message) {
      setError(message);
      // Set a new timeout to clear the error
      errorTimeoutRef.current = setTimeout(() => {
        setError(null);
      }, 3000); // Clear after 3 seconds
    } else {
      setError(null);
    }
  };
  
  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current);
      }
    };
  }, []);
  
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
  
  // Text-to-speech toggle function - updated to use pre-generated TTS
  const handleToggleTTS = async (index) => {
    // If already playing this segment, stop it
    if (activeTTS === index) {
      console.log("Stopping TTS for index:", index);
      
      // Don't show errors when manually stopping
      const wasManuallyStopped = true;
      
      if (gameState.settings.enableAITTS && audioRef.current) {
        try {
          // More forceful stopping of AI TTS
          audioRef.current.onended = null; // Remove event listeners first
          audioRef.current.onerror = null;
          audioRef.current.oncanplaythrough = null;
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          
          // Use empty blob instead of empty string for better browser compatibility
          try {
            const emptyBlob = new Blob([""], { type: "audio/wav" });
            audioRef.current.src = URL.createObjectURL(emptyBlob);
          } catch (e) {
            audioRef.current.src = "";
          }
        } catch (e) {
          console.log("Normal cleanup during TTS stop:", e);
          // Don't set error for normal cleanup
        }
      }
      
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      
      // Clear any error message that might be showing
      if (wasManuallyStopped) {
        clearErrorAfterDelay(null);
      }
      
      setActiveTTS(null);
      return;
    }
    
    // If playing a different segment, stop that first
    if (activeTTS !== null) {
      if (gameState.settings.enableAITTS && audioRef.current) {
        // Clean up current audio properly
        try {
          audioRef.current.onended = null;
          audioRef.current.onerror = null;
          audioRef.current.oncanplaythrough = null;
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
          
          // Use empty blob instead of empty string
          const emptyBlob = new Blob([""], { type: "audio/wav" });
          audioRef.current.src = URL.createObjectURL(emptyBlob);
        } catch (e) {
          console.log("Normal cleanup during TTS switch:", e);
        }
      }
      
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      
      setActiveTTS(null);
    }
    
    // Get text content to speak
    let textToSpeak = "";
    let preGeneratedAudio = null;
    
    if (index === 'summary' && gameState.storyProgress.length > 0) {
      textToSpeak = gameState.storyProgress[0].text;
      preGeneratedAudio = gameState.storyProgress[0].audioData;
    } else if (gameState.storyProgress && gameState.storyProgress[index]) {
      textToSpeak = gameState.storyProgress[index].text;
      preGeneratedAudio = gameState.storyProgress[index].audioData;
    } else {
      return; // No text to speak
    }
    
    // Use AI TTS if enabled
    if (gameState.settings.enableAITTS) {
      try {
        let audioData = preGeneratedAudio;
        
        // If no pre-generated audio, fetch it on-demand
        if (!audioData) {
          console.log("No pre-generated audio, fetching on demand");
          setLoading(true);
          try {
            const response = await api.generateTTS(textToSpeak);
            
            if (!response || !response.audioData) {
              throw new Error("No audio data received from server");
            }
            
            audioData = response.audioData;
          } finally {
            setLoading(false);
          }
        } else {
          console.log("Using pre-generated audio");
        }
        
        // Play audio once it's loaded
        if (audioRef.current && audioData) {
          // Clear any previous audio and listeners
          audioRef.current.oncanplaythrough = null;
          audioRef.current.onended = null;
          audioRef.current.onerror = null;
          
          // Set up new audio
          audioRef.current.src = `data:audio/wav;base64,${audioData}`;
          
          // Set up event handlers
          audioRef.current.oncanplaythrough = () => {
            console.log("Audio ready to play");
            audioRef.current.play().catch(e => {
              console.error("Failed to play audio:", e);
              setActiveTTS(null);
              clearErrorAfterDelay("Failed to play audio. Check your browser settings.");
            });
          };
          
          audioRef.current.onended = () => {
            console.log("Audio playback completed");
            setActiveTTS(null);
          };
          
          audioRef.current.onerror = (e) => {
            // Only show errors if we didn't manually stop
            if (activeTTS === index) {
              console.error("Audio error:", e);
              setActiveTTS(null);
              clearErrorAfterDelay("Audio playback error. Try again.");
            }
          };
        }
        
        // Mark this segment as active for TTS
        setActiveTTS(index);
      } catch (err) {
        console.error("TTS generation failed:", err);
        clearErrorAfterDelay("Failed to generate AI narration. Using browser TTS instead.");
        
        // Fallback to browser TTS
        if (window.speechSynthesis) {
          const utterance = new SpeechSynthesisUtterance(textToSpeak);
          utterance.rate = 0.9;
          utterance.onend = () => setActiveTTS(null);
          window.speechSynthesis.speak(utterance);
          setActiveTTS(index);
        }
      }
    } else {
      // Use browser's built-in TTS
      if (window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.rate = 0.9;
        utterance.onend = () => setActiveTTS(null);
        window.speechSynthesis.speak(utterance);
        setActiveTTS(index);
      }
    }
  };

  // Navigate to character creation - improved error handling 
  const handleStartSetup = async () => {
    setLoading(true);
    setError(null);
    console.log("Starting setup and fetching character options...");
    
    try {
      let options;
      try {
        options = await api.getCharacterOptions();
        console.log("Received character options:", options);
      } catch (optionsError) {
        console.error("Error fetching character options:", optionsError);
        options = {
          races: ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
          classes: ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
        };
        setError('Using default character options due to API error.');
      }
      
      setCharacterOptions(options);
      
      // Initialize character slots based on player count
      const initialCharacters = Array(gameState.settings?.playerCount || 2).fill(null).map((_, idx) => ({
        name: '',
        race: null,
        characterClass: null,
        gender: null,
        playerIndex: idx,
        icon: null
      }));
      
      setGameState(prev => ({
        ...prev,
        characters: initialCharacters
      }));
      
      setScreen('character');
    } catch (err) {
      console.error('Failed to initialize character creation:', err);
      setError(`Failed to initialize character creation: ${err.message || 'Unknown error'}`);
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
  
  // Start the game - update to use startNewChapter
  const handleStartGame = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Generate icons for all characters if images are enabled
      const updatedCharacters = [...gameState.characters];
      if (gameState.settings.enableImages) {
        for (let i = 0; i < updatedCharacters.length; i++) {
          const character = updatedCharacters[i];
          const { icon } = await api.generateCharacterIcon(character);
          updatedCharacters[i] = { ...character, icon };
        }
      }
      
      const initialGameState = {
        settings: gameState.settings,
        characters: updatedCharacters,
        currentPlayerIndex: 0,
        arcs: [{ chapters: [] }]
      };
      
      // Start the game with the first chapter
      const response = await api.startNewChapter(initialGameState);
      
      if (!response || !response.newChapter) {
        throw new Error("Invalid response from server when starting game");
      }
      
      const newChapter = response.newChapter;
      initialGameState.arcs[0].chapters.push(newChapter);
      setGameState(initialGameState);
      
      setViewingChapterIndex(0);
      setScreen('game');
    } catch (err) {
      console.error("Start game error:", err);
      setError('Failed to start game. Please try again. ' + err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle player action choice - updated to match new endpoint structure
  const handleActionChoice = async (choiceId, customAction = null) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Get the current player's chosen action
      const currentChoices = gameState.storyProgress[gameState.storyProgress.length - 1]?.choices || [];
      const chosenAction = customAction || 
        (currentChoices.find(c => c.id === choiceId)?.text || 
         currentChoices.find(c => c === choiceId) || choiceId);
      
      // Update the game state with the chosen action before sending to API
      const updatedGameState = {
        ...gameState,
        arcs: gameState.arcs || [{ chapters: gameState.chapters || [] }],
      };
      
      const response = await api.takeAction(updatedGameState, customAction);
      
      if (!response || !response.scene) {
        throw new Error("Invalid response from action endpoint");
      }
      
      const { scene, next_chapter_title, chapterSummary, chapterSummaryImage } = response;
      
      setGameState(prev => {
        // Create a new story segment with unique ID
        const newStory = {
          text: scene.text,
          image: scene.image,
          choices: scene.choices,
          audioData: scene.audioData,
          player: prev.characters[prev.currentPlayerIndex]?.name,
          action: chosenAction,
          _id: `segment-${Date.now()}-${Math.random()}`,
          timestamp: Date.now()
        };
        
        // Clone current state to avoid mutation
        const updatedGameState = { ...prev };
        const updatedChapters = [...(prev.chapters || [])];
        const currentChapter = { ...(updatedChapters[prev.currentChapterIndex] || {}) };
        
        // Make sure scenes array exists
        if (!currentChapter.scenes) {
          currentChapter.scenes = [];
        }
        
        // Add the current scene to the chapter
        currentChapter.scenes.push({
          ...scene,
          chosenAction: chosenAction
        });
        
        // Update the chapter in chapters array
        updatedChapters[prev.currentChapterIndex] = currentChapter;
        
        // Check if we're ending a chapter
        if (next_chapter_title) {
          // Store chapter summary if provided
          if (chapterSummary) {
            currentChapter.summary = chapterSummary;
            currentChapter.summaryImage = chapterSummaryImage;
          }
          
          // Update next chapter info
          setNextChapter({
            title: next_chapter_title,
            pendingPlayerIndex: scene.activePlayer.playerIndex
          });
          
          return {
            ...updatedGameState,
            storyProgress: [...prev.storyProgress, newStory],
            chapters: updatedChapters,
            readyForNewChapter: true
          };
        } else {
          // Regular flow for mid-chapter actions
          return {
            ...updatedGameState,
            storyProgress: [...prev.storyProgress, newStory],
            currentPlayerIndex: scene.activePlayer.playerIndex,
            chapters: updatedChapters
          };
        }
      });
      
    } catch (err) {
      setError('Failed to process action. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // New function to handle starting the next chapter
  const handleStartNewChapter = async () => {
    if (loading || !nextChapter) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log("Starting new chapter with title:", nextChapter.title);
      
      // Prepare game state for new chapter request
      const updatedGameState = {
        ...gameState,
        currentPlayerIndex: nextChapter.pendingPlayerIndex,
      };
      
      // Ensure we have the arcs structure the backend expects
      if (!updatedGameState.arcs) {
        updatedGameState.arcs = [{
          chapters: updatedGameState.chapters || []
        }];
      }
      
      const response = await api.startNewChapter(updatedGameState);
      
      if (!response || !response.newChapter) {
        throw new Error("Invalid response when starting new chapter");
      }
      
      const newChapter = response.newChapter;
      const firstScene = newChapter.scenes[0];
      
      setGameState(prev => {
        // Add the new chapter to the existing chapters array
        const updatedChapters = [...(prev.chapters || []), newChapter];
        const nextChapterIndex = updatedChapters.length - 1;
        
        // Update arcs structure
        const updatedArcs = prev.arcs || [{ chapters: [] }];
        updatedArcs[0].chapters = updatedChapters;
        
        // Create new story progress with just the first scene of the new chapter
        const newStoryProgress = [{
          text: firstScene.text,
          image: firstScene.image,
          audioData: firstScene.audioData,
          choices: firstScene.choices,
          _id: `scene-${Date.now()}-${Math.random()}`
        }];
        
        // Update viewing chapter index
        setViewingChapterIndex(nextChapterIndex);
        
        return {
          ...prev,
          storyProgress: newStoryProgress,
          currentPlayerIndex: nextChapter.pendingPlayerIndex,
          chapters: updatedChapters,
          arcs: updatedArcs,
          currentChapterIndex: nextChapterIndex,
          readyForNewChapter: false
        };
      });
      
      // Clear next chapter info
      setNextChapter(null);
      
    } catch (err) {
      setError('Failed to start new chapter. Please try again.');
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
            return chapterManager.deepCloneWithNewRefs(targetChapter.storedSegments[segIdx]);
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
        handleStartNewChapter={handleStartNewChapter} // Pass the new function
        nextChapter={nextChapter} // Pass next chapter info
        viewingChapterIndex={viewingChapterIndex}
        loading={loading} 
        error={error} 
        currentAction={currentAction} 
        activeTTS={activeTTS} 
        toggleTTS={handleToggleTTS} 
        storyRef={storyRef}
        audioRef={audioRef} // Pass the audio ref to GameScreen
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
      
      {/* Audio player for AI TTS (hidden) - improved configuration */}
      <audio 
        ref={audioRef}
        style={{ display: 'none' }} 
        controls={false}
        preload="auto"
        onError={() => {
          // Prevent error messages on cleanup/manual stopping
          console.log("Audio element error - handled");
        }}
      />
    </div>
  );
}

export default App;