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
  isHuddlePlanMode?: boolean;
}

const stripCodeFences = (content: string): string => {
  const trimmed = content.trim();
  if (trimmed.startsWith('```')) {
    const withoutStart = trimmed.replace(/^```(?:json)?\s*/i, '');
    const withoutEnd = withoutStart.replace(/\s*```$/i, '');
    return withoutEnd.trim();
  }
  return trimmed;
};

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages = [], error, isHuddlePlanMode = false }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const renderHuddlePlan = (rawContent: string) => {
    const stripped = stripCodeFences(rawContent);
    try {
      const data = JSON.parse(stripped);
      const meta = data?.curriculum_metadata || {};
      const huddles = Array.isArray(data?.huddles) ? data.huddles : [];

      return (
        <div className="huddle-plan">
          {meta.title ? <h2>{meta.title}</h2> : null}
          <div className="huddle-meta">
            {meta.target_role ? <p><strong>Role:</strong> {meta.target_role}</p> : null}
            {meta.discipline ? <p><strong>Discipline:</strong> {meta.discipline}</p> : null}
            {meta.total_duration ? <p><strong>Total Duration:</strong> {meta.total_duration}</p> : null}
            {meta.key_terminology && typeof meta.key_terminology === 'object' ? (
              <div>
                <p><strong>Key Terminology</strong></p>
                <ul>
                  {Object.entries(meta.key_terminology).map(([term, def]) => (
                    <li key={term}><strong>{term}:</strong> {String(def)}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          {huddles.length > 0 ? (
            <div className="huddles-list">
              {huddles.map((h: any) => (
                <div className="huddle-item" key={h.id || h.title}>
                  <h3>{`Huddle ${h.id ?? ''}${h.title ? `: ${h.title}` : ''}${h.type ? ` (${h.type})` : ''}`}</h3>
                  {h.main_focus ? <p><strong>Main Focus:</strong> {h.main_focus}</p> : null}
                  {Array.isArray(h.key_concepts) && h.key_concepts.length ? (
                    <div>
                      <p><strong>Key Concepts</strong></p>
                      <ul>
                        {h.key_concepts.map((c: any, i: number) => (
                          <li key={i}>{String(c)}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {h.clinical_scenario ? <p><strong>Clinical Scenario:</strong> {h.clinical_scenario}</p> : null}
                  {h.learning_outcome ? <p><strong>Learning Outcome:</strong> {h.learning_outcome}</p> : null}
                  {h.retrieval_query ? <p><strong>Retrieval Query:</strong> {h.retrieval_query}</p> : null}
                  {h.builds_on ? <p><strong>Builds On:</strong> {h.builds_on}</p> : null}
                  {h.sets_up ? <p><strong>Sets Up:</strong> {h.sets_up}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      );
    } catch {
      return (
        <div style={{ whiteSpace: 'pre-wrap' }}>{stripped}</div>
      );
    }
  };

  const renderMessageContent = (content: string, isUser: boolean) => {
    if (!content && !isUser) {
      return <TypingIndicator />;
    }

    if (isUser) {
      return content;
    } else {
      if (isHuddlePlanMode) {
        const stripped = stripCodeFences(content);
        const looksLikeJson = /^[\s\n]*[\[{]/.test(stripped);
        if (looksLikeJson) {
          return renderHuddlePlan(content);
        }
      }
      return (
        <div
          dangerouslySetInnerHTML={{ __html: content }}
          style={{ whiteSpace: 'normal', margin: 0 }}
        />
      );
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