import React, { useState } from 'react';
import { useProcessingStatus } from '../hooks/useProcessingStatus';
import ProcessingStatusIndicator from './ProcessingStatusIndicator';
import ProcessingStatusModal from './ProcessingStatusModal';

/**
 * Example component demonstrating how to use the processing status service
 * This component shows different ways to integrate processing status monitoring
 */
const ProcessingExample: React.FC = () => {
  const [lessonId, setLessonId] = useState<string>('');
  const [showModal, setShowModal] = useState(false);

  // Example 1: Using the hook with auto-start
  const { 
    status: autoStatus, 
    isPolling: autoPolling, 
    error: autoError,
    startPolling: startAutoPolling,
    stopPolling: stopAutoPolling 
  } = useProcessingStatus(undefined, {
    onComplete: (status) => {
      console.log('Processing completed:', status);
      alert(`Processing completed for lesson: ${status.lesson_id}`);
    },
    onError: (error) => {
      console.error('Processing error:', error);
      alert(`Processing error: ${error}`);
    }
  });

  // Example 2: Manual polling control
  const { 
    status: manualStatus, 
    isPolling: manualPolling,
    startPolling: startManualPolling,
    stopPolling: stopManualPolling 
  } = useProcessingStatus();

  const handleStartAutoPolling = () => {
    if (lessonId.trim()) {
      startAutoPolling(lessonId.trim());
    }
  };

  const handleStartManualPolling = () => {
    if (lessonId.trim()) {
      startManualPolling(lessonId.trim());
    }
  };

  const handleShowModal = () => {
    if (lessonId.trim()) {
      setShowModal(true);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Processing Status Service Examples</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <label htmlFor="lessonId">Lesson ID:</label>
        <input
          id="lessonId"
          type="text"
          value={lessonId}
          onChange={(e) => setLessonId(e.target.value)}
          placeholder="Enter lesson ID (e.g., lesson-123)"
          style={{ 
            marginLeft: '10px', 
            padding: '8px', 
            width: '200px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
      </div>

      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr 1fr' }}>
        {/* Example 1: Auto-polling with callbacks */}
        <div style={{ border: '1px solid #e0e0e0', padding: '16px', borderRadius: '8px' }}>
          <h3>Example 1: Auto-polling with Callbacks</h3>
          <p>This example shows automatic polling with completion and error callbacks.</p>
          
          <div style={{ marginBottom: '16px' }}>
            <button 
              onClick={handleStartAutoPolling}
              disabled={!lessonId.trim() || autoPolling}
              style={{ 
                marginRight: '8px',
                padding: '8px 16px',
                backgroundColor: autoPolling ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: autoPolling ? 'not-allowed' : 'pointer'
              }}
            >
              {autoPolling ? 'Polling...' : 'Start Auto Polling'}
            </button>
            
            <button 
              onClick={stopAutoPolling}
              disabled={!autoPolling}
              style={{ 
                padding: '8px 16px',
                backgroundColor: !autoPolling ? '#ccc' : '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: !autoPolling ? 'not-allowed' : 'pointer'
              }}
            >
              Stop Polling
            </button>
          </div>

          {autoStatus && (
            <ProcessingStatusIndicator 
              status={autoStatus} 
              compact={false}
            />
          )}

          {autoError && (
            <div style={{ 
              background: '#ffebee', 
              border: '1px solid #ffcdd2', 
              padding: '12px', 
              borderRadius: '4px',
              color: '#c62828'
            }}>
              Error: {autoError}
            </div>
          )}
        </div>

        {/* Example 2: Manual polling control */}
        <div style={{ border: '1px solid #e0e0e0', padding: '16px', borderRadius: '8px' }}>
          <h3>Example 2: Manual Polling Control</h3>
          <p>This example shows manual control over polling without automatic callbacks.</p>
          
          <div style={{ marginBottom: '16px' }}>
            <button 
              onClick={handleStartManualPolling}
              disabled={!lessonId.trim() || manualPolling}
              style={{ 
                marginRight: '8px',
                padding: '8px 16px',
                backgroundColor: manualPolling ? '#ccc' : '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: manualPolling ? 'not-allowed' : 'pointer'
              }}
            >
              {manualPolling ? 'Polling...' : 'Start Manual Polling'}
            </button>
            
            <button 
              onClick={stopManualPolling}
              disabled={!manualPolling}
              style={{ 
                padding: '8px 16px',
                backgroundColor: !manualPolling ? '#ccc' : '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: !manualPolling ? 'not-allowed' : 'pointer'
              }}
            >
              Stop Polling
            </button>
          </div>

          {manualStatus && (
            <ProcessingStatusIndicator 
              status={manualStatus} 
              compact={true}
            />
          )}
        </div>
      </div>

      {/* Example 3: Modal display */}
      <div style={{ 
        border: '1px solid #e0e0e0', 
        padding: '16px', 
        borderRadius: '8px',
        marginTop: '20px'
      }}>
        <h3>Example 3: Modal Display</h3>
        <p>This example shows processing status in a modal dialog.</p>
        
        <button 
          onClick={handleShowModal}
          disabled={!lessonId.trim()}
          style={{ 
            padding: '8px 16px',
            backgroundColor: !lessonId.trim() ? '#ccc' : '#6f42c1',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: !lessonId.trim() ? 'not-allowed' : 'pointer'
          }}
        >
          Show Processing Modal
        </button>
      </div>

      {/* Processing Status Modal */}
      {showModal && lessonId && (
        <ProcessingStatusModal
          lessonId={lessonId}
          onClose={() => setShowModal(false)}
          onComplete={(completedLessonId) => {
            console.log('Modal: Processing completed for', completedLessonId);
            setShowModal(false);
          }}
          onError={(error) => {
            console.error('Modal: Processing error:', error);
          }}
          title="Example Processing Status"
        />
      )}

      {/* Usage Instructions */}
      <div style={{ 
        marginTop: '40px', 
        padding: '20px', 
        backgroundColor: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <h3>Usage Instructions</h3>
        <ol>
          <li>Enter a lesson ID in the input field above</li>
          <li>Try different examples to see various integration patterns</li>
          <li>Example 1 shows automatic polling with completion callbacks</li>
          <li>Example 2 demonstrates manual polling control</li>
          <li>Example 3 displays processing status in a modal</li>
        </ol>
        
        <h4>Integration Patterns:</h4>
        <ul>
          <li><strong>Hook-based:</strong> Use <code>useProcessingStatus</code> for component-level integration</li>
          <li><strong>Service-based:</strong> Use <code>processingService</code> directly for more control</li>
          <li><strong>Component-based:</strong> Use <code>ProcessingStatusIndicator</code> and <code>ProcessingStatusModal</code> for UI</li>
        </ul>
      </div>
    </div>
  );
};

export default ProcessingExample;