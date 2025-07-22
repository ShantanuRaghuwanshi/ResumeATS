import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { getApiUrl } from "@/lib/utils";
import { ExportOptionsPanel } from "./export-options-panel";
import { ExportPreview } from "./export-preview";
import { ExportHistory } from "./export-history";
import { BatchExportPanel } from "./batch-export-panel";
import {
    Download,
    Settings,
    Eye,
    History,
    Package,
    FileText,
    Loader2
} from "lucide-react";

interface AdvancedExportInterfaceProps {
    resumeId: number;
    onBack?: () => void;
}

interface ExportFormat {
    name: string;
    extension: string;
    mime_type: string;
    description: string;
    supports_templates: boolean;
    supports_styling: boolean;
    ats_friendly: boolean;
}

interface ExportTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    industry: string;
    experience_level: string;
    preview_url: string;
    customizable_sections: string[];
    styling_options: {
        color_scheme: string[];
        font_family: string[];
        spacing: string[];
    };
}

interface ExportRequest {
    id: string;
    status: "pending" | "processing" | "completed" | "failed";
    format: string;
    template: string;
    filename: string;
    created_at: string;
    completed_at?: string;
    output_path?: string;
    file_size?: number;
    download_url?: string;
    error_message?: string;
}

export default function AdvancedExportInterface({
    resumeId,
    onBack
}: AdvancedExportInterfaceProps) {
    const [activeTab, setActiveTab] = useState("export");
    const [selectedFormat, setSelectedFormat] = useState("docx");
    const [selectedTemplate, setSelectedTemplate] = useState("modern");
    const [exportOptions, setExportOptions] = useState({
        filename: "",
        include_metadata: true,
        ats_optimized: false,
        custom_styling: {},
        sections_to_include: [],
        apply_optimizations: true
    });
    const [previewData, setPreviewData] = useState<string | null>(null);
    const [activeExports, setActiveExports] = useState<ExportRequest[]>([]);

    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Fetch supported formats
    const { data: formats, isLoading: formatsLoading } = useQuery({
        queryKey: ["export-formats"],
        queryFn: async () => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/formats`);
            if (!response.ok) throw new Error("Failed to fetch formats");
            const data = await response.json();
            return data.formats as ExportFormat[];
        }
    });

    // Fetch available templates
    const { data: templates, isLoading: templatesLoading } = useQuery({
        queryKey: ["export-templates"],
        queryFn: async () => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/templates`);
            if (!response.ok) throw new Error("Failed to fetch templates");
            const data = await response.json();
            return data.templates as ExportTemplate[];
        }
    });

    // Fetch resume data for preview
    const { data: resumeData } = useQuery({
        queryKey: ["resume", resumeId],
        queryFn: async () => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/resume_sections/`);
            if (!response.ok) throw new Error("Failed to fetch resume data");
            return response.json();
        },
        enabled: !!resumeId
    });

    // Create export request mutation
    const createExportMutation = useMutation({
        mutationFn: async (exportConfig: any) => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/single`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_id: "current_user", // Replace with actual user ID
                    resume_id: resumeId.toString(),
                    ...exportConfig
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Export failed");
            }

            return response.json();
        },
        onSuccess: (data: ExportRequest) => {
            toast({
                title: "Export Started",
                description: `Your ${data.format.toUpperCase()} export is being processed.`,
            });

            setActiveExports(prev => [...prev, data]);
            pollExportStatus(data.id);
        },
        onError: (error: Error) => {
            toast({
                title: "Export Failed",
                description: error.message,
                variant: "destructive",
            });
        }
    });

    // Generate preview mutation
    const generatePreviewMutation = useMutation({
        mutationFn: async () => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/preview`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    resume_data: resumeData,
                    format: "html",
                    template: selectedTemplate,
                    custom_styling: exportOptions.custom_styling
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to generate preview");
            }

            return response.json();
        },
        onSuccess: (data) => {
            setPreviewData(data.preview_content);
        },
        onError: (error: Error) => {
            toast({
                title: "Preview Failed",
                description: error.message,
                variant: "destructive",
            });
        }
    });

    // Poll export status
    const pollExportStatus = async (exportId: string) => {
        const apiUrl = getApiUrl();
        const maxAttempts = 30; // 5 minutes with 10-second intervals
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`${apiUrl}/api/v1/export/request/${exportId}`);
                if (!response.ok) return;

                const exportRequest: ExportRequest = await response.json();

                setActiveExports(prev =>
                    prev.map(exp => exp.id === exportId ? exportRequest : exp)
                );

                if (exportRequest.status === "completed") {
                    toast({
                        title: "Export Complete",
                        description: `Your ${exportRequest.format.toUpperCase()} file is ready for download.`,
                    });
                    queryClient.invalidateQueries({ queryKey: ["export-history"] });
                } else if (exportRequest.status === "failed") {
                    toast({
                        title: "Export Failed",
                        description: exportRequest.error_message || "Unknown error occurred",
                        variant: "destructive",
                    });
                } else if (attempts < maxAttempts) {
                    attempts++;
                    setTimeout(poll, 10000); // Poll every 10 seconds
                }
            } catch (error) {
                console.error("Error polling export status:", error);
            }
        };

        poll();
    };

    // Handle export
    const handleExport = () => {
        const filename = exportOptions.filename ||
            `resume_${new Date().toISOString().split('T')[0]}`;

        createExportMutation.mutate({
            format: selectedFormat,
            template: selectedTemplate,
            filename,
            ...exportOptions
        });
    };

    // Handle preview generation
    const handleGeneratePreview = () => {
        if (!resumeData) {
            toast({
                title: "Preview Unavailable",
                description: "Resume data is not loaded yet.",
                variant: "destructive",
            });
            return;
        }

        generatePreviewMutation.mutate();
    };

    // Handle download
    const handleDownload = async (exportRequest: ExportRequest) => {
        try {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/download/${exportRequest.id}`);

            if (!response.ok) {
                throw new Error("Download failed");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${exportRequest.filename}.${exportRequest.format}`;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast({
                title: "Download Complete",
                description: `${exportRequest.filename}.${exportRequest.format} has been downloaded.`,
            });
        } catch (error) {
            toast({
                title: "Download Failed",
                description: "Failed to download the file. Please try again.",
                variant: "destructive",
            });
        }
    };

    if (formatsLoading || templatesLoading) {
        return (
            <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
                <CardContent className="p-8">
                    <div className="flex items-center justify-center space-x-2">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span>Loading export options...</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
                <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                        <FileText className="w-6 h-6" />
                        <span>Advanced Export Options</span>
                    </CardTitle>
                </CardHeader>
            </Card>

            {/* Active Exports Status */}
            {activeExports.length > 0 && (
                <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
                    <CardHeader>
                        <CardTitle className="text-lg">Active Exports</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {activeExports.map((exportRequest) => (
                                <div
                                    key={exportRequest.id}
                                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                                >
                                    <div className="flex items-center space-x-3">
                                        <div className="flex items-center space-x-2">
                                            <FileText className="w-4 h-4" />
                                            <span className="font-medium">
                                                {exportRequest.filename}.{exportRequest.format}
                                            </span>
                                        </div>
                                        <Badge
                                            variant={
                                                exportRequest.status === "completed" ? "default" :
                                                    exportRequest.status === "failed" ? "destructive" :
                                                        "secondary"
                                            }
                                        >
                                            {exportRequest.status}
                                        </Badge>
                                    </div>

                                    <div className="flex items-center space-x-2">
                                        {exportRequest.status === "processing" && (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        )}
                                        {exportRequest.status === "completed" && (
                                            <Button
                                                size="sm"
                                                onClick={() => handleDownload(exportRequest)}
                                            >
                                                <Download className="w-4 h-4 mr-1" />
                                                Download
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Main Interface */}
            <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
                <CardContent className="p-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="grid w-full grid-cols-4">
                            <TabsTrigger value="export" className="flex items-center space-x-2">
                                <Settings className="w-4 h-4" />
                                <span>Export</span>
                            </TabsTrigger>
                            <TabsTrigger value="preview" className="flex items-center space-x-2">
                                <Eye className="w-4 h-4" />
                                <span>Preview</span>
                            </TabsTrigger>
                            <TabsTrigger value="history" className="flex items-center space-x-2">
                                <History className="w-4 h-4" />
                                <span>History</span>
                            </TabsTrigger>
                            <TabsTrigger value="batch" className="flex items-center space-x-2">
                                <Package className="w-4 h-4" />
                                <span>Batch</span>
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="export" className="mt-6">
                            <ExportOptionsPanel
                                formats={formats || []}
                                templates={templates || []}
                                selectedFormat={selectedFormat}
                                selectedTemplate={selectedTemplate}
                                exportOptions={exportOptions}
                                onFormatChange={setSelectedFormat}
                                onTemplateChange={setSelectedTemplate}
                                onOptionsChange={setExportOptions}
                                onExport={handleExport}
                                isExporting={createExportMutation.isPending}
                            />
                        </TabsContent>

                        <TabsContent value="preview" className="mt-6">
                            <ExportPreview
                                previewData={previewData}
                                selectedTemplate={selectedTemplate}
                                onGeneratePreview={handleGeneratePreview}
                                isGenerating={generatePreviewMutation.isPending}
                            />
                        </TabsContent>

                        <TabsContent value="history" className="mt-6">
                            <ExportHistory
                                resumeId={resumeId}
                                onDownload={handleDownload}
                            />
                        </TabsContent>

                        <TabsContent value="batch" className="mt-6">
                            <BatchExportPanel
                                resumeId={resumeId}
                                formats={formats || []}
                                templates={templates || []}
                            />
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>

            {/* Back Button */}
            {onBack && (
                <div className="flex justify-start">
                    <Button variant="outline" onClick={onBack}>
                        Back
                    </Button>
                </div>
            )}
        </div>
    );
}