import React, { useState, useEffect } from 'react';
import { useConfig } from '../contexts/ConfigContext';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import DocumentUpload from './DocumentUpload';
import { DropdownOption } from '../types';

const userTypeOptions: DropdownOption[] = [
  { value: 'developer', label: 'Developer' },
  { value: 'educator', label: 'Educator (Agency Level)' },
  { value: 'regular', label: 'Regular User', active: true },
];

const modeOptions: DropdownOption[] = [
  { value: 'chatbot', label: 'Chatbot', active: true },
  { value: 'quiz', label: 'Quiz Generator' },
  { value: 'pdf', label: 'PDF Generator' },
  { value: 'voice', label: 'Voiceover' },
];

const ChatInterface: React.FC = () => {
  const { state, setUserType, setMode, setBackendUrl, setProviderId, setStreaming, updateResponseTime } = useConfig();
  const [showDocumentUpload, setShowDocumentUpload] = useState(false);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [apiService] = useState(() => new APIService(state.backendUrl));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Prompt editor state
  const [selectedPromptType, setSelectedPromptType] = useState('main');
  const [selectedPrompt, setSelectedPrompt] = useState<any>(null);
  const [promptContent, setPromptContent] = useState('');
  const [promptName, setPromptName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    apiService.setBaseUrl(state.backendUrl);
  }, [state.backendUrl, apiService]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || state.isStreaming) return;

    const startTime = Date.now();
    setStreaming(true);
    setIsLoading(true);
    setError('');

    try {
      await apiService.sendStreamingMessage(
        message,
        (fullContent, newChunk) => {
          // Handle streaming response
          console.log('Streaming chunk:', newChunk);
        },
        (error) => {
          console.error('Streaming error:', error);
          setError('Streaming error occurred. Please try again.');
        },
        {
          userType: state.userType,
          mode: state.mode,
          providerId: state.providerId,
        }
      );

      const endTime = Date.now();
      updateResponseTime(endTime - startTime);
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message. Please check your connection and try again.');
    } finally {
      setStreaming(false);
      setIsLoading(false);
    }
  };

  const handleClearChat = async () => {
    setIsLoading(true);
    setError('');

    try {
      const result = await apiService.clearSession();
      if (result.success) {
        console.log('Chat cleared successfully');
      } else {
        console.error('Failed to clear chat:', result.error);
        setError('Failed to clear chat. Please try again.');
      }
    } catch (error) {
      console.error('Error clearing chat:', error);
      setError('Failed to clear chat. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePrompt = () => {
    // Save prompt logic here
    console.log('Saving prompt:', { promptName, promptContent, selectedPromptType });
  };

  const handleCreateNewPrompt = () => {
    setShowCreateForm(true);
    setSelectedPrompt(null);
    setPromptName('');
    setPromptContent('');
  };

  return (
    <div className="app-container">
      {/* Main Sidebar */}
      {!showDocumentUpload && !showPromptEditor && (
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-title">Configuration</div>
            <div className="sidebar-subtitle">Backend & Testing Settings</div>
          </div>

          <div className="sidebar-content">
            <div className="config-section">
              <div className="config-section-title">User Type</div>
              <div className="config-group">
                <p className="config-label">Select User Type</p>
                <Dropdown
                  options={userTypeOptions}
                  value={state.userType}
                  onChange={setUserType}
                />
              </div>
            </div>

            <div className="config-section">
              <div className="config-section-title">Application Mode</div>
              <div className="config-group">
                <p className="config-label">Select Mode</p>
                <Dropdown
                  options={modeOptions}
                  value={state.mode}
                  onChange={setMode}
                />
              </div>
            </div>

            <div className="config-section">
              <div className="config-section-title">Backend Settings</div>
              <div className="config-group">
                <label className="config-label" htmlFor="backendUrl">
                  Backend URL
                </label>
                <input
                  type="text"
                  className="config-input"
                  id="backendUrl"
                  placeholder="Enter backend URL"
                  value={state.backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                />
              </div>

              <div className="config-group">
                <label className="config-label" htmlFor="provId">
                  Provider ID
                </label>
                <input
                  type="text"
                  className="config-input"
                  id="provId"
                  placeholder="Enter provider ID"
                  value={state.providerId}
                  onChange={(e) => setProviderId(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="sidebar-footer">
            <div className="fixed-buttons">
              <button
                className="btn btn-primary"
                onClick={() => setShowPromptEditor(true)}
                title="Open prompt editor"
              >
                Prompts
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowDocumentUpload(true)}
                title="Upload documents"
              >
                Documents
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Upload Sidebar */}
      {showDocumentUpload && (
        <DocumentUpload
          onBack={() => setShowDocumentUpload(false)}
          apiService={apiService}
        />
      )}

      {/* Prompt Editor Sidebar */}
      {showPromptEditor && (
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-title">Prompt Editor</div>
            <div className="sidebar-subtitle">Manage your prompt templates</div>
          </div>

          <div className="sidebar-content">
            <div className="config-section">
              <div className="config-section-title">Prompt Type</div>
              <div className="config-group">
                <p className="config-label">Select Prompt Type</p>
                <Dropdown
                  options={[
                    { value: 'main', label: 'Main Prompts', active: true },
                    { value: 'use-case', label: 'Use Case Prompts' },
                    { value: 'role-based', label: 'Role Based Prompts' },
                    { value: 'discipline-based', label: 'Discipline Based Prompts' },
                  ]}
                  value={selectedPromptType}
                  onChange={setSelectedPromptType}
                />
              </div>
            </div>

            <div className="scrollable-content">
              <div className="prompts-list">
                <div className="text-center py-8 text-gray-500">No prompts found</div>
              </div>
            </div>
          </div>

          <div className="sidebar-footer">
            <div className="fixed-buttons">
              <button
                className="btn btn-primary"
                onClick={handleCreateNewPrompt}
              >
                Add New
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowPromptEditor(false)}
              >
                Back
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chat Container - Only show when not in prompt editor */}
      {!showPromptEditor && (
        <div className="chat-container">
          <div className="chat-header">
            <div className="chat-title">RAG System Testing Interface</div>
            <div className="metric">
              <span>⚡</span>
              <span>{state.responseTime}ms</span>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <ChatMessages />

          <ChatInput
            onSendMessage={handleSendMessage}
            onClearChat={handleClearChat}
            disabled={state.isStreaming || isLoading}
          />
        </div>
      )}

      {/* Prompt Editor Container - Show when prompt editor is open */}
      {showPromptEditor && (
        <div className="chat-container">
          <div className="chat-header">
            <div className="chat-title">
              {selectedPrompt ? selectedPrompt.name : 'New Prompt'}
            </div>
            <div className="metric">
              <button
                className="btn-single"
                onClick={handleSavePrompt}
                disabled={!promptName.trim() || !promptContent.trim()}
              >
                Save Changes
              </button>
            </div>
          </div>

          <div className="editor-container">
            {showCreateForm ? (
              <div className="space-y-4">
                <div className="config-section">
                  <div className="config-section-title">Prompt Details</div>
                  <div className="config-group">
                    <label className="config-label" htmlFor="promptName">
                      Prompt Name
                    </label>
                    <input
                      type="text"
                      className="config-input"
                      id="promptName"
                      placeholder="Enter prompt name"
                      value={promptName}
                      onChange={(e) => setPromptName(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            ) : null}

            <div className="space-y-4">
              <div>
                <label className="config-label">Prompt Content</label>
                <textarea
                  className="config-input min-h-[440px] resize-none"
                  value={promptContent}
                  onChange={(e) => setPromptContent(e.target.value)}
                  placeholder="Enter your prompt content here..."
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface; 