import React, { useEffect } from 'react';

export type ToastType = 'success' | 'error';

export interface ToastPayload {
  text: string;
  type: ToastType;
}

interface ToastMessageProps {
  message: ToastPayload | null;
  onClear: () => void;
  autoHideMs?: number;
}

const ToastMessage: React.FC<ToastMessageProps> = ({ message, onClear, autoHideMs = 3000 }) => {
  useEffect(() => {
    if (!message) return;
    const t = window.setTimeout(() => onClear(), autoHideMs);
    return () => window.clearTimeout(t);
  }, [message, onClear, autoHideMs]);

  if (!message) return null;

  return (
    <div className="toast-container">
      <div className={`toast toast-${message.type}`}>
        {message.text}
      </div>
    </div>
  );
};

export default ToastMessage;

