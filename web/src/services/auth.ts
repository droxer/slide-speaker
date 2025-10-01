// Authentication service for Google OAuth
import { resolveApiBaseUrl } from "@/utils/apiBaseUrl";

const API_BASE_URL = resolveApiBaseUrl();

export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  user: User;
  session_token: string;
  access_token: string;
  token_type: string;
}

/**
 * Initiate Google OAuth login flow
 */
export const initiateGoogleLogin = (): void => {
  // Redirect to the backend OAuth endpoint
  window.location.href = `${API_BASE_URL}/api/auth/login`;
};

/**
 * Logout user
 */
export const logout = async (sessionToken: string): Promise<void> => {
  try {
    await fetch(`${API_BASE_URL}/api/auth/logout?session_token=${encodeURIComponent(sessionToken)}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    console.error("Logout error:", error);
  }
};

/**
 * Get current user info
 */
export const getCurrentUser = async (sessionToken: string): Promise<User | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/user?session_token=${encodeURIComponent(sessionToken)}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Get current user error:", error);
    return null;
  }
};
