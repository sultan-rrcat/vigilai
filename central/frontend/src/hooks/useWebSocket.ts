import { useState, useEffect, useRef } from 'react';

interface WebSocketMessage {
  type: 'new_incident' | 'incident_update' | 'camera_update' | 'heartbeat';
  data: any;
}

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket Connected');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket Disconnected. Reconnecting in 3s...');
        // Simple exponential backoff or static timeout for reconnection
        setTimeout(connect, 3000);
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  return { isConnected, lastMessage };
}