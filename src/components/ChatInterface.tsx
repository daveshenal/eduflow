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

const roleOptions: DropdownOption[] = [
  { value: "frontline-staff", label: "Frontline Staff", active: true },
  { value: "clinical-manager", label: "Clinical Manager" },
  { value: "educator", label: "Educator" },
  { value: "director", label: "Director" }
];

const disciplineOptions: DropdownOption[] = [
  { value: "rn", label: "RN - Registered Nurse", active: true },
  { value: "lpn", label: "LPN - Licensed Practical Nurse" },
  { value: "pt", label: "PT - Physical Therapist" },
  { value: "pta", label: "PTA - Physical Therapist Assistant" },
  { value: "ot", label: "OT - Occupational Therapist" },
  { value: "ota", label: "OTA - Occupational Therapist Assistant" },
  { value: "slp", label: "SLP - Speech-Language Pathologist" },
  { value: "msw", label: "MSW - Medical Social Worker" },
  { value: "hha", label: "HHA - Home Health Aide" }
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




  var currentStep = 1; // Assuming this is a constant for now, can be dynamic later

  // Duration Card Component
  type Duration = {
    value: string;
    label: string;
    description: string;
    wordCount: string;
    icon: string;
    recommended?: boolean;
  };

  type DurationCardProps = {
    duration: Duration;
    isSelected: boolean;
    onSelect: (duration: Duration) => void;
  };

  const DurationCard: React.FC<DurationCardProps> = ({ duration, isSelected, onSelect }) => (
    <div
      className={`p-4 border-2 rounded-xl cursor-pointer transition-all duration-200 bg-white relative hover:border-red-400 ${isSelected ? 'border-red-400 bg-red-50' : 'border-gray-200'
        }`}
      onClick={() => onSelect(duration)}
    >
      {duration.recommended && (
        <div className="absolute -top-2 right-3 bg-red-400 text-white text-xs font-semibold px-2 py-1 rounded">
          Recommended
        </div>
      )}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-xl">{duration.icon}</span>
        <span className="text-base font-semibold text-gray-900">{duration.label}</span>
      </div>
      <div className="text-xs text-gray-600 mb-1">{duration.description}</div>
      <div className="text-xs text-gray-600">{duration.wordCount}</div>
    </div>
  );

  const durations = [
    { value: "5-minutes", label: "5 Minutes", description: "Quick, focused learning", wordCount: "~625-750 words", icon: "⚡" },
    { value: "10-minutes", label: "10 Minutes", description: "Comprehensive coverage", wordCount: "~1,250-1,500 words", icon: "📚", recommended: true },
    { value: "15-minutes", label: "15 Minutes", description: "In-depth exploration", wordCount: "~1,875-2,250 words", icon: "🎓" }
  ];

  

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
          <div className="huddles">
            {/* Scrollable Main Content */}
            <div className='huddles-body flex flex-col min-h-screen' style={{ flex: 1, overflowY: 'auto' }}>
              {/* Step 1: Topic Inputs */}
              {currentStep === 1 && (
                <div className="huddle-inputs-1 mr-20">

                  <div className='config-section'>
                    <div className="huddle-section-title">Learning Focus</div>
                    <div className="config-group">
                      <p className="huddle-label">What specific skill or knowledge should learners gain?</p>
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
                    <div className="huddle-section-title">Specific Topic</div>
                    <div className="config-group">
                      <p className="huddle-label">What is the main subject for this training?</p>
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
                    <div className="huddle-section-title">Expected Learning Outcomes</div>
                    <div className="form-group">
                      <p className="huddle-label">After this training, staff should be able to:</p>
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
                        style={{ height: '120px', resize: "none" }}
                      />
                    </div>
                  </div>
                </div>)}

              {/* Step 2: Target Audiance and Time */}
              {currentStep === 2 && (
                <div className="huddle-inputs-1 mr-20">

                  <div className="config-section">
                    <div className="huddle-section-title">Define Your Audience - Who will be taking this training?</div>
                    <div className="form-row" style={{ display: 'flex', gap: '1rem' }}>
                      <div className="config-group" style={{ flex: 1, width: '30%' }}>
                        <p className="huddle-label">Select Role</p>
                        <Dropdown
                          options={roleOptions}
                          value={state.mode}
                          onChange={handleModeChange}
                        />
                      </div>
                      <div className="config-group" style={{ flex: 1, width: '30%' }}>
                        <p className="huddle-label">Select Discipline</p>
                        <Dropdown
                          options={disciplineOptions}
                          value={state.mode}
                          onChange={handleModeChange}
                        />
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="huddle-section-title">Choose Training Duration</div>
                    <div className="huddle-label">How long should this training be?</div>

                    <div className="grid grid-cols-3 gap-3">
                      {durations.map(duration => (
                        <DurationCard
                          key={duration.value}
                          duration={duration}
                          isSelected={false} // Replace with your selection logic if needed
                          onSelect={() => { }} // Replace with your handler function if needed
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

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