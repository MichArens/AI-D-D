import { IPlayerCharacter, IStoryScene } from "../../../types/game-types";
import BaseWebSocketService from "../base-websocket-service";
import { HostMessageType } from "./host-message-types";

export default class HostWebsocketService extends BaseWebSocketService {
    private static instance: HostWebsocketService;
    private constructor() {
        super();
    }

    static getInstance(): HostWebsocketService {
        if (!HostWebsocketService.instance) {
            HostWebsocketService.instance = new HostWebsocketService();
        }
        return HostWebsocketService.instance;
    }

    on(messageType: HostMessageType, handler: (data: any) => void): void {
        super.on(messageType, handler);
    }

    createSession(): void {
        this.sendMessage({
            type: 'create_session'
        })
    }

    updateCharacters(characters: IPlayerCharacter[]): void {
        this.sendMessage({
            type: 'update_characters',
            data: {
                characters
            }
        });
    }

    updateGameState(newScene: IStoryScene): void {
        this.sendMessage({
            type: 'update_game_state',
            data: {
                scene: newScene
            }
        });
    }
    
}