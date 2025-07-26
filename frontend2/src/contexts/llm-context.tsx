import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { getApiUrl } from '@/lib/utils';

export interface LLMConfig {
  provider: 'ollama' | 'openai' | 'claude' | 'gemini';
  apiKey?: string;
  url?: string;
  model?: string;
  organizationId?: string;
  deploymentName?: string;
}

export interface SessionInfo {
  sessionId: string;
  expiresAt: string;
  createdAt: string;
}

interface LLMContextType {
  llmConfig: LLMConfig | null;
  sessionInfo: SessionInfo | null;
  setLLMConfig: (config: LLMConfig) => Promise<string>; // Returns session ID
  clearSession: () => void;
  isConfigured: boolean;
  isSessionValid: boolean;
}

const LLMContext = createContext<LLMContextType | undefined>(undefined);

interface LLMProviderProps {
  children: ReactNode;
}

export const LLMProvider: React.FC<LLMProviderProps> = ({ children }) => {
  const [llmConfig, setLLMConfigState] = useState<LLMConfig | null>(() => {
    // Try to load from localStorage on initialization
    const saved = localStorage.getItem('llm-config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [sessionInfo, setSessionInfoState] = useState<SessionInfo | null>(() => {
    // Try to load session from localStorage
    const saved = localStorage.getItem('resume-ats-session');
    if (saved) {
      try {
        const session = JSON.parse(saved);
        // Check if session is expired
        if (new Date(session.expiresAt) > new Date()) {
          return session;
        } else {
          localStorage.removeItem('resume-ats-session');
        }
      } catch {
        localStorage.removeItem('resume-ats-session');
      }
    }
    return null;
  });

  // Validate session on mount and periodically
  useEffect(() => {
    if (sessionInfo?.sessionId) {
      validateSession(sessionInfo.sessionId);
    }
  }, [sessionInfo?.sessionId]);

  const validateSession = async (sessionId: string): Promise<boolean> => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/session/validate/${sessionId}`);
      const result = await response.json();

      if (!result.valid) {
        clearSession();
        return false;
      }
      return true;
    } catch (error) {
      console.error('Session validation failed:', error);
      clearSession();
      return false;
    }
  };

  // Helper function to generate device ID
  const getDeviceId = (): string => {
    let deviceId = localStorage.getItem('device-id');
    if (!deviceId) {
      deviceId = 'device_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('device-id', deviceId);
    }
    return deviceId;
  };

  const setLLMConfig = async (config: LLMConfig): Promise<string> => {
    try {
      const apiUrl = getApiUrl();

      // Step 1: Test LLM configuration
      const testResponse = await fetch(`${apiUrl}/session/test-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: config.provider,
          model_name: config.model || 'gpt-3.5-turbo',
          api_key: config.apiKey,
          base_url: config.url,
          temperature: 0.7,
          max_tokens: 1000,
          test_prompt: 'Hello, please respond to confirm the configuration is working.'
        }),
      });

      if (!testResponse.ok) {
        const error = await testResponse.json();
        throw new Error(error.detail || 'Configuration test failed');
      }

      // Step 2: Create session
      const sessionResponse = await fetch(`${apiUrl}/session/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          llm_config: {
            provider: config.provider,
            model_name: config.model || 'gpt-3.5-turbo',
            api_key: config.apiKey,
            base_url: config.url,
            temperature: 0.7,
            max_tokens: 1000,
            additional_params: {
              organizationId: config.organizationId,
              deploymentName: config.deploymentName,
            }
          },
          device_id: getDeviceId(),
          session_duration_hours: 24,
          metadata: {
            user_agent: navigator.userAgent,
            platform: 'web'
          }
        }),
      });

      if (!sessionResponse.ok) {
        const error = await sessionResponse.json();
        throw new Error(error.detail || 'Session creation failed');
      }

      const sessionResult = await sessionResponse.json();

      // Step 3: Store configuration and session
      const newSessionInfo: SessionInfo = {
        sessionId: sessionResult.session_id,
        expiresAt: sessionResult.expires_at,
        createdAt: new Date().toISOString(),
      };

      setLLMConfigState(config);
      setSessionInfoState(newSessionInfo);

      // Save to localStorage
      localStorage.setItem('llm-config', JSON.stringify(config));
      localStorage.setItem('resume-ats-session', JSON.stringify(newSessionInfo));

      return sessionResult.session_id;
    } catch (error) {
      console.error('Failed to configure LLM:', error);
      throw error;
    }
  };

  const clearSession = () => {
    setLLMConfigState(null);
    setSessionInfoState(null);
    localStorage.removeItem('llm-config');
    localStorage.removeItem('resume-ats-session');
  };

  const isConfigured = llmConfig !== null && sessionInfo !== null;
  const isSessionValid = sessionInfo !== null && new Date(sessionInfo.expiresAt) > new Date();

  return (
    <LLMContext.Provider value={{
      llmConfig,
      sessionInfo,
      setLLMConfig,
      clearSession,
      isConfigured,
      isSessionValid
    }}>
      {children}
    </LLMContext.Provider>
  );
};

export const useLLMConfig = () => {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error('useLLMConfig must be used within a LLMProvider');
  }
  return context;
};
