import React, { useState, useEffect } from 'react';
import { User, Lesson, MicroLesson, UserProfile } from '../types';
import { lessonService } from '../services/lessonService';
import Header from './Header';
import LessonLibrary from './LessonLibrary';
import LessonViewer from './LessonViewer';
import MultimediaLibrary from './MultimediaLibrary';
import StudyBuddy from './StudyBuddy';
import UserSettings from './UserSettings';
import MyLibrary from './MyLibrary';
import Footer from './Footer';
import './MainApp.css';

interface MainAppProps {
  user: User;
  onLogout?: () => void;
}

type ViewType = 'lessons' | 'library' | 'settings';

const MainApp: React.FC<MainAppProps> = ({ user, onLogout }) => {
  const [currentView, setCurrentView] = useState<ViewType>('lessons');
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);
  const [microLessons, setMicroLessons] = useState<MicroLesson[]>([]);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [processingLesson, setProcessingLesson] = useState(false);

  useEffect(() => {
    initializeUser();
  }, [user]);

  const initializeUser = async () => {
    try {
      setLoading(true);

      // Load user lessons
      const userLessons = await lessonService.getUserLessons();
      setLessons(userLessons);

      if (userLessons.length > 0) {
        setSelectedLesson(userLessons[0]);
        // Load existing micro-lessons from cache/database (no generation on reload)
        const microLessonsData = await lessonService.getMicroLessons(userLessons[0].lesson_id);
        setMicroLessons(microLessonsData);
      }

    } catch (error) {
      console.error('Error initializing user:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLessonSelect = async (lesson: Lesson) => {
    setSelectedLesson(lesson);
    try {
      // Load existing micro-lessons from cache/database (no generation on select)
      const microLessonsData = await lessonService.getMicroLessons(lesson.lesson_id);
      setMicroLessons(microLessonsData);
    } catch (error) {
      console.error('Error loading micro lessons:', error);
    }
  };

  const handleLessonUpload = async (file: File) => {
    try {
      setProcessingLesson(true);
      const newLesson = await lessonService.uploadLesson(file);
      setLessons(prev => [newLesson, ...prev]);
      setSelectedLesson(newLesson);

      // Set empty micro lessons initially to show loading state
      setMicroLessons([]);

      // Poll for processing status and load micro lessons when ready
      await pollForMicroLessons(newLesson.lesson_id);

    } catch (error) {
      console.error('Error uploading lesson:', error);
      setProcessingLesson(false);
    }
  };

  const pollForMicroLessons = async (lessonId: string, maxAttempts = 30) => {
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        attempts++;

        // Try to load micro lessons
        const microLessonsData = await lessonService.getMicroLessons(lessonId);

        if (microLessonsData.length > 0) {
          // Success! Micro lessons are ready
          setMicroLessons(microLessonsData);
          setProcessingLesson(false);
          console.log('✅ Micro-lessons loaded successfully:', microLessonsData.length);
          return;
        }

        // Not ready yet, continue polling
        if (attempts < maxAttempts) {
          console.log(`⏳ Waiting for micro-lessons... (attempt ${attempts}/${maxAttempts})`);
          setTimeout(() => poll(), 2000); // Poll every 2 seconds
        } else {
          // Max attempts reached
          console.error('❌ Timeout waiting for micro-lessons');
          setProcessingLesson(false);
        }

      } catch (error) {
        console.error('Error polling for micro-lessons:', error);
        if (attempts < maxAttempts) {
          setTimeout(() => poll(), 2000);
        } else {
          setProcessingLesson(false);
        }
      }
    };

    // Start polling
    poll();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading your profile...</p>
      </div>
    );
  }

  return (
    <div className="main-app">
      <Header 
        user={user} 
        userProfile={userProfile}
        currentView={currentView}
        onViewChange={setCurrentView}
        onLogout={onLogout} 
      />
      
      {currentView === 'lessons' ? (
        <div className="app-grid">
          <section className="panel" aria-label="My Lessons">
            <LessonLibrary
              lessons={lessons}
              selectedLesson={selectedLesson}
              onLessonSelect={handleLessonSelect}
              onLessonUpload={handleLessonUpload}
            />
          </section>

          <main className="panel main" aria-label="Lesson Viewer">
            <LessonViewer
              lesson={selectedLesson}
              microLessons={microLessons}
              user={user}
              isProcessing={processingLesson}
            />
          </main>

          <aside className="panel tutor" aria-label="Tutor">
            <StudyBuddy
              lesson={selectedLesson}
              user={user}
            />
          </aside>
        </div>
      ) : currentView === 'library' ? (
        <div className="app-grid">
          <section className="panel full-width" aria-label="My Library">
            <MyLibrary
              lessons={lessons}
              onLessonSelect={(lesson) => {
                setSelectedLesson(lesson);
                setCurrentView('lessons');
              }}
            />
          </section>
        </div>
      ) : (
        <div className="settings-view">
          <UserSettings
            user={user}
            userProfile={userProfile}
            onProfileUpdate={setUserProfile}
            onLogout={onLogout}
          />
        </div>
      )}
      
      <Footer />
    </div>
  );
};

export default MainApp;