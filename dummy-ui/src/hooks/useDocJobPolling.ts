import { useCallback, useEffect, useMemo, useState } from 'react';
import APIService from '../services/api';
import { ToastPayload } from '../components/ToastMessage';

export interface JobStatus {
  status: string;
  message?: string;
  error?: string | null;
  result?: {
    docs?: Array<{
      title?: string;
      doc_index?: number;
      pdf_url?: string;
    }>;
  };
}

function parsePrompts(value: string): string[] {
  return value.split('\n').map((l) => l.trim()).filter(Boolean);
}

export function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

interface UseDocJobPollingOptions {
  apiService: APIService;
  indexId: string;
  onJobRunningChange?: (isRunning: boolean) => void;
  startJob: (payload: {
    jobId: string;
    callbackUrl?: string;
    indexId: string;
    prompts: string[];
    duration: number;
  }) => Promise<{ success: boolean; error?: string }>;
  labels: {
    startSuccess: string;
    startError: string;
    completedToast: string;
    failedToast: string;
  };
}

export function useDocJobPolling({
  apiService,
  indexId,
  onJobRunningChange,
  startJob,
  labels,
}: UseDocJobPollingOptions) {
  const [jobId, setJobId] = useState(() => `job-${Date.now()}`);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastKnownStatus, setLastKnownStatus] = useState<string | null>(null);
  const [callbackUrl, setCallbackUrl] = useState('');
  const [promptsText, setPromptsText] = useState('');
  const [duration, setDuration] = useState<'5' | '10'>('5');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<ToastPayload | null>(null);
  const [jobAcceptedAt, setJobAcceptedAt] = useState<number | null>(null);
  const [completedDurationMs, setCompletedDurationMs] = useState<number | null>(null);

  const prompts = useMemo(() => parsePrompts(promptsText), [promptsText]);
  const promptsCountLabel = prompts.length === 1 ? '1 prompt' : `${prompts.length} prompts`;
  const statusLower = String(jobStatus?.status || '').toLowerCase();
  const docs = jobStatus?.result?.docs || [];

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setToast(null);

    const trimmedCallbackUrl = callbackUrl.trim();
    const response = await startJob({
      jobId,
      callbackUrl: trimmedCallbackUrl.length > 0 ? trimmedCallbackUrl : undefined,
      indexId,
      prompts,
      duration: Number(duration),
    });

    if (response.success) {
      setToast({ type: 'success', text: labels.startSuccess });
      setActiveJobId(jobId);
      setJobStatus(null);
      setIsPolling(true);
      setLastKnownStatus(null);
      setJobAcceptedAt(Date.now());
      setCompletedDurationMs(null);
      setJobId(`job-${Date.now()}`);
    } else {
      setToast({ type: 'error', text: response.error || labels.startError });
      setJobAcceptedAt(null);
      setCompletedDurationMs(null);
    }

    setIsSubmitting(false);
  }, [callbackUrl, jobId, indexId, prompts, duration, startJob, labels]);

  useEffect(() => {
    if (!activeJobId) return;
    let cancelled = false;
    let intervalId: number | undefined;

    const pollOnce = async () => {
      const response = await apiService.getBgJobStatus(activeJobId);
      if (cancelled) return;

      if (!response.success) {
        setJobStatus({ status: 'Failed', message: response.error || 'Failed to fetch job status', error: response.error || null });
        setIsPolling(false);
        if (intervalId) window.clearInterval(intervalId);
        return;
      }

      const data = response.data;
      setJobStatus(data);

      const s = String(data?.status || '').toLowerCase();
      if (s === 'completed' || s === 'failed') {
        if (s === 'completed' && jobAcceptedAt) setCompletedDurationMs(Date.now() - jobAcceptedAt);
        else if (s === 'failed') setCompletedDurationMs(null);
        setIsPolling(false);
        if (intervalId) window.clearInterval(intervalId);
      }
    };

    void pollOnce();
    intervalId = window.setInterval(() => void pollOnce(), 15000);
    return () => { cancelled = true; if (intervalId) window.clearInterval(intervalId); };
  }, [activeJobId, apiService, jobAcceptedAt]);

  useEffect(() => {
    onJobRunningChange?.(isPolling);
    return () => onJobRunningChange?.(false);
  }, [isPolling, onJobRunningChange]);

  useEffect(() => {
    if (!jobStatus?.status || jobStatus.status === lastKnownStatus) return;
    const s = String(jobStatus.status || '').toLowerCase();
    setLastKnownStatus(jobStatus.status);
    if (s === 'completed') setToast({ type: 'success', text: jobStatus.message || labels.completedToast });
    else if (s === 'failed') setToast({ type: 'error', text: jobStatus.message || labels.failedToast });
  }, [jobStatus, lastKnownStatus, labels]);

  return {
    jobId, setJobId,
    callbackUrl, setCallbackUrl,
    promptsText, setPromptsText,
    duration, setDuration,
    isSubmitting, isPolling,
    toast, setToast,
    completedDurationMs,
    prompts, promptsCountLabel,
    statusLower, docs,
    activeJobId, jobStatus,
    handleSubmit,
  };
}