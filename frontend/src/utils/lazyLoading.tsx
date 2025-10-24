/**
 * Lazy loading utilities for React components and routes.
 */

import React from 'react';

// Route preloader for better performance
export class RoutePreloader {
  private static preloadedRoutes = new Set<string>();

  static preload(routeImport: () => Promise<any>): void {
    const routeKey = routeImport.toString();
    if (!this.preloadedRoutes.has(routeKey)) {
      this.preloadedRoutes.add(routeKey);
      routeImport().catch(console.error);
    }
  }

  static preloadAll(): void {
    // Preload all lazy components
    const components = [
      () => import('../components/LoginForm'),
      () => import('../components/MainApp'),
      () => import('../components/LessonLibrary'),
      () => import('../components/LessonViewer'),
      () => import('../components/MultimediaLibrary'),
      () => import('../components/StudyBuddy'),
      () => import('../components/UserSettings')
    ];

    components.forEach(component => this.preload(component));
  }
}

// Higher-order component for lazy loading with error boundary
export function withLazyLoading<T extends React.ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  fallback?: React.ComponentType
): React.ComponentType<React.ComponentProps<T>> {
  const LazyComponent = React.lazy(importFunc);
  
  return React.forwardRef<any, React.ComponentProps<T>>((props, ref) => (
    <React.Suspense 
      fallback={
        fallback ? 
        React.createElement(fallback) : 
        <div className="loading-spinner">Loading...</div>
      }
    >
      <LazyComponent {...props as any} ref={ref} />
    </React.Suspense>
  ));
}

// Hook for intersection observer-based lazy loading
export function useIntersectionObserver(
  callback: (entries: IntersectionObserverEntry[]) => void,
  options?: IntersectionObserverInit
): React.RefObject<HTMLElement> {
  const targetRef = React.useRef<HTMLElement>(null);

  React.useEffect(() => {
    const target = targetRef.current;
    if (!target) return;

    const observer = new IntersectionObserver(callback, {
      threshold: 0.1,
      ...options
    });

    observer.observe(target);

    return () => {
      observer.unobserve(target);
      observer.disconnect();
    };
  }, [callback, options]);

  return targetRef;
}