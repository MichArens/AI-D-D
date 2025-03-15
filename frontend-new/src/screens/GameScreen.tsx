import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../utils/api-service';
import { IGameState, IPlayerCharacter, IStoryArc, IStoryChapter, IStoryScene } from '../types/game-types';
import HighlightedText from '../components/HighlightedText';
import SpeakerMuteIcon from '../components/SpeakerMuteIcon';
import SpeakerIcon from '../components/SpeakerIcon';

interface GameScreenProps {
  gameState: IGameState;
  getActiveCharacter: () => IPlayerCharacter | undefined;
  getCurrrentArc: () => IStoryArc;
  getCurrentChapter: () => IStoryChapter;
  getCurrentScene: () => IStoryScene;
  getChapterByIndex: (index: number) => IStoryChapter | undefined;
  getCharacterByIndex: (index: number) => IPlayerCharacter | undefined;
  addNewArc: (firstArcChapter: IStoryChapter) => void;
  addNewChapter: (newChapter: IStoryChapter) => void;
  addNewScene: (newScene: IStoryScene) => void;
}

const GameScreen: React.FC<GameScreenProps> = ({
  gameState,
  getActiveCharacter,
  getCurrrentArc,
  getCurrentChapter,
  getCurrentScene,
  getChapterByIndex,
  getCharacterByIndex,
  addNewArc,
  addNewChapter,
  addNewScene,
}) => {
    // State for custom action input
    const [showCustomInput, setShowCustomInput] = useState(false);
    const [customAction, setCustomAction] = useState('');
    const [activeSceneTTS, setActiveSceneTTS] = useState<number | null>(null);
    const [isPlayingTTS, setIsPlayingTTS] = useState<boolean>(false);
    const [nextChapterTitle, setNextChapterTitle] = useState<string | null>(null);

    const [viewingChapterIndex, setViewingChapterIndex] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);

    const storyRef = useRef<HTMLDivElement>(null);
    const audioRef = useRef<HTMLAudioElement>(null);

    useEffect(() => {
        //TODO check how behaves
        if (storyRef.current) {
          storyRef.current.scrollTop = storyRef.current.scrollHeight;
        }
    }, [gameState]);

    const viewingChapter: IStoryChapter = useMemo(() => {
        return getChapterByIndex(viewingChapterIndex) || getCurrentChapter();
    }, [gameState, viewingChapterIndex]);

    const isViewingPastChapter: boolean = useMemo(() => {
        return viewingChapterIndex < getCurrentChapter().index;
    }, [gameState, viewingChapterIndex]);

    const handleCustomActionSubmit = useCallback(() => {
        if (customAction.trim()) {
          handleActionChoice(customAction);
          setCustomAction('');
          setShowCustomInput(false);
        }
    }, [customAction]);

    const handleChapterClick = (index: number) => {
        if (loading) {
          return;
        }
        setViewingChapterIndex(index);
    };

    const formatChapterTitle = useCallback((title: string) => {
        if (!title || title.trim() === '') {
            return `Chapter ?`;
        }
        
        const displayTitle = title.length > 50 ? title.substring(0, 50) + "..." : title;
        return displayTitle;
    }, []);

    const handleToggleTTS = async (index: number) => {
       //TODO handleToggleTTS(index);
    };

    const handleStartNewChapter = useCallback(async () => {
        if (loading || !nextChapterTitle) return;
    
        setLoading(true);
        setError(null);

        try {
            const response = await api.startNewChapter(gameState, nextChapterTitle);
        
            if (!response || !response.newChapter) {
                throw new Error("Invalid response from action endpoint");
            }

            const shouldStateNewArc: boolean = getCurrrentArc().chapters.length >= gameState.settings.chaptersPerArc;
            if (shouldStateNewArc) {
                addNewArc(response.newChapter);
            } else {
                addNewChapter(response.newChapter);
            }
            setViewingChapterIndex(response.newChapter.index);
        } catch (err) {
            setError('Failed to start new chapter. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [nextChapterTitle]);

    const handleActionChoice = async (text: string) => {
        if (loading) return;
    
        setLoading(true);
        setError(null);

        try {
            getCurrentScene().chosenAction = text;
            const response = await api.takeAction(gameState, undefined);
      
            if (!response || !response.scene) {
              throw new Error("Invalid response from action endpoint");
            }
            
            addNewScene(response.scene);
            if (response.chapterSummary) getCurrentChapter().summary = response.chapterSummary;
            if (response.chapterSummaryImage) getCurrentChapter().summaryImage = response.chapterSummaryImage;
            
            if (response.nextChapterTitle) {
                setNextChapterTitle(response.nextChapterTitle);
            }
        } catch (err) {
            setError('Failed to process action. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    
   return (
       <div className="game-screen">
         {/* Custom action modal */}
         {showCustomInput && (
           <div className="custom-action-modal">
             <div className="modal-content">
               <h3>Create Your Own Action</h3>
               <p>Describe what {getActiveCharacter()?.name} will do:</p>
               <textarea
                 value={customAction}
                 onChange={(e) => setCustomAction(e.target.value)}
                 placeholder="Describe your action here..."
                 rows={4}
                 maxLength={200}
               />
               <div className="custom-action-buttons">
                 <button 
                   className="secondary-button" 
                   onClick={() => setShowCustomInput(false)}
                 >
                   Cancel
                 </button>
                 <button 
                   className="main-button" 
                   onClick={handleCustomActionSubmit}
                   disabled={!customAction.trim() || loading}
                 >
                   Submit Action
                 </button>
               </div>
             </div>
           </div>
         )}
         
         {/* Sticky chapter header at top of screen - always show even if null with a fallback */}
         <div className="sticky-chapter-header">
           <h2>
             {viewingChapter ? (
               <>Chapter {viewingChapter.index + 1}: {formatChapterTitle(viewingChapter.title)}</>
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
                {gameState.arcs.flatMap(arc => arc.chapters).map((chapter) => {
                    const absoluteIndex = chapter.index;
                    return (
                        <div 
                            key={`chapter-${absoluteIndex}`} 
                            className={`chapter-item ${absoluteIndex === viewingChapterIndex ? 'active-chapter' : ''} ${loading ? 'disabled' : ''}`}
                            onClick={() => handleChapterClick(absoluteIndex)}
                            style={loading ? {cursor: 'not-allowed', opacity: '0.6'} : {}}
                        >
                            <h4>Chapter {absoluteIndex + 1}: {formatChapterTitle(chapter.title)}</h4>
                        </div>
                    );
                })}
             </div>
           </div>
   
           <div className="story-container" ref={storyRef}>
             {/* Show chapter summary view when viewing past chapter */}
             {isViewingPastChapter ? (
               <div className="chapter-summary-view">
                 <h3>Chapter Summary</h3>
                 <div className="story-text">
                   <HighlightedText 
                     text={getChapterByIndex(viewingChapterIndex)?.summary || ''} 
                     isPlaying={isPlayingTTS} 
                     isAITTS={gameState.settings.enableAITTS}
                     audioRef={audioRef}
                   />
                   
                   <button 
                     className={`tts-button ${isPlayingTTS ? 'tts-active' : ''}`}
                     onClick={() => handleToggleTTS(viewingChapterIndex)}
                     title={isPlayingTTS ? "Stop Narration" : "Play Narration"}
                     aria-label={isPlayingTTS ? "Stop Narration" : "Play Narration"}
                     disabled={loading}
                   >
                     {isPlayingTTS ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                   </button>
                 </div>
                 {getChapterByIndex(viewingChapterIndex)?.summaryImage && (
                   <div className="story-image centered-image">
                     <img src={`data:image/png;base64,${getChapterByIndex(viewingChapterIndex)!.summaryImage}`} alt="Chapter Summary" key={`img-summary-${viewingChapterIndex}-${Date.now()}`} />
                   </div>
                 )}
               </div>
             ): null}
             
             {/* Show regular story progression when not in summary mode */}
             {!isViewingPastChapter && 
              getCurrentChapter().scenes.map((scene: IStoryScene, index: number) => {
                // Generate a truly unique key for each segment
                const segmentKey = `${getCurrentChapter().index}-${index}`;
                const prevScene: IStoryScene | undefined = getCurrentChapter().scenes[index - 1];
                return (
                  <div key={segmentKey} className="story-segment">
                    <div className="story-text">
                      {/* Player action info */}
                      {prevScene && getCharacterByIndex(prevScene.activeCharacterIndex) && prevScene.chosenAction && (
                        <div className="player-action">
                          <div className="player-icon">
                            {getCharacterByIndex(prevScene.activeCharacterIndex)!.icon ? (
                              <img 
                                src={`data:image/png;base64,${getCharacterByIndex(prevScene.activeCharacterIndex)!.icon}`} 
                                alt={getCharacterByIndex(prevScene.activeCharacterIndex)!.name.charAt(0)} 
                              />
                            ) : (
                              <div className="icon-placeholder">{getCharacterByIndex(prevScene.activeCharacterIndex)!.name.charAt(0)}</div>
                            )}
                          </div>
                          <p><strong>{getCharacterByIndex(prevScene.activeCharacterIndex)!.name}</strong> chose to {prevScene.chosenAction}</p>
                        </div>
                      )}
                      
                      <HighlightedText 
                          text={scene.text} 
                          isPlaying={isPlayingTTS}
                          isAITTS={gameState.settings.enableAITTS}
                          audioRef={audioRef}
                      />
                      
                      {/* TTS Button */}
                      <button 
                        className={`tts-button ${isPlayingTTS ? 'tts-active' : ''}`}
                        onClick={() => handleToggleTTS(index)}
                        title={isPlayingTTS ? "Stop Narration" : "Play Narration"}
                        aria-label={isPlayingTTS ? "Stop Narration" : "Play Narration"}
                        disabled={loading}
                      >
                        {isPlayingTTS ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                      </button>
                    </div>
                    {scene.image && (
                      <div className="story-image">
                        <img 
                          src={`data:image/png;base64,${scene.image}`} 
                          alt="Scene" 
                          // Guaranteed unique key for image
                          key={`img-${segmentKey}-${Date.now()}`}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
           </div>
           
           <div className="action-panel">
             {!isViewingPastChapter ? (
               <>
                 <div className="current-player">
                   {getActiveCharacter() && (
                     <>
                       <h3>Current Player: 
                         <span className="player-name">{getActiveCharacter()!.name}</span>
                       </h3>
                       <div className="player-info">
                         {getActiveCharacter()!.icon ? (
                           <img 
                             src={`data:image/png;base64,${getActiveCharacter()!.icon}`} 
                             alt={getActiveCharacter()!.name} 
                             className="active-player-icon"
                           />
                         ) : (
                           <div className="icon-placeholder active">
                             {getActiveCharacter()!.name[0]}
                           </div>
                         )}
                         <div className="player-details">
                           <p>{getActiveCharacter()!.race} {getActiveCharacter()!.characterClass}</p>
                         </div>
                       </div>
                     </>
                   )}
                 </div>
                 
                 <div className="action-choices">
                   {/* Display "Start New Chapter" button if chapter is ready to end */}
                   {getCurrentChapter().scenes[getCurrentChapter().scenes.length - 1].choices.length === 0 ? (
                     <div className="new-chapter-container">
                       <h3>Chapter Complete</h3>
                       <p>The heroes' adventure continues in a new chapter...</p>
                       <button 
                         className="new-chapter-button"
                         onClick={handleStartNewChapter}
                         disabled={loading}
                       >
                         <i className="fa fa-book-open"></i> Begin: {nextChapterTitle || 'New Chapter'}
                       </button>
                     </div>
                   ) : (
                     <>
                       <h3>Choose Your Action:</h3>
                       
                       {/* Show action buttons when not loading */}
                       {!loading &&
                        getCurrentScene().choices && (
                         <>
                           {getCurrentScene().choices.map(choice => (
                             <button 
                               key={choice.id} 
                               className={'action-button'}
                               onClick={() => handleActionChoice(choice.text)}
                               disabled={loading}
                             >
                               {choice.text}
                             </button>
                           ))}
                           
                           {/* Add custom action button */}
                           <button 
                             className="action-button custom-action-button"
                             onClick={() => setShowCustomInput(true)}
                             disabled={loading}
                           >
                             Create your own action...
                           </button>
                         </>
                       )}
                     </>
                   )}
                   
                   {/* Enhanced loading indicator in action area */}
                   {loading && (
                     <div className="action-loading-container">
                       <div className="loading-spinner"></div>
                       <div className="loading-message">
                         <p>Generating next part of your adventure...</p>
                         <p className="loading-submessage">The Dungeon Master is thinking...</p>
                       </div>
                     </div>
                   )}
                 </div>
               </>
             ) : (
               <div className="history-controls">
                 <p>You are viewing a past chapter.</p>
                 <button 
                   className="main-button return-button"
                   onClick={() => handleChapterClick(getCurrentChapter().index)}
                   disabled={loading}
                 >
                   Return to Current Chapter
                 </button>
                 {loading && (
                   <div className="loading-message">Please wait until the story generation is complete...</div>
                 )}
               </div>
             )}
           </div>
         </div>
         
         {error && <div className="error-message">{error}</div>}
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
};

export default GameScreen;