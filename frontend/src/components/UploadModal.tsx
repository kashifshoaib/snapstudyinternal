import React, { useState, useRef } from 'react';
import { processingService } from '../services/processingService';
import ProcessingStatusModal from './ProcessingStatusModal';
import { UploadErrorDisplay } from './ErrorDisplay';
import { FileUploadField } from './FormField';
import { getErrorMessage } from '../utils/errorMessages';
import { InputValidator } from '../utils/inputValidation';
import './Modal.css';

interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  id: string;
}

interface UploadModalProps {
  onUpload: (file: File, onProgress?: (progress: number) => void) => Promise<{ lesson_id: string }>;
  onClose: () => void;
  onProcessingComplete?: (lessonId: string) => void;
}

// File validation constants
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'text/markdown',
  'application/rtf'
];

const ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.md', '.rtf'];

const UploadModal: React.FC<UploadModalProps> = ({ onUpload, onClose, onProcessingComplete }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadProgress[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [processingLessonId, setProcessingLessonId] = useState<string | null>(null);
  const [showProcessingModal, setShowProcessingModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File validation functions
  const validateFile = (file: File): string | null => {
    const validation = InputValidator.validateFile(file, {
      maxSize: MAX_FILE_SIZE,
      allowedTypes: ALLOWED_FILE_TYPES,
      allowedExtensions: ALLOWED_EXTENSIONS.map(ext => ext.replace('.', ''))
    });

    if (!validation.isValid) {
      return validation.errors.join(', ');
    }

    return null;
  };

  const validateFiles = (files: File[]): { validFiles: File[], errors: string[] } => {
    const validFiles: File[] = [];
    const errors: string[] = [];

    files.forEach(file => {
      const error = validateFile(file);
      if (error) {
        errors.push(error);
      } else {
        validFiles.push(file);
      }
    });

    return { validFiles, errors };
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files) {
      const files = Array.from(e.dataTransfer.files);
      addFilesToQueue(files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      addFilesToQueue(files);
    }
  };

  const addFilesToQueue = (files: File[]) => {
    const { validFiles, errors } = validateFiles(files);
    
    setValidationErrors(errors);
    
    if (validFiles.length > 0) {
      const newUploads: UploadProgress[] = validFiles.map(file => ({
        file,
        progress: 0,
        status: 'pending' as const,
        id: `${file.name}-${Date.now()}-${Math.random()}`
      }));
      
      setUploadQueue(prev => [...prev, ...newUploads]);
    }
  };

  const updateUploadProgress = (id: string, progress: number, status: UploadProgress['status'], error?: string) => {
    setUploadQueue(prev => prev.map(upload => 
      upload.id === id 
        ? { ...upload, progress, status, error }
        : upload
    ));
  };

  const handleUpload = async (uploadItem: UploadProgress) => {
    updateUploadProgress(uploadItem.id, 0, 'uploading');
    
    try {
      const result = await onUpload(uploadItem.file, (progress) => {
        updateUploadProgress(uploadItem.id, progress, 'uploading');
      });
      
      updateUploadProgress(uploadItem.id, 100, 'completed');
      
      // Start processing status monitoring
      if (result.lesson_id) {
        setProcessingLessonId(result.lesson_id);
        setShowProcessingModal(true);
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error, { component: 'upload', action: 'file_upload' });
      updateUploadProgress(uploadItem.id, 0, 'error', errorMessage.message);
    }
  };

  const handleUploadAll = async () => {
    const pendingUploads = uploadQueue.filter(upload => upload.status === 'pending');
    
    // Process uploads concurrently
    const uploadPromises = pendingUploads.map(upload => handleUpload(upload));
    
    try {
      await Promise.allSettled(uploadPromises);
    } catch (error) {
      console.error('Some uploads failed:', error);
    }
  };

  const removeFromQueue = (id: string) => {
    setUploadQueue(prev => prev.filter(upload => upload.id !== id));
  };

  const clearQueue = () => {
    setUploadQueue([]);
    setValidationErrors([]);
  };

  const handleProcessingComplete = (lessonId: string) => {
    setShowProcessingModal(false);
    setProcessingLessonId(null);
    onProcessingComplete?.(lessonId);
    onClose();
  };

  const handleProcessingError = (error: string) => {
    console.error('Processing error:', error);
    // Keep modal open to show error state
  };

  const handleProcessingModalClose = () => {
    setShowProcessingModal(false);
    // Don't reset processingLessonId in case user wants to check status later
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Upload Learning Material</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div 
            className={`upload-area ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.ppt,.pptx,.md,.rtf"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            
            {uploadQueue.length > 0 ? (
              <div className="files-selected">
                <div className="upload-icon">📁</div>
                <p>{uploadQueue.length} file{uploadQueue.length > 1 ? 's' : ''} selected</p>
                <p className="upload-subtitle">Ready to upload</p>
              </div>
            ) : (
              <div className="upload-prompt">
                <div className="upload-icon">📁</div>
                <p>Drag and drop your files here</p>
                <p className="upload-subtitle">or click to browse</p>
                <p className="supported-formats">
                  Supported: PDF, DOC, DOCX, TXT, PPT, PPTX, MD, RTF (Max 50MB each)
                </p>
              </div>
            )}
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <UploadErrorDisplay
              error={{ 
                message: 'File validation failed',
                validationErrors: validationErrors.map(err => ({ field: 'file', message: err }))
              }}
              onRetry={() => setValidationErrors([])}
              className="upload-validation-errors"
            />
          )}

          {/* Upload Queue */}
          {uploadQueue.length > 0 && (
            <div className="upload-queue">
              <div className="queue-header">
                <h4>Upload Queue ({uploadQueue.length} files)</h4>
                <button className="clear-queue-button" onClick={clearQueue}>
                  Clear All
                </button>
              </div>
              
              <div className="queue-items">
                {uploadQueue.map((upload) => (
                  <div key={upload.id} className="queue-item">
                    <div className="file-info">
                      <div className="file-icon">
                        {upload.status === 'completed' ? '✅' : 
                         upload.status === 'error' ? '❌' : 
                         upload.status === 'uploading' ? '⏳' : '📄'}
                      </div>
                      <div className="file-details">
                        <p className="file-name">{upload.file.name}</p>
                        <p className="file-size">{formatFileSize(upload.file.size)}</p>
                        {upload.error && (
                          <p className="error-text">{upload.error}</p>
                        )}
                      </div>
                    </div>
                    
                    {upload.status === 'uploading' && (
                      <div className="progress-container">
                        <div className="progress-bar">
                          <div 
                            className="progress-fill" 
                            style={{ width: `${upload.progress}%` }}
                          />
                        </div>
                        <span className="progress-text">{Math.round(upload.progress)}%</span>
                      </div>
                    )}
                    
                    {upload.status === 'pending' && (
                      <button 
                        className="remove-file-button"
                        onClick={() => removeFromQueue(upload.id)}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
              
              <div className="upload-actions">
                <button 
                  className="cancel-button" 
                  onClick={clearQueue}
                >
                  Clear Queue
                </button>
                <button 
                  className="upload-confirm-button" 
                  onClick={handleUploadAll}
                  disabled={uploadQueue.every(u => u.status !== 'pending')}
                >
                  Upload All Files
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Processing Status Modal */}
        {showProcessingModal && processingLessonId && (
          <ProcessingStatusModal
            lessonId={processingLessonId}
            onClose={handleProcessingModalClose}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
            title="Processing Your Content"
          />
        )}
      </div>
    </div>
  );
};

export default UploadModal;