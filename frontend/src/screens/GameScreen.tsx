import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../utils/api-service';
import { IGameState, IPlayerCharacter, IStoryArc, IStoryChapter, IStoryScene } from '../types/game-types';
import HighlightedText from '../components/HighlightedText';
import SpeakerMuteIcon from '../components/SpeakerMuteIcon';
import SpeakerIcon from '../components/SpeakerIcon';
import HostWebsocketService from '../utils/websocket/host/host-websocket-service';
import { HostMessageType } from '../utils/websocket/host/host-message-types';

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
    
    const scrollToBottom = useCallback(() => {
        if (storyRef.current) {
            storyRef.current.scrollTop = storyRef.current.scrollHeight;
        }
    }, []);
    
    useEffect(() => {
        if (!isViewingPastChapter) {
            setTimeout(scrollToBottom, 100);
        }
    }, [getCurrentChapter().scenes.length, isViewingPastChapter, scrollToBottom]);

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

    useEffect(() => {
        stopTTS();
    }, [viewingChapterIndex]);

    const formatChapterTitle = useCallback((title: string) => {
        if (!title || title.trim() === '') {
            return `Chapter ?`;
        }
        
        const displayTitle = title.length > 50 ? title.substring(0, 50) + "..." : title;
        return displayTitle;
    }, []);

    const stopTTS = useCallback(() => {
        if (isPlayingTTS) {
            if (gameState.settings.enableAITTS) {
                if (audioRef.current) {
                    audioRef.current.pause();
                    audioRef.current.currentTime = 0;
                }
            } else {
                window.speechSynthesis.cancel();
            }
            setIsPlayingTTS(false);
            setActiveSceneTTS(null);
        }
    }, [isPlayingTTS, audioRef.current]);
    
    const handleToggleTTS = async (sceneIndex: number) => {
        try {
            if (isPlayingTTS && activeSceneTTS === sceneIndex) {
                stopTTS();
                return;
            } else {
                if (isPlayingTTS) {
                    stopTTS();
                }
                
                setActiveSceneTTS(sceneIndex);
                setIsPlayingTTS(true);
                
                if (gameState.settings.enableAITTS) {
                    let audioData: string | undefined;
                    if (isViewingPastChapter) {
                        const chapter = getChapterByIndex(viewingChapterIndex);
                        audioData = chapter?.summaryAudioData;
                    } else {
                        audioData = getCurrentChapter().scenes[sceneIndex].audioData;
                    }
    
                    if (!audioData) throw new Error("No audio data available for this scene");

                    if (audioRef.current) {
                        audioRef.current.src = `data:audio/mp3;base64,${audioData}`;
                        audioRef.current.onended = () => {
                            setIsPlayingTTS(false);
                            setActiveSceneTTS(null);
                        };
                        
                        await audioRef.current.play();
                    }
                } else {
                    let textToRead: string;
                    if (isViewingPastChapter) {
                        const chapter = getChapterByIndex(viewingChapterIndex);
                        textToRead = chapter?.summary || "";
                    } else {
                        textToRead = getCurrentChapter().scenes[sceneIndex].text;
                    }
                    if (!textToRead) throw new Error("No text available for this scene");
                    
                    const utterance = new SpeechSynthesisUtterance(textToRead);
                    utterance.rate = 0.9;
                    utterance.onend = () => {
                        setIsPlayingTTS(false);
                        setActiveSceneTTS(null);
                    };
                    
                    window.speechSynthesis.speak(utterance);
                }
            }
        } catch (err) {
            console.error("Failed to play audio:", err);
            setIsPlayingTTS(false);
            setActiveSceneTTS(null);
        }
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
            if (response.chapterSummaryAudioData) getCurrentChapter().summaryAudioData = response.chapterSummaryAudioData;
            
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

    useEffect(() => { 
        console.log("Effect ran");
        if (gameState.sessionCode) {
            HostWebsocketService.getInstance().on(HostMessageType.PLAYER_ACTION, handleRemotePlayerAction);
        }
        
        return () => {
            console.log("Cleanup ran");
            if (gameState.sessionCode) {
                HostWebsocketService.getInstance().off(HostMessageType.PLAYER_ACTION, handleRemotePlayerAction);
                HostWebsocketService.getInstance().disconnect();
            }
        };
    }, []);

    useEffect(() => {
        if (!isViewingPastChapter) {
            setTimeout(scrollToBottom, 100);
        }
        updateRemotePlayers();
    }, [getCurrentChapter().scenes.length, isViewingPastChapter, scrollToBottom]);

    const updateRemotePlayers = useCallback(() => {
        if (gameState.sessionCode) {
            console.log("Updating remote players...", gameState.sessionCode);
            const currentScene = getCurrentScene();
            if (currentScene) {
                HostWebsocketService.getInstance().updateGameState(currentScene);
            }
        }
    }, [getCurrentScene, gameState.sessionCode]);

    const handleRemotePlayerAction = (data: any) => {
        if (loading) return;
        
        const { player_index, action } = data.data;
        console.log(`Remote player ${player_index} chose action: ${action}`);
        
        // Get the character assigned to this remote player
        const activeCharacter = getCharacterByIndex(player_index);
        if (activeCharacter) {
            console.log(`Character ${activeCharacter.name} is taking action: ${action}`);
        }
        
        // Process the action
        handleActionChoice(action);
    };

    return (
       <div className="game-screen">
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
                     className={`tts-button ${isPlayingTTS && activeSceneTTS === viewingChapterIndex ? 'tts-active' : ''}`}
                     onClick={() => handleToggleTTS(viewingChapterIndex)}
                     title={isPlayingTTS && activeSceneTTS === viewingChapterIndex ? "Stop Narration" : "Play Narration"}
                     aria-label={isPlayingTTS && activeSceneTTS === viewingChapterIndex ? "Stop Narration" : "Play Narration"}
                     disabled={loading}
                   >
                     {isPlayingTTS && activeSceneTTS === viewingChapterIndex ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                   </button>
                 </div>
                 {getChapterByIndex(viewingChapterIndex)?.summaryImage && (
                   <div className="story-image centered-image">
                     <img src={`data:image/png;base64,${getChapterByIndex(viewingChapterIndex)!.summaryImage}`} alt="Chapter Summary" key={`img-summary-${viewingChapterIndex}-${Date.now()}`} />
                   </div>
                 )}
               </div>
             ): null}
             
             {!isViewingPastChapter && 
              getCurrentChapter().scenes.map((scene: IStoryScene, index: number) => {
                const segmentKey = `${getCurrentChapter().index}-${index}`;
                const prevScene: IStoryScene | undefined = getCurrentChapter().scenes[index - 1];
                return (
                  <div key={segmentKey} className="story-segment">
                    <div className="story-text">
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
                          isPlaying={isPlayingTTS && activeSceneTTS === index}
                          isAITTS={gameState.settings.enableAITTS}
                          audioRef={audioRef}
                      />
                      
                      <button 
                        className={`tts-button ${isPlayingTTS && activeSceneTTS === index ? 'tts-active' : ''}`}
                        onClick={() => handleToggleTTS(index)}
                        title={isPlayingTTS && activeSceneTTS === index ? "Stop Narration" : "Play Narration"}
                        aria-label={isPlayingTTS && activeSceneTTS === index ? "Stop Narration" : "Play Narration"}
                        disabled={loading}
                      >
                        {isPlayingTTS && activeSceneTTS === index ? <SpeakerMuteIcon /> : <SpeakerIcon />}
                      </button>
                    </div>
                    {scene.image && (
                      <div className="story-image">
                        <img 
                          src={`data:image/png;base64,${scene.image}`} 
                          alt="Scene" 
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
         {gameState.sessionCode && (
            <div className="session-info">
                <div className="session-code-display">
                    Game Code: <span className="code-highlight">{gameState.sessionCode}</span>
                </div>
                <p className="session-info">Share this code with friends to join your game</p>
            </div>
         )}
         <audio 
            ref={audioRef}
            style={{ display: 'none' }} 
            controls={false}
            preload="auto"
            onError={() => {
                console.log("Audio element error - handled");
            }}
        />
       </div>
     );
};

export default GameScreen;