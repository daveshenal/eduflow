import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../types';

const TypingIndicator: React.FC = () => (
  <div className="typing-indicator">
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
  </div>
);

interface ChatMessagesProps {
  messages?: ChatMessage[];
  error?: string;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages = [], error }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Function to render raw message content without any processing
  const renderMessageContent = (content: string, isUser: boolean) => {
    // Show typing indicator for empty assistant messages
    if (!content && !isUser) {
      return <TypingIndicator />;
    }
    
    // Always display content as raw text, preserving whitespace
    return <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{content}</pre>;
  };

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.isUser ? 'user' : 'assistant'}`}
        >
          <div className="message-content">
            {renderMessageContent(message.content, message.isUser)}
          </div>
        </div>
      ))}
      {error && (
        <div className="error-message message">
          Error: {error}
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;