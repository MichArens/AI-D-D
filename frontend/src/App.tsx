import React from 'react';
import './App.css';
import { GameScreens } from './types/game-screens';
import SetupScreen from './screens/SetupScreen';
import CharacterScreen from './screens/CharacterScreen';
import { useGameState } from './states/game-state';
import GameScreen from './screens/GameScreen';
import JoinGameScreen from './screens/JoinGameScreen';

function App() {
    const [screen, setScreen] = React.useState<GameScreens>('setup');
    const {
        gameState, 
        updateSettings, 
        updateCharacters, 
        addNewArc,
        addNewChapter,
        addNewScene,
        getActiveCharacter,
        getCurrrentArc,
        getCurrentChapter,
        getCurrentScene,
        getChapterByIndex,
        getCharacterByIndex
    } = useGameState();

    return (
        <div className={`dnd-app ${screen === 'game' ? 'dnd-app-fullscreen' : ''}`}>
            {screen === 'setup' && <SetupScreen 
            gameState={gameState} 
            updateSettings={updateSettings} 
            setScreen={setScreen} 
            />}
            {screen === 'character' && <CharacterScreen 
            gameState={gameState}
            updateCharacters={updateCharacters}
            addNewChapter={addNewChapter}
            setScreen={setScreen} 
            />}
            {screen === 'game' && <GameScreen 
            gameState={gameState}
            getActiveCharacter={getActiveCharacter}
            getCurrrentArc={getCurrrentArc}
            getCurrentChapter={getCurrentChapter}
            getCurrentScene={getCurrentScene}
            getChapterByIndex={getChapterByIndex}
            getCharacterByIndex={getCharacterByIndex}
            addNewArc={addNewArc}
            addNewChapter={addNewChapter}
            addNewScene={addNewScene}
            />}
            
            {screen === 'join' && <JoinGameScreen 
            setScreen={setScreen}
            />}

            {/* Background music player (hidden) */}
            {/* {gameState.musicUrl && gameState.settings.enableMusic && (
            <audio 
                src={gameState.musicUrl} 
                autoPlay 
                loop 
                style={{ display: 'none' }} 
            />
            )} */}
        </div>
    );
}

export default App;
