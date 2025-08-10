import { APIResponse } from '../types';

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setBaseUrl(url: string) {
    this.baseUrl = url;
  }

  private async makeRequest(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  async sendChatMessage(
    config: {
      message: string;
      userType: string;
      providerId?: string;
    },
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: string) => void
  ): Promise<string> {
    try {
      const requestBody = {
        message: config.message,
        userType: config.userType,
        providerId: config.providerId,
      };

      const response = await fetch(`${this.baseUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;
        onChunk(fullContent, chunk);
      }

      return fullContent;
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      onError(errMsg);
      throw error;
    }
  }

  async sendHuddleStream(
    config: {
      learningFocus: string;
      topic: string;
      clinicalContext: string;
      expectedOutcomes: string;
      role: string;
      roleValue: string;
      discipline: string;
      disciplineValue: string;
      duration: string;
      providerId?: string;
    },
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: string) => void
  ): Promise<string> {
    try {
      const requestBody = {
        learning_focus: config.learningFocus,
        topic: config.topic,
        clinical_context: config.clinicalContext,
        expected_outcomes: config.expectedOutcomes,
        role: config.role,
        role_value: config.roleValue,
        discipline: config.discipline,
        discipline_value: config.disciplineValue,
        duration: config.duration,
        provider_id: config.providerId,
      };

      const response = await fetch(`${this.baseUrl}/huddles/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;
        onChunk(fullContent, chunk);
      }

      return fullContent;
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      onError(errMsg);
      throw error;
    }
  }

  async clearSession(providerId?: string): Promise<APIResponse> {
    // Match the JS version's clear session endpoint with hardcoded fallback
    const providerIdToUse = providerId;
    const endpoint = `/clear-session/${providerIdToUse}`;

    return this.makeRequest(endpoint, {
      method: 'DELETE',
    });
  }

  async uploadDocuments(
    files: File[],
    config: {
      indexType: string;
      globalCategory?: string;
      globalAccreditation?: string;
      globalFederal?: string;
      globalState?: string;
      providerCategory?: string;
      providerId?: string;
    },
    onProgress?: (progress: { loaded: number; total: number; percentage: number }) => void
  ): Promise<APIResponse> {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append('files', file);
    });

    formData.append('index_type', config.indexType);
    if (config.globalCategory) formData.append('global_category', config.globalCategory);
    if (config.globalAccreditation) formData.append('global_accreditation', config.globalAccreditation);
    if (config.globalFederal) formData.append('global_federal', config.globalFederal);
    if (config.globalState) formData.append('global_state', config.globalState);
    if (config.providerCategory) formData.append('provider_category', config.providerCategory);
    if (config.providerId) formData.append('provider_id', config.providerId);

    try {
      const xhr = new XMLHttpRequest();

      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable && onProgress) {
            const progress = {
              loaded: event.loaded,
              total: event.total,
              percentage: (event.loaded / event.total) * 100,
            };
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              resolve({ success: true, data });
            } catch {
              resolve({ success: true, data: xhr.responseText });
            }
          } else {
            resolve({
              success: false,
              error: `HTTP ${xhr.status}: ${xhr.statusText}`,
            });
          }
        });

        xhr.addEventListener('error', () => {
          resolve({
            success: false,
            error: 'Network error occurred',
          });
        });

        xhr.open('POST', `${this.baseUrl}/upload-documents`);
        xhr.send(formData);
      });
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed',
      };
    }
  }

  async getPrompts(type?: string): Promise<APIResponse> {
    const endpoint = type ? `/prompts?type=${type}` : '/prompts';
    return this.makeRequest(endpoint);
  }

  async getPrompt(id: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${id}`);
  }

  async createPrompt(prompt: {
    name: string;
    version: string;
    status: string;
    description: string;
    content: string;
    type: string;
  }): Promise<APIResponse> {
    return this.makeRequest('/prompts', {
      method: 'POST',
      body: JSON.stringify(prompt),
    });
  }

  async updatePrompt(id: string, prompt: any): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(prompt),
    });
  }

  async deletePrompt(id: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${id}`, {
      method: 'DELETE',
    });
  }
}

export default APIService;