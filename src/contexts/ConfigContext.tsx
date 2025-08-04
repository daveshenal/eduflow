import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { ConfigSettings, UserType, ApplicationMode } from '../types';

interface ConfigState {
  userType: UserType;
  mode: ApplicationMode;
  backendUrl: string;
  providerId: string;
  isStreaming: boolean;
  responseTime: number;
}

type ConfigAction =
  | { type: 'SET_USER_TYPE'; payload: UserType }
  | { type: 'SET_MODE'; payload: ApplicationMode }
  | { type: 'SET_BACKEND_URL'; payload: string }
  | { type: 'SET_PROVIDER_ID'; payload: string }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'UPDATE_RESPONSE_TIME'; payload: number }
  | { type: 'LOAD_SETTINGS'; payload: ConfigSettings };

const initialState: ConfigState = {
  userType: 'regular',
  mode: 'chatbot',
  backendUrl: 'http://localhost:8000',
  providerId: '',
  isStreaming: false,
  responseTime: 0,
};

const configReducer = (state: ConfigState, action: ConfigAction): ConfigState => {
  switch (action.type) {
    case 'SET_USER_TYPE':
      return { ...state, userType: action.payload };
    case 'SET_MODE':
      return { ...state, mode: action.payload };
    case 'SET_BACKEND_URL':
      return { ...state, backendUrl: action.payload };
    case 'SET_PROVIDER_ID':
      return { ...state, providerId: action.payload };
    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload };
    case 'UPDATE_RESPONSE_TIME':
      return { ...state, responseTime: action.payload };
    case 'LOAD_SETTINGS':
      return { 
        ...state, 
        userType: action.payload.userType as UserType,
        mode: action.payload.mode as ApplicationMode,
        backendUrl: action.payload.backendUrl,
        providerId: action.payload.providerId,
      };
    default:
      return state;
  }
};

interface ConfigContextType {
  state: ConfigState;
  setUserType: (userType: UserType) => void;
  setMode: (mode: ApplicationMode) => void;
  setBackendUrl: (url: string) => void;
  setProviderId: (id: string) => void;
  setStreaming: (streaming: boolean) => void;
  updateResponseTime: (time: number) => void;
  loadSettings: (settings: ConfigSettings) => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export const useConfig = () => {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
};

interface ConfigProviderProps {
  children: ReactNode;
}

export const ConfigProvider: React.FC<ConfigProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(configReducer, initialState);

  const setUserType = (userType: UserType) => {
    dispatch({ type: 'SET_USER_TYPE', payload: userType });
  };

  const setMode = (mode: ApplicationMode) => {
    dispatch({ type: 'SET_MODE', payload: mode });
  };

  const setBackendUrl = (url: string) => {
    dispatch({ type: 'SET_BACKEND_URL', payload: url });
  };

  const setProviderId = (id: string) => {
    dispatch({ type: 'SET_PROVIDER_ID', payload: id });
  };

  const setStreaming = (streaming: boolean) => {
    dispatch({ type: 'SET_STREAMING', payload: streaming });
  };

  const updateResponseTime = (time: number) => {
    dispatch({ type: 'UPDATE_RESPONSE_TIME', payload: time });
  };

  const loadSettings = (settings: ConfigSettings) => {
    dispatch({ type: 'LOAD_SETTINGS', payload: settings });
  };

  const value: ConfigContextType = {
    state,
    setUserType,
    setMode,
    setBackendUrl,
    setProviderId,
    setStreaming,
    updateResponseTime,
    loadSettings,
  };

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}; 