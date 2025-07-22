import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import {
    History,
    Search,
    MessageSquare,
    Calendar,
    Trash2,
    Download,
    Filter,
    Clock
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import type { ConversationSession } from "./section-chat";

interface ChatHistoryProps {
    resumeId: string;
    onConversationSelect?: (session: ConversationSession) => void;
}

interface ConversationSummary {
    id: string;
    section: string;
    messageCount: number;
    lastMessage: string;
    lastActivity: Date;
    createdAt: Date;
    suggestionsCount: number;
    appliedSuggestionsCount: number;
}

const SECTION_LABELS: Record<string, string> = {
    personal: "Personal Details",
    summary: "Professional Summary",
    experience: "Work Experience",
    skills: "Skills",
    education: "Education",
    projects: "Projects",
};

export default function ChatHistory({ resumeId, onConversationSelect }: ChatHistoryProps) {
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedSection, setSelectedSection] = useState<string | null>(null);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Fetch conversation history
    const { data: conversations, isLoading } = useQuery({
        queryKey: ["conversation-history", resumeId],
        queryFn: async (): Promise<ConversationSummary[]> => {
            const response = await apiRequest("GET", `/conversation/history/${resumeId}`);
            return response.json();
        },
    });

    // Delete conversation mutation
    const deleteConversationMutation = useMutation({
        mutationFn: async (conversationId: string) => {
            await apiRequest("DELETE", `/conversation/${conversationId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["conversation-history", resumeId] });
            toast({
                title: "Conversation deleted",
                description: "The conversation has been removed from your history.",
            });
        },
        onError: (error) => {
            toast({
                title: "Failed to delete conversation",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Export conversation mutation
    const exportConversationMutation = useMutation({
        mutationFn: async (conversationId: string) => {
            const response = await apiRequest("GET", `/conversation/${conversationId}/export`);
            return response.blob();
        },
        onSuccess: (blob, conversationId) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `conversation-${conversationId}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast({
                title: "Conversation exported",
                description: "The conversation has been downloaded as a JSON file.",
            });
        },
        onError: (error) => {
            toast({
                title: "Failed to export conversation",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    const handleConversationClick = async (conversationId: string) => {
        if (!onConversationSelect) return;

        try {
            const response = await apiRequest("GET", `/conversation/${conversationId}`);
            const session: ConversationSession = await response.json();
            onConversationSelect(session);
        } catch (error) {
            toast({
                title: "Failed to load conversation",
                description: "Please try again.",
                variant: "destructive",
            });
        }
    };

    const handleDeleteConversation = (conversationId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        deleteConversationMutation.mutate(conversationId);
    };

    const handleExportConversation = (conversationId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        exportConversationMutation.mutate(conversationId);
    };

    // Filter conversations based on search and section
    const filteredConversations = conversations?.filter((conv) => {
        const matchesSearch = !searchQuery ||
            conv.lastMessage.toLowerCase().includes(searchQuery.toLowerCase()) ||
            SECTION_LABELS[conv.section]?.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesSection = !selectedSection || conv.section === selectedSection;

        return matchesSearch && matchesSection;
    }) || [];

    // Group conversations by date
    const groupedConversations = filteredConversations.reduce((acc, conv) => {
        const date = new Date(conv.lastActivity).toDateString();
        if (!acc[date]) {
            acc[date] = [];
        }
        acc[date].push(conv);
        return acc;
    }, {} as Record<string, ConversationSummary[]>);

    const sections = Array.from(new Set(conversations?.map(c => c.section) || []));

    if (isLoading) {
        return (
            <Card className="h-full">
                <CardContent className="flex items-center justify-center h-full">
                    <div className="text-center">
                        <History className="w-8 h-8 mx-auto mb-2 text-muted-foreground animate-pulse" />
                        <p className="text-sm text-muted-foreground">Loading conversation history...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!conversations?.length) {
        return (
            <Card className="h-full">
                <CardContent className="flex items-center justify-center h-full">
                    <div className="text-center">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                        <h3 className="text-lg font-medium text-slate-800 mb-2">No conversations yet</h3>
                        <p className="text-sm text-muted-foreground">
                            Start chatting with the AI assistant to see your conversation history here.
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <History className="w-5 h-5 text-primary" />
                    Conversation History
                </CardTitle>

                <div className="space-y-3">
                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                            placeholder="Search conversations..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10"
                        />
                    </div>

                    {/* Section filter */}
                    <div className="flex gap-2 flex-wrap">
                        <Button
                            variant={selectedSection === null ? "default" : "outline"}
                            size="sm"
                            onClick={() => setSelectedSection(null)}
                            className="text-xs"
                        >
                            <Filter className="w-3 h-3 mr-1" />
                            All Sections
                        </Button>
                        {sections.map((section) => (
                            <Button
                                key={section}
                                variant={selectedSection === section ? "default" : "outline"}
                                size="sm"
                                onClick={() => setSelectedSection(section)}
                                className="text-xs"
                            >
                                {SECTION_LABELS[section] || section}
                            </Button>
                        ))}
                    </div>
                </div>
            </CardHeader>

            <Separator />

            <CardContent className="flex-1 p-0">
                <ScrollArea className="h-full">
                    <div className="p-4 space-y-4">
                        {Object.entries(groupedConversations).map(([date, dateConversations]) => (
                            <div key={date} className="space-y-2">
                                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                    <Calendar className="w-4 h-4" />
                                    {date}
                                </div>

                                <div className="space-y-2 pl-6">
                                    {dateConversations.map((conversation) => (
                                        <ConversationItem
                                            key={conversation.id}
                                            conversation={conversation}
                                            onClick={() => handleConversationClick(conversation.id)}
                                            onDelete={(e) => handleDeleteConversation(conversation.id, e)}
                                            onExport={(e) => handleExportConversation(conversation.id, e)}
                                            isDeleting={deleteConversationMutation.isPending}
                                            isExporting={exportConversationMutation.isPending}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}

                        {filteredConversations.length === 0 && (
                            <div className="text-center py-8">
                                <Search className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">
                                    No conversations found matching your search.
                                </p>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}

interface ConversationItemProps {
    conversation: ConversationSummary;
    onClick: () => void;
    onDelete: (e: React.MouseEvent) => void;
    onExport: (e: React.MouseEvent) => void;
    isDeleting: boolean;
    isExporting: boolean;
}

function ConversationItem({
    conversation,
    onClick,
    onDelete,
    onExport,
    isDeleting,
    isExporting
}: ConversationItemProps) {
    return (
        <div
            className="group p-3 bg-muted/50 rounded-lg cursor-pointer hover:bg-muted transition-colors"
            onClick={onClick}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">
                            {SECTION_LABELS[conversation.section] || conversation.section}
                        </Badge>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <MessageSquare className="w-3 h-3" />
                            {conversation.messageCount} messages
                        </div>
                    </div>

                    <p className="text-sm text-slate-800 line-clamp-2 mb-2">
                        {conversation.lastMessage}
                    </p>

                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {new Date(conversation.lastActivity).toLocaleTimeString()}
                            </div>

                            {conversation.suggestionsCount > 0 && (
                                <div className="flex items-center gap-1">
                                    <span>{conversation.appliedSuggestionsCount}/{conversation.suggestionsCount} applied</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onExport}
                        disabled={isExporting}
                        className="h-8 w-8 p-0"
                    >
                        <Download className="w-3 h-3" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onDelete}
                        disabled={isDeleting}
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                    >
                        <Trash2 className="w-3 h-3" />
                    </Button>
                </div>
            </div>
        </div>
    );
}