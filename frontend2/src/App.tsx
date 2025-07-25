import { Switch, Route } from "wouter";
import { useEffect } from "react";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { ErrorBoundary } from "@/components/error-boundary";
import { integrationService } from "@/services/integration-service";
import { LLMProvider } from "@/contexts/llm-context";
import Dashboard from "@/pages/dashboard";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Dashboard} />
      <Route component={NotFound} />
    </Switch>
  );
}

function AppContent() {
  const { toast } = useToast();

  useEffect(() => {
    // Initialize integration service
    const initializeApp = async () => {
      try {
        // Set toast instance for error notifications
        integrationService.setToast(toast);

        // Initialize integration service
        await integrationService.initialize();

        // Setup offline/online handling
        const cleanup = integrationService.setupOfflineHandling();

        return cleanup;
      } catch (error) {
        console.error('Failed to initialize app:', error);
        toast({
          title: 'Initialization Error',
          description: 'Failed to initialize the application. Please refresh the page.',
          variant: 'destructive',
        });
      }
    };

    const cleanup = initializeApp();

    return () => {
      cleanup?.then(cleanupFn => cleanupFn?.());
    };
  }, [toast]);

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('App Error Boundary:', error, errorInfo);
        toast({
          title: 'Application Error',
          description: 'An unexpected error occurred. The page will be reloaded.',
          variant: 'destructive',
        });
      }}
    >
      <Router />
    </ErrorBoundary>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <LLMProvider>
          <TooltipProvider>
            <Toaster />
            <AppContent />
          </TooltipProvider>
        </LLMProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
