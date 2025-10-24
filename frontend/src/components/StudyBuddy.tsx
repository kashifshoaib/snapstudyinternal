import React, { useState, useEffect, useRef } from 'react';
import { Lesson, User, ChatMessage } from '../types';
import { chatService } from '../services/chatService';
import './StudyBuddy.css';

interface StudyBuddyProps {
  lesson: Lesson | null;
  user: User;
}

// Paper plane icon for send button
const PaperPlaneIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24">
    <path d="M2 21l20-9L2 3l5 8-5 10zm7-7 11-2-11-2 0 4z" fill="currentColor"/>
  </svg>
);

const StudyBuddy: React.FC<StudyBuddyProps> = ({ lesson, user }) => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize chat session and load history
  // Only re-initialize when lesson ID actually changes
  const lessonId = lesson?.lesson_id;
  const lessonIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    // Skip if lesson ID hasn't changed
    if (lessonId === lessonIdRef.current) {
      return;
    }

    lessonIdRef.current = lessonId;

    const initializeChat = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Generate a simple session ID locally (backend will create one if needed)
        const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        setSessionId(newSessionId);

        // Skip loading chat history for now (backend handles session creation)
        // Add welcome message for new sessions
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          content: '👋 Hi! Ask me to summarize, explain, or quiz you on this lesson.',
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages([welcomeMessage]);
      } catch (err) {
        console.error('Failed to initialize chat:', err);
        setError('Failed to connect to chat service. Please try again.');

        // Fallback to welcome message
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          content: '👋 Hi! Ask me to summarize, explain, or quiz you on this lesson.',
          sender: 'ai',
          timestamp: new Date()
        };
        setMessages([welcomeMessage]);
      } finally {
        setIsLoading(false);
      }
    };

    initializeChat();
  }, [lessonId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Cleanup WebSocket connection on unmount
  useEffect(() => {
    return () => {
      chatService.disconnect();
    };
  }, []);

  const handleSend = async () => {
    if (!message.trim() || isLoading) return;
    
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      content: message.trim(),
      sender: 'user',
      timestamp: new Date()
    };
    
    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    const messageContent = message.trim();
    setMessage('');
    setIsLoading(true);
    setError(null);
    
    // Create placeholder for streaming AI response
    const aiMessageId = `ai-${Date.now()}`;
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      content: '',
      sender: 'ai',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, aiMessage]);
    
    try {
      // Use HTTP API directly (WebSocket disabled for debugging)
      await fallbackToRegularAPI();
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
      setMessages(prev => 
        prev.map(msg => 
          msg.id === aiMessageId 
            ? { ...msg, content: '❌ Sorry, I encountered an error. Please try again.' }
            : msg
        )
      );
      setIsLoading(false);
    }
    
    async function fallbackToRegularAPI() {
      try {
        const response = await chatService.sendMessage(
          messageContent,
          lesson?.lesson_id,
          sessionId || undefined
        );
        
        // Update AI message with response
        setMessages(prev =>
          prev.map(msg =>
            msg.id === aiMessageId
              ? { ...msg, content: response.response }  // Use 'response' field from API
              : msg
          )
        );
        
        // Update session ID if provided
        if (response.session_id) {
          setSessionId(response.session_id);
        }
      } catch (fallbackErr) {
        console.error('Fallback API call failed:', fallbackErr);
        setError('Failed to send message. Please try again.');
        
        // Update AI message with error
        setMessages(prev => 
          prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: '❌ Sorry, I encountered an error. Please try again.' }
              : msg
          )
        );
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <div className="panel-header">Study Buddy</div>
      <div className="panel-body tutor-panel">
        {error && (
          <div className="error-message" style={{ 
            color: '#e74c3c', 
            padding: '8px', 
            marginBottom: '8px', 
            fontSize: '14px',
            backgroundColor: '#fdf2f2',
            border: '1px solid #fecaca',
            borderRadius: '4px'
          }}>
            {error}
          </div>
        )}
        
        <div className="thread">
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.sender === 'ai' ? 'ai' : 'me'}`}>
              {msg.content}
            </div>
          ))}
          
          {isLoading && (
            <div className="bubble ai">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        <div className="tutor-input">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? "AI is thinking..." : "Type a message…"}
            aria-label="Type a message"
            disabled={isLoading}
          />
        </div>
        
        <button 
          className="fab-send" 
          title="Send" 
          aria-label="Send" 
          onClick={handleSend}
          disabled={isLoading || !message.trim()}
          style={{ 
            opacity: isLoading || !message.trim() ? 0.5 : 1,
            cursor: isLoading || !message.trim() ? 'not-allowed' : 'pointer'
          }}
        >
          <PaperPlaneIcon />
        </button>
      </div>
    </>
  );
};

export default StudyBuddy;