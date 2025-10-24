import React from 'react';
import { ProcessingStatus } from '../services/processingService';
import { 
  getStatusMessage, 
  getProgressColor, 
  getStageIcon, 
  formatEstimatedTime 
} from '../utils/processingUtils';
import './ProcessingStatusIndicator.css';

interface ProcessingStatusIndicatorProps {
  status: ProcessingStatus;
  showDetails?: boolean;
  compact?: boolean;
  className?: string;
}

const ProcessingStatusIndicator: React.FC<ProcessingStatusIndicatorProps> = ({
  status,
  showDetails = true,
  compact = false,
  className = ''
}) => {
  const getStatusIcon = () => {
    if (status.stage) {
      return getStageIcon(status.stage);
    }
    
    switch (status.status) {
      case 'processing':
        return '⏳';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '📄';
    }
  };

  const statusText = getStatusMessage(status);
  const progressColor = getProgressColor(status);

  if (compact) {
    return (
      <div className={`processing-status-compact ${className}`}>
        <span className="status-icon">{getStatusIcon()}</span>
        <span className="status-text">{statusText}</span>
        {status.status === 'processing' && (
          <span className="progress-percentage">
            {Math.round(status.progress_percentage)}%
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`processing-status-indicator ${className}`}>
      <div className="status-header">
        <div className="status-icon-large">{getStatusIcon()}</div>
        <div className="status-info">
          <h4 className="status-title">{statusText}</h4>
          {status.stage && (
            <p className="status-stage">{status.stage}</p>
          )}
        </div>
      </div>

      {status.status === 'processing' && (
        <div className="progress-section">
          <div className="progress-bar-container">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ 
                  width: `${status.progress_percentage}%`,
                  backgroundColor: progressColor
                }}
              />
            </div>
            <span className="progress-text">
              {Math.round(status.progress_percentage)}%
            </span>
          </div>
          
          {status.estimated_completion_time && (
            <p className="estimated-time">
              Estimated completion: {formatEstimatedTime(status.estimated_completion_time)}
            </p>
          )}
        </div>
      )}

      {status.status === 'failed' && status.error_message && (
        <div className="error-section">
          <p className="error-message">{status.error_message}</p>
        </div>
      )}

      {showDetails && (
        <div className="status-details">
          <p className="status-timestamp">
            Last updated: {new Date(status.updated_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
};

export default ProcessingStatusIndicator;