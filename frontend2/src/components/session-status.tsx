import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Clock,
    Settings,
    LogOut,
    CheckCircle,
    AlertTriangle,
    RefreshCw
} from 'lucide-react';
import { useLLMConfig } from '@/contexts/llm-context';
import { useToast } from '@/hooks/use-toast';

export default function SessionStatus() {
    const {
        llmConfig,
        sessionInfo,
        isSessionValid,
        isConfigured,
        clearSession
    } = useLLMConfig();
    const { toast } = useToast();
    const [isValidating, setIsValidating] = useState(false);

    const handleClearSession = () => {
        clearSession();
        toast({
            title: "Session cleared",
            description: "Your session has been cleared. Please configure LLM again.",
        });
    };

    const validateSession = async () => {
        if (!sessionInfo?.sessionId) return;

        setIsValidating(true);
        try {
            const response = await fetch(`/api/v1/session/validate/${sessionInfo.sessionId}`);
            const result = await response.json();

            if (result.valid) {
                toast({
                    title: "Session valid",
                    description: "Your session is active and valid.",
                });
            } else {
                toast({
                    title: "Session invalid",
                    description: result.error_message || "Session is no longer valid.",
                    variant: "destructive",
                });
                clearSession();
            }
        } catch (error) {
            toast({
                title: "Validation failed",
                description: "Could not validate session.",
                variant: "destructive",
            });
        } finally {
            setIsValidating(false);
        }
    };

    const formatTimeRemaining = (expiresAt: string): string => {
        const now = new Date();
        const expires = new Date(expiresAt);
        const diff = expires.getTime() - now.getTime();

        if (diff <= 0) return "Expired";

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            return `${hours}h ${minutes}m remaining`;
        } else {
            return `${minutes}m remaining`;
        }
    };

    if (!isConfigured) {
        return (
            <Card className="border-dashed">
                <CardContent className="pt-6">
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <AlertTriangle className="h-4 w-4" />
                        <span>No active session. Please configure LLM first.</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <Settings className="h-4 w-4" />
                    Session Status
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Session Status */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {isSessionValid ? (
                            <>
                                <CheckCircle className="h-4 w-4 text-green-500" />
                                <Badge variant="default" className="bg-green-100 text-green-800">
                                    Active
                                </Badge>
                            </>
                        ) : (
                            <>
                                <AlertTriangle className="h-4 w-4 text-red-500" />
                                <Badge variant="destructive">
                                    Expired
                                </Badge>
                            </>
                        )}
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={validateSession}
                        disabled={isValidating}
                    >
                        {isValidating ? (
                            <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                            <RefreshCw className="h-3 w-3" />
                        )}
                    </Button>
                </div>

                {/* LLM Provider Info */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Provider:</span>
                        <span className="font-medium capitalize">{llmConfig?.provider}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Model:</span>
                        <span className="font-medium">{llmConfig?.model}</span>
                    </div>
                </div>

                {/* Session Info */}
                {sessionInfo && (
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Session ID:</span>
                            <span className="font-mono text-xs">
                                {sessionInfo.sessionId.slice(0, 8)}...
                            </span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">
                                <Clock className="h-3 w-3 inline mr-1" />
                                Time remaining:
                            </span>
                            <span className={`font-medium ${!isSessionValid ? 'text-red-500' : ''}`}>
                                {formatTimeRemaining(sessionInfo.expiresAt)}
                            </span>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="pt-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleClearSession}
                        className="w-full"
                    >
                        <LogOut className="h-3 w-3 mr-2" />
                        Clear Session
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
