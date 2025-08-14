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
      learningLevel?: string;
      numHuddles?: number;
      providerId?: string;
    },
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: string) => void
  ): Promise<string> {
    try {
      const requestBody = {
        learningFocus: config.learningFocus,
        topic: config.topic,
        clinicalContext: config.clinicalContext,
        expectedOutcomes: config.expectedOutcomes,
        role: config.role,
        roleValue: config.roleValue,
        discipline: config.discipline,
        disciplineValue: config.disciplineValue,
        duration: config.duration,
        learningLevel: config.learningLevel,
        numHuddles: config.numHuddles,
        providerId: config.providerId,
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

  async sendHuddlePlan(
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
      learningLevel?: string;
      numHuddles?: number;
      providerId?: string;
    },
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: string) => void
  ): Promise<string> {
    try {
      const requestBody = {
        learningFocus: config.learningFocus,
        topic: config.topic,
        clinicalContext: config.clinicalContext,
        expectedOutcomes: config.expectedOutcomes,
        role: config.role,
        roleValue: config.roleValue,
        discipline: config.discipline,
        disciplineValue: config.disciplineValue,
        duration: config.duration,
        learningLevel: config.learningLevel,
        numHuddles: config.numHuddles,
        providerId: config.providerId,
      };

      const response = await fetch(`${this.baseUrl}/huddles/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(text || 'Unexpected non-JSON response');
      }

      let data: any;
      try {
        data = await response.json();
      } catch (e) {
        throw new Error(e instanceof Error ? e.message : 'Invalid JSON in response');
      }

      const fullContent = JSON.stringify(data?.plan ?? data);
      onChunk(fullContent, fullContent);
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

  async generateVoiceover(payload: {
    huddleHtml: string;
    tone?: string;
    paceWpm?: number;
  }): Promise<APIResponse> {
    return this.makeRequest('/huddles/voiceover', {
      method: 'POST',
      body: JSON.stringify(payload),
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

  async getPrompts(tableName: string, skip = 0, limit = 100): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/?skip=${skip}&limit=${limit}`);
  }

  async getActivePrompt(tableName: string, name: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/active/${encodeURIComponent(name)}`);
  }

  async createPrompt(
    tableName: string,
    prompt: {
      name: string;
      version: string;
      description?: string;
      prompt: string;
    }
  ): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/`, {
      method: 'POST',
      body: JSON.stringify(prompt),
    });
  }

  async updatePrompt(
    tableName: string,
    name: string,
    version: string,
    promptUpdate: { prompt?: string; description?: string }
  ): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, {
      method: 'PUT',
      body: JSON.stringify(promptUpdate),
    });
  }

  async deletePrompt(tableName: string, name: string, version: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, {
      method: 'DELETE',
    });
  }

  async activatePrompt(tableName: string, name: string, version: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${tableName}/activate`, {
      method: 'POST',
      body: JSON.stringify({ name, version }),
    });
  }
}

export default APIService;