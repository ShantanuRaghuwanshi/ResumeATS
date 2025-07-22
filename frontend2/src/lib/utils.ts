import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Returns the backend API URL from environment variables
export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
}
