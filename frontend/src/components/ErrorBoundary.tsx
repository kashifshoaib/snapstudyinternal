/**
 * Enhanced Error Boundary component for graceful error handling.
 * 
 * This component catches JavaScript errors anywhere in the component tree,
 * logs those errors, and displays a fallback UI instead of crashing the app.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { notificationManager } from '../utils/loadingStateManager';
import './ErrorBoundary.css';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetOnPropsChange?: boolean;
  resetKeys?: Array<string | number>;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  private resetTimeoutId: number | null = null;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error
    this.logError(error, errorInfo);
    
    // Update state with error info
    this.setState({
      errorInfo
    });

    // Call the onError callback if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Show error notification
    this.showErrorNotification(error);
  }

  componentDidUpdate(prevProps: Props) {
    const { resetOnPropsChange, resetKeys } = this.props;
    const { hasError } = this.state;

    // Reset error state if resetKeys have changed
    if (hasError && resetOnPropsChange && resetKeys) {
      const prevResetKeys = prevProps.resetKeys || [];
      const hasResetKeyChanged = resetKeys.some(
        (key, index) => key !== prevResetKeys[index]
      );

      if (hasResetKeyChanged) {
        this.resetErrorBoundary();
      }
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  private logError(error: Error, errorInfo: ErrorInfo) {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Error Boundary Caught an Error');
      console.error('Error:', error);
      console.error('Error Info:', errorInfo);
      console.error('Component Stack:', errorInfo.componentStack);
      console.groupEnd();
    }

    // Log to external service in production
    if (process.env.NODE_ENV === 'production') {
      this.logToExternalService(error, errorInfo);
    }
  }

  private logToExternalService(error: Error, errorInfo: ErrorInfo) {
    // Example integration with error tracking service
    try {
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        userId: this.getCurrentUserId(),
        errorId: this.state.errorId
      };

      // Send to your error tracking service (e.g., Sentry, LogRocket, etc.)
      // Example: Sentry.captureException(error, { extra: errorData });
      
      // For now, just log to console
      console.error('Error logged to external service:', errorData);
    } catch (loggingError) {
      console.error('Failed to log error to external service:', loggingError);
    }
  }

  private getCurrentUserId(): string | null {
    // Try to get user ID from various sources
    try {
      // From localStorage
      const authData = localStorage.getItem('auth');
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.user?.user_id || null;
      }
      
      // From sessionStorage
      const sessionAuth = sessionStorage.getItem('auth');
      if (sessionAuth) {
        const parsed = JSON.parse(sessionAuth);
        return parsed.user?.user_id || null;
      }
      
      return null;
    } catch {
      return null;
    }
  }

  private showErrorNotification(error: Error) {
    const isNetworkError = error.message.includes('fetch') || 
                          error.message.includes('network') ||
                          !navigator.onLine;

    if (isNetworkError) {
      notificationManager.error(
        'Connection Error',
        'There was a problem connecting to our servers. Please check your internet connection and try again.',
        true
      );
    } else {
      notificationManager.error(
        'Something went wrong',
        'An unexpected error occurred. Our team has been notified and is working on a fix.',
        true
      );
    }
  }

  private resetErrorBoundary = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    });
  };

  private handleRetry = () => {
    this.resetErrorBoundary();
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReportError = () => {
    const { error, errorInfo, errorId } = this.state;
    
    if (error && errorId) {
      // Create a detailed error report
      const errorReport = {
        errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo?.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      };

      // Copy to clipboard or open email client
      const reportText = `Error Report (ID: ${errorId})\n\n${JSON.stringify(errorReport, null, 2)}`;
      
      if (navigator.clipboard) {
        navigator.clipboard.writeText(reportText).then(() => {
          notificationManager.success(
            'Error Report Copied',
            'The error report has been copied to your clipboard. Please paste it in your support request.'
          );
        });
      } else {
        // Fallback: open email client
        const subject = encodeURIComponent(`Error Report - ${errorId}`);
        const body = encodeURIComponent(reportText);
        window.open(`mailto:support@snapstudy.com?subject=${subject}&body=${body}`);
      }
    }
  };

  render() {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Custom fallback UI
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            
            <h2 className="error-title">Oops! Something went wrong</h2>
            
            <p className="error-message">
              We're sorry, but something unexpected happened. Don't worry - your data is safe, 
              and our team has been automatically notified about this issue.
            </p>

            {process.env.NODE_ENV === 'development' && error && (
              <details className="error-details">
                <summary>Error Details (Development Only)</summary>
                <pre className="error-stack">
                  {error.message}
                  {error.stack && `\n\n${error.stack}`}
                </pre>
              </details>
            )}

            <div className="error-actions">
              <button 
                className="btn btn-primary"
                onClick={this.handleRetry}
              >
                Try Again
              </button>
              
              <button 
                className="btn btn-secondary"
                onClick={this.handleReload}
              >
                Reload Page
              </button>
              
              <button 
                className="btn btn-outline"
                onClick={this.handleReportError}
              >
                Report Error
              </button>
            </div>

            <div className="error-help">
              <p>
                If this problem persists, please{' '}
                <a href="mailto:support@snapstudy.com">contact our support team</a>{' '}
                with error ID: <code>{this.state.errorId}</code>
              </p>
            </div>
          </div>


        </div>
      );
    }

    return children;
  }
}

// Higher-order component for wrapping components with error boundary
export function withErrorBoundary<T extends object>(
  Component: React.ComponentType<T>,
  errorBoundaryProps?: Omit<Props, 'children'>
): React.ComponentType<T> {
  return function ErrorBoundaryWrapper(props: T) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

// Hook for programmatically triggering error boundary
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    // This will trigger the nearest error boundary
    throw error;
  };
}