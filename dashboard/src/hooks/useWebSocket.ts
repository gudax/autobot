import { useEffect, useState, useCallback, useRef } from 'react';
import type { WebSocketMessage } from '@/types';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
}

export const useWebSocket = (channel: string = 'all', options: UseWebSocketOptions = {}) => {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnect = true,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<Event | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();

  const connect = useCallback(() => {
    try {
      // Disconnect existing connection first
      if (wsRef.current) {
        console.log('Closing existing WebSocket before reconnecting');
        disconnect();
      }

      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      const ws = new WebSocket(`${wsUrl}/ws/${channel}`);

      ws.onopen = () => {
        console.log(`WebSocket connected to channel: ${channel}`);
        setIsConnected(true);
        setError(null);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError(event);
        onError?.(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        setIsConnected(false);
        onDisconnect?.();

        // Clear reference if this is the current WebSocket
        if (wsRef.current === ws) {
          wsRef.current = null;
        }

        // Attempt to reconnect (only if not manually closed)
        if (reconnect && event.code !== 1000) {
          // Clear any existing reconnection timeout
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }

          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            // Check if we haven't already reconnected
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
              connect();
            }
          }, reconnectInterval);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
    }
  }, [channel, onMessage, onConnect, onDisconnect, onError, reconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }

    // Clean up WebSocket connection
    if (wsRef.current) {
      // Remove all event listeners to prevent memory leaks
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.onclose = null;

      // Close connection if still open or connecting
      try {
        if (
          wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING
        ) {
          wsRef.current.close();
        }
      } catch (error) {
        console.error('Error closing WebSocket:', error);
      }

      wsRef.current = null;
    }

    // Reset connection state
    setIsConnected(false);
    setError(null);
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const subscribe = useCallback((newChannel: string) => {
    sendMessage({
      type: 'subscribe',
      channel: newChannel,
    });
  }, [sendMessage]);

  const unsubscribe = useCallback((oldChannel: string) => {
    sendMessage({
      type: 'unsubscribe',
      channel: oldChannel,
    });
  }, [sendMessage]);

  useEffect(() => {
    // Initial connection
    connect();

    // Cleanup on unmount or when dependencies change
    return () => {
      disconnect();
    };
  }, [channel]); // Only reconnect when channel changes

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    subscribe,
    unsubscribe,
  };
};
