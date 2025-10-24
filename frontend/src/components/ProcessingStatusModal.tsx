import React from 'react';
import { useProcessingStatus } from '../hooks/useProcessingStatus';
import ProcessingStatusIndicator from './ProcessingStatusIndicator';
import './Modal.css';

interface ProcessingStatusModalProps {
  lessonId: string;
  onClose: () => void;
  onComplete?: (lessonId: string) => void;
  onError?: (error: string) => void;
  title?: string;
}

const ProcessingStatusModal: React.FC<ProcessingStatusModalProps> = ({
  lessonId,
  onClose,
  onComplete,
  onError,
  title = 'Processing Content'
}) => {
  const { status, isPolling, error } = useProcessingStatus(lessonId, {
    autoStart: true,
    onComplete: (completedStatus) => {
      onComplete?.(completedStatus.lesson_id);
    },
    onError: (errorMessage) => {
      onError?.(errorMessage);
    }
  });

  const handleClose = () => {
    onClose();
  };

  const canClose = !isPolling || status?.status === 'completed' || status?.status === 'failed';

  return (
    <div className="modal-overlay" onClick={canClose ? handleClose : undefined}>
      <div className="modal-content processing-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          {canClose && (
            <button className="close-button" onClick={handleClose}>×</button>
          )}
        </div>

        <div className="modal-body">
          {status ? (
            <ProcessingStatusIndicator 
              status={status} 
              showDetails={true}
              className="modal-processing-indicator"
            />
          ) : (
            <div className="loading-placeholder">
              <div className="loading-spinner"></div>
              <p>Checking processing status...</p>
            </div>
          )}

          {error && (
            <div className="error-section">
              <h4>⚠️ Error</h4>
              <p className="error-message">{error}</p>
            </div>
          )}

          {status?.status === 'processing' && (
            <div className="processing-info">
              <p className="info-text">
                Your content is being processed. This may take a few minutes depending on the size and complexity of your material.
              </p>
              <p className="info-text">
                You can safely close this window - processing will continue in the background.
              </p>
            </div>
          )}

          {status?.status === 'completed' && (
            <div className="success-section">
              <h4>🎉 Processing Complete!</h4>
              <p>Your content has been successfully processed and is ready for learning.</p>
            </div>
          )}

          {status?.status === 'failed' && (
            <div className="error-section">
              <h4>❌ Processing Failed</h4>
              <p>There was an issue processing your content. Please try uploading again or contact support if the problem persists.</p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {status?.status === 'processing' && (
            <button className="secondary-button" onClick={handleClose}>
              Continue in Background
            </button>
          )}
          
          {(status?.status === 'completed' || status?.status === 'failed') && (
            <button className="primary-button" onClick={handleClose}>
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProcessingStatusModal;