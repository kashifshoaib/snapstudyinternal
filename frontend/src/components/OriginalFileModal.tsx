import React, { useEffect, useState } from 'react';
import { lessonService } from '../services/lessonService';
import './Modal.css';

interface OriginalFileModalProps {
  lessonId: string;
  lessonTitle: string;
  onClose: () => void;
}

const OriginalFileModal: React.FC<OriginalFileModalProps> = ({ lessonId, lessonTitle, onClose }) => {
  const [fileUrl, setFileUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileType, setFileType] = useState<string>('');

  useEffect(() => {
    loadFileUrl();
    // Cleanup blob URL when component unmounts
    return () => {
      if (fileUrl && fileUrl.startsWith('blob:')) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [lessonId]);

  const loadFileUrl = async () => {
    try {
      setLoading(true);

      // Detect file type from title
      const ext = lessonTitle.split('.').pop()?.toLowerCase();
      setFileType(ext || '');

      // Fetch the file as a blob with authentication headers
      const token = localStorage.getItem('auth_token');
      const baseUrl = (await import('../services/api')).default.defaults.baseURL || '';
      const url = `${baseUrl}/api/v1/lessons/${lessonId}/original-file`;

      console.log('Fetching file from:', url);

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to load file: ${response.statusText}`);
      }

      // Create blob from response
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      console.log('Blob URL created:', blobUrl);
      setFileUrl(blobUrl);
      setError(null);
    } catch (err) {
      setError('Failed to load original file');
      console.error('Error loading file:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const url = await lessonService.getOriginalFileUrl(lessonId);
      const link = document.createElement('a');
      link.href = url;
      link.download = lessonTitle;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error downloading file:', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content original-file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Original File: {lessonTitle}</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body" style={{ height: '70vh', display: 'flex', flexDirection: 'column' }}>
          {loading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading file...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <p>{error}</p>
              <button onClick={loadFileUrl}>Retry</button>
            </div>
          )}

          {!loading && !error && fileUrl && (
            <>
              {fileType === 'pdf' ? (
                <object
                  data={`${fileUrl}#toolbar=0`}
                  type="application/pdf"
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                >
                  <embed
                    src={`${fileUrl}#toolbar=0`}
                    type="application/pdf"
                    style={{
                      width: '100%',
                      height: '100%',
                      border: 'none',
                      borderRadius: '4px'
                    }}
                  />
                  <div style={{ padding: '20px', textAlign: 'center' }}>
                    <p>Unable to display PDF in browser.</p>
                    <button className="upload-confirm-button" onClick={handleDownload}>
                      Download PDF
                    </button>
                  </div>
                </object>
              ) : (
                <iframe
                  src={fileUrl}
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    borderRadius: '4px'
                  }}
                  title={`Original file: ${lessonTitle}`}
                />
              )}
            </>
          )}
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', padding: '16px' }}>
          <button className="cancel-button" onClick={onClose}>
            Close
          </button>
          <button className="upload-confirm-button" onClick={handleDownload}>
            Download
          </button>
        </div>
      </div>
    </div>
  );
};

export default OriginalFileModal;
