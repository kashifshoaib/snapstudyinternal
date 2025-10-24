/**
 * Enhanced error display component with context-aware messaging
 */

import React, { useState } from 'react';
import { getErrorMessage, createErrorReport, ErrorContext } from '../utils/errorMessages';
import { analyticsService } from '../services/analyticsService';
import './ErrorDisplay.css';

interface ErrorDisplayProps {
  error: any;
  context?: ErrorContext;
  onRetry?: () => void;
  onDismiss?: () => void;
  showDetails?: boolean;
  className?: string;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  context = {},
  onRetry,
  onDismiss,
  showDetails = false,
  className = ''
}) => {
  const [showFullDetails, setShowFullDetails] = useState(false);
  const [isReporting, setIsReporting] = useState(false);
  const [reportSent, setReportSent] = useState(false);

  const errorMessage = getErrorMessage(error, context);
  const errorReport = createErrorReport(error, context);

  const handleReportError = async () => {
    try {
      setIsReporting(true);
      await analyticsService.trackError(errorReport);
      setReportSent(true);
      setTimeout(() => setReportSent(false), 3000);
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    } finally {
      setIsReporting(false);
    }
  };

  const getSeverityIcon = () => {
    switch (errorMessage.severity) {
      case 'critical':
        return '🚨';
      case 'high':
        return '⚠️';
      case 'medium':
        return '⚡';
      case 'low':
        return 'ℹ️';
      default:
        return '⚠️';
    }
  };

  const getSeverityClass = () => {
    return `error-display-${errorMessage.severity}`;
  };

  return (
    <div className={`error-display ${getSeverityClass()} ${className}`}>
      <div className="error-display-header">
        <div className="error-display-icon">
          {getSeverityIcon()}
        </div>
        <div className="error-display-title">
          <h3>{errorMessage.title}</h3>
          {onDismiss && (
            <button 
              className="error-display-close"
              onClick={onDismiss}
              aria-label="Dismiss error"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="error-display-content">
        <p className="error-display-message">{errorMessage.message}</p>

        {errorMessage.suggestedActions.length > 0 && (
          <div className="error-display-actions">
            <h4>What you can do:</h4>
            <ul>
              {errorMessage.suggestedActions.map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="error-display-buttons">
          {onRetry && errorMessage.recoverable && (
            <button 
              className="error-display-retry"
              onClick={onRetry}
            >
              Try Again
            </button>
          )}

          {!reportSent ? (
            <button 
              className="error-display-report"
              onClick={handleReportError}
              disabled={isReporting}
            >
              {isReporting ? 'Reporting...' : 'Report Issue'}
            </button>
          ) : (
            <span className="error-display-reported">✓ Reported</span>
          )}

          {showDetails && (
            <button 
              className="error-display-details-toggle"
              onClick={() => setShowFullDetails(!showFullDetails)}
            >
              {showFullDetails ? 'Hide Details' : 'Show Details'}
            </button>
          )}
        </div>

        {showFullDetails && (
          <div className="error-display-details">
            <h4>Technical Details</h4>
            <div className="error-display-technical">
              <div className="error-detail-item">
                <strong>Error Type:</strong> {error?.name || 'Unknown'}
              </div>
              <div className="error-detail-item">
                <strong>Status Code:</strong> {error?.response?.status || 'N/A'}
              </div>
              <div className="error-detail-item">
                <strong>Component:</strong> {context.component || 'Unknown'}
              </div>
              <div className="error-detail-item">
                <strong>Action:</strong> {context.action || 'Unknown'}
              </div>
              <div className="error-detail-item">
                <strong>Timestamp:</strong> {new Date(errorReport.timestamp).toLocaleString()}
              </div>
              {error?.message && (
                <div className="error-detail-item">
                  <strong>Message:</strong> 
                  <pre>{error.message}</pre>
                </div>
              )}
              {error?.response?.data && (
                <div className="error-detail-item">
                  <strong>Server Response:</strong>
                  <pre>{JSON.stringify(error.response.data, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Specialized error displays for common scenarios
export const NetworkErrorDisplay: React.FC<Omit<ErrorDisplayProps, 'context'>> = (props) => (
  <ErrorDisplay 
    {...props} 
    context={{ component: 'network', action: 'connection' }}
  />
);

export const UploadErrorDisplay: React.FC<Omit<ErrorDisplayProps, 'context'>> = (props) => (
  <ErrorDisplay 
    {...props} 
    context={{ component: 'upload', action: 'file_upload' }}
  />
);

export const AuthErrorDisplay: React.FC<Omit<ErrorDisplayProps, 'context'>> = (props) => (
  <ErrorDisplay 
    {...props} 
    context={{ component: 'auth', action: 'authenticate' }}
  />
);

export const ValidationErrorDisplay: React.FC<Omit<ErrorDisplayProps, 'context'> & { 
  validationErrors?: Record<string, string[]> 
}> = ({ validationErrors, ...props }) => {
  if (validationErrors) {
    return (
      <div className="validation-error-display">
        {Object.entries(validationErrors).map(([field, errors]) => (
          <div key={field} className="validation-field-error">
            <strong>{field}:</strong> {errors.join(', ')}
          </div>
        ))}
      </div>
    );
  }
  
  return (
    <ErrorDisplay 
      {...props} 
      context={{ component: 'form', action: 'validation' }}
    />
  );
};

export default ErrorDisplay;