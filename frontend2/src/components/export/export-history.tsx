import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { getApiUrl, fetchWithSession } from "@/lib/utils";
import {
    History,
    Download,
    Search,
    Filter,
    FileText,
    FileImage,
    File,
    Calendar,
    HardDrive,
    RefreshCw,
    Trash2,
    Eye
} from "lucide-react";

interface ExportHistoryItem {
    id: string;
    export_request_id: string;
    format: string;
    template: string;
    filename: string;
    file_size: number;
    download_count: number;
    last_downloaded?: string;
    download_history: string[];
    file_path: string;
    is_available: boolean;
    expires_at?: string;
    created_at: string;
    metadata: Record<string, any>;
}

interface ExportHistoryProps {
    resumeId: number;
    onDownload: (exportRequest: any) => void;
}

const formatIcons: Record<string, React.ElementType> = {
    docx: FileText,
    pdf: FileImage,
    txt: File,
    json: File,
    html: FileText,
};

const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
};

export function ExportHistory({ resumeId, onDownload }: ExportHistoryProps) {
    const [searchTerm, setSearchTerm] = useState("");
    const [formatFilter, setFormatFilter] = useState("all");
    const [sortBy, setSortBy] = useState("created_at");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

    const { toast } = useToast();

    // Fetch export history
    const {
        data: historyData,
        isLoading,
        refetch,
        error
    } = useQuery({
        queryKey: ["export-history", "current_user"], // Replace with actual user ID
        queryFn: async () => {
            const response = await fetchWithSession("/api/v1/export/history/current_user");
            if (!response.ok) {
                throw new Error("Failed to fetch export history");
            }
            const data = await response.json();
            return data.history as ExportHistoryItem[];
        },
        refetchInterval: 30000, // Refetch every 30 seconds
    });

    // Filter and sort history
    const filteredHistory = historyData?.filter(item => {
        const matchesSearch = item.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
            item.template.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFormat = formatFilter === "all" || item.format === formatFilter;
        return matchesSearch && matchesFormat;
    }).sort((a, b) => {
        const aValue = a[sortBy as keyof ExportHistoryItem];
        const bValue = b[sortBy as keyof ExportHistoryItem];

        if (sortOrder === "asc") {
            return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
        } else {
            return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
        }
    }) || [];

    // Get unique formats for filter
    const availableFormats = [...new Set(historyData?.map(item => item.format) || [])];

    const handleDownload = async (historyItem: ExportHistoryItem) => {
        if (!historyItem.is_available) {
            toast({
                title: "File Not Available",
                description: "This export file is no longer available for download.",
                variant: "destructive",
            });
            return;
        }

        // Create a mock export request object for compatibility
        const exportRequest = {
            id: historyItem.export_request_id,
            status: "completed" as const,
            format: historyItem.format,
            template: historyItem.template,
            filename: historyItem.filename,
            created_at: historyItem.created_at,
            output_path: historyItem.file_path,
            file_size: historyItem.file_size
        };

        onDownload(exportRequest);
    };

    const handleReDownload = async (historyItem: ExportHistoryItem) => {
        try {
            const response = await fetchWithSession(`/api/v1/export/download/${historyItem.export_request_id}`);

            if (!response.ok) {
                throw new Error("Download failed");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${historyItem.filename}.${historyItem.format}`;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast({
                title: "Download Complete",
                description: `${historyItem.filename}.${historyItem.format} has been downloaded.`,
            });

            // Refresh history to update download count
            refetch();
        } catch (error) {
            toast({
                title: "Download Failed",
                description: "Failed to download the file. Please try again.",
                variant: "destructive",
            });
        }
    };

    if (error) {
        return (
            <Card>
                <CardContent className="p-6">
                    <div className="text-center text-slate-500">
                        <History className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                        <h3 className="text-lg font-semibold mb-2">Failed to Load History</h3>
                        <p className="mb-4">Unable to fetch your export history.</p>
                        <Button onClick={() => refetch()} variant="outline">
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Try Again
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <History className="w-5 h-5" />
                            <span>Export History</span>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => refetch()}
                            disabled={isLoading}
                        >
                            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
                            Refresh
                        </Button>
                    </CardTitle>
                </CardHeader>
            </Card>

            {/* Filters and Search */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row gap-4">
                        {/* Search */}
                        <div className="flex-1">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                                <Input
                                    placeholder="Search by filename or template..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                        </div>

                        {/* Format Filter */}
                        <div className="w-full md:w-48">
                            <Select value={formatFilter} onValueChange={setFormatFilter}>
                                <SelectTrigger>
                                    <Filter className="w-4 h-4 mr-2" />
                                    <SelectValue placeholder="All formats" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Formats</SelectItem>
                                    {availableFormats.map((format) => (
                                        <SelectItem key={format} value={format}>
                                            {format.toUpperCase()}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Sort */}
                        <div className="w-full md:w-48">
                            <Select value={`${sortBy}-${sortOrder}`} onValueChange={(value) => {
                                const [field, order] = value.split("-");
                                setSortBy(field);
                                setSortOrder(order as "asc" | "desc");
                            }}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Sort by" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="created_at-desc">Newest First</SelectItem>
                                    <SelectItem value="created_at-asc">Oldest First</SelectItem>
                                    <SelectItem value="filename-asc">Name A-Z</SelectItem>
                                    <SelectItem value="filename-desc">Name Z-A</SelectItem>
                                    <SelectItem value="file_size-desc">Largest First</SelectItem>
                                    <SelectItem value="file_size-asc">Smallest First</SelectItem>
                                    <SelectItem value="download_count-desc">Most Downloaded</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* History List */}
            <Card>
                <CardContent className="p-6">
                    {isLoading ? (
                        <div className="space-y-4">
                            {[...Array(3)].map((_, i) => (
                                <div key={i} className="animate-pulse">
                                    <div className="flex items-center space-x-4 p-4 border rounded-lg">
                                        <div className="w-12 h-12 bg-slate-200 rounded-lg"></div>
                                        <div className="flex-1 space-y-2">
                                            <div className="h-4 bg-slate-200 rounded w-1/3"></div>
                                            <div className="h-3 bg-slate-200 rounded w-1/2"></div>
                                        </div>
                                        <div className="w-24 h-8 bg-slate-200 rounded"></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : filteredHistory.length === 0 ? (
                        <div className="text-center text-slate-500 py-12">
                            <History className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                            <h3 className="text-lg font-semibold mb-2">No Export History</h3>
                            <p>
                                {historyData?.length === 0
                                    ? "You haven't exported any resumes yet."
                                    : "No exports match your current filters."
                                }
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredHistory.map((item) => {
                                const Icon = formatIcons[item.format] || File;
                                const isExpired = item.expires_at && new Date(item.expires_at) < new Date();

                                return (
                                    <div
                                        key={item.id}
                                        className={`flex items-center space-x-4 p-4 border rounded-lg transition-colors ${item.is_available && !isExpired
                                            ? "hover:bg-slate-50"
                                            : "bg-slate-50 opacity-75"
                                            }`}
                                    >
                                        {/* File Icon */}
                                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${item.is_available && !isExpired
                                            ? "bg-primary/10 text-primary"
                                            : "bg-slate-200 text-slate-400"
                                            }`}>
                                            <Icon className="w-6 h-6" />
                                        </div>

                                        {/* File Info */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center space-x-2 mb-1">
                                                <h4 className="font-semibold text-slate-800 truncate">
                                                    {item.filename}.{item.format}
                                                </h4>
                                                <Badge variant="outline" className="text-xs">
                                                    {item.format.toUpperCase()}
                                                </Badge>
                                                <Badge variant="secondary" className="text-xs">
                                                    {item.template}
                                                </Badge>
                                            </div>

                                            <div className="flex items-center space-x-4 text-sm text-slate-600">
                                                <div className="flex items-center space-x-1">
                                                    <Calendar className="w-3 h-3" />
                                                    <span>{formatDate(item.created_at)}</span>
                                                </div>

                                                <div className="flex items-center space-x-1">
                                                    <HardDrive className="w-3 h-3" />
                                                    <span>{formatBytes(item.file_size)}</span>
                                                </div>

                                                <div className="flex items-center space-x-1">
                                                    <Download className="w-3 h-3" />
                                                    <span>{item.download_count} downloads</span>
                                                </div>
                                            </div>

                                            {item.last_downloaded && (
                                                <div className="text-xs text-slate-500 mt-1">
                                                    Last downloaded: {formatDate(item.last_downloaded)}
                                                </div>
                                            )}

                                            {isExpired && (
                                                <div className="text-xs text-red-500 mt-1">
                                                    Expired on: {formatDate(item.expires_at!)}
                                                </div>
                                            )}
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center space-x-2">
                                            {item.is_available && !isExpired ? (
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleReDownload(item)}
                                                >
                                                    <Download className="w-4 h-4 mr-1" />
                                                    Download
                                                </Button>
                                            ) : (
                                                <Badge variant="secondary" className="text-xs">
                                                    {isExpired ? "Expired" : "Unavailable"}
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Summary Stats */}
            {historyData && historyData.length > 0 && (
                <Card>
                    <CardContent className="p-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                            <div>
                                <div className="text-2xl font-bold text-slate-800">
                                    {historyData.length}
                                </div>
                                <div className="text-sm text-slate-600">Total Exports</div>
                            </div>

                            <div>
                                <div className="text-2xl font-bold text-slate-800">
                                    {historyData.reduce((sum, item) => sum + item.download_count, 0)}
                                </div>
                                <div className="text-sm text-slate-600">Total Downloads</div>
                            </div>

                            <div>
                                <div className="text-2xl font-bold text-slate-800">
                                    {formatBytes(historyData.reduce((sum, item) => sum + item.file_size, 0))}
                                </div>
                                <div className="text-sm text-slate-600">Total Size</div>
                            </div>

                            <div>
                                <div className="text-2xl font-bold text-slate-800">
                                    {historyData.filter(item => item.is_available).length}
                                </div>
                                <div className="text-sm text-slate-600">Available</div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}