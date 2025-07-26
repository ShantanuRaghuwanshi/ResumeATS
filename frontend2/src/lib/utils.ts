import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Returns the backend API URL from environment variables
export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
}

/**
 * Get session headers (excluding session API endpoints)
 */
export function getSessionHeaders(url?: string): Record<string, string> {
  // Session endpoints that should not include session headers
  const sessionApiPaths = [
    '/api/v1/session',
    '/api/v1/session/',
    '/api/v1/session/test-config',
    '/api/v1/session/create',
    '/api/v1/session/list'
  ];

  // Check if the URL matches any session API paths
  if (url) {
    const urlPath = new URL(url, 'http://localhost').pathname;
    const isSessionApi = sessionApiPaths.some(path =>
      urlPath === path || urlPath.startsWith(path + '/')
    );

    if (isSessionApi) {
      return {};
    }
  }

  const sessionData = localStorage.getItem('resume-ats-session');
  if (sessionData) {
    try {
      const session = JSON.parse(sessionData);
      if (session.sessionId && new Date(session.expiresAt) > new Date()) {
        return { 'X-Session-ID': session.sessionId };
      }
    } catch (error) {
      console.error('Failed to parse session data:', error);
    }
  }
  return {};
}

/**
 * Utility function for making fetch requests with automatic session headers
 */
export async function fetchWithSession(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const fullUrl = url.startsWith("http") ? url : `${getApiUrl()}${url}`;
  const sessionHeaders = getSessionHeaders(fullUrl);

  const headers = {
    ...sessionHeaders,
    ...options.headers,
  };

  return fetch(fullUrl, {
    ...options,
    headers,
    credentials: "include",
  });
}
