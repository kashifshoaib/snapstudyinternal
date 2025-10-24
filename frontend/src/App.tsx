import React, { Suspense } from 'react';
import { User, OnboardingData } from './types';
import ErrorBoundary from './components/ErrorBoundary';
import { performanceMonitor, usePerformanceMonitor } from './utils/performance';
import { RoutePreloader } from './utils/lazyLoading';
import { DataSyncProvider } from './contexts/DataSyncContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import './App.css';

// Lazy load main components
const LoginForm = React.lazy(() => import('./components/LoginForm'));
const OnboardingFlow = React.lazy(() => import('./components/OnboardingFlow'));
const MainApp = React.lazy(() => import('./components/MainApp'));

// Main App Content Component
const AppContent: React.FC = () => {
  const { state } = useAuth();
  const { measureAsyncOperation } = usePerformanceMonitor('App');

  // Preload components after initial load
  React.useEffect(() => {
    setTimeout(() => {
      RoutePreloader.preloadAll();
    }, 2000);
  }, []);

  // Track performance metrics
  React.useEffect(() => {
    if (state.isAuthenticated && state.user) {
      performanceMonitor.recordMetric('AuthenticationSuccess', 1);
    } else if (state.error) {
      performanceMonitor.recordMetric('AuthenticationFailure', 1, {
        error: state.error
      });
    }
  }, [state.isAuthenticated, state.user, state.error]);

  if (state.isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading SnapStudy...</p>
      </div>
    );
  }

  return (
    <Suspense fallback={
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading application...</p>
      </div>
    }>
      {!state.isAuthenticated || !state.user ? (
        <LoginForm />
      ) : state.needsOnboarding ? (
        <OnboardingFlow />
      ) : (
        <MainApp 
          user={state.user}
        />
      )}
    </Suspense>
  );
};

const App: React.FC = () => {
  return (
    <DataSyncProvider>
      <AuthProvider>
        <ErrorBoundary
          onError={(error, errorInfo) => {
            // Track application errors
            performanceMonitor.recordMetric('ApplicationError', 1, {
              error: error.message,
              componentStack: errorInfo.componentStack
            });
          }}
        >
          <AppContent />
        </ErrorBoundary>
      </AuthProvider>
    </DataSyncProvider>
  );
};

export default App;