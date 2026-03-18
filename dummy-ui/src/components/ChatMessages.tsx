import React, { useEffect, useRef, useState } from 'react';
import { ChatMessage } from '../types';

const TypingIndicator: React.FC = () => (
  <div className="typing-indicator">
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
  </div>
);

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onClearChat: () => void;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onClearChat,
  disabled = false,
}) => {
  const [message, setMessage] = useState('');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isTyping, setIsTyping] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    onClearChat();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    setIsTyping(e.target.value.length > 0);
  };

  // Auto-resize textarea with improved handling
  useEffect(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 8 * 16; // 8rem in pixels
      textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [message]);

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <button
          className="clear-button"
          onClick={handleClear}
          disabled={disabled}
          title="Clear chat history"
        >
          Clear
        </button>
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="Type your message here..."
          value={message}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          rows={1}
          title="Type your message and press Enter to send"
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!message.trim() || disabled}
          title={message.trim() ? 'Send message' : 'Type a message to send'}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22,2 15,22 11,13 2,9"></polygon>
          </svg>
        </button>
      </div>
    </div>
  );
};

interface ChatMessagesProps {
  messages?: ChatMessage[];
  error?: string;
  onSendMessage: (message: string) => void;
  onClearChat: () => void;
  disabled?: boolean;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages = [],
  error,
  onSendMessage,
  onClearChat,
  disabled = false,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const renderMessageContent = (content: string, isUser: boolean) => {
    if (!content && !isUser) {
      return <TypingIndicator />;
    }

    if (isUser) {
      return content;
    } else {
      return (
        <div
          dangerouslySetInnerHTML={{ __html: content }}
          style={{ whiteSpace: 'normal', margin: 0 }}
        />
      );
    }
  };

  return (
    <>
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
      <ChatInput
        onSendMessage={onSendMessage}
        onClearChat={onClearChat}
        disabled={disabled}
      />
    </>
  );
};

export default ChatMessages;