export interface IGameSettings {
    playerCount: number;
    enableImages: boolean;
    enableAITTS: boolean;  // Changed from enableTTS to enableAITTS
    enableMusic: boolean;
    aiModel?: string;
    scenesPerChapter: number;
    chaptersPerArc: number;
}

export  interface IPlayerCharacter {
    name: string;
    race?: string;
    characterClass?: string;
    gender?: string;
    playerIndex: number;
    icon?: string;  // Base64 encoded image
}

export  interface IActionChoice {
    id: number;
    text: string;
}

export  interface IStoryScene {
    text: string;
    image?: string;
    audioData?: string;
    choices: IActionChoice[];
    activeCharacterIndex: number;
    chosenAction?: string;
}

export  interface IStoryChapter {
    title: string;
    summary?: string;
    summaryImage?: string;
    scenes: IStoryScene[];
    index: number;
}

export  interface IStoryArc {  // Fixed typo from "StroyArc" to "StoryArc"
    chapters: IStoryChapter[];
}

export  interface IGameState {
    settings: IGameSettings;
    characters: IPlayerCharacter[];
    arcs: IStoryArc[];
    musicUrl?: string;
}