export interface ConfigSettings {
  userType: string;
  mode: string;
  backendUrl: string;
  providerId: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

export interface DocumentUploadConfig {
  indexType: 'global' | 'provider';
  globalCategory?: 'accreditations' | 'federal' | 'state';
  globalAccreditation?: 'tjc' | 'achc' | 'chap';
  globalFederal?: 'cms' | 'regulations';
  globalState?: string;
  providerCategory?: 'accreditations' | 'clinical' | 'hr';
}

export interface PromptTemplate {
  id: string;
  name: string;
  version: string;
  status: 'active' | 'inactive';
  description: string;
  content: string;
  type: 'main' | 'use-case' | 'role-based' | 'discipline-based';
}

export interface DropdownOption {
  value: string;
  label: string;
  active?: boolean;
}

export interface APIResponse {
  success: boolean;
  message?: string;
  data?: any;
  error?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface FileInfo {
  name: string;
  size: number;
  type: string;
  lastModified: number;
}

export type UserType = 'developer' | 'educator' | 'regular';
export type ApplicationMode = 'chatbot' | 'quiz' | 'pdf' | 'voice' | 'planner';
export type IndexType = 'global' | 'provider';
export type GlobalCategory = 'accreditations' | 'federal' | 'state';
export type ProviderCategory = 'accreditations' | 'clinical' | 'hr'; 