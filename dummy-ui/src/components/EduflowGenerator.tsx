import React, { useState } from 'react';
import APIService from '../services/api';

interface EduflowGeneratorProps {
  apiService: APIService;
  indexId: string;
}

const EduflowGenerator: React.FC<EduflowGeneratorProps> = ({ apiService, indexId }) => {
  const [jobId, setJobId] = useState(() => `job-${Date.now()}`);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [learningFocus, setLearningFocus] = useState('');
  const [topic, setTopic] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [duration, setDuration] = useState<'5' | '10'>('10');
  const [numDocs, setNumDocs] = useState('3');
  const [voice, setVoice] = useState('neutral');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatusMessage(null);
    setError(null);

    const clampedNumDocs = Math.max(1, Math.min(8, Number(numDocs) || 1));

    const payload = {
      jobId,
      callbackUrl,
      indexId,
      learningFocus,
      topic,
      targetAudience,
      duration: Number(duration),
      numDocs: clampedNumDocs,
      voice,
    };

    const response = await apiService.startEduflowJob(payload);

    if (response.success) {
      setStatusMessage('EduFlow generation job started successfully.');
      // refresh job id for next run
      setJobId(`job-${Date.now()}`);
    } else {
      setError(response.error || 'Failed to start EduFlow generation job.');
    }

    setIsSubmitting(false);
  };

  return (
    <div className="editor-container">
      <h2 className="huddle-section-title">EduFlow Content Generation</h2>
      <p className="huddle-label">
        Configure the curriculum generation job and start the background process.
      </p>

      <form onSubmit={handleSubmit} className="config-section" style={{ maxWidth: '920px' }}>

        <div className="config-group">
          <label className="config-label" htmlFor="topic">
            Topic
          </label>
          <input
            id="topic"
            type="text"
            className="config-input"
            placeholder="e.g. Comprehensive nursing assessment techniques"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
          />
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="learningFocus">
            Learning Focus
          </label>
          <input
            id="learningFocus"
            type="text"
            className="config-input"
            placeholder="e.g. Skilled nursing assessment techniques, Patient evaluation and monitoring skills"
            value={learningFocus}
            onChange={(e) => setLearningFocus(e.target.value)}
            required
          />
        </div>

        <div className="config-group">
          <label className="config-label" htmlFor="targetAudience">
            Target Audience
          </label>
          <input
            id="targetAudience"
            type="text"
            className="config-input"
            placeholder="e.g. Home health registered nurses"
            value={targetAudience}
            onChange={(e) => setTargetAudience(e.target.value)}
            required
          />
        </div>

        <div className="config-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="config-group" style={{ flex: '0 0 calc(25% - 0.75rem)', minWidth: '160px' }}>
            <label className="config-label" htmlFor="duration">
              Duration (minutes per doc)
            </label>
            <select
              id="duration"
              className="config-input"
              value={duration}
              onChange={(e) => setDuration(e.target.value as '5' | '10')}
              required
            >
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </div>

          <div className="config-group" style={{ flex: '0 0 calc(25% - 0.75rem)', minWidth: '200px' }}>
            <label className="config-label" htmlFor="numDocs">
              Number of Docs (max 8)
            </label>
            <input
              id="numDocs"
              type="number"
              min={3}
              max={8}
              className="config-input"
              value={numDocs}
              onChange={(e) => setNumDocs(e.target.value)}
              required
            />
          </div>

          <div className="config-group" style={{ flex: '1 1 calc(50% - 0.75rem)', minWidth: '260px' }}>
            <label className="config-label" htmlFor="voice">
              Voice
            </label>
            <input
              id="voice"
              type="text"
              className="config-input"
              placeholder="e.g. neutral, enthusiastic - leave blank to skip audio"
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="config-row">
          <div className="config-group">
            <label className="config-label" htmlFor="jobId">
              Job ID
            </label>
            <input
              id="jobId"
              type="text"
              className="config-input"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            />
          </div>

          <div className="config-group">
            <label className="config-label" htmlFor="callbackUrl">
              Callback URL
            </label>
            <input
              id="callbackUrl"
              type="url"
              className="config-input"
              placeholder="https://your-app.com/api/eduflow/callback"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="btn-flex" style={{ marginTop: '1.5rem' }}>
          <button
            type="submit"
            className={`btn btn-primary${isSubmitting ? ' loading' : ''}`}
            disabled={isSubmitting}
          >
            Start EduFlow Generation
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

export default EduflowGenerator;

