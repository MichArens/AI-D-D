import React from 'react';
import HighlightedText from './HighlightedText';
import SpeakerIcon from './SpeakerIcon';
import SpeakerMuteIcon from './SpeakerMuteIcon';

const GameScreen = ({ gameState, setGameState, handleActionChoice, loading, error, currentAction, activeTTS, toggleTTS, storyRef }) => {
  // Current chapter title for the header
  const currentChapter = gameState.chapters && gameState.chapters[gameState.currentChapterIndex];
  
  return (
    <div className="game-screen">
      {/* Sticky chapter header at top of screen */}
      {currentChapter && (
        <div className="sticky-chapter-header">
          <h2>Chapter {gameState.currentChapterIndex + 1}: {currentChapter.title}</h2>
        </div>
      )}
      
      <div className="game-layout">
        <div className="chapters-sidebar">
          <h3>Chapters</h3>
          {gameState.chapters && gameState.chapters.map((chapter, index) => (
            <div 
              key={index} 
              className={`chapter-item ${index === gameState.currentChapterIndex ? 'active-chapter' : ''}`}
            >
              <h4>Chapter {index + 1}: {chapter.title}</h4>
              {chapter.image && (
                <div className="chapter-image">
                  <img src={`data:image/png;base64,${chapter.image}`} alt={chapter.title} />
                </div>
              )}
              {chapter.summary && <p>{chapter.summary}</p>}
            </div>
          ))}
        </div>

        <div className="story-container" ref={storyRef}>
          {gameState.storyProgress.map((segment, index) => (
            <div 
              key={index} 
              className={`story-segment ${segment.chapterId !== undefined && 
                segment.chapterId !== (gameState.storyProgress[index-1]?.chapterId || -1) ? 
                'new-chapter' : ''}`}
            >
              {segment.chapterId !== undefined && 
               segment.chapterId !== (gameState.storyProgress[index-1]?.chapterId || -1) && 
               gameState.chapters && gameState.chapters[segment.chapterId] && (
                <div className="chapter-header">
                  <h3>Chapter {segment.chapterId + 1}: {gameState.chapters[segment.chapterId].title}</h3>
                </div>
              )}
              
              <div className="story-text">
                {segment.player && segment.action && (
                  <div className="player-action">
                    <div className="player-icon">
                      {gameState.characters.find(c => c.name === segment.player)?.icon ? (
                        <img 
                          src={`data:image/png;base64,${gameState.characters.find(c => c.name === segment.player)?.icon}`} 
                          alt={segment.player} 
                        />
                      ) : (
                        <div className="icon-placeholder">{segment.player[0]}</div>
                      )}
                    </div>
                    <p><strong>{segment.player}</strong> chose to {segment.action}</p>
                  </div>
                )}
                
                <HighlightedText 
                    text={segment.text} 
                    activeTTS={activeTTS} 
                    isPlaying={activeTTS === index} 
                />
                
                {/* TTS Button with speaker icons */}
                {gameState.settings.enableTTS && segment.text && (
                  <button 
                    className={`tts-button ${activeTTS === index ? 'tts-active' : ''}`}
                    onClick={() => toggleTTS(index)}
                    title={activeTTS === index ? "Stop Narration" : "Play Narration"}
                    aria-label={activeTTS === index ? "Stop Narration" : "Play Narration"}
                  >
                    {activeTTS === index ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                  </button>
                )}
              </div>
              {segment.image && (
                <div className="story-image">
                  <img src={`data:image/png;base64,${segment.image}`} alt="Scene" />
                </div>
              )}
            </div>
          ))}
        </div>
        
        <div className="action-panel">
          {/* Current chapter info - removed rounds counter */}
          {currentChapter && (
            <div className="current-chapter-info">
              <h3>Chapter {gameState.currentChapterIndex + 1}</h3>
              <h4>{currentChapter.title}</h4>
            </div>
          )}
          
          <div className="current-player">
            {gameState.characters[gameState.currentPlayerIndex] && (
              <>
                <h3>Current Player: 
                  <span className="player-name">{gameState.characters[gameState.currentPlayerIndex].name}</span>
                </h3>
                <div className="player-info">
                  {gameState.characters[gameState.currentPlayerIndex].icon ? (
                    <img 
                      src={`data:image/png;base64,${gameState.characters[gameState.currentPlayerIndex].icon}`} 
                      alt={gameState.characters[gameState.currentPlayerIndex].name} 
                      className="active-player-icon"
                    />
                  ) : (
                    <div className="icon-placeholder active">
                      {gameState.characters[gameState.currentPlayerIndex].name[0]}
                    </div>
                  )}
                  <div className="player-details">
                    <p>{gameState.characters[gameState.currentPlayerIndex].race} {gameState.characters[gameState.currentPlayerIndex].characterClass}</p>
                  </div>
                </div>
              </>
            )}
          </div>
          
          <div className="action-choices">
            <h3>Choose Your Action:</h3>
            
            {gameState.storyProgress.length > 0 && 
             gameState.storyProgress[gameState.storyProgress.length - 1].choices && 
             gameState.storyProgress[gameState.storyProgress.length - 1].choices.map(choice => (
              <button 
                key={choice.id} 
                className={`action-button ${currentAction === choice.id ? 'selected' : ''}`}
                onClick={() => handleActionChoice(choice.id)}
                disabled={loading}
              >
                {choice.text}
              </button>
            ))}
            
            {loading && <div className="loading-message">Generating story...</div>}
          </div>
        </div>
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default GameScreen;
