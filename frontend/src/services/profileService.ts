import { ProfileConfig, User } from '../types';

class ProfileService {
  private profileConfig: ProfileConfig | null = null;
  private configLoaded = false;

  /**
   * Load profile configuration from profile.json
   */
  async loadProfileConfig(): Promise<ProfileConfig | null> {
    if (this.configLoaded) {
      return this.profileConfig;
    }

    try {
      const response = await fetch('/profile.json');
      if (!response.ok) {
        console.warn('profile.json not found or not accessible');
        this.configLoaded = true;
        return null;
      }

      this.profileConfig = await response.json();
      this.configLoaded = true;
      console.log('Profile configuration loaded successfully');
      return this.profileConfig;
    } catch (error) {
      console.error('Error loading profile.json:', error);
      this.configLoaded = true;
      return null;
    }
  }

  /**
   * Check if guest login is enabled
   */
  async isGuestEnabled(): Promise<boolean> {
    const config = await this.loadProfileConfig();
    return config?.guestEnabled ?? false;
  }

  /**
   * Authenticate user against profile.json
   * Returns the user if credentials match, null otherwise
   */
  async authenticateWithProfile(email: string, password: string): Promise<User | null> {
    const config = await this.loadProfileConfig();

    if (!config || !config.guestEnabled) {
      return null;
    }

    const { guestUser } = config;

    // Check if credentials match
    if (guestUser.email === email && (guestUser as any).password === password) {
      // Remove password from the returned user object
      const { password: _, ...userWithoutPassword } = guestUser as any;
      console.log('Guest user authenticated from profile.json');
      return userWithoutPassword as User;
    }

    return null;
  }

  /**
   * Get guest user (without password)
   */
  async getGuestUser(): Promise<User | null> {
    const config = await this.loadProfileConfig();

    if (!config || !config.guestEnabled) {
      return null;
    }

    const { password: _, ...userWithoutPassword } = config.guestUser as any;
    return userWithoutPassword as User;
  }
}

export const profileService = new ProfileService();
