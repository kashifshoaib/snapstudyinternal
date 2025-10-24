/**
 * Reusable skeleton loader components for different UI elements
 */

import React from 'react';
import './SkeletonLoader.css';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ 
  width = '100%', 
  height = '1rem', 
  borderRadius = '4px',
  className = ''
}) => (
  <div 
    className={`skeleton ${className}`}
    style={{ 
      width, 
      height, 
      borderRadius 
    }}
  />
);

export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({ 
  lines = 3, 
  className = '' 
}) => (
  <div className={`skeleton-text ${className}`}>
    {Array.from({ length: lines }, (_, i) => (
      <Skeleton 
        key={i} 
        height="1rem" 
        width={i === lines - 1 ? '75%' : '100%'}
        className="skeleton-text-line"
      />
    ))}
  </div>
);

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton-card ${className}`}>
    <Skeleton height="200px" className="skeleton-card-image" />
    <div className="skeleton-card-content">
      <Skeleton height="1.5rem" width="80%" className="skeleton-card-title" />
      <SkeletonText lines={2} className="skeleton-card-text" />
      <div className="skeleton-card-actions">
        <Skeleton height="2.5rem" width="100px" borderRadius="20px" />
        <Skeleton height="2.5rem" width="80px" borderRadius="20px" />
      </div>
    </div>
  </div>
);

export const SkeletonList: React.FC<{ 
  items?: number; 
  itemHeight?: string | number;
  className?: string;
}> = ({ 
  items = 5, 
  itemHeight = '60px',
  className = '' 
}) => (
  <div className={`skeleton-list ${className}`}>
    {Array.from({ length: items }, (_, i) => (
      <div key={i} className="skeleton-list-item">
        <Skeleton width="40px" height="40px" borderRadius="50%" />
        <div className="skeleton-list-content">
          <Skeleton height="1rem" width="60%" />
          <Skeleton height="0.875rem" width="40%" />
        </div>
      </div>
    ))}
  </div>
);

export const SkeletonChart: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton-chart ${className}`}>
    <div className="skeleton-chart-header">
      <Skeleton height="1.5rem" width="200px" />
      <Skeleton height="1rem" width="100px" />
    </div>
    <div className="skeleton-chart-content">
      <div className="skeleton-chart-bars">
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton 
            key={i} 
            width="40px" 
            height={`${Math.random() * 100 + 50}px`}
            className="skeleton-chart-bar"
          />
        ))}
      </div>
    </div>
  </div>
);

export const SkeletonQuiz: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton-quiz ${className}`}>
    <div className="skeleton-quiz-header">
      <Skeleton height="2rem" width="70%" />
      <Skeleton height="1rem" width="30%" />
    </div>
    <div className="skeleton-quiz-question">
      <SkeletonText lines={2} />
    </div>
    <div className="skeleton-quiz-options">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="skeleton-quiz-option">
          <Skeleton width="20px" height="20px" borderRadius="50%" />
          <Skeleton height="1rem" width="80%" />
        </div>
      ))}
    </div>
    <div className="skeleton-quiz-actions">
      <Skeleton height="2.5rem" width="120px" borderRadius="20px" />
    </div>
  </div>
);

export const SkeletonLesson: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton-lesson ${className}`}>
    <div className="skeleton-lesson-header">
      <Skeleton height="2.5rem" width="60%" />
      <div className="skeleton-lesson-meta">
        <Skeleton height="1rem" width="100px" />
        <Skeleton height="1rem" width="80px" />
      </div>
    </div>
    <div className="skeleton-lesson-progress">
      <Skeleton height="8px" width="100%" borderRadius="4px" />
    </div>
    <div className="skeleton-lesson-content">
      <SkeletonText lines={5} />
      <Skeleton height="200px" width="100%" className="skeleton-lesson-media" />
      <SkeletonText lines={3} />
    </div>
    <div className="skeleton-lesson-navigation">
      <Skeleton height="2.5rem" width="100px" borderRadius="20px" />
      <Skeleton height="2.5rem" width="100px" borderRadius="20px" />
    </div>
  </div>
);

export const SkeletonDashboard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`skeleton-dashboard ${className}`}>
    <div className="skeleton-dashboard-header">
      <Skeleton height="2rem" width="300px" />
      <Skeleton height="1rem" width="200px" />
    </div>
    <div className="skeleton-dashboard-stats">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="skeleton-dashboard-stat">
          <Skeleton height="3rem" width="60px" />
          <Skeleton height="1rem" width="100%" />
        </div>
      ))}
    </div>
    <div className="skeleton-dashboard-charts">
      <SkeletonChart />
      <SkeletonChart />
    </div>
  </div>
);