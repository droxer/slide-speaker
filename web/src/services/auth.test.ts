/**
 * Unit tests for the auth service.
 */

import { initiateGoogleLogin, logout, getCurrentUser } from './auth';

// Mock window.location
const mockWindowLocation = {
  href: '',
};

// Mock fetch
global.fetch = jest.fn();

describe('AuthService', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Mock window.location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: mockWindowLocation,
    });
    
    // Reset mock location href
    mockWindowLocation.href = '';
  });

  describe('initiateGoogleLogin', () => {
    it('should redirect to Google OAuth endpoint', () => {
      // Set REACT_APP_API_BASE_URL environment variable
      process.env.REACT_APP_API_BASE_URL = 'http://localhost:8000';
      
      // Call the function
      initiateGoogleLogin();
      
      // Verify redirection
      expect(window.location.href).toBe('http://localhost:8000/api/auth/login');
    });

    it('should use empty string when REACT_APP_API_BASE_URL is not set', () => {
      // Unset REACT_APP_API_BASE_URL environment variable
      delete process.env.REACT_APP_API_BASE_URL;
      
      // Call the function
      initiateGoogleLogin();
      
      // Verify redirection
      expect(window.location.href).toBe('http://localhost:8000/api/auth/login');
    });
  });

  describe('logout', () => {
    it('should successfully call logout endpoint', async () => {
      // Mock fetch response
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({}),
      });

      // Call the function
      await logout('test_session_token');

      // Verify fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/logout?session_token=test_session_token',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    });

    it('should handle logout errors gracefully', async () => {
      // Mock fetch to reject
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      // Mock console.error
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      // Call the function
      await logout('test_session_token');

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/logout?session_token=test_session_token',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      // Verify error was logged
      expect(consoleErrorSpy).toHaveBeenCalledWith('Logout error:', expect.any(Error));

      // Restore console.error
      consoleErrorSpy.mockRestore();
    });
  });

  describe('getCurrentUser', () => {
    it('should successfully get current user info', async () => {
      // Mock user data
      const mockUser = {
        id: 'test_user_id',
        email: 'test@example.com',
        name: 'Test User',
        picture: 'http://example.com/picture.jpg',
        created_at: '2023-01-01T00:00:00',
        updated_at: '2023-01-01T00:00:00',
      };

      // Mock fetch response
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue(mockUser),
      });

      // Call the function
      const result = await getCurrentUser('test_session_token');

      // Verify fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/user?session_token=test_session_token',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      // Verify the result
      expect(result).toEqual(mockUser);
    });

    it('should return null when response is not ok', async () => {
      // Mock fetch response with error status
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
        json: jest.fn().mockResolvedValue({}),
      });

      // Mock console.error
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      // Call the function
      const result = await getCurrentUser('test_session_token');

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/user?session_token=test_session_token',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      // Verify the result
      expect(result).toBeNull();

      // Verify error was logged
      expect(consoleErrorSpy).toHaveBeenCalledWith('Get current user error:', expect.any(Error));

      // Restore console.error
      consoleErrorSpy.mockRestore();
    });

    it('should handle network errors gracefully', async () => {
      // Mock fetch to reject
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      // Mock console.error
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      // Call the function
      const result = await getCurrentUser('test_session_token');

      // Verify fetch was called
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/user?session_token=test_session_token',
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      // Verify the result
      expect(result).toBeNull();

      // Verify error was logged
      expect(consoleErrorSpy).toHaveBeenCalledWith('Get current user error:', expect.any(Error));

      // Restore console.error
      consoleErrorSpy.mockRestore();
    });
  });
});