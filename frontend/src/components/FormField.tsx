/**
 * Enhanced form field component with validation error highlighting
 */

import React, { useState, useEffect } from 'react';
import { getErrorMessage } from '../utils/errorMessages';
import { InputValidator, ValidationRule, ValidationResult } from '../utils/inputValidation';
import './FormField.css';

interface FormFieldProps {
  label: string;
  name: string;
  type?: 'text' | 'email' | 'password' | 'textarea' | 'file' | 'select';
  value?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string | string[];
  options?: Array<{ value: string; label: string }>;
  accept?: string; // for file inputs
  multiple?: boolean; // for file inputs
  rows?: number; // for textarea
  onChange?: (value: string, files?: FileList | null, validationResult?: ValidationResult) => void;
  onBlur?: () => void;
  onFocus?: () => void;
  className?: string;
  helpText?: string;
  maxLength?: number;
  minLength?: number;
  pattern?: string;
  autoComplete?: string;
  validationRules?: ValidationRule;
  sanitizeInput?: boolean;
  allowedFileTypes?: string[];
  maxFileSize?: number; // in bytes
}

const FormField: React.FC<FormFieldProps> = ({
  label,
  name,
  type = 'text',
  value = '',
  placeholder,
  required = false,
  disabled = false,
  error,
  options = [],
  accept,
  multiple = false,
  rows = 3,
  onChange,
  onBlur,
  onFocus,
  className = '',
  helpText,
  maxLength,
  minLength,
  pattern,
  autoComplete,
  validationRules,
  sanitizeInput = true,
  allowedFileTypes = [],
  maxFileSize = 10 * 1024 * 1024 // 10MB default
}) => {
  const [focused, setFocused] = useState(false);
  const [touched, setTouched] = useState(false);
  const [internalValue, setInternalValue] = useState(value);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    setInternalValue(value);
  }, [value]);

  const externalErrors = error ? (Array.isArray(error) ? error : [error]) : [];
  const allErrors = [...externalErrors, ...validationErrors];
  const hasError = allErrors.length > 0;
  const showError = hasError && touched;

  const validateInput = (inputValue: string, files?: FileList | null): ValidationResult => {
    let validationResult: ValidationResult = { isValid: true, errors: [] };

    if (type === 'file' && files) {
      // Validate files
      for (let i = 0; i < files.length; i++) {
        const fileValidation = InputValidator.validateFile(files[i], {
          maxSize: maxFileSize,
          allowedTypes: allowedFileTypes.length > 0 ? allowedFileTypes : undefined,
          allowedExtensions: accept ? accept.split(',').map(ext => ext.trim().replace('.', '')) : undefined
        });
        
        if (!fileValidation.isValid) {
          validationResult.errors.push(...fileValidation.errors);
        }
      }
      validationResult.isValid = validationResult.errors.length === 0;
    } else {
      // Validate text input
      const rules: ValidationRule = {
        required,
        minLength,
        maxLength,
        pattern: pattern ? new RegExp(pattern) : undefined,
        ...validationRules
      };

      if (type === 'email') {
        validationResult = InputValidator.validateEmail(inputValue);
      } else if (type === 'password') {
        validationResult = InputValidator.validatePassword(inputValue);
      } else {
        validationResult = InputValidator.validateText(inputValue, rules);
      }
    }

    return validationResult;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    let newValue = e.target.value;
    let files: FileList | null = null;

    if (type === 'file') {
      const fileInput = e.target as HTMLInputElement;
      files = fileInput.files;
    } else if (sanitizeInput && typeof newValue === 'string') {
      // Sanitize text input
      newValue = InputValidator.sanitizeString(newValue);
    }

    setInternalValue(newValue);

    // Validate input
    const validationResult = validateInput(newValue, files);
    setValidationErrors(validationResult.errors);

    // Call onChange with validation result
    onChange?.(newValue, files, validationResult);
  };

  const handleFocus = () => {
    setFocused(true);
    onFocus?.();
  };

  const handleBlur = () => {
    setFocused(false);
    setTouched(true);
    onBlur?.();
  };

  const getFieldClass = () => {
    let classes = 'form-field-input';
    
    if (showError) {
      classes += ' form-field-error';
    } else if (touched && !hasError && internalValue) {
      classes += ' form-field-success';
    }
    
    if (focused) {
      classes += ' form-field-focused';
    }
    
    if (disabled) {
      classes += ' form-field-disabled';
    }
    
    return classes;
  };

  const renderInput = () => {
    const commonProps = {
      id: name,
      name,
      value: internalValue,
      placeholder,
      required,
      disabled,
      onChange: handleChange,
      onFocus: handleFocus,
      onBlur: handleBlur,
      className: getFieldClass(),
      maxLength,
      minLength,
      pattern,
      autoComplete
    };

    switch (type) {
      case 'textarea':
        return (
          <textarea
            {...commonProps}
            rows={rows}
          />
        );

      case 'select':
        return (
          <select {...commonProps}>
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'file':
        return (
          <input
            {...commonProps}
            type="file"
            accept={accept}
            multiple={multiple}
            value={undefined} // File inputs can't have controlled values
          />
        );

      default:
        return (
          <input
            {...commonProps}
            type={type}
          />
        );
    }
  };

  const renderError = () => {
    if (!showError) return null;
    
    return (
      <div className="form-field-error-messages">
        {allErrors.map((msg, index) => (
          <div key={index} className="form-field-error-message">
            <span className="form-field-error-icon">⚠️</span>
            {msg}
          </div>
        ))}
      </div>
    );
  };

  const renderCharacterCount = () => {
    if (!maxLength || type === 'file') return null;

    const currentLength = internalValue.length;
    const isNearLimit = currentLength > maxLength * 0.8;
    
    return (
      <div className={`form-field-character-count ${isNearLimit ? 'near-limit' : ''}`}>
        {currentLength}/{maxLength}
      </div>
    );
  };

  return (
    <div className={`form-field ${className}`}>
      <label htmlFor={name} className="form-field-label">
        {label}
        {required && <span className="form-field-required">*</span>}
      </label>
      
      <div className="form-field-input-container">
        {renderInput()}
        {type === 'file' && (
          <div className="form-field-file-info">
            {accept && (
              <small className="form-field-accept">
                Accepted formats: {accept.replace(/\./g, '').toUpperCase()}
              </small>
            )}
          </div>
        )}
      </div>
      
      {renderError()}
      
      {helpText && !showError && (
        <div className="form-field-help">
          {helpText}
        </div>
      )}
      
      {renderCharacterCount()}
    </div>
  );
};

// Specialized form field components
export const EmailField: React.FC<Omit<FormFieldProps, 'type'>> = (props) => (
  <FormField 
    {...props} 
    type="email" 
    autoComplete="email"
    pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
  />
);

export const PasswordField: React.FC<Omit<FormFieldProps, 'type'>> = (props) => (
  <FormField 
    {...props} 
    type="password" 
    autoComplete="current-password"
    minLength={8}
  />
);

export const FileUploadField: React.FC<Omit<FormFieldProps, 'type'> & {
  maxSize?: number; // in MB
  onFileValidation?: (files: FileList | null) => string | null;
}> = ({ maxSize = 10, onFileValidation, onChange, ...props }) => {
  const handleFileChange = (value: string, files?: FileList | null, validationResult?: ValidationResult) => {
    let validationError: string | null = null;

    if (files && files.length > 0) {
      // Check file size
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.size > maxSize * 1024 * 1024) {
          validationError = `File "${file.name}" is too large. Maximum size is ${maxSize}MB.`;
          break;
        }
      }

      // Custom validation
      if (!validationError && onFileValidation) {
        validationError = onFileValidation(files);
      }
    }

    onChange?.(value, files);
  };

  return (
    <FormField 
      {...props} 
      type="file"
      onChange={handleFileChange}
      helpText={props.helpText || `Maximum file size: ${maxSize}MB`}
    />
  );
};

export default FormField;