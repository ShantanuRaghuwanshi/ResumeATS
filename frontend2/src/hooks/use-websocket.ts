import { useEffect, useRef, useState, useCallback } from 'react';
import { useToast } from './use-toast';

export interface WebSocketMessage {
  type: string;
  data: any;
  session_id?: string;
  user_id?: string;
  timestamp: string;
}

export interface WebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  sendMessage: (message: any) => void;
  disconnect: () => void;
  reconnect: () => void;
  lastMessage: WebSocketMessage | null;
}

export function useWebSocket(
  url: string,
  options: WebSocketOptions = {}
): UseWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectAttempts = 3,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const { toast } = useToast();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        onDisconnect?.();

        // Attempt to reconnect if within retry limits
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else {
          toast({
            title: 'Connection Lost',
            description: 'Unable to maintain real-time connection. Please refresh the page.',
            variant: 'destructive',
          });
        }
      };

      ws.onerror = (error) => {
        setIsConnecting(false);
        onError?.(error);
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      setIsConnecting(false);
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [url, onMessage, onConnect, onDisconnect, onError, reconnectAttempts, reconnectInterval, toast]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    reconnectCountRef.current = reconnectAttempts; // Prevent reconnection
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
  }, [reconnectAttempts]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectCountRef.current = 0;
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    isConnected,
    isConnecting,
    sendMessage,
    disconnect,
    reconnect,
    lastMessage,
  };
}