// Centralized API configuration for Vercel deployment & local development

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const API_ROOT = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/api\/v1\/?$/, '')
  : 'http://localhost:8000';

export const safeFetch = async (url: string, options?: RequestInit): Promise<Response> => {
  try {
    return await fetch(url, options);
  } catch (firstErr) {
    const fallbackUrl = url.includes('localhost')
      ? url.replace('localhost', '127.0.0.1')
      : url.includes('127.0.0.1')
      ? url.replace('127.0.0.1', 'localhost')
      : url;
    if (fallbackUrl === url) throw firstErr;
    try {
      return await fetch(fallbackUrl, options);
    } catch {
      throw firstErr;
    }
  }
};
