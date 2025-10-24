import { ProcessingStatus } from '../services/processingService';

/**
 * Format estimated completion time for display
 */
export const formatEstimatedTime = (estimatedTime: string): string => {
  try {
    const date = new Date(estimatedTime);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    
    if (diffMs <= 0) {
      return 'Any moment now';
    }
    
    const diffMinutes = Math.ceil(diffMs / (1000 * 60));
    
    if (diffMinutes < 1) {
      return 'Less than a minute';
    } else if (diffMinutes === 1) {
      return '1 minute';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} minutes`;
    } else {
      const hours = Math.floor(diffMinutes / 60);
      const remainingMinutes = diffMinutes % 60;
      
      if (hours === 1 && remainingMinutes === 0) {
        return '1 hour';
      } else if (remainingMinutes === 0) {
        return `${hours} hours`;
      } else {
        return `${hours}h ${remainingMinutes}m`;
      }
    }
  } catch (error) {
    return estimatedTime;
  }
};

/**
 * Get user-friendly status message
 */
export const getStatusMessage = (status: ProcessingStatus): string => {
  switch (status.status) {
    case 'processing':
      if (status.stage) {
        return `Processing: ${status.stage}`;
      }
      return 'Processing your content...';
    case 'completed':
      return 'Content ready for learning!';
    case 'failed':
      return status.error_message || 'Processing failed';
    default:
      return 'Unknown status';
  }
};

/**
 * Get progress color based on status and percentage
 */
export const getProgressColor = (status: ProcessingStatus): string => {
  switch (status.status) {
    case 'processing':
      if (status.progress_percentage < 30) {
        return '#ff9800'; // Orange for early stages
      } else if (status.progress_percentage < 70) {
        return '#2196f3'; // Blue for middle stages
      } else {
        return '#4caf50'; // Green for near completion
      }
    case 'completed':
      return '#4caf50'; // Green
    case 'failed':
      return '#f44336'; // Red
    default:
      return '#757575'; // Gray
  }
};

/**
 * Check if processing is in a terminal state
 */
export const isTerminalState = (status: ProcessingStatus): boolean => {
  return status.status === 'completed' || status.status === 'failed';
};

/**
 * Get appropriate icon for processing stage
 */
export const getStageIcon = (stage: string): string => {
  const stageIcons: Record<string, string> = {
    'uploading': '📤',
    'parsing': '📖',
    'analyzing': '🔍',
    'generating': '⚙️',
    'optimizing': '🔧',
    'finalizing': '✨',
    'completed': '✅',
    'failed': '❌'
  };
  
  const normalizedStage = stage.toLowerCase();
  return stageIcons[normalizedStage] || '⏳';
};

/**
 * Calculate processing speed (percentage per minute)
 */
export const calculateProcessingSpeed = (
  currentProgress: number,
  startTime: string
): number => {
  try {
    const start = new Date(startTime);
    const now = new Date();
    const elapsedMinutes = (now.getTime() - start.getTime()) / (1000 * 60);
    
    if (elapsedMinutes <= 0) {
      return 0;
    }
    
    return currentProgress / elapsedMinutes;
  } catch (error) {
    return 0;
  }
};

/**
 * Estimate remaining time based on current progress and speed
 */
export const estimateRemainingTime = (
  currentProgress: number,
  processingSpeed: number
): string => {
  if (processingSpeed <= 0 || currentProgress >= 100) {
    return 'Unknown';
  }
  
  const remainingProgress = 100 - currentProgress;
  const remainingMinutes = Math.ceil(remainingProgress / processingSpeed);
  
  if (remainingMinutes < 1) {
    return 'Less than a minute';
  } else if (remainingMinutes === 1) {
    return '1 minute';
  } else if (remainingMinutes < 60) {
    return `${remainingMinutes} minutes`;
  } else {
    const hours = Math.floor(remainingMinutes / 60);
    const minutes = remainingMinutes % 60;
    
    if (hours === 1 && minutes === 0) {
      return '1 hour';
    } else if (minutes === 0) {
      return `${hours} hours`;
    } else {
      return `${hours}h ${minutes}m`;
    }
  }
};