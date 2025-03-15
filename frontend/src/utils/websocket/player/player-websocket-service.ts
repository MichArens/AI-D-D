import BaseWebSocketService from "../base-websocket-service";
import { PlayerMessageType } from "./player-message-types";

export default class PlayerWebsocketService extends BaseWebSocketService {
    private static instance: PlayerWebsocketService;
    private constructor() {
        super();
    }

    static getInstance(): PlayerWebsocketService {
        if (!PlayerWebsocketService.instance) {
            PlayerWebsocketService.instance = new PlayerWebsocketService();
        }
        return PlayerWebsocketService.instance;
    }

    on(messageType: PlayerMessageType, handler: (data: any) => void): void {
        super.on(messageType, handler);
    }

    joinSession(sessionCode: string): void {
        this.sendMessage({
            type: 'join_session',
            data: {
                sessionCode
            }
        })
    }

    selectCharacter(characterIndex: number): void {
        this.sendMessage({
            type: 'select_character',
            data: {
                character_index: characterIndex
            }
        });
    }

    sendPlayerAction(action: string): void {
        this.sendMessage({
            type: 'player_action',
            data: {
                action
            }
        });
    }
}