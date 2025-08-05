import React, { useState, useEffect } from 'react';
import { useConfig } from '../contexts/ConfigContext';
import APIService from '../services/api';
import Dropdown from './Dropdown';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import DocumentUpload from './DocumentUpload';
import PromptEditor from './PromptsEditor';
// import TrainingWizard from './HuddleInfo'; // Import the new component
import { DropdownOption, ChatMessage, UserType, ApplicationMode } from '../types';

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
  // const [showTrainingWizard, setShowTrainingWizard] = useState(false); // Add this state
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

  // ADD THIS: Handle PDF content generation
  // const handleGenerateTrainingContent = async (config: any) => {
  //   console.log('Generating PDF training content with config:', config);

  //   // Close the wizard
  //   setShowTrainingWizard(false);

  //   // Show loading state
  //   setIsLoading(true);
  //   setError('');

  //   try {
  //     // Add this to your API service or call your backend directly
  //     // Example API call:
  //     const response = await apiService.generateTrainingPDF({
  //       topic: config.topic,
  //       role: config.role,
  //       discipline: config.discipline,
  //       duration: config.duration,
  //       objectives: config.objectives,
  //       userType: state.userType,
  //       providerId: state.providerId
  //     });

  //     if (response.success) {
  //       // Handle successful PDF generation
  //       // You might want to show a download link or success message
  //       const successMessage: ChatMessage = {
  //         id: Date.now().toString(),
  //         content: `<strong>PDF Generated Successfully!</strong><br/>
  //         Topic: ${config.topic}<br/>
  //         Duration: ${config.duration}<br/>
  //         Audience: ${config.role} - ${config.discipline}<br/>
  //         <a href="${response.pdfUrl}" target="_blank" class="text-blue-500 underline">Download PDF</a>`,
  //         isUser: false,
  //         timestamp: new Date(),
  //       };
  //       setMessages(prev => [...prev, successMessage]);
  //     } else {
  //       setError('Failed to generate PDF. Please try again.');
  //     }
  //   } catch (error) {
  //     console.error('Error generating PDF:', error);
  //     setError('Failed to generate PDF. Please check your connection and try again.');
  //   } finally {
  //     setIsLoading(false);
  //   }
  // };

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

  const handleUserTypeChange = (newValue: UserType) => {
    setUserType(newValue);

    switch (newValue) {
      case "developer":
        console.log("Developer user type selected");
        break;
      case "educator":
        console.log("Educator (Agency Level) user type selected");
        break;
      case "regular":
        console.log("Regular User type selected");
        break;
      default:
        console.log(`Unknown user type: ${newValue}`);
    }
  };

  const handleModeChange = (newValue: ApplicationMode) => {
    setMode(newValue);

    switch (newValue) {
      case "chatbot":
        console.log("Chatbot mode selected");
        break;
      case "quiz":
        console.log("Quiz generator mode selected");
        break;
      case "pdf":
        console.log("PDF generator mode selected");
        break;
      case "voice":
        console.log("Voiceover mode selected");
        break;
      default:
        console.log(`Unknown mode: ${newValue}`);
    }
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
                onChange={handleUserTypeChange}
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
                onChange={handleModeChange}
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
          <div className="chat-title">
            {state.mode === 'pdf' ? 'Huddle Generator' : 'RAG System Testing Interface'}
          </div>
          <div className="metric">
            <span>⚡</span>
            <span>{state.responseTime}s</span>
          </div>
        </div>

        {/* MODIFY THIS: Show different content based on mode */}
        {state.mode === 'pdf' ? (
          // Parent wrapper - assumes this is inside a component that spans full screen
          <div className="huddles">
            {/* Scrollable Main Content */}
            <div className='huddles-body flex flex-col min-h-screen' style={{ flex: 1, overflowY: 'auto' }}>

              <div className="huddle-inputs-1 mr-20">

                <div className='config-section'>
                  <div className="config-section-title">Learning Focus</div>
                  <div className="config-group">
                    <label htmlFor="huddleTopic" className="config-label">What specific skill or knowledge should learners gain?</label>
                    <input
                      type="text"
                      className="config-input"
                      id="learningFocus"
                      placeholder={'Clinical Assessment - Patient evaluation and monitoring skills'}
                      // value={state.providerId || "Clinical Assessment - Patient evaluation and monitoring skills"}
                    />
                  </div>
                </div>
                <div className='config-section'>
                  <div className="config-section-title">Specific Topic</div>
                  <div className="config-group">
                    <label htmlFor="huddleTopic" className="config-label">What is the main subject for this training?</label>
                    <input
                      type="text"
                      className="config-input"
                      id="editPromptDescription"
                      // value={state.providerId || "Comprehensive nursing assessment techniques"}
                      placeholder={"Comprehensive nursing assessment techniques"}
                    />
                  </div>
                </div>

                <div className='config-section'>
                  <div className="config-section-title">Expected Learning Outcomes</div>
                  <div className="form-group">
                    <label htmlFor="huddleTopic" className="config-label">After this training, staff should be able to:</label>
                    <textarea
                      className="config-input"
                      id="editPromptDescription"
                      // value={state.backendUrl ||``}
                      placeholder={
                        `- Patients recently discharged from hospital
- Patients with multiple risk factors
- Multiple comorbidities and ongoing management
- Initial assessment and care planning
- High fall risk, medication issues, etc.
- Communication, compliance, or support issues`}
                      style={{ height: '150px', resize: "none" }}
                    />
                  </div>
                </div>
              </div>

                        
              
            </div>
            {/* Sticky Footer */}
            <div className="main-footer border-t border-gray-300 bg-white sticky bottom-0">
              <div className=" bg-white bg-opacity-20 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-red-400 h-full rounded-full transition-all duration-300"
                  style={{ width: `70%` }}
                />
              </div>
              <div className="flex justify-center items-center space-x-10 mt-3">
                <button className="px-5 py-3 rounded-lg text-sm font-semibold transition-colors">
                  Previous
                </button>

                <div className="text-xs text-gray-600">
                  Step {1} of {4}
                </div>

                <button className="px-5 py-3 rounded-lg text-sm font-semibold transition-colors">
                  Next Step
                </button>
              </div>
            </div>
          </div>


        ) : (
          <>
            <ChatMessages messages={messages} error={error} />
            <ChatInput
              onSendMessage={handleSendMessage}
              onClearChat={handleClearChat}
              disabled={state.isStreaming || isLoading}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;