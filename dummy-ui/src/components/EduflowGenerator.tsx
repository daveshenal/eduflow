import React, { useEffect, useState } from 'react';
import APIService from '../services/api';
import ToastMessage, { ToastPayload } from './ToastMessage';

interface EduflowGeneratorProps {
  apiService: APIService;
  indexId: string;
}

const EduflowGenerator: React.FC<EduflowGeneratorProps> = ({ apiService, indexId }) => {
  const [jobId, setJobId] = useState(() => `job-${Date.now()}`);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastKnownStatus, setLastKnownStatus] = useState<string | null>(null);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [learningFocus, setLearningFocus] = useState('');
  const [topic, setTopic] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [duration, setDuration] = useState<'5' | '10'>('5');
  const [numDocs, setNumDocs] = useState('3');
  const [voice, setVoice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastPayload | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setToast(null);

    const clampedNumDocs = Math.max(1, Math.min(8, Number(numDocs) || 1));

    const trimmedVoice = voice.trim();

    const trimmedCallbackUrl = callbackUrl.trim();
    const payload = {
      jobId,
      callbackUrl: trimmedCallbackUrl.length > 0 ? trimmedCallbackUrl : undefined,
      indexId,
      learningFocus,
      topic,
      targetAudience,
      duration: Number(duration),
      numDocs: clampedNumDocs,
      // Treat empty string as "no voice provided"
      voice: trimmedVoice.length > 0 ? trimmedVoice : undefined,
    };

    const response = await apiService.startEduflowJob(payload);

    if (response.success) {
      setToast({ type: 'success', text: 'EduFlow generation job started successfully.' });
      // Start polling using the jobId that was just submitted.
      const startedJobId = jobId;
      setActiveJobId(startedJobId);
      setJobStatus(null);
      setIsPolling(true);
      setLastKnownStatus(null);
      // refresh job id for next run
      setJobId(`job-${Date.now()}`);
    } else {
      setToast({ type: 'error', text: response.error || 'Failed to start EduFlow generation job.' });
    }

    setIsSubmitting(false);
  };

  useEffect(() => {
    if (!activeJobId) return;

    let cancelled = false;
    let intervalId: number | undefined;

    const pollOnce = async () => {
      const response = await apiService.getBgJobStatus(activeJobId);
      if (cancelled) return;

      if (!response.success) {
        setJobStatus({
          status: 'Failed',
          message: response.error || 'Failed to fetch job status',
          error: response.error || null,
        });
        setIsPolling(false);
        if (intervalId) window.clearInterval(intervalId);
        return;
      }

      const data = response.data;
      setJobStatus(data);

      const statusLower = String(data?.status || '').toLowerCase();
      if (statusLower === 'completed' || statusLower === 'failed') {
        setIsPolling(false);
        if (intervalId) window.clearInterval(intervalId);
      }
    };

    // Poll immediately, then every 15 seconds.
    void pollOnce();
    intervalId = window.setInterval(() => void pollOnce(), 15000);

    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [activeJobId, apiService]);

  useEffect(() => {
    if (!jobStatus?.status) return;
    if (jobStatus.status === lastKnownStatus) return;

    const statusLower = String(jobStatus.status || '').toLowerCase();
    setLastKnownStatus(jobStatus.status);

    if (statusLower === 'completed') {
      setToast({ type: 'success', text: jobStatus.message || 'EduFlow generation completed.' });
    } else if (statusLower === 'failed') {
      setToast({ type: 'error', text: jobStatus.message || 'EduFlow generation failed.' });
    }
  }, [jobStatus, lastKnownStatus]);

  const statusLower = String(jobStatus?.status || '').toLowerCase();
  const docs = jobStatus?.result?.docs || [];

  return (
    <div className="editor-container">
      <ToastMessage message={toast} onClear={() => setToast(null)} />
      <h2 className="content-section-title">EduFlow Content Generation</h2>
      <p className="content-label">
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
              Voice (optional)
            </label>
            <input
              id="voice"
              type="text"
              className="config-input"
              placeholder="e.g. en-US-JennyNeural, leave blank to skip audio"
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
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
              Callback URL (optional)
            </label>
            <input
              id="callbackUrl"
              type="url"
              className="config-input"
              placeholder="https://your-app.com/api/eduflow/callback"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
            />
          </div>
        </div>

        <div className="btn-flex" style={{ marginTop: '1.5rem' }}>
          <button
            type="submit"
            className={`btn btn-primary${isSubmitting ? ' loading' : ''}`}
            disabled={isSubmitting || isPolling}
          >
            Start EduFlow Generation
          </button>
        </div>
      </form>

      {activeJobId && jobStatus && isPolling && (
        <div className="loading" style={{ marginTop: '1.5rem' }}>
          <span className="loading-spinner" /> {jobStatus.message || 'Generating...'}
        </div>
      )}

      {activeJobId && jobStatus && statusLower === 'completed' && (
        <div style={{ marginTop: '1.5rem' }}>
          <div className="success-message">Generation completed. Download the results below.</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {docs.map((doc: any, i: number) => {
              const docTitle = doc?.title || `Document ${doc?.doc_index || i + 1}`;
              return (
                <div
                  key={doc?.doc_index ?? i}
                  style={{
                    padding: '0.9rem',
                    borderRadius: '0.75rem',
                    background: 'rgba(255, 255, 255, 0.7)',
                    border: '1px solid rgba(64, 121, 140, 0.12)',
                    boxShadow: '0 2px 12px rgba(64, 121, 140, 0.08)',
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>{docTitle}</div>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    {doc?.pdf_url && (
                      <a href={doc.pdf_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
                        Download PDF
                      </a>
                    )}
                    {doc?.audio_url && (
                      <a href={doc.audio_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
                        Download Audio
                      </a>
                    )}
                    {doc?.voicescript_url && (
                      <a href={doc.voicescript_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
                        Download Voice Script
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeJobId && jobStatus && statusLower === 'failed' && (
        <div className="error-message" style={{ marginTop: '1.5rem' }}>
          {jobStatus.message || 'Generation failed.'}
        </div>
      )}
    </div>
  );
};

export default EduflowGenerator;

