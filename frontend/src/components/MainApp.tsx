import React, { useState, useEffect } from 'react';
import { User, Lesson, MicroLesson, UserProfile } from '../types';
import { lessonService } from '../services/lessonService';
import Header from './Header';
import LessonLibrary from './LessonLibrary';
import LessonViewer from './LessonViewer';
import MultimediaLibrary from './MultimediaLibrary';
import StudyBuddy from './StudyBuddy';
import UserSettings from './UserSettings';
import Footer from './Footer';
import './MainApp.css';

interface MainAppProps {
  user: User;
  onLogout?: () => void;
}

type ViewType = 'lessons' | 'settings';

const MainApp: React.FC<MainAppProps> = ({ user, onLogout }) => {
  const [currentView, setCurrentView] = useState<ViewType>('lessons');
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selectedLesson, setSelectedLesson] = useState<Lesson | null>(null);
  const [microLessons, setMicroLessons] = useState<MicroLesson[]>([]);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

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
      const microLessonsData = await lessonService.getMicroLessons(lesson.lesson_id);
      setMicroLessons(microLessonsData);
    } catch (error) {
      console.error('Error loading micro lessons:', error);
    }
  };

  const handleLessonUpload = async (file: File) => {
    try {
      const newLesson = await lessonService.uploadLesson(file);
      setLessons(prev => [newLesson, ...prev]);
      setSelectedLesson(newLesson);
      
      // Load micro lessons for the new lesson
      const microLessonsData = await lessonService.getMicroLessons(newLesson.lesson_id);
      setMicroLessons(microLessonsData);
    } catch (error) {
      console.error('Error uploading lesson:', error);
    }
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
            />
          </main>

          <aside className="panel tutor" aria-label="Tutor">
            <StudyBuddy
              lesson={selectedLesson}
              user={user}
            />
          </aside>
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