/**
 * Frontend integration service for coordinating all components and services
 */

import { queryClient } from '@/lib/queryClient';
import { useWebSocket } from '@/hooks/use-websocket';
import { useToast } from '@/hooks/use-toast';

export interface ServiceError {
  service: string;
  operation: string;
  error: string;
  timestamp: string;
  fallback?: boolean;
}

export interface SystemStatus {
  overall_healthy: boolean;
  services: Record<string, {
    healthy: boolean;
    last_check: string;
    error_count: number;
    last_error?: string;
  }>;
  websocket_connections: {
    active_connections: number;
    connections_by_type: Record<string, number>;
  };
  performance_metrics: any;
  circuit_breakers: Record<string, {
    state: string;
    failure_count: number;
  }>;
}

class IntegrationService {
  private baseUrl: string;
  private toast: any;
  private retryAttempts = 3;
  private retryDelay = 1000;
  private circuitBreakers: Map<string, { failures: number; lastFailure: number; isOpen: boolean }> = new Map();

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  /**
   * Initialize the integration service
   */
  async initialize() {
    try {
      // Check system health on startup
      await this.checkSystemHealth();
      
      // Setup error handling for React Query
      this.setupQueryErrorHandling();
      
      console.log('Integration service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize integration service:', error);
      throw error;
    }
  }

  /**
   * Setup global error handling for React Query
   */
  private setupQueryErrorHandling() {
    queryClient.setDefaultOptions({
      queries: {
        retry: (failureCount, error: any) => {
          // Don't retry on 4xx errors
          if (error?.response?.status >= 400 && error?.response?.status < 500) {
            return false;
          }
          return failureCount < this.retryAttempts;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        onError: (error: any) => {
          this.handleQueryError(error);
        },
      },
      mutations: {
        retry: (failureCount, error: any) => {
          if (error?.response?.status >= 400 && error?.response?.status < 500) {
            return false;
          }
          return failureCount < this.retryAttempts;
        },
        onError: (error: any) => {
          this.handleMutationError(error);
        },
      },
    });
  }

  /**
   * Handle React Query errors
   */
  private handleQueryError(error: any) {
    const service = this.extractServiceFromError(error);
    this.recordServiceError(service, error);
    
    // Show user-friendly error message
    if (this.toast) {
      this.toast({
        title: 'Service Error',
        description: this.getErrorMessage(error),
        variant: 'destructive',
      });
    }
  }

  /**
   * Handle React Query mutation errors
   */
  private handleMutationError(error: any) {
    const service = this.extractServiceFromError(error);
    this.recordServiceError(service, error);
    
    // Show user-friendly error message
    if (this.toast) {
      this.toast({
        title: 'Operation Failed',
        description: this.getErrorMessage(error),
        variant: 'destructive',
      });
    }
  }

  /**
   * Extract service name from error
   */
  private extractServiceFromError(error: any): string {
    const url = error?.config?.url || error?.request?.responseURL || '';
    
    if (url.includes('/conversation')) return 'conversation';
    if (url.includes('/section')) return 'section_optimization';
    if (url.includes('/job-analysis')) return 'job_analysis';
    if (url.includes('/feedback')) return 'feedback';
    if (url.includes('/version')) return 'version_management';
    if (url.includes('/resume')) return 'resume';
    
    return 'unknown';
  }

  /**
   * Record service error for circuit breaker logic
   */
  private recordServiceError(service: string, error: any) {
    const now = Date.now();
    const breaker = this.circuitBreakers.get(service) || { failures: 0, lastFailure: 0, isOpen: false };
    
    breaker.failures++;
    breaker.lastFailure = now;
    
    // Open circuit breaker if too many failures
    if (breaker.failures >= 5 && !breaker.isOpen) {
      breaker.isOpen = true;
      console.warn(`Circuit breaker opened for service: ${service}`);
      
      // Auto-reset after 5 minutes
      setTimeout(() => {
        breaker.isOpen = false;
        breaker.failures = 0;
        console.info(`Circuit breaker reset for service: ${service}`);
      }, 5 * 60 * 1000);
    }
    
    this.circuitBreakers.set(service, breaker);
  }

  /**
   * Check if circuit breaker is open for a service
   */
  isCircuitBreakerOpen(service: string): boolean {
    const breaker = this.circuitBreakers.get(service);
    return breaker?.isOpen || false;
  }

  /**
   * Get user-friendly error message
   */
  private getErrorMessage(error: any): string {
    if (error?.response?.data?.detail) {
      return error.response.data.detail;
    }
    
    if (error?.response?.status === 503) {
      return 'Service is temporarily unavailable. Please try again later.';
    }
    
    if (error?.response?.status >= 500) {
      return 'An internal server error occurred. Please try again.';
    }
    
    if (error?.response?.status === 429) {
      return 'Too many requests. Please wait a moment and try again.';
    }
    
    if (error?.code === 'NETWORK_ERROR') {
      return 'Network connection error. Please check your internet connection.';
    }
    
    return error?.message || 'An unexpected error occurred.';
  }

  /**
   * Execute API call with error handling and fallback
   */
  async executeWithErrorHandling<T>(
    operation: () => Promise<T>,
    service: string,
    fallback?: () => T
  ): Promise<T> {
    // Check circuit breaker
    if (this.isCircuitBreakerOpen(service)) {
      if (fallback) {
        console.warn(`Using fallback for ${service} (circuit breaker open)`);
        return fallback();
      }
      throw new Error(`Service ${service} is temporarily unavailable`);
    }

    try {
      const result = await operation();
      
      // Reset circuit breaker on success
      const breaker = this.circuitBreakers.get(service);
      if (breaker) {
        breaker.failures = 0;
        breaker.isOpen = false;
      }
      
      return result;
    } catch (error) {
      this.recordServiceError(service, error);
      
      // Try fallback if available
      if (fallback) {
        console.warn(`Using fallback for ${service} due to error:`, error);
        return fallback();
      }
      
      throw error;
    }
  }

  /**
   * Check system health
   */
  async checkSystemHealth(): Promise<SystemStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/monitoring/health/detailed`);
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      
      const data = await response.json();
      return data.system_status;
    } catch (error) {
      console.error('System health check failed:', error);
      throw error;
    }
  }

  /**
   * Get system metrics
   */
  async getSystemMetrics() {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/monitoring/metrics`);
      
      if (!response.ok) {
        throw new Error(`Metrics fetch failed: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to get system metrics:', error);
      throw error;
    }
  }

  /**
   * Setup WebSocket connection with error handling
   */
  setupWebSocket(
    connectionType: string,
    sessionId?: string,
    userId?: string
  ) {
    const wsUrl = `${this.baseUrl.replace('http', 'ws')}/api/v1/ws/${connectionType}`;
    const params = new URLSearchParams();
    
    if (sessionId) params.append('session_id', sessionId);
    if (userId) params.append('user_id', userId);
    
    const fullUrl = `${wsUrl}?${params.toString()}`;
    
    return useWebSocket(fullUrl, {
      onConnect: () => {
        console.log(`WebSocket connected: ${connectionType}`);
      },
      onDisconnect: () => {
        console.log(`WebSocket disconnected: ${connectionType}`);
      },
      onError: (error) => {
        console.error(`WebSocket error for ${connectionType}:`, error);
        this.recordServiceError('websocket', error);
      },
      reconnectAttempts: 5,
      reconnectInterval: 3000,
    });
  }

  /**
   * Handle offline/online state
   */
  setupOfflineHandling() {
    const handleOnline = () => {
      console.log('Connection restored');
      // Invalidate all queries to refresh data
      queryClient.invalidateQueries();
      
      if (this.toast) {
        this.toast({
          title: 'Connection Restored',
          description: 'You are back online. Data is being refreshed.',
        });
      }
    };

    const handleOffline = () => {
      console.log('Connection lost');
      
      if (this.toast) {
        this.toast({
          title: 'Connection Lost',
          description: 'You are offline. Some features may not work properly.',
          variant: 'destructive',
        });
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }

  /**
   * Set toast instance for error notifications
   */
  setToast(toast: any) {
    this.toast = toast;
  }

  /**
   * Get circuit breaker status
   */
  getCircuitBreakerStatus() {
    const status: Record<string, any> = {};
    
    this.circuitBreakers.forEach((breaker, service) => {
      status[service] = {
        isOpen: breaker.isOpen,
        failures: breaker.failures,
        lastFailure: breaker.lastFailure,
      };
    });
    
    return status;
  }

  /**
   * Reset circuit breaker for a service
   */
  resetCircuitBreaker(service: string) {
    const breaker = this.circuitBreakers.get(service);
    if (breaker) {
      breaker.isOpen = false;
      breaker.failures = 0;
      console.info(`Circuit breaker manually reset for service: ${service}`);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.circuitBreakers.clear();
  }
}

// Global integration service instance
export const integrationService = new IntegrationService();

// Hook for using integration service in components
export function useIntegrationService() {
  return integrationService;
}