import React, { useState, useEffect } from 'react';
import { Lesson } from '../types';
import { lessonService } from '../services/lessonService';
import OriginalFileModal from './OriginalFileModal';
import './LessonLibrary.css';

interface MyLibraryProps {
  lessons: Lesson[];
  onLessonSelect?: (lesson: Lesson) => void;
}

// SVG Icons with theme colors
const PDFIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" fill="url(#grad1)" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 2V8H20" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M10 13H8V17" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M8 15H9.5" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <defs>
      <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.1"/>
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.15"/>
      </linearGradient>
    </defs>
  </svg>
);

const DocIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" fill="url(#grad2)" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 2V8H20" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M16 13H8" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M16 17H8" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <defs>
      <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.1"/>
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.15"/>
      </linearGradient>
    </defs>
  </svg>
);

const PresentationIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" fill="url(#grad3)" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 2V8H20" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <rect x="8" y="12" width="8" height="6" fill="#667eea" fillOpacity="0.2" stroke="#667eea" strokeWidth="1.5"/>
    <defs>
      <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.1"/>
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.15"/>
      </linearGradient>
    </defs>
  </svg>
);

const TextIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" fill="url(#grad4)" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 2V8H20" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M16 13H8M16 17H8M13 9H8" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <defs>
      <linearGradient id="grad4" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.1"/>
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.15"/>
      </linearGradient>
    </defs>
  </svg>
);

const DefaultFileIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" fill="url(#grad5)" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M13 2V9H20" stroke="#667eea" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <defs>
      <linearGradient id="grad5" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.1"/>
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.15"/>
      </linearGradient>
    </defs>
  </svg>
);

const MyLibrary: React.FC<MyLibraryProps> = ({ lessons, onLessonSelect }) => {
  const [selectedFileLesson, setSelectedFileLesson] = useState<Lesson | null>(null);
  const [showFileModal, setShowFileModal] = useState(false);

  const handleViewOriginalFile = (lesson: Lesson, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFileLesson(lesson);
    setShowFileModal(true);
  };

  const handleDownloadFile = async (lesson: Lesson, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await lessonService.viewOriginalFile(lesson.lesson_id);
    } catch (error) {
      console.error('Error downloading file:', error);
      alert('Failed to download file');
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getFileIcon = (lesson: Lesson) => {
    const ext = lesson.original_filename?.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return <PDFIcon />;
      case 'doc':
      case 'docx':
        return <DocIcon />;
      case 'ppt':
      case 'pptx':
        return <PresentationIcon />;
      case 'txt':
      case 'md':
        return <TextIcon />;
      default:
        return <DefaultFileIcon />;
    }
  };

  return (
    <>
      <div className="panel-header">My Library</div>
      <div className="panel-body">
        {lessons.length === 0 ? (
          <div className="empty-state">
            <p className="text-muted">No lessons uploaded yet</p>
            <p className="text-small">Upload your first lesson to get started!</p>
          </div>
        ) : (
          <div className="library-list">
            {lessons.map((lesson) => (
              <div
                key={lesson.lesson_id}
                className="library-item"
                onClick={() => onLessonSelect && onLessonSelect(lesson)}
              >
                <div className="library-item-icon">
                  {getFileIcon(lesson)}
                </div>
                <div className="library-item-details">
                  <h4 className="library-item-title">{lesson.title}</h4>
                  {lesson.original_filename && (
                    <p className="library-item-meta">
                      {lesson.original_filename}
                    </p>
                  )}
                  <p className="library-item-date">
                    Uploaded: {formatDate(lesson.created_at)}
                  </p>
                </div>
                <div className="library-item-actions">
                  <button
                    className="action-button view-button"
                    onClick={(e) => handleViewOriginalFile(lesson, e)}
                    title="View original file"
                  >
                    View
                  </button>
                  <button
                    className="action-button download-button"
                    onClick={(e) => handleDownloadFile(lesson, e)}
                    title="Download original file"
                  >
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showFileModal && selectedFileLesson && (
        <OriginalFileModal
          lessonId={selectedFileLesson.lesson_id}
          lessonTitle={selectedFileLesson.title}
          onClose={() => setShowFileModal(false)}
        />
      )}
    </>
  );
};

export default MyLibrary;
