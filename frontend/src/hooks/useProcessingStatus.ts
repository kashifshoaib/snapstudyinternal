import { useState, useEffect, useCallback, useRef } from 'react';
import { processingService, ProcessingStatus } from '../services/processingService';

interface UseProcessingStatusOptions {
  onComplete?: (status: ProcessingStatus) => void;
  onError?: (error: string) => void;
  autoStart?: boolean;
}

interface UseProcessingStatusReturn {
  status: ProcessingStatus | null;
  isPolling: boolean;
  error: string | null;
  startPolling: (lessonId: string) => void;
  stopPolling: () => void;
  clearError: () => void;
}

export const useProcessingStatus = (
  lessonId?: string,
  options: UseProcessingStatusOptions = {}
): UseProcessingStatusReturn => {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentLessonId = useRef<string | null>(null);

  const { onComplete, onError, autoStart = false } = options;

  const handleProgress = useCallback((newStatus: ProcessingStatus) => {
    setStatus(newStatus);
    setError(null);
  }, []);

  const handleComplete = useCallback((completedStatus: ProcessingStatus) => {
    setStatus(completedStatus);
    setIsPolling(false);
    setError(null);
    onComplete?.(completedStatus);
  }, [onComplete]);

  const handleError = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setIsPolling(false);
    onError?.(errorMessage);
  }, [onError]);

  const startPolling = useCallback((targetLessonId: string) => {
    if (currentLessonId.current) {
      processingService.stopPolling(currentLessonId.current);
    }

    currentLessonId.current = targetLessonId;
    setIsPolling(true);
    setError(null);

    processingService.startPolling(
      targetLessonId,
      handleProgress,
      handleComplete,
      handleError
    );
  }, [handleProgress, handleComplete, handleError]);

  const stopPolling = useCallback(() => {
    if (currentLessonId.current) {
      processingService.stopPolling(currentLessonId.current);
      setIsPolling(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Auto-start polling if lessonId is provided and autoStart is true
  useEffect(() => {
    if (lessonId && autoStart) {
      startPolling(lessonId);
    }

    return () => {
      if (currentLessonId.current) {
        processingService.stopPolling(currentLessonId.current);
      }
    };
  }, [lessonId, autoStart, startPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentLessonId.current) {
        processingService.stopPolling(currentLessonId.current);
      }
    };
  }, []);

  return {
    status,
    isPolling,
    error,
    startPolling,
    stopPolling,
    clearError
  };
};