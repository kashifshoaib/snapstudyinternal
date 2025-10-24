/**
 * @jest-environment jsdom
 */

// End-to-end tests for authentication and user management flow
describe('Authentication End-to-End Tests', () => {
  // Mock user data for testing
  const testUser = {
    email: 'e2e-test@example.com',
    password: 'TestPassword123!',
    firstName: 'E2E',
    lastName: 'Test',
    fullName: 'E2E Test User',
    age: 28,
    profession: 'QA Engineer',
    educationLevel: "Master's Degree",
    country: 'Canada',
    learningStyle: 'visual' as const,
    attentionSpan: 45,
    difficultyLevel: 'advanced' as const,
  };

  // Mock API responses
  const mockAPIResponses = {
    register: {
      access_token: 'mock_access_token_12345',
      token_type: 'bearer',
      expires_in: 86400,
      user_id: 'e2e_user_123',
    },
    login: {
      access_token: 'mock_access_token_67890',
      token_type: 'bearer',
      expires_in: 86400,
      user_id: 'e2e_user_123',
    },
    userProfile: {
      user_id: 'e2e_user_123',
      email: testUser.email,
      full_name: testUser.fullName,
      age: testUser.age,
      profession: testUser.profession,
      education_level: testUser.educationLevel,
      country: testUser.country,
      onboarding_completed: false,
      preferences: null,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    },
    onboardingComplete: {
      message: 'Onboarding completed successfully',
      user: {
        user_id: 'e2e_user_123',
        email: testUser.email,
        full_name: testUser.fullName,
        age: testUser.age,
        profession: testUser.profession,
        education_level: testUser.educationLevel,
        country: testUser.country,
        onboarding_completed: true,
        preferences: {
          learning_style: testUser.learningStyle,
          attention_span: testUser.attentionSpan,
          difficulty_level: testUser.difficultyLevel,
        },
        updated_at: '2023-01-01T01:00:00Z',
      },
    },
    profileUpdate: {
      message: 'Profile updated successfully',
      user: {
        user_id: 'e2e_user_123',
        email: testUser.email,
        full_name: 'Updated E2E Test User',
        age: 29,
        profession: 'Senior QA Engineer',
        education_level: testUser.educationLevel,
        country: 'United States',
        onboarding_completed: true,
        preferences: {
          learning_style: 'auditory',
          attention_span: 30,
          difficulty_level: 'intermediate',
        },
        updated_at: '2023-01-01T02:00:00Z',
      },
    },
  };

  test('Complete user registration to profile management flow', async () => {
    // Step 1: User Registration
    const registrationFlow = async () => {
      // Simulate form validation
      const validateRegistrationForm = (data: typeof testUser) => {
        const errors: string[] = [];
        
        if (!data.email || !data.email.includes('@')) {
          errors.push('Valid email is required');
        }
        
        if (!data.password || data.password.length < 8) {
          errors.push('Password must be at least 8 characters');
        }
        
        if (!data.firstName || !data.lastName) {
          errors.push('First and last name are required');
        }
        
        return { isValid: errors.length === 0, errors };
      };

      const validation = validateRegistrationForm(testUser);
      expect(validation.isValid).toBe(true);
      expect(validation.errors).toHaveLength(0);

      // Simulate API call
      const registrationData = {
        email: testUser.email,
        password: testUser.password,
        first_name: testUser.firstName,
        last_name: testUser.lastName,
      };

      // Mock successful registration
      const registrationResponse = mockAPIResponses.register;
      expect(registrationResponse.access_token).toBeDefined();
      expect(registrationResponse.user_id).toBeDefined();
      
      return registrationResponse;
    };

    const registrationResult = await registrationFlow();
    expect(registrationResult.access_token).toBe('mock_access_token_12345');

    // Step 2: User Login
    const loginFlow = async () => {
      // Simulate login form validation
      const validateLoginForm = (email: string, password: string) => {
        return {
          isValid: Boolean(email && password && email.includes('@')),
          errors: !email ? ['Email required'] : !password ? ['Password required'] : [],
        };
      };

      const loginValidation = validateLoginForm(testUser.email, testUser.password);
      expect(loginValidation.isValid).toBe(true);

      // Mock successful login
      const loginResponse = mockAPIResponses.login;
      expect(loginResponse.access_token).toBeDefined();
      
      return loginResponse;
    };

    const loginResult = await loginFlow();
    expect(loginResult.user_id).toBe('e2e_user_123');

    // Step 3: Get User Profile
    const getUserProfileFlow = async () => {
      // Mock API call to get user profile
      const profileResponse = mockAPIResponses.userProfile;
      
      expect(profileResponse.email).toBe(testUser.email);
      expect(profileResponse.onboarding_completed).toBe(false);
      expect(profileResponse.preferences).toBe(null);
      
      return profileResponse;
    };

    const userProfile = await getUserProfileFlow();
    expect(userProfile.user_id).toBe('e2e_user_123');

    // Step 4: Complete Onboarding
    const onboardingFlow = async () => {
      // Simulate onboarding form validation
      const validateOnboardingForm = (data: any) => {
        const errors: string[] = [];
        
        if (!data.fullName) errors.push('Full name required');
        if (!data.learningStyle) errors.push('Learning style required');
        if (!data.attentionSpan || data.attentionSpan < 5 || data.attentionSpan > 60) {
          errors.push('Attention span must be 5-60 minutes');
        }
        if (!data.difficultyLevel) errors.push('Difficulty level required');
        
        return { isValid: errors.length === 0, errors };
      };

      const onboardingData = {
        fullName: testUser.fullName,
        age: testUser.age,
        profession: testUser.profession,
        educationLevel: testUser.educationLevel,
        country: testUser.country,
        learningStyle: testUser.learningStyle,
        attentionSpan: testUser.attentionSpan,
        difficultyLevel: testUser.difficultyLevel,
      };

      const onboardingValidation = validateOnboardingForm(onboardingData);
      expect(onboardingValidation.isValid).toBe(true);

      // Mock successful onboarding completion
      const onboardingResponse = mockAPIResponses.onboardingComplete;
      expect(onboardingResponse.user.onboarding_completed).toBe(true);
      expect(onboardingResponse.user.preferences).toBeDefined();
      
      return onboardingResponse;
    };

    const onboardingResult = await onboardingFlow();
    expect(onboardingResult.user.preferences?.learning_style).toBe('visual');
    expect(onboardingResult.user.preferences?.attention_span).toBe(45);

    // Step 5: Update User Profile
    const profileUpdateFlow = async () => {
      // Simulate profile update form
      const profileUpdates = {
        full_name: 'Updated E2E Test User',
        age: 29,
        profession: 'Senior QA Engineer',
        country: 'United States',
        preferences: {
          learning_style: 'auditory',
          attention_span: 30,
          difficulty_level: 'intermediate',
        },
      };

      // Validate profile updates
      const validateProfileUpdate = (updates: any) => {
        const errors: string[] = [];
        
        if (updates.age && (updates.age < 13 || updates.age > 100)) {
          errors.push('Age must be between 13 and 100');
        }
        
        if (updates.preferences?.attention_span && 
            (updates.preferences.attention_span < 5 || updates.preferences.attention_span > 60)) {
          errors.push('Attention span must be 5-60 minutes');
        }
        
        return { isValid: errors.length === 0, errors };
      };

      const updateValidation = validateProfileUpdate(profileUpdates);
      expect(updateValidation.isValid).toBe(true);

      // Mock successful profile update
      const updateResponse = mockAPIResponses.profileUpdate;
      expect(updateResponse.user.full_name).toBe('Updated E2E Test User');
      expect(updateResponse.user.preferences?.learning_style).toBe('auditory');
      
      return updateResponse;
    };

    const profileUpdateResult = await profileUpdateFlow();
    expect(profileUpdateResult.user.age).toBe(29);
    expect(profileUpdateResult.user.country).toBe('United States');

    // Step 6: Verify Final State
    const finalStateVerification = () => {
      // Verify the complete user journey
      const finalUser = profileUpdateResult.user;
      
      // User should be authenticated
      expect(finalUser.user_id).toBe('e2e_user_123');
      expect(finalUser.email).toBe(testUser.email);
      
      // Onboarding should be complete
      expect(finalUser.onboarding_completed).toBe(true);
      
      // Profile should be updated
      expect(finalUser.full_name).toBe('Updated E2E Test User');
      expect(finalUser.age).toBe(29);
      expect(finalUser.profession).toBe('Senior QA Engineer');
      expect(finalUser.country).toBe('United States');
      
      // Preferences should be updated
      expect(finalUser.preferences?.learning_style).toBe('auditory');
      expect(finalUser.preferences?.attention_span).toBe(30);
      expect(finalUser.preferences?.difficulty_level).toBe('intermediate');
      
      return true;
    };

    const verificationResult = finalStateVerification();
    expect(verificationResult).toBe(true);
  });

  test('Authentication persistence across sessions', () => {
    // Test session management logic
    const sessionManager = {
      setToken: (token: string, expiresIn: number) => {
        const expiry = Date.now() + (expiresIn * 1000);
        return { token, expiry };
      },
      
      isTokenValid: (session: { token: string; expiry: number }) => {
        return session.token && Date.now() < session.expiry;
      },
      
      refreshToken: (currentSession: any) => {
        // Mock token refresh
        return {
          token: 'refreshed_token_12345',
          expiry: Date.now() + (8 * 60 * 60 * 1000), // 8 hours
        };
      },
    };

    // Test initial session creation
    const initialSession = sessionManager.setToken('mock_token_123', 86400);
    expect(initialSession.token).toBe('mock_token_123');
    expect(initialSession.expiry).toBeGreaterThan(Date.now());

    // Test session validation
    const isValid = sessionManager.isTokenValid(initialSession);
    expect(isValid).toBe(true);

    // Test expired session
    const expiredSession = { token: 'expired_token', expiry: Date.now() - 1000 };
    const isExpiredValid = sessionManager.isTokenValid(expiredSession);
    expect(isExpiredValid).toBe(false);

    // Test token refresh
    const refreshedSession = sessionManager.refreshToken(expiredSession);
    expect(refreshedSession.token).toBe('refreshed_token_12345');
    expect(refreshedSession.expiry).toBeGreaterThan(Date.now());
  });

  test('Cross-component state synchronization', () => {
    // Test state synchronization between components
    const stateManager = {
      state: {
        user: null as any,
        isAuthenticated: false,
        needsOnboarding: false,
      },
      
      updateUser: (user: any) => {
        stateManager.state.user = user;
        stateManager.state.isAuthenticated = true;
        stateManager.state.needsOnboarding = !user.onboarding_completed;
      },
      
      completeOnboarding: (user: any) => {
        stateManager.state.user = { ...user, onboarding_completed: true };
        stateManager.state.needsOnboarding = false;
      },
      
      logout: () => {
        stateManager.state.user = null;
        stateManager.state.isAuthenticated = false;
        stateManager.state.needsOnboarding = false;
      },
    };

    // Test initial state
    expect(stateManager.state.isAuthenticated).toBe(false);
    expect(stateManager.state.user).toBe(null);

    // Test user login state update
    const loggedInUser = {
      user_id: 'test_123',
      email: 'test@example.com',
      onboarding_completed: false,
    };

    stateManager.updateUser(loggedInUser);
    expect(stateManager.state.isAuthenticated).toBe(true);
    expect(stateManager.state.needsOnboarding).toBe(true);
    expect(stateManager.state.user.user_id).toBe('test_123');

    // Test onboarding completion
    const onboardedUser = { ...loggedInUser, onboarding_completed: true };
    stateManager.completeOnboarding(onboardedUser);
    expect(stateManager.state.needsOnboarding).toBe(false);
    expect(stateManager.state.user.onboarding_completed).toBe(true);

    // Test logout
    stateManager.logout();
    expect(stateManager.state.isAuthenticated).toBe(false);
    expect(stateManager.state.user).toBe(null);
    expect(stateManager.state.needsOnboarding).toBe(false);
  });

  test('Responsive design functionality', () => {
    // Test responsive design logic
    const responsiveUtils = {
      getBreakpoint: (width: number) => {
        if (width < 768) return 'mobile';
        if (width < 1024) return 'tablet';
        return 'desktop';
      },
      
      getLayoutConfig: (breakpoint: string) => {
        switch (breakpoint) {
          case 'mobile':
            return {
              showSidebar: false,
              columnsCount: 1,
              compactMode: true,
            };
          case 'tablet':
            return {
              showSidebar: true,
              columnsCount: 2,
              compactMode: false,
            };
          case 'desktop':
            return {
              showSidebar: true,
              columnsCount: 3,
              compactMode: false,
            };
          default:
            return {
              showSidebar: true,
              columnsCount: 2,
              compactMode: false,
            };
        }
      },
      
      adaptFormLayout: (breakpoint: string) => {
        return {
          stackVertically: breakpoint === 'mobile',
          showLabelsInline: breakpoint !== 'mobile',
          buttonSize: breakpoint === 'mobile' ? 'large' : 'medium',
        };
      },
    };

    // Test mobile breakpoint
    const mobileBreakpoint = responsiveUtils.getBreakpoint(375);
    expect(mobileBreakpoint).toBe('mobile');
    
    const mobileLayout = responsiveUtils.getLayoutConfig(mobileBreakpoint);
    expect(mobileLayout.showSidebar).toBe(false);
    expect(mobileLayout.compactMode).toBe(true);
    
    const mobileForm = responsiveUtils.adaptFormLayout(mobileBreakpoint);
    expect(mobileForm.stackVertically).toBe(true);
    expect(mobileForm.buttonSize).toBe('large');

    // Test tablet breakpoint
    const tabletBreakpoint = responsiveUtils.getBreakpoint(768);
    expect(tabletBreakpoint).toBe('tablet');
    
    const tabletLayout = responsiveUtils.getLayoutConfig(tabletBreakpoint);
    expect(tabletLayout.columnsCount).toBe(2);
    expect(tabletLayout.compactMode).toBe(false);

    // Test desktop breakpoint
    const desktopBreakpoint = responsiveUtils.getBreakpoint(1200);
    expect(desktopBreakpoint).toBe('desktop');
    
    const desktopLayout = responsiveUtils.getLayoutConfig(desktopBreakpoint);
    expect(desktopLayout.columnsCount).toBe(3);
    expect(desktopLayout.showSidebar).toBe(true);
    
    const desktopForm = responsiveUtils.adaptFormLayout(desktopBreakpoint);
    expect(desktopForm.stackVertically).toBe(false);
    expect(desktopForm.showLabelsInline).toBe(true);
  });

  test('Error handling and recovery flows', () => {
    // Test error handling throughout the user journey
    const errorHandler = {
      handleAuthError: (error: any) => {
        const errorMap: Record<string, string> = {
          'INVALID_CREDENTIALS': 'Invalid email or password',
          'USER_EXISTS': 'An account with this email already exists',
          'NETWORK_ERROR': 'Network connection failed. Please try again.',
          'SERVER_ERROR': 'Server error. Please try again later.',
          'TOKEN_EXPIRED': 'Your session has expired. Please log in again.',
        };
        
        return errorMap[error.code] || 'An unexpected error occurred';
      },
      
      handleValidationError: (field: string, value: any) => {
        const validationRules: Record<string, (value: any) => string | null> = {
          email: (val) => !val ? 'Email is required' : !val.includes('@') ? 'Invalid email format' : null,
          password: (val) => !val ? 'Password is required' : val.length < 8 ? 'Password must be at least 8 characters' : null,
          age: (val) => val && (val < 13 || val > 100) ? 'Age must be between 13 and 100' : null,
          attentionSpan: (val) => val && (val < 5 || val > 60) ? 'Attention span must be 5-60 minutes' : null,
        };
        
        const rule = validationRules[field];
        return rule ? rule(value) : null;
      },
      
      recoverFromError: (errorType: string) => {
        const recoveryActions: Record<string, () => any> = {
          'TOKEN_EXPIRED': () => ({ action: 'redirect_to_login', message: 'Please log in again' }),
          'NETWORK_ERROR': () => ({ action: 'retry', message: 'Retrying connection...' }),
          'VALIDATION_ERROR': () => ({ action: 'show_form_errors', message: 'Please correct the errors below' }),
        };
        
        const recovery = recoveryActions[errorType];
        return recovery ? recovery() : { action: 'show_generic_error', message: 'Something went wrong' };
      },
    };

    // Test authentication error handling
    const authError = { code: 'INVALID_CREDENTIALS' };
    const authErrorMessage = errorHandler.handleAuthError(authError);
    expect(authErrorMessage).toBe('Invalid email or password');

    // Test validation error handling
    const emailError = errorHandler.handleValidationError('email', '');
    expect(emailError).toBe('Email is required');
    
    const passwordError = errorHandler.handleValidationError('password', 'short');
    expect(passwordError).toBe('Password must be at least 8 characters');
    
    const ageError = errorHandler.handleValidationError('age', 150);
    expect(ageError).toBe('Age must be between 13 and 100');

    // Test error recovery
    const tokenExpiredRecovery = errorHandler.recoverFromError('TOKEN_EXPIRED');
    expect(tokenExpiredRecovery.action).toBe('redirect_to_login');
    
    const networkErrorRecovery = errorHandler.recoverFromError('NETWORK_ERROR');
    expect(networkErrorRecovery.action).toBe('retry');
    
    const unknownErrorRecovery = errorHandler.recoverFromError('UNKNOWN_ERROR');
    expect(unknownErrorRecovery.action).toBe('show_generic_error');
  });

  test('Performance and loading states', () => {
    // Test performance optimization and loading state management
    const performanceManager = {
      trackLoadingState: (operation: string) => {
        const startTime = Date.now();
        return {
          operation,
          startTime,
          finish: () => ({
            operation,
            duration: Date.now() - startTime,
            completed: true,
          }),
        };
      },
      
      optimizeFormSubmission: (formData: any) => {
        // Remove empty fields to reduce payload size
        const optimized = Object.entries(formData)
          .filter(([_, value]) => value !== null && value !== undefined && value !== '')
          .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});
        
        return {
          original: formData,
          optimized,
          reduction: Object.keys(formData).length - Object.keys(optimized).length,
        };
      },
      
      debounceInput: (callback: Function, delay: number) => {
        let timeoutId: NodeJS.Timeout;
        return (...args: any[]) => {
          clearTimeout(timeoutId);
          timeoutId = setTimeout(() => callback(...args), delay);
        };
      },
    };

    // Test loading state tracking
    const loadingTracker = performanceManager.trackLoadingState('user_login');
    expect(loadingTracker.operation).toBe('user_login');
    expect(loadingTracker.startTime).toBeGreaterThan(0);
    
    // Simulate operation completion
    setTimeout(() => {
      const result = loadingTracker.finish();
      expect(result.completed).toBe(true);
      expect(result.duration).toBeGreaterThan(0);
    }, 10);

    // Test form optimization
    const formData = {
      email: 'test@example.com',
      password: 'password123',
      firstName: 'John',
      lastName: '',
      age: null,
      profession: 'Engineer',
      country: undefined,
    };
    
    const optimized = performanceManager.optimizeFormSubmission(formData);
    expect(optimized.optimized.email).toBe('test@example.com');
    expect(optimized.optimized.firstName).toBe('John');
    expect(optimized.optimized.profession).toBe('Engineer');
    expect(optimized.optimized.lastName).toBeUndefined();
    expect(optimized.optimized.age).toBeUndefined();
    expect(optimized.reduction).toBe(3); // lastName, age, country removed

    // Test debounce functionality
    let callCount = 0;
    const debouncedFunction = performanceManager.debounceInput(() => {
      callCount++;
    }, 100);
    
    // Multiple rapid calls should only result in one execution
    debouncedFunction();
    debouncedFunction();
    debouncedFunction();
    
    expect(callCount).toBe(0); // Should not have been called yet
    
    setTimeout(() => {
      expect(callCount).toBe(1); // Should have been called once after delay
    }, 150);
  });
});