import React, { useMemo, useState } from 'react';
import APIService from '../services/api';
import ToastMessage, { ToastPayload } from './ToastMessage';

interface DocMemGeneratorProps {
  apiService: APIService;
  indexId: string;
}

function parsePrompts(value: string): string[] {
  return value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
}

const DocMemGenerator: React.FC<DocMemGeneratorProps> = ({ apiService, indexId }) => {
  const [jobId, setJobId] = useState(() => `memory-${Date.now()}`);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [promptsText, setPromptsText] = useState('');
  const [duration, setDuration] = useState<'5' | '10'>('5');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastPayload | null>(null);

  const prompts = useMemo(() => parsePrompts(promptsText), [promptsText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setToast(null);

    const response = await apiService.startMemoryJob({
      jobId,
      callbackUrl,
      indexId,
      prompts,
      duration: Number(duration),
    });

    if (response.success) {
      setToast({ type: 'success', text: 'Memory-based generation job started successfully.' });
      setJobId(`job-${Date.now()}`);
    } else {
      setToast({ type: 'error', text: response.error || 'Failed to start memory-based generation job.' });
    }

    setIsSubmitting(false);
  };

  const promptsCountLabel = prompts.length === 1 ? '1 prompt' : `${prompts.length} prompts`;

  return (
    <div className="editor-container">
      <ToastMessage message={toast} onClear={() => setToast(null)} />
      <h2 className="huddle-section-title">Memory-Augmented Sequential RAG</h2>
      <p className="huddle-label">
        Provide a list of prompts. Each prompt becomes one document, and a running summary is
        used as memory across the sequence.
      </p>

      <form onSubmit={handleSubmit} className="config-section" style={{ maxWidth: '920px' }}>
        <div className="config-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="config-group" style={{ flex: '1 1 280px' }}>
            <label className="config-label" htmlFor="memJobId">
              Job ID
            </label>
            <input
              id="memJobId"
              type="text"
              className="config-input"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            />
          </div>

          <div className="config-group" style={{ flex: '2 1 380px' }}>
            <label className="config-label" htmlFor="memCallbackUrl">
              Callback URL
            </label>
            <input
              id="memCallbackUrl"
              type="url"
              className="config-input"
              placeholder="https://your-app.com/api/memory/callback"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="config-group" style={{ width: '160px' }}>
          <label className="config-label" htmlFor="memDuration">
            Duration
          </label>
          <select
            id="memDuration"
            className="config-input"
            value={duration}
            onChange={(e) => setDuration(e.target.value as '5' | '10')}
            required
          >
            <option value="5">5</option>
            <option value="10">10</option>
          </select>
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="memPrompts">
            Prompts (one per line) — {promptsCountLabel}
          </label>
          <textarea
            id="memPrompts"
            className="config-input"
            placeholder={`Example:\nExplain photosynthesis for grade 7\nPractice questions on photosynthesis\nQuiz questions on photosynthesis`}
            value={promptsText}
            onChange={(e) => setPromptsText(e.target.value)}
            style={{ minHeight: '140px', resize: 'none' }}
            required
          />
        </div>

        <div className="btn-flex" style={{ marginTop: '1.25rem' }}>
          <button
            type="submit"
            className={`btn btn-primary${isSubmitting ? ' loading' : ''}`}
            disabled={isSubmitting || prompts.length === 0}
          >
            Start Memory Generation
          </button>
        </div>
      </form>
    </div>
  );
};

export default DocMemGenerator;

