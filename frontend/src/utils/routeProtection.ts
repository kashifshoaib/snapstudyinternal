import { User } from '../types';

export enum RouteProtectionLevel {
  PUBLIC = 'public',
  AUTHENTICATED = 'authenticated',
  ONBOARDED = 'onboarded',
}

export interface RouteConfig {
  path: string;
  protection: RouteProtectionLevel;
  redirectTo?: string;
  allowedRoles?: string[];
}

/**
 * Route protection utility class
 */
export class RouteProtector {
  /**
   * Check if user can access a route based on protection level
   */
  static canAccessRoute(
    protection: RouteProtectionLevel,
    isAuthenticated: boolean,
    needsOnboarding: boolean,
    user: User | null
  ): boolean {
    switch (protection) {
      case RouteProtectionLevel.PUBLIC:
        return true;

      case RouteProtectionLevel.AUTHENTICATED:
        return isAuthenticated && !!user;

      case RouteProtectionLevel.ONBOARDED:
        return isAuthenticated && !!user && !needsOnboarding;

      default:
        return false;
    }
  }

  /**
   * Get the appropriate redirect path for unauthorized access
   */
  static getRedirectPath(
    protection: RouteProtectionLevel,
    isAuthenticated: boolean,
    needsOnboarding: boolean,
    customRedirect?: string
  ): string | null {
    if (customRedirect) {
      return customRedirect;
    }

    switch (protection) {
      case RouteProtectionLevel.AUTHENTICATED:
      case RouteProtectionLevel.ONBOARDED:
        if (!isAuthenticated) {
          return '/login';
        }
        if (needsOnboarding && protection === RouteProtectionLevel.ONBOARDED) {
          return '/onboarding';
        }
        break;

      default:
        return null;
    }

    return null;
  }

  /**
   * Check if user has required role (for future role-based access control)
   */
  static hasRequiredRole(user: User | null, allowedRoles?: string[]): boolean {
    if (!allowedRoles || allowedRoles.length === 0) {
      return true;
    }

    // For now, all authenticated users have access
    // This can be extended when role system is implemented
    return !!user;
  }
}

/**
 * Default route configurations for the application
 */
export const defaultRoutes: RouteConfig[] = [
  {
    path: '/',
    protection: RouteProtectionLevel.PUBLIC,
  },
  {
    path: '/login',
    protection: RouteProtectionLevel.PUBLIC,
  },
  {
    path: '/register',
    protection: RouteProtectionLevel.PUBLIC,
  },
  {
    path: '/onboarding',
    protection: RouteProtectionLevel.AUTHENTICATED,
  },
  {
    path: '/dashboard',
    protection: RouteProtectionLevel.ONBOARDED,
  },
  {
    path: '/profile',
    protection: RouteProtectionLevel.ONBOARDED,
  },
  {
    path: '/settings',
    protection: RouteProtectionLevel.ONBOARDED,
  },
  {
    path: '/lessons',
    protection: RouteProtectionLevel.ONBOARDED,
  },
  {
    path: '/analytics',
    protection: RouteProtectionLevel.ONBOARDED,
  },
];

/**
 * Hook for route protection logic
 */
export function useRouteProtection() {
  return {
    canAccessRoute: RouteProtector.canAccessRoute,
    getRedirectPath: RouteProtector.getRedirectPath,
    hasRequiredRole: RouteProtector.hasRequiredRole,
  };
}