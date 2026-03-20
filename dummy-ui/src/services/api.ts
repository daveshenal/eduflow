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
      // kept for compatibility, currently unused by backend
      userType: string;
      // used as index_id for the RAG backend
      indexId: string;
    },
    onChunk: (fullContent: string, newChunk: string) => void,
    onError: (error: string) => void
  ): Promise<string> {
    try {
      const requestBody = {
        index_id: config.indexId,
        message: config.message,
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

  async uploadDocuments(
    files: File[],
    indexId: string,
    onProgress?: (progress: { loaded: number; total: number; percentage: number }) => void
  ): Promise<APIResponse> {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append('files', file);
    });

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

        xhr.open('POST', `${this.baseUrl}/knowledgebase/${encodeURIComponent(indexId)}/upload`);
        xhr.send(formData);
      });
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Upload failed',
      };
    }
  }

  async getPrompts(skip = 0, limit = 100): Promise<APIResponse> {
    return this.makeRequest(`/prompts/list?skip=${skip}&limit=${limit}`);
  }

  async getActivePrompt(name: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/active/${encodeURIComponent(name)}`);
  }

  async createPrompt(
    prompt: {
      name: string;
      version: string;
      description?: string;
      prompt: string;
    }
  ): Promise<APIResponse> {
    return this.makeRequest(`/prompts/new`, {
      method: 'POST',
      body: JSON.stringify(prompt),
    });
  }

  async updatePrompt(
    name: string,
    version: string,
    promptUpdate: { prompt?: string; description?: string }
  ): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, {
      method: 'PUT',
      body: JSON.stringify(promptUpdate),
    });
  }

  async deletePrompt(name: string, version: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, {
      method: 'DELETE',
    });
  }

  async activatePrompt(name: string, version: string): Promise<APIResponse> {
    return this.makeRequest(`/prompts/activate`, {
      method: 'POST',
      body: JSON.stringify({ name, version }),
    });
  }

  async getAllowedPromptNames(): Promise<APIResponse> {
    return this.makeRequest('/prompts/allowed-names');
  }

  async startEduflowJob(payload: {
    jobId: string;
    callbackUrl: string;
    indexId: string;
    learningFocus: string;
    topic: string;
    targetAudience: string;
    duration: number;
    numDocs: number;
    voice?: string;
  }): Promise<APIResponse> {
    const body: any = {
      job_id: payload.jobId,
      callback_url: payload.callbackUrl,
      index_id: payload.indexId,
      learning_focus: payload.learningFocus,
      topic: payload.topic,
      target_audience: payload.targetAudience,
      duration: payload.duration,
      num_docs: payload.numDocs,
    };

    if (payload.voice) {
      body.voice = payload.voice;
    }

    return this.makeRequest('/gen/start', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async startBaselineJob(payload: {
    jobId: string;
    callbackUrl: string;
    indexId: string;
    prompts: string[];
    duration: number;
  }): Promise<APIResponse> {
    const body = {
      job_id: payload.jobId,
      callback_url: payload.callbackUrl,
      index_id: payload.indexId,
      prompts: payload.prompts,
      duration: payload.duration,
    };

    return this.makeRequest('/gen/start-baseline', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async startMemoryJob(payload: {
    jobId: string;
    callbackUrl: string;
    indexId: string;
    prompts: string[];
    duration: number;
  }): Promise<APIResponse> {
    const body = {
      job_id: payload.jobId,
      callback_url: payload.callbackUrl,
      index_id: payload.indexId,
      prompts: payload.prompts,
      duration: payload.duration,
    };

    return this.makeRequest('/gen/start-memory', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async getBgJobStatus(jobId: string): Promise<APIResponse> {
    return this.makeRequest(`/bg_jobs/${encodeURIComponent(jobId)}`);
  }
}

export default APIService;