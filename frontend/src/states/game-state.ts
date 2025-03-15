import { create } from "zustand";
import { IGameSettings, IGameState, IPlayerCharacter, IStoryArc, IStoryChapter, IStoryScene } from "../types/game-types";

interface IGameStateStore {
    gameState: IGameState;
    updateSettings: (newSettings: IGameSettings) => void;
    updateCharacters: (newCharacters: IPlayerCharacter[]) => void;
    addNewArc: (firstArcChapter: IStoryChapter) => void;
    addNewChapter: (newChapter: IStoryChapter) => void;
    addNewScene: (newScene: IStoryScene) => void;
    getActiveCharacter: () => IPlayerCharacter | undefined;
    getCurrrentArc: () => IStoryArc;
    getCurrentChapter: () => IStoryChapter;
    getCurrentScene: () => IStoryScene;
    getChapterByIndex: (index: number) => IStoryChapter | undefined;
    getCharacterByIndex: (index: number) => IPlayerCharacter | undefined;
}
  
export const useGameState = create<IGameStateStore>((set, get) => ({
    gameState: {
        settings: {
            playerCount: 2,
            enableAITTS: false,
            enableMusic: false,
            aiModel: 'llama',
            scenesPerChapter: 3,
            chaptersPerArc: 3,
            enableImages: false
        },
        characters: [],
        arcs: [
            {
            chapters: [],
            }
        ],
    },
    updateSettings: (newSettings: IGameSettings) => {
        set((state) => ({
            gameState: {
            ...state.gameState,
            settings: {
                ...state.gameState.settings,
                ...newSettings
            }
            },
        }));
    },
    updateCharacters: (newCharacters: IPlayerCharacter[]) => {
        set((state)=> ({
            gameState: {
            ...state.gameState,
            characters: newCharacters
            }
        }))
    },
    addNewArc: (firstArcChapter: IStoryChapter) => {
        set((state) => {
            const newArc: IStoryArc = {
                chapters: [
                    firstArcChapter
                ]
            };
            return {
                gameState: {
                    ...state.gameState,
                    arcs: [...state.gameState.arcs, newArc]
                }
            };
        });
    },
    addNewChapter: (newChapter: IStoryChapter) => {
        set(state => {
            const arcs = [...state.gameState.arcs];
            if (arcs.length === 0) return state;
    
            const lastArc = arcs[arcs.length - 1];
            lastArc.chapters.push(newChapter);
            return { gameState: { ...state.gameState, arcs } };
        });
    },
    addNewScene: (newScene: IStoryScene) => {
        set(state => {
            state.getCurrentChapter().scenes.push(newScene);
            return state;
        });
    },
    getActiveCharacter: () => {
        const lastScene = get().getCurrentScene();
        return get().getCharacterByIndex(lastScene.activeCharacterIndex);
    },
    getCurrrentArc: () => {
        return get().gameState.arcs[get().gameState.arcs.length - 1];
    },
    getCurrentChapter: () => {
        const lastArc = get().getCurrrentArc();
        return lastArc.chapters[lastArc.chapters.length - 1];
    },
    getCurrentScene: () => {
        const lastChapter = get().getCurrentChapter();
        return lastChapter.scenes[lastChapter.scenes.length - 1];
    },
    getChapterByIndex: (index: number) => {
        const relevantArcIndex = Math.floor(index / get().gameState.settings.chaptersPerArc);
        if (relevantArcIndex >= get().gameState.arcs.length) return undefined;
        const relevantChapterIndex = index % get().gameState.settings.chaptersPerArc;
        return get().gameState.arcs[relevantArcIndex].chapters[relevantChapterIndex];
    },
    getCharacterByIndex: (index: number) => {
        return get().gameState.characters[index];
    }
}));