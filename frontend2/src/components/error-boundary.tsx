/**
 * Error boundary component for handling React errors
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { integrationService } from '@/services/integration-service';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
    errorId: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
            errorId: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return {
            hasError: true,
            error,
            errorId: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        this.setState({
            errorInfo,
        });

        // Log error to integration service
        this.logError(error, errorInfo);

        // Call custom error handler if provided
        this.props.onError?.(error, errorInfo);
    }

    private logError(error: Error, errorInfo: ErrorInfo) {
        const errorDetails = {
            message: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
            errorBoundary: this.constructor.name,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
        };

        // Log to console for development
        console.error('Error Boundary caught an error:', errorDetails);

        // In production, you might want to send this to an error reporting service
        if (process.env.NODE_ENV === 'production') {
            // Example: Send to error reporting service
            // errorReportingService.captureException(error, errorDetails);
        }
    }

    private handleRetry = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
            errorId: null,
        });
    };

    private handleReload = () => {
        window.location.reload();
    };

    private handleGoHome = () => {
        window.location.href = '/';
    };

    private handleReportBug = () => {
        const { error, errorInfo, errorId } = this.state;

        const bugReport = {
            errorId,
            message: error?.message,
            stack: error?.stack,
            componentStack: errorInfo?.componentStack,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
        };

        // Create mailto link with bug report
        const subject = encodeURIComponent(`Bug Report: ${error?.message || 'Unknown Error'}`);
        const body = encodeURIComponent(`
Error ID: ${errorId}
Timestamp: ${bugReport.timestamp}
URL: ${bugReport.url}
User Agent: ${bugReport.userAgent}

Error Message: ${bugReport.message}

Stack Trace:
${bugReport.stack}

Component Stack:
${bugReport.componentStack}

Please describe what you were doing when this error occurred:
[Your description here]
    `);

        window.open(`mailto:support@example.com?subject=${subject}&body=${body}`);
    };

    render() {
        if (this.state.hasError) {
            // Custom fallback UI if provided
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default error UI
            return (
                <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
                    <Card className="w-full max-w-2xl">
                        <CardHeader className="text-center">
                            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                                <AlertTriangle className="h-6 w-6 text-red-600" />
                            </div>
                            <CardTitle className="text-2xl font-bold text-slate-900">
                                Something went wrong
                            </CardTitle>
                            <CardDescription className="text-slate-600">
                                We encountered an unexpected error. Don't worry, we've been notified and are working on a fix.
                            </CardDescription>
                        </CardHeader>

                        <CardContent className="space-y-6">
                            {/* Error ID for support */}
                            <div className="rounded-lg bg-slate-100 p-3">
                                <p className="text-sm text-slate-600">
                                    <strong>Error ID:</strong> {this.state.errorId}
                                </p>
                                <p className="text-xs text-slate-500 mt-1">
                                    Please include this ID when reporting the issue.
                                </p>
                            </div>

                            {/* Error details (only in development) */}
                            {process.env.NODE_ENV === 'development' && this.state.error && (
                                <details className="rounded-lg bg-red-50 p-3">
                                    <summary className="cursor-pointer text-sm font-medium text-red-800">
                                        Error Details (Development Only)
                                    </summary>
                                    <div className="mt-2 space-y-2">
                                        <div>
                                            <p className="text-xs font-medium text-red-700">Message:</p>
                                            <p className="text-xs text-red-600 font-mono">
                                                {this.state.error.message}
                                            </p>
                                        </div>
                                        {this.state.error.stack && (
                                            <div>
                                                <p className="text-xs font-medium text-red-700">Stack Trace:</p>
                                                <pre className="text-xs text-red-600 font-mono whitespace-pre-wrap overflow-auto max-h-32">
                                                    {this.state.error.stack}
                                                </pre>
                                            </div>
                                        )}
                                        {this.state.errorInfo?.componentStack && (
                                            <div>
                                                <p className="text-xs font-medium text-red-700">Component Stack:</p>
                                                <pre className="text-xs text-red-600 font-mono whitespace-pre-wrap overflow-auto max-h-32">
                                                    {this.state.errorInfo.componentStack}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                </details>
                            )}

                            {/* Action buttons */}
                            <div className="flex flex-col sm:flex-row gap-3">
                                <Button
                                    onClick={this.handleRetry}
                                    className="flex-1"
                                    variant="default"
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Try Again
                                </Button>

                                <Button
                                    onClick={this.handleReload}
                                    className="flex-1"
                                    variant="outline"
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Reload Page
                                </Button>

                                <Button
                                    onClick={this.handleGoHome}
                                    className="flex-1"
                                    variant="outline"
                                >
                                    <Home className="w-4 h-4 mr-2" />
                                    Go Home
                                </Button>
                            </div>

                            {/* Report bug button */}
                            <div className="pt-4 border-t">
                                <Button
                                    onClick={this.handleReportBug}
                                    variant="ghost"
                                    size="sm"
                                    className="w-full text-slate-600 hover:text-slate-900"
                                >
                                    <Bug className="w-4 h-4 mr-2" />
                                    Report this issue
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}

// Higher-order component for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
    Component: React.ComponentType<P>,
    errorBoundaryProps?: Omit<Props, 'children'>
) {
    const WrappedComponent = (props: P) => (
        <ErrorBoundary {...errorBoundaryProps}>
            <Component {...props} />
        </ErrorBoundary>
    );

    WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

    return WrappedComponent;
}

// Hook for handling async errors in functional components
export function useErrorHandler() {
    return (error: Error, errorInfo?: any) => {
        // Log error to integration service
        console.error('Async error caught:', error, errorInfo);

        // In a real app, you might want to show a toast notification
        // or update some global error state
        throw error; // Re-throw to trigger error boundary
    };
}