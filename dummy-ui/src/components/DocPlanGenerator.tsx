import React from 'react';
import APIService from '../services/api';
import ToastMessage from './ToastMessage';
import { useDocJobPolling, formatDuration } from '../hooks/useDocJobPolling';

interface DocPlanGeneratorProps {
  apiService: APIService;
  indexId: string;
  onJobRunningChange?: (isRunning: boolean) => void;
}

const DocPlanGenerator: React.FC<DocPlanGeneratorProps> = ({ apiService, indexId, onJobRunningChange }) => {
  const startJob = React.useCallback(
    (payload: Parameters<typeof apiService.startBaselineJob>[0]) =>
      apiService.startBaselineJob(payload),
    [apiService]
  );

  const {
    jobId, setJobId, callbackUrl, setCallbackUrl,
    promptsText, setPromptsText, duration, setDuration,
    isSubmitting, isPolling, toast, setToast,
    completedDurationMs, prompts, promptsCountLabel,
    statusLower, docs, activeJobId, jobStatus, handleSubmit,
  } = useDocJobPolling({
    apiService, indexId, onJobRunningChange, startJob,
    labels: {
      startSuccess: 'Baseline generation job started successfully.',
      startError: 'Failed to start baseline generation job.',
      completedToast: 'Baseline generation completed.',
      failedToast: 'Baseline generation failed.',
    },
  });

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
            <label className="config-label" htmlFor="baselineJobId">Job ID</label>
            <input id="baselineJobId" type="text" className="config-input" value={jobId} onChange={(e) => setJobId(e.target.value)} />
          </div>
          <div className="config-group" style={{ flex: '2 1 380px' }}>
            <label className="config-label" htmlFor="baselineCallbackUrl">Callback URL (optional)</label>
            <input id="baselineCallbackUrl" type="url" className="config-input" placeholder="https://your-app.com/api/baseline/callback" value={callbackUrl} onChange={(e) => setCallbackUrl(e.target.value)} />
          </div>
        </div>
        <div className="config-group" style={{ width: '180px' }}>
          <label className="config-label" htmlFor="baselineDuration">Duration (minutes per doc)</label>
          <select id="baselineDuration" className="config-input" value={duration} onChange={(e) => setDuration(e.target.value as '5' | '10')} required>
            <option value="5">5</option>
            <option value="10">10</option>
          </select>
        </div>
        <div className="config-group">
          <label className="config-label" htmlFor="baselinePrompts">Prompts (one per line) — {promptsCountLabel}</label>
          <textarea id="baselinePrompts" className="config-input" placeholder={`Example:\nOASIS Foundations\nClinical Assessment Mastery`} value={promptsText} onChange={(e) => setPromptsText(e.target.value)} style={{ minHeight: '140px', resize: 'none' }} required />
        </div>
        <div className="btn-flex" style={{ marginTop: '1.25rem' }}>
          <button type="submit" className={`btn btn-primary${isSubmitting ? ' loading' : ''}`} disabled={isSubmitting || isPolling || prompts.length === 0}>
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
        <div style={{ marginTop: '1.5rem', maxWidth: '920px' }}>
          <div className="success-message">
            Generation completed{completedDurationMs !== null ? ` in ${formatDuration(completedDurationMs)}` : ''}. Download the results below.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {docs.map((doc, i) => (
              <div className='downloads' key={doc?.doc_index ?? i}>
                <div className='dropdown' style={{ fontWeight: 500, marginBottom: '0.6rem' }}>{doc?.title || `Document ${doc?.doc_index || i + 1}`}:</div>
                <div className='dropdown' style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                  {doc?.pdf_url && <a className="doc-link" href={doc.pdf_url} target="_blank" rel="noreferrer">Download PDF</a>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {activeJobId && jobStatus && statusLower === 'failed' && (
        <div className="error-message" style={{ maxWidth: '920px' }}>{jobStatus.message || 'Content Generation failed.'}</div>
      )}
    </div>
  );
};

export default DocPlanGenerator;