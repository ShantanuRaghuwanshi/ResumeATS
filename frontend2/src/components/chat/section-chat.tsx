import { useState, useRef, useEffect, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    Send,
    Bot,
    User,
    Lightbulb,
    CheckCircle,
    XCircle,
    Clock,
    MessageSquare,
    Wifi,
    WifiOff
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import { useWebSocket, WebSocketMessage } from "@/hooks/use-websocket";

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    suggestions?: Suggestion[];
}

export interface Suggestion {
    id: string;
    type: "content" | "structure" | "keyword" | "formatting";
    title: string;
    description: string;
    originalText?: string;
    suggestedText?: string;
    impactScore: number;
    reasoning: string;
    applied?: boolean;
}

export interface ConversationSession {
    id: string;
    resumeId: string;
    section: string;
    createdAt: Date;
    lastActivity: Date;
    messages: Message[];
}

interface SectionChatProps {
    resumeId: string;
    section: string;
    onSuggestionApplied?: (suggestion: Suggestion) => void;
    onSectionChange?: (section: string) => void;
}

const RESUME_SECTIONS = [
    { id: "personal", label: "Personal Details", icon: User },
    { id: "summary", label: "Professional Summary", icon: MessageSquare },
    { id: "experience", label: "Work Experience", icon: Clock },
    { id: "skills", label: "Skills", icon: Lightbulb },
    { id: "education", label: "Education", icon: CheckCircle },
    { id: "projects", label: "Projects", icon: XCircle },
];

export default function SectionChat({
    resumeId,
    section,
    onSuggestionApplied,
    onSectionChange
}: SectionChatProps) {
    const [message, setMessage] = useState("");
    const [isTyping, setIsTyping] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Fetch conversation session
    const { data: session, isLoading } = useQuery({
        queryKey: ["conversation", resumeId, section],
        queryFn: async (): Promise<ConversationSession> => {
            const response = await apiRequest("GET", `/conversation/${resumeId}/${section}`);
            return response.json();
        },
        retry: false,
    });

    // WebSocket connection for real-time chat
    const wsUrl = sessionId
        ? `ws://localhost:8000/api/v1/ws/conversation?session_id=${sessionId}`
        : null;

    const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
        switch (message.type) {
            case 'message_response':
                // Add AI response to conversation
                const aiMessage: Message = {
                    id: message.data.id || `ai-${Date.now()}`,
                    role: 'assistant',
                    content: message.data.message || message.data.content,
                    timestamp: new Date(message.data.timestamp || Date.now()),
                    suggestions: message.data.suggestions || [],
                };

                queryClient.setQueryData(
                    ["conversation", resumeId, section],
                    (old: ConversationSession | undefined) => {
                        if (!old) return old;
                        return {
                            ...old,
                            messages: [...old.messages, aiMessage],
                        };
                    }
                );
                setIsTyping(false);
                break;

            case 'user_typing':
                // Handle typing indicators from other users
                if (message.data.user_id !== 'current-user') {
                    setIsTyping(message.data.typing);
                }
                break;

            case 'connection_established':
                console.log('Chat WebSocket connected:', message.data);
                break;

            case 'error':
                console.error('Chat WebSocket error:', message.data);
                setIsTyping(false);
                toast({
                    title: "Connection Error",
                    description: message.data.error_message || "WebSocket connection error",
                    variant: "destructive",
                });
                break;

            default:
                console.log('Unhandled chat message type:', message.type);
        }
    }, [queryClient, resumeId, section, toast]);

    const {
        isConnected: wsConnected,
        isConnecting: wsConnecting,
        sendMessage: sendWebSocketMessage,
    } = useWebSocket(wsUrl || '', {
        onMessage: handleWebSocketMessage,
        onConnect: () => {
            console.log('Chat WebSocket connected');
        },
        onDisconnect: () => {
            console.log('Chat WebSocket disconnected');
        },
        onError: (error) => {
            console.error('Chat WebSocket error:', error);
        },
    });

    // Start new conversation mutation
    const startConversationMutation = useMutation({
        mutationFn: async () => {
            const response = await apiRequest("POST", `/conversation/start`, {
                resumeId,
                section,
            });
            return response.json();
        },
        onSuccess: (data) => {
            if (data.session?.id) {
                setSessionId(data.session.id);
            }
            queryClient.invalidateQueries({ queryKey: ["conversation", resumeId, section] });
        },
    });

    // Send message mutation (fallback for HTTP)
    const sendMessageMutation = useMutation({
        mutationFn: async (messageContent: string) => {
            if (!session?.id) throw new Error("No active session");

            const response = await apiRequest("POST", `/conversation/${session.id}/message`, {
                content: messageContent,
            });
            return response.json();
        },
        onMutate: async (messageContent) => {
            // Optimistically add user message
            const userMessage: Message = {
                id: `temp-${Date.now()}`,
                role: "user",
                content: messageContent,
                timestamp: new Date(),
            };

            queryClient.setQueryData(
                ["conversation", resumeId, section],
                (old: ConversationSession | undefined) => {
                    if (!old) return old;
                    return {
                        ...old,
                        messages: [...old.messages, userMessage],
                    };
                }
            );

            setIsTyping(true);
            return { userMessage };
        },
        onSuccess: (aiResponse) => {
            // Add AI response (only if not using WebSocket)
            if (!wsConnected) {
                queryClient.setQueryData(
                    ["conversation", resumeId, section],
                    (old: ConversationSession | undefined) => {
                        if (!old) return old;
                        return {
                            ...old,
                            messages: [...old.messages, aiResponse],
                        };
                    }
                );
            }
            setIsTyping(false);
        },
        onError: (error) => {
            setIsTyping(false);
            toast({
                title: "Failed to send message",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Apply suggestion mutation
    const applySuggestionMutation = useMutation({
        mutationFn: async (suggestionId: string) => {
            if (!session?.id) throw new Error("No active session");

            const response = await apiRequest("POST", `/conversation/${session.id}/apply-suggestion`, {
                suggestionId,
            });
            return response.json();
        },
        onSuccess: (result) => {
            toast({
                title: "Suggestion applied",
                description: "Your resume has been updated successfully.",
            });

            // Mark suggestion as applied
            queryClient.setQueryData(
                ["conversation", resumeId, section],
                (old: ConversationSession | undefined) => {
                    if (!old) return old;
                    return {
                        ...old,
                        messages: old.messages.map(msg => ({
                            ...msg,
                            suggestions: msg.suggestions?.map(s =>
                                s.id === result.suggestionId ? { ...s, applied: true } : s
                            ),
                        })),
                    };
                }
            );

            if (onSuggestionApplied) {
                onSuggestionApplied(result.suggestion);
            }
        },
        onError: (error) => {
            toast({
                title: "Failed to apply suggestion",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [session?.messages, isTyping]);

    // Start conversation if none exists
    useEffect(() => {
        if (!isLoading && !session) {
            startConversationMutation.mutate();
        }
    }, [isLoading, session]);

    const handleSendMessage = () => {
        if (!message.trim() || sendMessageMutation.isPending) return;

        sendMessageMutation.mutate(message);
        setMessage("");
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleApplySuggestion = (suggestionId: string) => {
        applySuggestionMutation.mutate(suggestionId);
    };

    const renderMessage = (msg: Message) => {
        const isUser = msg.role === "user";

        return (
            <div key={msg.id} className={cn("flex gap-3 mb-4", isUser ? "justify-end" : "justify-start")}>
                {!isUser && (
                    <Avatar className="w-8 h-8 mt-1">
                        <AvatarFallback className="bg-primary/10">
                            <Bot className="w-4 h-4 text-primary" />
                        </AvatarFallback>
                    </Avatar>
                )}

                <div className={cn("max-w-[80%] space-y-2", isUser ? "order-first" : "")}>
                    <div
                        className={cn(
                            "rounded-lg px-4 py-2 text-sm",
                            isUser
                                ? "bg-primary text-primary-foreground ml-auto"
                                : "bg-muted"
                        )}
                    >
                        {msg.content}
                    </div>

                    {msg.suggestions && msg.suggestions.length > 0 && (
                        <div className="space-y-2">
                            {msg.suggestions.map((suggestion) => (
                                <SuggestionCard
                                    key={suggestion.id}
                                    suggestion={suggestion}
                                    onApply={() => handleApplySuggestion(suggestion.id)}
                                    isApplying={applySuggestionMutation.isPending}
                                />
                            ))}
                        </div>
                    )}

                    <div className="text-xs text-muted-foreground">
                        {msg.timestamp.toLocaleTimeString()}
                    </div>
                </div>

                {isUser && (
                    <Avatar className="w-8 h-8 mt-1">
                        <AvatarFallback className="bg-secondary">
                            <User className="w-4 h-4" />
                        </AvatarFallback>
                    </Avatar>
                )}
            </div>
        );
    };

    if (isLoading || startConversationMutation.isPending) {
        return (
            <Card className="h-full">
                <CardContent className="flex items-center justify-center h-full">
                    <div className="text-center">
                        <Bot className="w-8 h-8 mx-auto mb-2 text-muted-foreground animate-pulse" />
                        <p className="text-sm text-muted-foreground">Starting conversation...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <MessageSquare className="w-5 h-5 text-primary" />
                        AI Assistant
                    </CardTitle>
                    <SectionSelector
                        currentSection={section}
                        onSectionChange={onSectionChange}
                    />
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Discussing:</span>
                    <Badge variant="secondary">
                        {RESUME_SECTIONS.find(s => s.id === section)?.label || section}
                    </Badge>
                </div>
            </CardHeader>

            <Separator />

            <CardContent className="flex-1 flex flex-col p-0">
                <ScrollArea className="flex-1 p-4">
                    <div className="space-y-4">
                        {session?.messages.map(renderMessage)}

                        {isTyping && (
                            <div className="flex gap-3 mb-4">
                                <Avatar className="w-8 h-8 mt-1">
                                    <AvatarFallback className="bg-primary/10">
                                        <Bot className="w-4 h-4 text-primary" />
                                    </AvatarFallback>
                                </Avatar>
                                <div className="bg-muted rounded-lg px-4 py-2 text-sm">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
                                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </ScrollArea>

                <Separator />

                <div className="p-4">
                    <div className="flex gap-2">
                        <Input
                            placeholder={`Ask about your ${RESUME_SECTIONS.find(s => s.id === section)?.label.toLowerCase()}...`}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={sendMessageMutation.isPending}
                        />
                        <Button
                            onClick={handleSendMessage}
                            disabled={!message.trim() || sendMessageMutation.isPending}
                            size="icon"
                        >
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

interface SuggestionCardProps {
    suggestion: Suggestion;
    onApply: () => void;
    isApplying: boolean;
}

function SuggestionCard({ suggestion, onApply, isApplying }: SuggestionCardProps) {
    const getTypeIcon = (type: string) => {
        switch (type) {
            case "content": return MessageSquare;
            case "structure": return CheckCircle;
            case "keyword": return Lightbulb;
            case "formatting": return XCircle;
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

    const Icon = getTypeIcon(suggestion.type);

    return (
        <Card className={cn("border-l-4", getTypeColor(suggestion.type))}>
            <CardContent className="p-3">
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                            <Icon className="w-4 h-4" />
                            <h4 className="font-medium text-sm">{suggestion.title}</h4>
                            <Badge variant="outline" className="text-xs">
                                Impact: {Math.round(suggestion.impactScore * 100)}%
                            </Badge>
                        </div>

                        <p className="text-xs text-muted-foreground mb-2">
                            {suggestion.description}
                        </p>

                        {suggestion.originalText && suggestion.suggestedText && (
                            <div className="space-y-2 text-xs">
                                <div>
                                    <span className="font-medium text-red-600">Before:</span>
                                    <p className="bg-red-50 p-2 rounded border-l-2 border-red-200 mt-1">
                                        {suggestion.originalText}
                                    </p>
                                </div>
                                <div>
                                    <span className="font-medium text-green-600">After:</span>
                                    <p className="bg-green-50 p-2 rounded border-l-2 border-green-200 mt-1">
                                        {suggestion.suggestedText}
                                    </p>
                                </div>
                            </div>
                        )}

                        <p className="text-xs text-muted-foreground mt-2 italic">
                            {suggestion.reasoning}
                        </p>
                    </div>

                    <div className="flex flex-col gap-1">
                        {suggestion.applied ? (
                            <Badge variant="default" className="bg-green-100 text-green-800">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Applied
                            </Badge>
                        ) : (
                            <Button
                                size="sm"
                                onClick={onApply}
                                disabled={isApplying}
                                className="text-xs"
                            >
                                {isApplying ? "Applying..." : "Apply"}
                            </Button>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

interface SectionSelectorProps {
    currentSection: string;
    onSectionChange?: (section: string) => void;
}

function SectionSelector({ currentSection, onSectionChange }: SectionSelectorProps) {
    if (!onSectionChange) return null;

    return (
        <div className="flex gap-1">
            {RESUME_SECTIONS.map((section) => {
                const Icon = section.icon;
                const isActive = currentSection === section.id;

                return (
                    <Button
                        key={section.id}
                        variant={isActive ? "default" : "ghost"}
                        size="sm"
                        onClick={() => onSectionChange(section.id)}
                        className="text-xs"
                    >
                        <Icon className="w-3 h-3 mr-1" />
                        {section.label}
                    </Button>
                );
            })}
        </div>
    );
}