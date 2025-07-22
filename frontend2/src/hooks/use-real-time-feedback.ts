import { useCallback, useEffect, useState } from 'react';
import { useWebSocket, WebSocketMessage } from './use-websocket';

export interface FeedbackData {
  session_id: string;
  section: string;
  character_count: number;
  word_count: number;
  readability_score: number;
  current_quality_score: number;
  ats_compatibility: number;
  grammar_issues: string[];
  style_suggestions: string[];
  keyword_suggestions: string[];
  timestamp: string;
}

export interface ProgressUpdate {
  operation: string;
  progress: number;
  status: string;
  details?: string;
}

export interface NotificationData {
  notification_type: string;
  title: string;
  message: string;
  data?: any;
}

export interface UseRealTimeFeedbackOptions {
  sessionId?: string;
  userId?: string;
  onFeedback?: (feedback: FeedbackData) => void;
  onProgress?: (progress: ProgressUpdate) => void;
  onNotification?: (notification: NotificationData) => void;
}

export interface UseRealTimeFeedbackReturn {
  isConnected: boolean;
  isConnecting: boolean;
  sendFeedbackRequest: (section: string, content: string, previousContent?: string) => void;
  setContext: (context: any) => void;
  lastFeedback: FeedbackData | null;
  lastProgress: ProgressUpdate | null;
  lastNotification: NotificationData | null;
  disconnect: () => void;
  reconnect: () => void;
}

export function useRealTimeFeedback(
  options: UseRealTimeFeedbackOptions = {}
): UseRealTimeFeedbackReturn {
  const { sessionId, userId, onFeedback, onProgress, onNotification } = options;
  
  const [lastFeedback, setLastFeedback] = useState<FeedbackData | null>(null);
  const [lastProgress, setLastProgress] = useState<ProgressUpdate | null>(null);
  const [lastNotification, setLastNotification] = useState<NotificationData | null>(null);

  // Construct WebSocket URL
  const wsUrl = `ws://localhost:8000/api/v1/ws/feedback${sessionId ? `?session_id=${sessionId}` : ''}${userId ? `${sessionId ? '&' : '?'}user_id=${userId}` : ''}`;

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'real_time_feedback':
        const feedbackData = message.data.feedback as FeedbackData;
        setLastFeedback(feedbackData);
        onFeedback?.(feedbackData);
        break;

      case 'progress_update':
        const progressData = message.data as ProgressUpdate;
        setLastProgress(progressData);
        onProgress?.(progressData);
        break;

      case 'notification':
        const notificationData = message.data as NotificationData;
        setLastNotification(notificationData);
        onNotification?.(notificationData);
        break;

      case 'connection_established':
        console.log('Real-time feedback connection established:', message.data);
        break;

      case 'error':
        console.error('WebSocket error:', message.data);
        break;

      default:
        console.log('Unhandled message type:', message.type, message.data);
    }
  }, [onFeedback, onProgress, onNotification]);

  const {
    isConnected,
    isConnecting,
    sendMessage,
    disconnect,
    reconnect,
  } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    onConnect: () => {
      console.log('Real-time feedback WebSocket connected');
      
      // Send initial context if available
      if (sessionId || userId) {
        sendMessage({
          type: 'set_context',
          context: {
            session_id: sessionId,
            user_id: userId,
          },
        });
      }
    },
    onDisconnect: () => {
      console.log('Real-time feedback WebSocket disconnected');
    },
    onError: (error) => {
      console.error('Real-time feedback WebSocket error:', error);
    },
  });

  const sendFeedbackRequest = useCallback((
    section: string,
    content: string,
    previousContent?: string
  ) => {
    sendMessage({
      type: 'request_feedback',
      section,
      content,
      previous_content: previousContent,
    });
  }, [sendMessage]);

  const setContext = useCallback((context: any) => {
    sendMessage({
      type: 'set_context',
      context,
    });
  }, [sendMessage]);

  return {
    isConnected,
    isConnecting,
    sendFeedbackRequest,
    setContext,
    lastFeedback,
    lastProgress,
    lastNotification,
    disconnect,
    reconnect,
  };
}