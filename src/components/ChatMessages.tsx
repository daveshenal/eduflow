import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage } from '../types';

interface ChatMessagesProps {
  messages?: ChatMessage[];
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages = [] }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: "Hello! I'm ready to help you test your backend. The interface is configured to connect to your streaming chat endpoint. Try sending me a message!",
      isUser: false,
      timestamp: new Date(),
    },
  ]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [localMessages]);

  useEffect(() => {
    if (messages.length > 0) {
      setLocalMessages(messages);
    }
  }, [messages]);

  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-messages">
      {localMessages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.isUser ? 'user' : 'assistant'}`}
        >
          <div className="message-header">
            <strong>
              {message.isUser ? 'You' : 'HOP AI'}
            </strong>
            <span>
              {formatTime(message.timestamp)}
            </span>
          </div>
          <div className="message-content">
            {message.content}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages; 