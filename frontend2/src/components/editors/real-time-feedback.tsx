import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
    CheckCircle,
    AlertTriangle,
    Info,
    Zap,
    Target,
    FileText,
    Clock,
    TrendingUp,
    Wifi,
    WifiOff,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useRealTimeFeedback, FeedbackData } from '@/hooks/use-real-time-feedback';

interface RealTimeFeedbackProps {
    sessionId?: string;
    userId?: string;
    section: string;
    content: string;
    previousContent?: string;
    className?: string;
}

export default function RealTimeFeedback({
    sessionId,
    userId,
    section,
    content,
    previousContent,
    className,
}: RealTimeFeedbackProps) {
    const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
    const [lastAnalyzedContent, setLastAnalyzedContent] = useState<string>('');

    const {
        isConnected,
        isConnecting,
        sendFeedbackRequest,
        lastFeedback,
        lastProgress,
        lastNotification,
    } = useRealTimeFeedback({
        sessionId,
        userId,
        onFeedback: (feedback) => {
            console.log('Received real-time feedback:', feedback);
        },
        onProgress: (progress) => {
            console.log('Progress update:', progress);
        },
        onNotification: (notification) => {
            console.log('Notification:', notification);
        },
    });

    // Debounced content analysis
    useEffect(() => {
        if (content && content !== lastAnalyzedContent && content.trim().length > 0) {
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }

            const timer = setTimeout(() => {
                if (isConnected) {
                    sendFeedbackRequest(section, content, previousContent);
                    setLastAnalyzedContent(content);
                }
            }, 1000); // 1 second debounce

            setDebounceTimer(timer);
        }

        return () => {
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
        };
    }, [content, lastAnalyzedContent, section, previousContent, isConnected, sendFeedbackRequest, debounceTimer]);

    const getScoreColor = (score: number) => {
        if (score >= 0.8) return 'text-green-600';
        if (score >= 0.6) return 'text-yellow-600';
        return 'text-red-600';
    };

    const getScoreBadgeVariant = (score: number): 'default' | 'secondary' | 'destructive' => {
        if (score >= 0.8) return 'default';
        if (score >= 0.6) return 'secondary';
        return 'destructive';
    };

    const renderConnectionStatus = () => (
        <div className="flex items-center gap-2 text-sm">
            {isConnecting ? (
                <>
                    <Clock className="w-4 h-4 animate-spin text-yellow-500" />
                    <span className="text-yellow-600">Connecting...</span>
                </>
            ) : isConnected ? (
                <>
                    <Wifi className="w-4 h-4 text-green-500" />
                    <span className="text-green-600">Live feedback active</span>
                </>
            ) : (
                <>
                    <WifiOff className="w-4 h-4 text-red-500" />
                    <span className="text-red-600">Disconnected</span>
                </>
            )}
        </div>
    );

    const renderFeedbackMetrics = (feedback: FeedbackData) => (
        <div className="space-y-4">
            {/* Quality Scores */}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Quality Score</span>
                        <Badge variant={getScoreBadgeVariant(feedback.current_quality_score)}>
                            {Math.round(feedback.current_quality_score * 100)}%
                        </Badge>
                    </div>
                    <Progress value={feedback.current_quality_score * 100} className="h-2" />
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">ATS Compatibility</span>
                        <Badge variant={getScoreBadgeVariant(feedback.ats_compatibility)}>
                            {Math.round(feedback.ats_compatibility * 100)}%
                        </Badge>
                    </div>
                    <Progress value={feedback.ats_compatibility * 100} className="h-2" />
                </div>
            </div>

            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Readability</span>
                    <Badge variant={getScoreBadgeVariant(feedback.readability_score)}>
                        {Math.round(feedback.readability_score * 100)}%
                    </Badge>
                </div>
                <Progress value={feedback.readability_score * 100} className="h-2" />
            </div>

            {/* Content Statistics */}
            <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                        {feedback.character_count} characters
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                        {feedback.word_count} words
                    </span>
                </div>
            </div>
        </div>
    );

    const renderSuggestions = (feedback: FeedbackData) => (
        <div className="space-y-3">
            {/* Grammar Issues */}
            {feedback.grammar_issues.length > 0 && (
                <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                        <div className="font-medium mb-1">Grammar Issues Found:</div>
                        <ul className="list-disc list-inside space-y-1 text-sm">
                            {feedback.grammar_issues.map((issue, index) => (
                                <li key={index}>{issue}</li>
                            ))}
                        </ul>
                    </AlertDescription>
                </Alert>
            )}

            {/* Style Suggestions */}
            {feedback.style_suggestions.length > 0 && (
                <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                        <div className="font-medium mb-1">Style Improvements:</div>
                        <ul className="list-disc list-inside space-y-1 text-sm">
                            {feedback.style_suggestions.map((suggestion, index) => (
                                <li key={index}>{suggestion}</li>
                            ))}
                        </ul>
                    </AlertDescription>
                </Alert>
            )}

            {/* Keyword Suggestions */}
            {feedback.keyword_suggestions.length > 0 && (
                <Alert>
                    <Zap className="h-4 w-4" />
                    <AlertDescription>
                        <div className="font-medium mb-1">Keyword Optimization:</div>
                        <ul className="list-disc list-inside space-y-1 text-sm">
                            {feedback.keyword_suggestions.map((suggestion, index) => (
                                <li key={index}>{suggestion}</li>
                            ))}
                        </ul>
                    </AlertDescription>
                </Alert>
            )}
        </div>
    );

    return (
        <Card className={cn('h-fit', className)}>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-primary" />
                        Real-time Feedback
                    </CardTitle>
                    {renderConnectionStatus()}
                </div>
            </CardHeader>

            <Separator />

            <CardContent className="pt-4">
                {lastProgress && (
                    <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">{lastProgress.operation}</span>
                            <span className="text-sm text-muted-foreground">
                                {Math.round(lastProgress.progress * 100)}%
                            </span>
                        </div>
                        <Progress value={lastProgress.progress * 100} className="h-2" />
                        {lastProgress.details && (
                            <p className="text-xs text-muted-foreground mt-1">
                                {lastProgress.details}
                            </p>
                        )}
                    </div>
                )}

                {lastNotification && (
                    <Alert className="mb-4">
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                            <div className="font-medium">{lastNotification.title}</div>
                            <div className="text-sm">{lastNotification.message}</div>
                        </AlertDescription>
                    </Alert>
                )}

                {lastFeedback ? (
                    <div className="space-y-4">
                        {renderFeedbackMetrics(lastFeedback)}

                        <Separator />

                        {renderSuggestions(lastFeedback)}

                        <div className="text-xs text-muted-foreground text-center pt-2">
                            Last updated: {new Date(lastFeedback.timestamp).toLocaleTimeString()}
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <FileText className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            {isConnected
                                ? 'Start typing to get real-time feedback...'
                                : 'Connecting to feedback service...'
                            }
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}