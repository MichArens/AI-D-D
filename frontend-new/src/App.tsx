import React from 'react';
import './App.css';
import { GameScreens } from './types/game-screens';
import SetupScreen from './screens/SetupScreen';
import { IGameState } from './types/game-types';

function App() {
  const [screen, setScreen] = React.useState<GameScreens>('setup');
  const [gameState, setGameState] = React.useState<IGameState>({
    settings: {
      playerCount: 2,
      enableAITTS: false,
      enableMusic: false,
      aiModel: 'llama',
      scenesPerChapter: 3,
      chaptersPerArc: 3,
    },
    characters: [],
    arcs: [
      {
        chapters: [],
      }
  ],
  });
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  // Functions
  const handleStartSetup = () => {
    // Implementation goes here
  };

  return (
      <div className={`dnd-app ${screen === 'game' ? 'dnd-app-fullscreen' : ''}`}>
        {screen === 'setup' && <SetupScreen 
          gameState={gameState} 
          setGameState={setGameState} 
          handleStartSetup={handleStartSetup} 
          loading={loading} 
          error={error} 
          setScreen={setScreen} 
        />}
        {/* {screen === 'character' && <CharacterScreen 
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
        />} */}
        
        {/* Background music player (hidden) */}
        {/* {gameState.musicUrl && gameState.settings.enableMusic && (
          <audio 
            src={gameState.musicUrl} 
            autoPlay 
            loop 
            style={{ display: 'none' }} 
          />
        )} */}
        
        {/* Audio player for AI TTS (hidden) - improved configuration */}
        {/* <audio 
          ref={audioRef}
          style={{ display: 'none' }} 
          controls={false}
          preload="auto"
          onError={() => {
            // Prevent error messages on cleanup/manual stopping
            console.log("Audio element error - handled");
          }}
        /> */}
      </div>
    );
}

export default App;
