import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Bot,
    MessageSquare,
    Lightbulb,
    TrendingUp,
    Clock,
    CheckCircle,
    AlertCircle
} from "lucide-react";
import SectionChat from "./section-chat";
import { apiRequest } from "@/lib/queryClient";
import type { Suggestion } from "./section-chat";

interface AIAssistantProps {
    resumeId: string;
    initialSection?: string;
    onSuggestionApplied?: (suggestion: Suggestion) => void;
}

interface AssistantStats {
    totalSuggestions: number;
    appliedSuggestions: number;
    improvementScore: number;
    activeConversations: number;
    lastActivity: Date;
}

export default function AIAssistant({
    resumeId,
    initialSection = "personal",
    onSuggestionApplied
}: AIAssistantProps) {
    const [activeSection, setActiveSection] = useState(initialSection);
    const [activeTab, setActiveTab] = useState("chat");

    // Fetch assistant stats
    const { data: stats } = useQuery({
        queryKey: ["assistant-stats", resumeId],
        queryFn: async (): Promise<AssistantStats> => {
            const response = await apiRequest("GET", `/assistant/stats/${resumeId}`);
            return response.json();
        },
        refetchInterval: 30000, // Refresh every 30 seconds
    });

    // Fetch recent suggestions
    const { data: recentSuggestions } = useQuery({
        queryKey: ["recent-suggestions", resumeId],
        queryFn: async (): Promise<Suggestion[]> => {
            const response = await apiRequest("GET", `/assistant/suggestions/${resumeId}/recent`);
            return response.json();
        },
        refetchInterval: 10000, // Refresh every 10 seconds
    });

    const handleSectionChange = (section: string) => {
        setActiveSection(section);
    };

    const handleSuggestionApplied = (suggestion: Suggestion) => {
        if (onSuggestionApplied) {
            onSuggestionApplied(suggestion);
        }
    };

    return (
        <div className="h-full flex flex-col">
            <Card className="mb-4">
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <Bot className="w-5 h-5 text-primary" />
                        AI Resume Assistant
                    </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center">
                            <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-full mx-auto mb-2">
                                <Lightbulb className="w-5 h-5 text-blue-600" />
                            </div>
                            <div className="text-2xl font-bold text-slate-800">
                                {stats?.totalSuggestions || 0}
                            </div>
                            <div className="text-xs text-muted-foreground">Total Suggestions</div>
                        </div>

                        <div className="text-center">
                            <div className="flex items-center justify-center w-10 h-10 bg-green-100 rounded-full mx-auto mb-2">
                                <CheckCircle className="w-5 h-5 text-green-600" />
                            </div>
                            <div className="text-2xl font-bold text-slate-800">
                                {stats?.appliedSuggestions || 0}
                            </div>
                            <div className="text-xs text-muted-foreground">Applied</div>
                        </div>

                        <div className="text-center">
                            <div className="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-full mx-auto mb-2">
                                <TrendingUp className="w-5 h-5 text-purple-600" />
                            </div>
                            <div className="text-2xl font-bold text-slate-800">
                                {stats?.improvementScore || 0}%
                            </div>
                            <div className="text-xs text-muted-foreground">Improvement</div>
                        </div>

                        <div className="text-center">
                            <div className="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-full mx-auto mb-2">
                                <MessageSquare className="w-5 h-5 text-orange-600" />
                            </div>
                            <div className="text-2xl font-bold text-slate-800">
                                {stats?.activeConversations || 0}
                            </div>
                            <div className="text-xs text-muted-foreground">Active Chats</div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="flex-1">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="chat" className="flex items-center gap-2">
                            <MessageSquare className="w-4 h-4" />
                            Chat Assistant
                        </TabsTrigger>
                        <TabsTrigger value="suggestions" className="flex items-center gap-2">
                            <Lightbulb className="w-4 h-4" />
                            Recent Suggestions
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="chat" className="h-full mt-4">
                        <SectionChat
                            resumeId={resumeId}
                            section={activeSection}
                            onSuggestionApplied={handleSuggestionApplied}
                            onSectionChange={handleSectionChange}
                        />
                    </TabsContent>

                    <TabsContent value="suggestions" className="h-full mt-4">
                        <RecentSuggestions
                            suggestions={recentSuggestions || []}
                            onSuggestionApplied={handleSuggestionApplied}
                        />
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    );
}

interface RecentSuggestionsProps {
    suggestions: Suggestion[];
    onSuggestionApplied: (suggestion: Suggestion) => void;
}

function RecentSuggestions({ suggestions, onSuggestionApplied }: RecentSuggestionsProps) {
    if (!suggestions.length) {
        return (
            <Card className="h-full">
                <CardContent className="flex items-center justify-center h-full">
                    <div className="text-center">
                        <Lightbulb className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                        <h3 className="text-lg font-medium text-slate-800 mb-2">No suggestions yet</h3>
                        <p className="text-sm text-muted-foreground">
                            Start a conversation with the AI assistant to get personalized suggestions.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const groupedSuggestions = suggestions.reduce((acc, suggestion) => {
        const section = suggestion.type;
        if (!acc[section]) {
            acc[section] = [];
        }
        acc[section].push(suggestion);
        return acc;
    }, {} as Record<string, Suggestion[]>);

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                    <Clock className="w-5 h-5 text-primary" />
                    Recent Suggestions
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {Object.entries(groupedSuggestions).map(([section, sectionSuggestions]) => (
                    <div key={section} className="space-y-2">
                        <div className="flex items-center gap-2">
                            <Badge variant="outline" className="capitalize">
                                {section}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                                {sectionSuggestions.length} suggestion{sectionSuggestions.length !== 1 ? 's' : ''}
                            </span>
                        </div>

                        <div className="space-y-2 pl-4">
                            {sectionSuggestions.map((suggestion) => (
                                <SuggestionItem
                                    key={suggestion.id}
                                    suggestion={suggestion}
                                    onApplied={() => onSuggestionApplied(suggestion)}
                                />
                            ))}
                        </div>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
}

interface SuggestionItemProps {
    suggestion: Suggestion;
    onApplied: () => void;
}

function SuggestionItem({ suggestion, onApplied }: SuggestionItemProps) {
    const getTypeIcon = (type: string) => {
        switch (type) {
            case "content": return MessageSquare;
            case "structure": return CheckCircle;
            case "keyword": return Lightbulb;
            case "formatting": return AlertCircle;
            default: return Lightbulb;
        }
    };

    const Icon = getTypeIcon(suggestion.type);

    return (
        <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center justify-center w-8 h-8 bg-background rounded-full">
                <Icon className="w-4 h-4 text-primary" />
            </div>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-sm truncate">{suggestion.title}</h4>
                    <Badge variant="outline" className="text-xs">
                        {Math.round(suggestion.impactScore * 100)}%
                    </Badge>
                </div>

                <p className="text-xs text-muted-foreground line-clamp-2">
                    {suggestion.description}
                </p>
            </div>

            <div className="flex-shrink-0">
                {suggestion.applied ? (
                    <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Applied
                    </Badge>
                ) : (
                    <Button size="sm" variant="outline" onClick={onApplied} className="text-xs">
                        Apply
                    </Button>
                )}
            </div>
        </div>
    );
}