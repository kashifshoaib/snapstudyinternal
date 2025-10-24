/**
 * Tests for enhanced error handling and loading states
 */

import { getErrorMessage, formatValidationErrors, isRecoverableError, getErrorSeverity } from '../utils/errorMessages';

// Mock analytics service
jest.mock('../services/analyticsService', () => ({
  analyticsService: {
    trackEngagementEvent: jest.fn(),
    trackError: jest.fn()
  }
}));

describe('Error Message Utils', () => {
  test('maps HTTP status codes to appropriate error types', () => {
    const error400 = { response: { status: 400 } };
    const error401 = { response: { status: 401 } };
    const error404 = { response: { status: 404 } };
    const error500 = { response: { status: 500 } };

    expect(getErrorMessage(error400).title).toBe('Invalid Input');
    expect(getErrorMessage(error401).title).toBe('Authentication Required');
    expect(getErrorMessage(error404).title).toBe('Not Found');
    expect(getErrorMessage(error500).title).toBe('Server Error');
  });

  test('provides context-aware error messages', () => {
    const networkError = { name: 'NetworkError' };

    const uploadContext = getErrorMessage(networkError, { component: 'upload' });
    const chatContext = getErrorMessage(networkError, { component: 'chat' });

    expect(uploadContext.title).toBe('Upload Failed');
    expect(chatContext.title).toBe('Chat Connection Lost');
  });

  test('formats validation errors correctly', () => {
    const validationErrors = {
      email: ['Invalid email format', 'Email is required'],
      password: ['Password too short']
    };

    const formatted = formatValidationErrors(validationErrors);

    expect(formatted.email).toBe('Invalid email format. Email is required');
    expect(formatted.password).toBe('Password too short');
  });

  test('determines error recoverability correctly', () => {
    const recoverableError = { response: { status: 500 } };
    const nonRecoverableError = { response: { status: 404 } };

    expect(isRecoverableError(recoverableError)).toBe(true);
    expect(isRecoverableError(nonRecoverableError)).toBe(false);
  });

  test('assigns appropriate severity levels', () => {
    const criticalError = { response: { status: 500 } };
    const lowError = { response: { status: 400 } };

    expect(getErrorSeverity(criticalError)).toBe('high');
    expect(getErrorSeverity(lowError)).toBe('low');
  });

  test('handles file upload specific errors', () => {
    const fileSizeError = {
      response: {
        status: 413,
        data: { detail: 'File too large' }
      }
    };

    const fileTypeError = {
      response: {
        status: 400,
        data: { detail: 'Unsupported file type' }
      }
    };

    const sizeMessage = getErrorMessage(fileSizeError);
    const typeMessage = getErrorMessage(fileTypeError);

    expect(sizeMessage.title).toBe('File Too Large');
    expect(typeMessage.title).toBe('Unsupported File Type');
  });

  test('creates comprehensive error reports', () => {
    const error = {
      name: 'TestError',
      message: 'Test error message',
      stack: 'Error stack trace'
    };

    const context = {
      component: 'upload',
      action: 'file_upload',
      userInput: { fileName: 'test.pdf' }
    };

    const errorMessage = getErrorMessage(error, context);

    expect(errorMessage.title).toBe('Upload Failed');
    expect(errorMessage.suggestedActions.length).toBeGreaterThan(0);
    expect(errorMessage.severity).toBeDefined();
    expect(errorMessage.recoverable).toBeDefined();
  });

  test('handles network errors appropriately', () => {
    const networkError = { name: 'NetworkError' };
    const timeoutError = { name: 'TimeoutError' };
    const connectionError = { code: 'ERR_NETWORK' };

    expect(getErrorMessage(networkError).title).toBe('Connection Problem');
    expect(getErrorMessage(timeoutError).title).toBe('Request Timeout');
    expect(getErrorMessage(connectionError).title).toBe('Connection Problem');
  });

  test('provides appropriate suggested actions', () => {
    const authError = { response: { status: 401 } };
    const serverError = { response: { status: 500 } };
    const validationError = { response: { status: 400 } };

    const authMessage = getErrorMessage(authError);
    const serverMessage = getErrorMessage(serverError);
    const validationMessage = getErrorMessage(validationError);

    expect(authMessage.suggestedActions).toContain('Click here to log in again');
    expect(serverMessage.suggestedActions).toContain('Try again in a few minutes');
    expect(validationMessage.suggestedActions).toContain('Review the highlighted fields');
  });
});