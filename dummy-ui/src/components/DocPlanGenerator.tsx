import React, { useEffect, useMemo, useState } from 'react';
import APIService from '../services/api';
import ToastMessage, { ToastPayload } from './ToastMessage';

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
  const [jobId, setJobId] = useState(() => `job-${Date.now()}`);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastKnownStatus, setLastKnownStatus] = useState<string | null>(null);
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

    const trimmedCallbackUrl = callbackUrl.trim();
    const response = await apiService.startBaselineJob({
      jobId,
      callbackUrl: trimmedCallbackUrl.length > 0 ? trimmedCallbackUrl : undefined,
      indexId,
      prompts,
      duration: Number(duration),
    });

    if (response.success) {
      setToast({ type: 'success', text: 'Baseline generation job started successfully.' });
      const startedJobId = jobId;
      setActiveJobId(startedJobId);
      setJobStatus(null);
      setIsPolling(true);
      setLastKnownStatus(null);
      setJobId(`job-${Date.now()}`);
    } else {
      setToast({ type: 'error', text: response.error || 'Failed to start baseline generation job.' });
    }

    setIsSubmitting(false);
  };

  const promptsCountLabel = prompts.length === 1 ? '1 prompt' : `${prompts.length} prompts`;

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
      setToast({ type: 'success', text: jobStatus.message || 'Baseline generation completed.' });
    } else if (statusLower === 'failed') {
      setToast({ type: 'error', text: jobStatus.message || 'Baseline generation failed.' });
    }
  }, [jobStatus, lastKnownStatus]);

  const statusLower = String(jobStatus?.status || '').toLowerCase();
  const docs = jobStatus?.result?.docs || [];

  return (
    <div className="editor-container">
      <ToastMessage message={toast} onClear={() => setToast(null)} />
      <h2 className="content-section-title">Human-Guided Sequential RAG</h2>
      <p className="content-label">
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
              Callback URL (optional)
            </label>
            <input
              id="baselineCallbackUrl"
              type="url"
              className="config-input"
              placeholder="https://your-app.com/api/baseline/callback"
              value={callbackUrl}
              onChange={(e) => setCallbackUrl(e.target.value)}
            />
          </div>
        </div>

        <div className="config-group" style={{ width: '180px' }}>
          <label className="config-label" htmlFor="baselineDuration">
            Duration (minutes per doc)
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

        <div className="config-group">
          <label className="config-label" htmlFor="baselinePrompts">
            Prompts (one per line) — {promptsCountLabel}
          </label>
          <textarea
            id="baselinePrompts"
            className="config-input"
            placeholder={`Example:\nOASIS Foundations: Building Clinical Assessment Excellence\nClinical Assessment Mastery: Translating Observations to OASIS Responses\nComplex Case Navigation: OASIS Documentation for Challenging Scenarios`}
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
            disabled={isSubmitting || isPolling || prompts.length === 0}
          >
            Start Baseline Generation
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
                <div className='downloads' key={doc?.doc_index ?? i}>

                <div className = 'dropdown' style={{ fontWeight: 500 }}>
                  {docTitle}:
                </div>

                <div className = 'dropdown' style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                  {doc?.pdf_url && (
                    <a className="doc-link" href={doc.pdf_url} target="_blank" rel="noreferrer">
                      PDF File
                    </a>
                  )}
                  {doc?.audio_url && (
                    <a className="doc-link" href={doc.audio_url} target="_blank" rel="noreferrer">
                      Audio MP3
                    </a>
                  )}
                  {doc?.voicescript_url && (
                    <a className="doc-link" href={doc.voicescript_url} target="_blank" rel="noreferrer">
                      Voice Script
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
        <div className="error-message" style={{
          padding: '10px 20px',
          display: 'inline-block',
          boxSizing: 'border-box',
          wordBreak: 'break-word',
        }}>
          {jobStatus.message || 'Generation failed.'}
        </div>
      )}
    </div>
  );
};

export default DocPlanGenerator;

