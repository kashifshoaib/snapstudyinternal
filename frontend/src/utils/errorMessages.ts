/**
 * Error message mapping and utilities for user-friendly error handling
 */

export interface ErrorContext {
  component?: string;
  action?: string;
  userInput?: any;
  timestamp?: string;
}

export interface ErrorMessage {
  title: string;
  message: string;
  suggestedActions: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  recoverable: boolean;
  timestamp?: string;
}

// Error type mappings
export const ERROR_TYPES = {
  NETWORK: 'network',
  AUTHENTICATION: 'authentication',
  VALIDATION: 'validation',
  SERVER: 'server',
  CLIENT: 'client',
  TIMEOUT: 'timeout',
  PERMISSION: 'permission',
  NOT_FOUND: 'not_found',
  RATE_LIMIT: 'rate_limit',
  FILE_UPLOAD: 'file_upload',
  PROCESSING: 'processing'
} as const;

type ErrorType = typeof ERROR_TYPES[keyof typeof ERROR_TYPES];

// HTTP status code to error type mapping
const HTTP_STATUS_TO_ERROR_TYPE: Record<number, ErrorType> = {
  400: ERROR_TYPES.VALIDATION,
  401: ERROR_TYPES.AUTHENTICATION,
  403: ERROR_TYPES.PERMISSION,
  404: ERROR_TYPES.NOT_FOUND,
  408: ERROR_TYPES.TIMEOUT,
  413: ERROR_TYPES.FILE_UPLOAD,
  429: ERROR_TYPES.RATE_LIMIT,
  500: ERROR_TYPES.SERVER,
  502: ERROR_TYPES.SERVER,
  503: ERROR_TYPES.SERVER,
  504: ERROR_TYPES.TIMEOUT
};

// Context-aware error messages
const ERROR_MESSAGES: Record<ErrorType, Record<string, ErrorMessage>> = {
  [ERROR_TYPES.NETWORK]: {
    default: {
      title: 'Connection Problem',
      message: 'Unable to connect to the server. Please check your internet connection.',
      suggestedActions: [
        'Check your internet connection',
        'Try refreshing the page',
        'Wait a moment and try again'
      ],
      severity: 'medium',
      recoverable: true
    },
    upload: {
      title: 'Upload Failed',
      message: 'Your file upload was interrupted due to a connection issue.',
      suggestedActions: [
        'Check your internet connection',
        'Try uploading the file again',
        'Use a smaller file if possible'
      ],
      severity: 'medium',
      recoverable: true
    },
    chat: {
      title: 'Chat Connection Lost',
      message: 'Lost connection to the chat service. Your conversation will resume when reconnected.',
      suggestedActions: [
        'Check your internet connection',
        'The chat will automatically reconnect',
        'Refresh the page if the issue persists'
      ],
      severity: 'low',
      recoverable: true
    }
  },

  [ERROR_TYPES.AUTHENTICATION]: {
    default: {
      title: 'Authentication Required',
      message: 'Your session has expired. Please log in again to continue.',
      suggestedActions: [
        'Click here to log in again',
        'Your progress has been saved'
      ],
      severity: 'high',
      recoverable: true
    },
    token_expired: {
      title: 'Session Expired',
      message: 'Your login session has expired for security reasons.',
      suggestedActions: [
        'Log in again to continue',
        'Enable "Remember me" for longer sessions'
      ],
      severity: 'medium',
      recoverable: true
    }
  },

  [ERROR_TYPES.VALIDATION]: {
    default: {
      title: 'Invalid Input',
      message: 'Please check your input and try again.',
      suggestedActions: [
        'Review the highlighted fields',
        'Make sure all required fields are filled',
        'Check the format of your input'
      ],
      severity: 'low',
      recoverable: true
    },
    file_upload: {
      title: 'Invalid File',
      message: 'The selected file doesn\'t meet the requirements.',
      suggestedActions: [
        'Check the file type (PDF, DOCX, TXT supported)',
        'Make sure the file is under 10MB',
        'Try a different file'
      ],
      severity: 'low',
      recoverable: true
    },
    form: {
      title: 'Form Validation Error',
      message: 'Some fields need your attention before you can continue.',
      suggestedActions: [
        'Check the highlighted fields below',
        'Make sure all required information is provided',
        'Correct any formatting errors'
      ],
      severity: 'low',
      recoverable: true
    }
  },

  [ERROR_TYPES.SERVER]: {
    default: {
      title: 'Server Error',
      message: 'Something went wrong on our end. We\'re working to fix it.',
      suggestedActions: [
        'Try again in a few minutes',
        'Contact support if the problem persists',
        'Your data has been saved'
      ],
      severity: 'high',
      recoverable: true
    },
    processing: {
      title: 'Processing Error',
      message: 'We couldn\'t process your content right now.',
      suggestedActions: [
        'Try uploading your content again',
        'Make sure your file is not corrupted',
        'Contact support if this keeps happening'
      ],
      severity: 'medium',
      recoverable: true
    }
  },

  [ERROR_TYPES.CLIENT]: {
    default: {
      title: 'Application Error',
      message: 'Something unexpected happened in the application.',
      suggestedActions: [
        'Refresh the page to continue',
        'Clear your browser cache if problems persist',
        'Try using a different browser'
      ],
      severity: 'medium',
      recoverable: true
    }
  },

  [ERROR_TYPES.TIMEOUT]: {
    default: {
      title: 'Request Timeout',
      message: 'The request is taking longer than expected.',
      suggestedActions: [
        'Try again - it might work faster now',
        'Check your internet connection',
        'Contact support if this keeps happening'
      ],
      severity: 'medium',
      recoverable: true
    },
    upload: {
      title: 'Upload Timeout',
      message: 'Your file upload is taking too long.',
      suggestedActions: [
        'Try uploading a smaller file',
        'Check your internet connection speed',
        'Try again during off-peak hours'
      ],
      severity: 'medium',
      recoverable: true
    }
  },

  [ERROR_TYPES.PERMISSION]: {
    default: {
      title: 'Access Denied',
      message: 'You don\'t have permission to perform this action.',
      suggestedActions: [
        'Make sure you\'re logged in',
        'Contact your administrator for access',
        'Try logging out and back in'
      ],
      severity: 'high',
      recoverable: false
    }
  },

  [ERROR_TYPES.NOT_FOUND]: {
    default: {
      title: 'Not Found',
      message: 'The requested content could not be found.',
      suggestedActions: [
        'Check if the link is correct',
        'Go back to the previous page',
        'Search for the content you\'re looking for'
      ],
      severity: 'medium',
      recoverable: false
    },
    lesson: {
      title: 'Lesson Not Found',
      message: 'This lesson is no longer available or has been moved.',
      suggestedActions: [
        'Return to your lesson library',
        'Search for similar lessons',
        'Contact support if you think this is an error'
      ],
      severity: 'medium',
      recoverable: false
    }
  },

  [ERROR_TYPES.RATE_LIMIT]: {
    default: {
      title: 'Too Many Requests',
      message: 'You\'re making requests too quickly. Please slow down.',
      suggestedActions: [
        'Wait a moment before trying again',
        'Avoid clicking buttons multiple times',
        'The limit will reset automatically'
      ],
      severity: 'low',
      recoverable: true
    }
  },

  [ERROR_TYPES.FILE_UPLOAD]: {
    default: {
      title: 'File Upload Error',
      message: 'There was a problem uploading your file.',
      suggestedActions: [
        'Make sure your file is under 10MB',
        'Check that the file type is supported',
        'Try uploading a different file'
      ],
      severity: 'medium',
      recoverable: true
    },
    size: {
      title: 'File Too Large',
      message: 'Your file is too large to upload.',
      suggestedActions: [
        'Use a file smaller than 10MB',
        'Compress your file if possible',
        'Split large documents into smaller parts'
      ],
      severity: 'low',
      recoverable: true
    },
    type: {
      title: 'Unsupported File Type',
      message: 'This file type is not supported.',
      suggestedActions: [
        'Use PDF, DOCX, or TXT files',
        'Convert your file to a supported format',
        'Contact support for other file types'
      ],
      severity: 'low',
      recoverable: true
    }
  },

  [ERROR_TYPES.PROCESSING]: {
    default: {
      title: 'Processing Failed',
      message: 'We couldn\'t process your content successfully.',
      suggestedActions: [
        'Try uploading your content again',
        'Make sure your file is readable and not corrupted',
        'Contact support if this keeps happening'
      ],
      severity: 'medium',
      recoverable: true
    }
  }
};

/**
 * Get user-friendly error message based on error details
 */
export function getErrorMessage(
  error: any,
  context: ErrorContext = {}
): ErrorMessage {
  let errorType: ErrorType = ERROR_TYPES.CLIENT;
  let contextKey = 'default';

  // Determine error type from various sources
  if (error?.response?.status) {
    errorType = HTTP_STATUS_TO_ERROR_TYPE[error.response.status] || ERROR_TYPES.SERVER;
  } else if (error?.code) {
    switch (error.code) {
      case 'NETWORK_ERROR':
      case 'ERR_NETWORK':
        errorType = ERROR_TYPES.NETWORK;
        break;
      case 'TIMEOUT':
      case 'ERR_TIMEOUT':
        errorType = ERROR_TYPES.TIMEOUT;
        break;
      case 'VALIDATION_ERROR':
        errorType = ERROR_TYPES.VALIDATION;
        break;
      case 'AUTH_ERROR':
        errorType = ERROR_TYPES.AUTHENTICATION;
        break;
      default:
        errorType = ERROR_TYPES.CLIENT;
    }
  } else if (error?.name === 'NetworkError') {
    errorType = ERROR_TYPES.NETWORK;
  } else if (error?.name === 'TimeoutError') {
    errorType = ERROR_TYPES.TIMEOUT;
  }

  // Determine context key
  if (context.component) {
    switch (context.component.toLowerCase()) {
      case 'upload':
      case 'uploadmodal':
        contextKey = 'upload';
        break;
      case 'chat':
      case 'studybuddy':
        contextKey = 'chat';
        break;
      case 'lesson':
      case 'lessonviewer':
        contextKey = 'lesson';
        break;
      case 'form':
        contextKey = 'form';
        break;
      case 'processing':
        contextKey = 'processing';
        break;
    }
  }

  if (context.action) {
    switch (context.action.toLowerCase()) {
      case 'upload':
        contextKey = 'upload';
        break;
      case 'login':
      case 'authenticate':
        contextKey = 'token_expired';
        break;
      case 'file_upload':
        contextKey = 'file_upload';
        break;
      case 'processing':
        contextKey = 'processing';
        break;
    }
  }

  // Handle specific error messages from server
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail.toLowerCase();
    if (detail.includes('file too large')) {
      errorType = ERROR_TYPES.FILE_UPLOAD;
      contextKey = 'size';
    } else if (detail.includes('unsupported file type')) {
      errorType = ERROR_TYPES.FILE_UPLOAD;
      contextKey = 'type';
    } else if (detail.includes('token expired')) {
      errorType = ERROR_TYPES.AUTHENTICATION;
      contextKey = 'token_expired';
    }
  }

  // Get the appropriate error message
  const errorMessages = ERROR_MESSAGES[errorType];
  const errorMessage = errorMessages[contextKey] || errorMessages.default;

  return {
    ...errorMessage,
    timestamp: new Date().toISOString()
  };
}

/**
 * Format validation errors for form fields
 */
export function formatValidationErrors(errors: Record<string, string[]>): Record<string, string> {
  const formatted: Record<string, string> = {};
  
  for (const [field, messages] of Object.entries(errors)) {
    formatted[field] = messages.join('. ');
  }
  
  return formatted;
}

/**
 * Check if an error is recoverable
 */
export function isRecoverableError(error: any, context: ErrorContext = {}): boolean {
  const errorMessage = getErrorMessage(error, context);
  return errorMessage.recoverable;
}

/**
 * Get error severity level
 */
export function getErrorSeverity(error: any, context: ErrorContext = {}): 'low' | 'medium' | 'high' | 'critical' {
  const errorMessage = getErrorMessage(error, context);
  return errorMessage.severity;
}

/**
 * Create a user-friendly error report
 */
export function createErrorReport(error: any, context: ErrorContext = {}) {
  const errorMessage = getErrorMessage(error, context);
  
  return {
    ...errorMessage,
    context,
    originalError: {
      message: error?.message,
      stack: error?.stack,
      code: error?.code,
      status: error?.response?.status,
      data: error?.response?.data
    },
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href
  };
}