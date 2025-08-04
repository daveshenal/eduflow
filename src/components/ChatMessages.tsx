import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../types';

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

  // Function to render message content as HTML if it contains HTML tags
  const renderMessageContent = (content: string) => {
    // Check if content contains HTML tags
    const hasHTMLTags = /<[^>]*>/g.test(content);
    
    if (hasHTMLTags) {
      // Render as HTML (be careful with this in production - consider sanitizing)
      return <div dangerouslySetInnerHTML={{ __html: content }} />;
    } else {
      // Render as plain text
      return <div>{content}</div>;
    }
  };

  return (
    <div className="chat-messages">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.isUser ? 'user' : 'assistant'}`}
        >
          <div className="message-content">
            {renderMessageContent(message.content)}
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