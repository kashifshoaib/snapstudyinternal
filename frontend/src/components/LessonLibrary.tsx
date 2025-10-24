import React from 'react';
import { Lesson } from '../types';

interface LessonLibraryProps {
  lessons: Lesson[];
  selectedLesson: Lesson | null;
  onLessonSelect: (lesson: Lesson) => void;
  onLessonUpload: (file: File) => void;
}

// SVG Icons matching snapstudy.html
const CheckIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24">
    <path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" fill="currentColor"/>
  </svg>
);

const VideoIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24">
    <path d="M17 10.5V7a2 2 0 0 0-2-2H4C2.9 5 2 5.9 2 7v10a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3.5l5 3.5V7l-5 3.5z" fill="currentColor"/>
  </svg>
);

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20">
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
  </svg>
);

const LessonLibrary: React.FC<LessonLibraryProps> = ({
  lessons,
  selectedLesson,
  onLessonSelect,
  onLessonUpload
}) => {
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onLessonUpload(file);
    }
  };

  return (
    <>
      <div className="panel-header">
        <span>My Library</span>
        <button className="plus-btn" title="Upload New Lesson">
          <input
            type="file"
            id="file-upload"
            accept=".pdf,.doc,.docx,.txt"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <label htmlFor="file-upload" style={{ cursor: 'pointer', display: 'flex' }}>
            <PlusIcon />
          </label>
        </button>
      </div>
      <div className="panel-body">
        <div className="list">
          {lessons.length === 0 ? (
            <>
              <div className="row">
                <div className="icon green"><CheckIcon /></div>
                <div className="title">Neural Nets 101</div>
              </div>
              <div className="row">
                <div className="icon gray"><VideoIcon /></div>
                <div className="title">Reinforcement Learning</div>
              </div>
              <div className="row">
                <div className="icon gray"><VideoIcon /></div>
                <div className="title">Vector Databases</div>
              </div>
            </>
          ) : (
            lessons.map((lesson) => (
              <div
                key={lesson.lesson_id}
                className={`row ${selectedLesson?.lesson_id === lesson.lesson_id ? 'selected' : ''}`}
                onClick={() => onLessonSelect(lesson)}
              >
                <div className={`icon ${lesson.status === 'completed' ? 'green' : 'gray'}`}>
                  {lesson.status === 'completed' ? <CheckIcon /> : <VideoIcon />}
                </div>
                <div className="title">{lesson.title}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
};

export default LessonLibrary;