type MessageHandler = (data: any) => void;

abstract class BaseWebSocketService {
    protected readonly ws_address: string;
    protected ws: WebSocket | null = null;
    public onOpen: (() => void) | null = null;
    protected messageHandlers: { [messageType: string]: MessageHandler[] } = {};

    protected constructor() {
        this.ws_address = `ws://${window.location.hostname}:8000/ws/game-session`;
    }

    connect(): void {
        this.ws = new WebSocket(this.ws_address);
        this.ws.onopen = () => {
           this.ws?.readyState == WebSocket.OPEN && this.onOpen && this.onOpen();
        };
        
        this.ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
        };
        
        this.ws.onclose = () => {
          console.log("WebSocket connection closed");
        //   this.attemptReconnect();
        };
    }

    disconnect(): void {
        if (this.ws) {
          this.ws.close();
          this.ws = null;
        }
        // if (this.reconnectTimeout) {
        //   clearTimeout(this.reconnectTimeout);
        //   this.reconnectTimeout = null;
        // }
        // this.updateStatus('disconnected');
    }
    protected handleMessage(data: any): void {      
        if (data.type && this.messageHandlers[data.type]) {
            for (const handler of this.messageHandlers[data.type]) {
                handler(data);
            }
        }
    }
    
    on(messageType: string, handler: MessageHandler): void {
        if (!this.messageHandlers[messageType]) {
            this.messageHandlers[messageType] = [];
        }
        this.messageHandlers[messageType].push(handler);
    }

    off(messageType: string, handler: MessageHandler): void {
        if (this.messageHandlers[messageType]) {
            this.messageHandlers[messageType] = this.messageHandlers[messageType].filter(h => h !== handler);
        }
    }

    protected sendMessage(message: {type: string, data?: any}): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error("WebSocket is not connected");
        }
    }
}

export default BaseWebSocketService;