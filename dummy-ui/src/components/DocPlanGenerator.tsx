import React, { useMemo, useState } from 'react';
import APIService from '../services/api';

interface DocPlanGeneratorProps {
  apiService: APIService;
  indexId: string;
}

function parsePrompts(value: string): string[] {
  return value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
}

const DocPlanGenerator: React.FC<DocPlanGeneratorProps> = ({ apiService, indexId }) => {
  const [jobId, setJobId] = useState(() => `baseline-${Date.now()}`);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [promptsText, setPromptsText] = useState('');
  const [duration, setDuration] = useState<'5' | '10'>('5');
  const [voice, setVoice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const prompts = useMemo(() => parsePrompts(promptsText), [promptsText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMessage(null);
    setError(null);

    const response = await apiService.startBaselineJob({
      jobId,
      callbackUrl,
      indexId,
      prompts,
      duration: Number(duration),
      voice,
    });

    if (response.success) {
      setStatusMessage('Baseline generation job started successfully.');
      setJobId(`baseline-${Date.now()}`);
    } else {
      setError(response.error || 'Failed to start baseline generation job.');
    }

    setIsSubmitting(false);
  };

  const promptsCountLabel = prompts.length === 1 ? '1 prompt' : `${prompts.length} prompts`;

  return (
    <div className="editor-container">
      <h2 className="huddle-section-title">Human-Guided Sequential RAG</h2>
      <p className="huddle-label">
        Provide a list of prompts. Each prompt becomes one document (retrieval query per doc).
      </p>

      <form onSubmit={handleSubmit} className="config-section" style={{ maxWidth: '920px' }}>
        <div className="config-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="config-group" style={{ flex: '1 1 280px' }}>
            <label className="config-label" htmlFor="baselineJobId">
              Job ID
            </label>
            <input
              id="baselineJobId"
              type="text"
              className="config-input"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            />
          </div>

          <div className="config-group" style={{ flex: '2 1 380px' }}>
            <label className="config-label" htmlFor="baselineCallbackUrl">
              Callback URL
            </label>
            <input
              id="baselineCallbackUrl"
              type="url"
              className="config-input"
              placeholder="https://your-app.com/api/baseline/callback"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="config-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="config-group" style={{ flex: '0 0 calc(25% - 0.75rem)', minWidth: '160px' }}>
            <label className="config-label" htmlFor="baselineDuration">
              Duration
            </label>
            <select
              id="baselineDuration"
              className="config-input"
              value={duration}
              onChange={(e) => setDuration(e.target.value as '5' | '10')}
              required
            >
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </div>

          <div className="config-group" style={{ flex: '1 1 calc(75% - 0.75rem)', minWidth: '260px' }}>
            <label className="config-label" htmlFor="baselineVoice">
              Voice
            </label>
            <input
              id="baselineVoice"
              type="text"
              className="config-input"
              placeholder="e.g. neutral, enthusiastic"
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="baselinePrompts">
            Prompts (one per line) — {promptsCountLabel}
          </label>
          <textarea
            id="baselinePrompts"
            className="config-input"
            placeholder={`Example:\nGrade 6 fractions lesson with examples\nPractice problems for fractions\nQuiz questions for fractions`}
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
            Start Baseline Generation
          </button>
        </div>

        {statusMessage && (
          <div className="success-message" style={{ marginTop: '1rem' }}>
            {statusMessage}
          </div>
        )}

        {error && (
          <div className="error-message" style={{ marginTop: '1rem' }}>
            {error}
          </div>
        )}
      </form>
    </div>
  );
};

export default DocPlanGenerator;

