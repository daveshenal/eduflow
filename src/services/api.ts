import { APIResponse } from '../types';

class APIService {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
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
    onError: (error: string) => void,
    config: { userType?: string; mode?: string; providerId?: string } = {}
  ): Promise<string> {
    try {
      const requestBody = {
        message: message,
        provider_id: config.providerId || '595959', // Use hardcoded fallback
        mode: config.mode || 'chatbot',
      };

      // Debug logging
      console.log('Request URL:', `${this.baseUrl}/chat-stream`);
      console.log('Request body:', requestBody);
      console.log('Provider ID:', config.providerId || '595959');
      console.log('Mode:', config.mode);

      // Use the same endpoint as your working JS version
      const response = await fetch(`${this.baseUrl}/chat-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Match the request body structure from your working JS version
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        // Try to get the error message from the response
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.text();
          console.log('Server error response:', errorData);
          if (errorData) {
            errorMessage += ` - ${errorData}`;
          }
        } catch (e) {
          console.log('Could not parse error response');
        }
        throw new Error(errorMessage);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body available');
      }

      const decoder = new TextDecoder();
      let assistantContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data && !data.includes('[ERROR]')) {
              assistantContent += data;
              onChunk(assistantContent, data);
            } else if (data.includes('[ERROR]')) {
              onError(data);
            }
          }
        }
      }

      return assistantContent;
    } catch (error) {
      // Fix the error handling to avoid [object Object] logging
      const errorMessage = error instanceof Error ? error.message : String(error);
      onError(errorMessage);
      throw error;
    }
  }

  async clearSession(providerId?: string): Promise<APIResponse> {
    // Match the JS version's clear session endpoint with hardcoded fallback
    const providerIdToUse = providerId || '595959';
    const endpoint = `/clear-session/${providerIdToUse}`;
    
    return this.makeRequest(endpoint, {
      method: 'DELETE',
    });
  }

  async uploadFile(file: File, providerId?: string): Promise<Response> {
    const formData = new FormData();
    formData.append('file', file);
    // Use hardcoded fallback for provider_id
    formData.append('provider_id', providerId || '595959');

    const response = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response;
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