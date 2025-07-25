import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface LLMConfig {
  provider: 'ollama' | 'openai' | 'claude' | 'gemini';
  apiKey?: string;
  url?: string;
  model?: string;
  organizationId?: string;
  deploymentName?: string;
}

interface LLMContextType {
  llmConfig: LLMConfig | null;
  setLLMConfig: (config: LLMConfig) => void;
  isConfigured: boolean;
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

  const setLLMConfig = (config: LLMConfig) => {
    setLLMConfigState(config);
    // Save to localStorage
    localStorage.setItem('llm-config', JSON.stringify(config));
  };

  const isConfigured = llmConfig !== null;

  return (
    <LLMContext.Provider value={{ llmConfig, setLLMConfig, isConfigured }}>
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
