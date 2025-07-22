import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    Lightbulb,
    CheckCircle,
    XCircle,
    MessageSquare,
    Target,
    Palette,
    FileText,
    ThumbsUp,
    ThumbsDown,
    Eye,
    EyeOff
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import type { Suggestion } from "../chat/section-chat";

interface SuggestionPanelProps {
    resumeId: string;
    section: string;
    suggestions: Suggestion[];
    onSuggestionApplied?: (suggestion: Suggestion) => void;
}

export default function SuggestionPanel({
    resumeId,
    section,
    suggestions,
    onSuggestionApplied
}: SuggestionPanelProps) {
    const [expandedSuggestions, setExpandedSuggestions] = useState<Set<string>>(new Set());
    const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Apply suggestion mutation
    const applySuggestionMutation = useMutation({
        mutationFn: async (suggestionId: string) => {
            const response = await apiRequest("POST", `/resume/${resumeId}/section/${section}/apply-suggestion`, {
                suggestionId,
            });
            return response.json();
        },
        onSuccess: (result, suggestionId) => {
            setAppliedSuggestions(prev => new Set([...prev, suggestionId]));

            toast({
                title: "Suggestion applied",
                description: "Your content has been updated successfully.",
            });

            if (onSuggestionApplied) {
                const suggestion = suggestions.find(s => s.id === suggestionId);
                if (suggestion) {
                    onSuggestionApplied({ ...suggestion, applied: true });
                }
            }

            queryClient.invalidateQueries({ queryKey: ["resume-section", resumeId, section] });
        },
        onError: (error) => {
            toast({
                title: "Failed to apply suggestion",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Rate suggestion mutation
    const rateSuggestionMutation = useMutation({
        mutationFn: async ({ suggestionId, rating }: { suggestionId: string; rating: "positive" | "negative" }) => {
            await apiRequest("POST", `/suggestions/${suggestionId}/rate`, { rating });
        },
        onSuccess: () => {
            toast({
                title: "Feedback recorded",
                description: "Thank you for your feedback!",
            });
        },
    });

    const toggleExpanded = (suggestionId: string) => {
        setExpandedSuggestions(prev => {
            const newSet = new Set(prev);
            if (newSet.has(suggestionId)) {
                newSet.delete(suggestionId);
            } else {
                newSet.add(suggestionId);
            }
            return newSet;
        });
    };

    const handleApplySuggestion = (suggestionId: string) => {
        applySuggestionMutation.mutate(suggestionId);
    };

    const handleRateSuggestion = (suggestionId: string, rating: "positive" | "negative") => {
        rateSuggestionMutation.mutate({ suggestionId, rating });
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case "content": return MessageSquare;
            case "structure": return FileText;
            case "keyword": return Target;
            case "formatting": return Palette;
            default: return Lightbulb;
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case "content": return "bg-blue-50 border-blue-200 text-blue-800";
            case "structure": return "bg-green-50 border-green-200 text-green-800";
            case "keyword": return "bg-yellow-50 border-yellow-200 text-yellow-800";
            case "formatting": return "bg-purple-50 border-purple-200 text-purple-800";
            default: return "bg-gray-50 border-gray-200 text-gray-800";
        }
    };

    const groupedSuggestions = suggestions.reduce((acc, suggestion) => {
        if (!acc[suggestion.type]) {
            acc[suggestion.type] = [];
        }
        acc[suggestion.type].push(suggestion);
        return acc;
    }, {} as Record<string, Suggestion[]>);

    if (suggestions.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Lightbulb className="w-5 h-5 text-primary" />
                        AI Suggestions
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-center text-muted-foreground">
                        <Lightbulb className="w-8 h-8 mx-auto mb-2" />
                        <p className="text-sm">No suggestions available</p>
                        <p className="text-xs mt-1">
                            Click "AI Suggestions" in the editor to generate recommendations
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-fit">
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-primary" />
                    AI Suggestions
                    <Badge variant="secondary" className="ml-auto">
                        {suggestions.length}
                    </Badge>
                </CardTitle>
            </CardHeader>

            <Separator />

            <CardContent className="p-0">
                <ScrollArea className="h-96">
                    <div className="p-4 space-y-4">
                        {Object.entries(groupedSuggestions).map(([type, typeSuggestions]) => (
                            <div key={type} className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="capitalize">
                                        {type}
                                    </Badge>
                                    <span className="text-sm text-muted-foreground">
                                        {typeSuggestions.length} suggestion{typeSuggestions.length !== 1 ? 's' : ''}
                                    </span>
                                </div>

                                <div className="space-y-2 pl-2">
                                    {typeSuggestions.map((suggestion) => (
                                        <SuggestionCard
                                            key={suggestion.id}
                                            suggestion={suggestion}
                                            isExpanded={expandedSuggestions.has(suggestion.id)}
                                            isApplied={appliedSuggestions.has(suggestion.id) || suggestion.applied}
                                            isApplying={applySuggestionMutation.isPending}
                                            onToggleExpanded={() => toggleExpanded(suggestion.id)}
                                            onApply={() => handleApplySuggestion(suggestion.id)}
                                            onRate={(rating) => handleRateSuggestion(suggestion.id, rating)}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}

interface SuggestionCardProps {
    suggestion: Suggestion;
    isExpanded: boolean;
    isApplied: boolean;
    isApplying: boolean;
    onToggleExpanded: () => void;
    onApply: () => void;
    onRate: (rating: "positive" | "negative") => void;
}

function SuggestionCard({
    suggestion,
    isExpanded,
    isApplied,
    isApplying,
    onToggleExpanded,
    onApply,
    onRate
}: SuggestionCardProps) {
    const getTypeIcon = (type: string) => {
        switch (type) {
            case "content": return MessageSquare;
            case "structure": return FileText;
            case "keyword": return Target;
            case "formatting": return Palette;
            default: return Lightbulb;
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case "content": return "border-blue-200";
            case "structure": return "border-green-200";
            case "keyword": return "border-yellow-200";
            case "formatting": return "border-purple-200";
            default: return "border-gray-200";
        }
    };

    const Icon = getTypeIcon(suggestion.type);

    return (
        <Card className={cn("border-l-4", getTypeColor(suggestion.type))}>
            <CardContent className="p-3">
                <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-2 flex-1 min-w-0">
                            <Icon className="w-4 h-4 mt-0.5 flex-shrink-0 text-primary" />
                            <div className="flex-1 min-w-0">
                                <h4 className="font-medium text-sm line-clamp-2">{suggestion.title}</h4>
                                <div className="flex items-center gap-2 mt-1">
                                    <Badge variant="outline" className="text-xs">
                                        Impact: {Math.round(suggestion.impactScore * 100)}%
                                    </Badge>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={onToggleExpanded}
                                        className="h-6 px-2 text-xs"
                                    >
                                        {isExpanded ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                                        {isExpanded ? "Less" : "More"}
                                    </Button>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-1">
                            {isApplied ? (
                                <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Applied
                                </Badge>
                            ) : (
                                <Button
                                    size="sm"
                                    onClick={onApply}
                                    disabled={isApplying}
                                    className="text-xs h-7"
                                >
                                    {isApplying ? "Applying..." : "Apply"}
                                </Button>
                            )}
                        </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-muted-foreground">
                        {suggestion.description}
                    </p>

                    {/* Expanded Content */}
                    {isExpanded && (
                        <div className="space-y-3 pt-2 border-t">
                            {/* Before/After */}
                            {suggestion.originalText && suggestion.suggestedText && (
                                <div className="space-y-2">
                                    <div>
                                        <span className="text-xs font-medium text-red-600">Before:</span>
                                        <div className="bg-red-50 p-2 rounded border-l-2 border-red-200 mt-1">
                                            <p className="text-xs">{suggestion.originalText}</p>
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-xs font-medium text-green-600">After:</span>
                                        <div className="bg-green-50 p-2 rounded border-l-2 border-green-200 mt-1">
                                            <p className="text-xs">{suggestion.suggestedText}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Reasoning */}
                            <div>
                                <span className="text-xs font-medium text-slate-600">Reasoning:</span>
                                <p className="text-xs text-muted-foreground mt-1 italic">
                                    {suggestion.reasoning}
                                </p>
                            </div>

                            {/* Rating */}
                            <div className="flex items-center justify-between pt-2 border-t">
                                <span className="text-xs text-muted-foreground">Was this helpful?</span>
                                <div className="flex gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => onRate("positive")}
                                        className="h-6 w-6 p-0"
                                    >
                                        <ThumbsUp className="w-3 h-3" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => onRate("negative")}
                                        className="h-6 w-6 p-0"
                                    >
                                        <ThumbsDown className="w-3 h-3" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}