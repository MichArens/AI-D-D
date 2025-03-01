import React from 'react';
import HighlightedText from './HighlightedText';
import SpeakerIcon from './SpeakerIcon';
import SpeakerMuteIcon from './SpeakerMuteIcon';

const GameScreen = ({ 
  gameState, 
  setGameState, 
  handleActionChoice, 
  handleViewChapter,
  viewingChapterIndex,
  loading, 
  error, 
  currentAction, 
  activeTTS, 
  toggleTTS, 
  storyRef 
}) => {
  // Safe access to current chapter
  const currentChapter = gameState.chapters && gameState.chapters.length > gameState.currentChapterIndex ? 
    gameState.chapters[gameState.currentChapterIndex] : null;
  
  // Safe access to viewing chapter
  const viewingChapter = gameState.chapters && gameState.chapters.length > viewingChapterIndex ? 
    gameState.chapters[viewingChapterIndex] : null;
  
  // Flag to check if viewing a past chapter
  const isViewingPastChapter = viewingChapterIndex < gameState.currentChapterIndex;
  
  // Check if chapters are available
  const hasChapters = gameState.chapters && gameState.chapters.length > 0;
  
  return (
    <div className="game-screen">
      {/* Sticky chapter header at top of screen - always show even if null with a fallback */}
      <div className="sticky-chapter-header">
        <h2>
          {viewingChapter ? (
            <>Chapter {viewingChapterIndex + 1}: {viewingChapter.title || "Adventure"}</>
          ) : (
            <>Chapter 1: Adventure Begins</>
          )}
          {isViewingPastChapter && <span className="history-badge">History Mode</span>}
        </h2>
      </div>
      
      <div className="game-layout">
        <div className="chapters-sidebar">
          <h3>Chapters</h3>
          <div className="chapters-list">
            {hasChapters ? (
              gameState.chapters.map((chapter, index) => (
                <div 
                  key={index} 
                  className={`chapter-item ${index === viewingChapterIndex ? 'active-chapter' : ''}`}
                  onClick={() => handleViewChapter(index)}
                >
                  {/* Only show chapter title in sidebar */}
                  <h4>Chapter {index + 1}: {chapter.title || "Chapter"}</h4>
                </div>
              ))
            ) : (
              <div className="chapter-item active-chapter">
                <h4>Chapter 1: Adventure Begins</h4>
              </div>
            )}
          </div>
        </div>

        <div className="story-container" ref={storyRef}>
          {/* Show chapter summary view when viewing past chapter */}
          {isViewingPastChapter && gameState.storyProgress.length > 0 && gameState.storyProgress[0].isChapterSummary && (
            <div className="chapter-summary-view">
              <h3>Chapter Summary</h3>
              <div className="story-text">
                <HighlightedText 
                  text={gameState.storyProgress[0].text} 
                  activeTTS={activeTTS} 
                  isPlaying={activeTTS === 'summary'} 
                />
                
                {/* Add TTS button for the summary */}
                {gameState.settings.enableTTS && gameState.storyProgress[0].text && (
                  <button 
                    className={`tts-button ${activeTTS === 'summary' ? 'tts-active' : ''}`}
                    onClick={() => toggleTTS('summary')}
                    title={activeTTS === 'summary' ? "Stop Narration" : "Play Narration"}
                    aria-label={activeTTS === 'summary' ? "Stop Narration" : "Play Narration"}
                  >
                    {activeTTS === 'summary' ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                  </button>
                )}
              </div>
              {gameState.storyProgress[0].image && (
                <div className="story-image centered-image">
                  <img src={`data:image/png;base64,${gameState.storyProgress[0].image}`} alt="Chapter Summary" />
                </div>
              )}
            </div>
          )}
          
          {/* Show regular story progression when not in summary mode */}
          {(!isViewingPastChapter || !gameState.storyProgress[0]?.isChapterSummary) && 
           gameState.storyProgress.map((segment, index) => (
            <div 
              key={index} 
              className={`story-segment ${segment.chapterId !== undefined && 
                segment.chapterId !== (gameState.storyProgress[index-1]?.chapterId || -1) ? 
                'new-chapter' : ''}`}
            >
              {/* Remove chapter headers inside the story segments */}
              
              <div className="story-text">
                {/* Player action info */}
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
          {/* Remove the redundant chapter info section */}
          
          {/* Only show player actions if viewing current chapter */}
          {!isViewingPastChapter ? (
            <>
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
            </>
          ) : (
            <div className="history-controls">
              <p>You are viewing a past chapter.</p>
              <button 
                className="main-button return-button"
                onClick={() => handleViewChapter(gameState.currentChapterIndex)}
              >
                Return to Current Chapter
              </button>
            </div>
          )}
        </div>
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default GameScreen;
