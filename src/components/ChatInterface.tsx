import React, { useState, useEffect} from 'react';
import { useConfig } from '../contexts/ConfigContext';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import DocumentUpload from './DocumentUpload';
import PromptEditor from './PromptsEditor';
import { DropdownOption, ChatMessage} from '../types';

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

// Main Chat Interface Component
const ChatInterface: React.FC = () => {
  const { state, setUserType, setMode, setBackendUrl, setProviderId, setStreaming, updateResponseTime } = useConfig();
  const [showDocumentUpload, setShowDocumentUpload] = useState(false);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [apiService] = useState(() => new APIService(state.backendUrl));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: `<strong>HOP AI</strong><br /> Hello! I'm ready to help you test your backend. 
      The interface is configured to connect to your streaming chat endpoint. Try sending me a message!`,      
      isUser: false,
      timestamp: new Date(),
    },
  ]);

  useEffect(() => {
    apiService.setBaseUrl(state.backendUrl);
  }, [state.backendUrl, apiService]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || state.isStreaming) return;

    const startTime = Date.now();
    setStreaming(true);
    setIsLoading(true);
    setError('');

    // Add user message to chat
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      isUser: true,
      timestamp: new Date(),
    };

    // Add assistant message placeholder for streaming
    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      content: '',
      isUser: false,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);

    try {
      await apiService.sendStreamingMessage(
        message,
        (fullContent, newChunk) => {
          // Update the assistant message with the streaming content
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (!lastMessage.isUser) {
              lastMessage.content = fullContent;
            }
            return newMessages;
          });
        },
        (error) => {
          console.error('Streaming error:', error);
          setError('Streaming error occurred. Please try again.');
          // Remove the empty assistant message on error
          setMessages(prev => prev.slice(0, -1));
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
      // Remove the empty assistant message on error
      setMessages(prev => prev.slice(0, -1));
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
        // Reset messages to initial state
        setMessages([
          {
            id: '1',
            content: `<strong>HOP AI</strong><br /> Hello! I'm ready to help you test your backend. 
            The interface is configured to connect to your streaming chat endpoint. Try sending me a message!`,
            isUser: false,
            timestamp: new Date(),
          },
        ]);
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

  // Show prompt editor
  if (showPromptEditor) {
    return <PromptEditor onBack={() => setShowPromptEditor(false)} />;
  }

  // Show document upload
  if (showDocumentUpload) {
    return (
      <div className="app-container">
        <DocumentUpload
          onBack={() => setShowDocumentUpload(false)}
          apiService={apiService}
        />
        <div className="chat-container">
          <div className="chat-header">
            <div className="chat-title">Document Upload</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Main Sidebar */}
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

      {/* Chat Container */}
      <div className="chat-container">
        <div className="chat-header">
          <div className="chat-title">RAG System Testing Interface</div>
          <div className="metric">
            <span>⚡</span>
            <span>{state.responseTime}ms</span>
          </div>
        </div>

        <ChatMessages messages={messages} error={error} />

        <ChatInput
          onSendMessage={handleSendMessage}
          onClearChat={handleClearChat}
          disabled={state.isStreaming || isLoading}
        />
      </div>
    </div>
  );
};

export default ChatInterface;