import { APIResponse } from '../types';

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8002') {
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

  async sendStreamingMessage(
    message: string,
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: any) => void,
    config: { userType?: string; mode?: string; providerId?: string } = {}
  ): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          user_type: config.userType || 'regular',
          mode: config.mode || 'chatbot',
          provider_id: config.providerId || '',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body available');
      }

      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;
        onChunk(fullContent, chunk);
      }
    } catch (error) {
      onError(error);
    }
  }

  async clearSession(): Promise<APIResponse> {
    return this.makeRequest('/clear-session', {
      method: 'POST',
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