import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { getApiUrl } from "@/lib/utils";
import {
    Package,
    Plus,
    Trash2,
    Download,
    Loader2,
    FileText,
    FileImage,
    File,
    Settings,
    Archive
} from "lucide-react";

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

interface ResumeVersion {
    id: string;
    name: string;
    description: string;
    created_at: string;
    optimization_score?: number;
    job_target?: string;
}

interface BatchExportConfig {
    version_id: string;
    format: string;
    template: string;
    filename: string;
    include_metadata: boolean;
    ats_optimized: boolean;
    custom_styling: Record<string, any>;
    sections_to_include: string[];
    apply_optimizations: boolean;
}

interface BatchExportRequest {
    id: string;
    batch_name: string;
    status: "pending" | "processing" | "completed" | "failed" | "partial";
    total_items: number;
    completed_items: number;
    failed_items: number;
    progress_percentage: number;
    created_at: string;
    completed_at?: string;
    output_path?: string;
    total_size?: number;
    download_url?: string;
}

interface BatchExportPanelProps {
    resumeId: number;
    formats: ExportFormat[];
    templates: ExportTemplate[];
}

const formatIcons: Record<string, React.ElementType> = {
    docx: FileText,
    pdf: FileImage,
    txt: File,
    json: File,
    html: FileText,
};

export function BatchExportPanel({
    resumeId,
    formats,
    templates
}: BatchExportPanelProps) {
    const [batchName, setBatchName] = useState("");
    const [outputFormat, setOutputFormat] = useState<"zip" | "individual">("zip");
    const [includeManifest, setIncludeManifest] = useState(true);
    const [compressOutput, setCompressOutput] = useState(true);
    const [exportConfigs, setExportConfigs] = useState<BatchExportConfig[]>([]);
    const [activeBatches, setActiveBatches] = useState<BatchExportRequest[]>([]);

    const { toast } = useToast();

    // Fetch available resume versions
    const { data: versions, isLoading: versionsLoading } = useQuery({
        queryKey: ["resume-versions", "current_user"], // Replace with actual user ID
        queryFn: async () => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/versions/list/current_user`);
            if (!response.ok) throw new Error("Failed to fetch versions");
            const data = await response.json();
            return data.versions as ResumeVersion[];
        }
    });

    // Create batch export mutation
    const createBatchExportMutation = useMutation({
        mutationFn: async (batchConfig: any) => {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/batch`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(batchConfig),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Batch export failed");
            }

            return response.json();
        },
        onSuccess: (data: BatchExportRequest) => {
            toast({
                title: "Batch Export Started",
                description: `Processing ${data.total_items} exports in batch "${data.batch_name}".`,
            });

            setActiveBatches(prev => [...prev, data]);
            pollBatchStatus(data.id);
        },
        onError: (error: Error) => {
            toast({
                title: "Batch Export Failed",
                description: error.message,
                variant: "destructive",
            });
        }
    });

    // Add new export configuration
    const addExportConfig = () => {
        const newConfig: BatchExportConfig = {
            version_id: versions?.[0]?.id || "",
            format: "docx",
            template: "modern",
            filename: `export_${exportConfigs.length + 1}`,
            include_metadata: true,
            ats_optimized: false,
            custom_styling: {},
            sections_to_include: [],
            apply_optimizations: true
        };

        setExportConfigs([...exportConfigs, newConfig]);
    };

    // Remove export configuration
    const removeExportConfig = (index: number) => {
        setExportConfigs(exportConfigs.filter((_, i) => i !== index));
    };

    // Update export configuration
    const updateExportConfig = (index: number, updates: Partial<BatchExportConfig>) => {
        const newConfigs = [...exportConfigs];
        newConfigs[index] = { ...newConfigs[index], ...updates };
        setExportConfigs(newConfigs);
    };

    // Poll batch status
    const pollBatchStatus = async (batchId: string) => {
        const apiUrl = getApiUrl();
        const maxAttempts = 60; // 10 minutes with 10-second intervals
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`${apiUrl}/api/v1/export/batch/${batchId}`);
                if (!response.ok) return;

                const batchRequest: BatchExportRequest = await response.json();

                setActiveBatches(prev =>
                    prev.map(batch => batch.id === batchId ? batchRequest : batch)
                );

                if (batchRequest.status === "completed" || batchRequest.status === "partial") {
                    toast({
                        title: "Batch Export Complete",
                        description: `Batch "${batchRequest.batch_name}" has finished processing.`,
                    });
                } else if (batchRequest.status === "failed") {
                    toast({
                        title: "Batch Export Failed",
                        description: `Batch "${batchRequest.batch_name}" failed to process.`,
                        variant: "destructive",
                    });
                } else if (attempts < maxAttempts) {
                    attempts++;
                    setTimeout(poll, 10000); // Poll every 10 seconds
                }
            } catch (error) {
                console.error("Error polling batch status:", error);
            }
        };

        poll();
    };

    // Handle batch export
    const handleBatchExport = () => {
        if (!batchName.trim()) {
            toast({
                title: "Batch Name Required",
                description: "Please enter a name for this batch export.",
                variant: "destructive",
            });
            return;
        }

        if (exportConfigs.length === 0) {
            toast({
                title: "No Export Configurations",
                description: "Please add at least one export configuration.",
                variant: "destructive",
            });
            return;
        }

        const versionIds = exportConfigs.map(config => config.version_id);
        const exportConfigsForApi = exportConfigs.map(config => ({
            format: config.format,
            template: config.template,
            filename: config.filename,
            include_metadata: config.include_metadata,
            ats_optimized: config.ats_optimized,
            custom_styling: config.custom_styling,
            sections_to_include: config.sections_to_include,
            apply_optimizations: config.apply_optimizations
        }));

        createBatchExportMutation.mutate({
            user_id: "current_user", // Replace with actual user ID
            batch_name: batchName,
            version_ids: versionIds,
            export_configs: exportConfigsForApi,
            output_format: outputFormat,
            include_manifest: includeManifest,
            compress_output: compressOutput
        });
    };

    // Handle batch download
    const handleBatchDownload = async (batch: BatchExportRequest) => {
        try {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/api/v1/export/download/batch/${batch.id}`);

            if (!response.ok) {
                throw new Error("Download failed");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${batch.batch_name}.${outputFormat === "zip" ? "zip" : "tar"}`;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast({
                title: "Batch Download Complete",
                description: `${batch.batch_name} has been downloaded.`,
            });
        } catch (error) {
            toast({
                title: "Download Failed",
                description: "Failed to download the batch export. Please try again.",
                variant: "destructive",
            });
        }
    };

    if (versionsLoading) {
        return (
            <Card>
                <CardContent className="p-8">
                    <div className="flex items-center justify-center space-x-2">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span>Loading resume versions...</span>
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
                    <CardTitle className="flex items-center space-x-2">
                        <Package className="w-5 h-5" />
                        <span>Batch Export</span>
                    </CardTitle>
                </CardHeader>
            </Card>

            {/* Active Batches */}
            {activeBatches.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Active Batch Exports</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {activeBatches.map((batch) => (
                                <div
                                    key={batch.id}
                                    className="p-4 bg-slate-50 rounded-lg space-y-3"
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h4 className="font-semibold">{batch.batch_name}</h4>
                                            <p className="text-sm text-slate-600">
                                                {batch.completed_items} of {batch.total_items} completed
                                                {batch.failed_items > 0 && ` (${batch.failed_items} failed)`}
                                            </p>
                                        </div>

                                        <div className="flex items-center space-x-2">
                                            <Badge
                                                variant={
                                                    batch.status === "completed" ? "default" :
                                                        batch.status === "failed" ? "destructive" :
                                                            batch.status === "partial" ? "secondary" :
                                                                "outline"
                                                }
                                            >
                                                {batch.status}
                                            </Badge>

                                            {(batch.status === "completed" || batch.status === "partial") && (
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleBatchDownload(batch)}
                                                >
                                                    <Download className="w-4 h-4 mr-1" />
                                                    Download
                                                </Button>
                                            )}
                                        </div>
                                    </div>

                                    <Progress value={batch.progress_percentage} className="w-full" />
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Batch Configuration */}
            <Card>
                <CardHeader>
                    <CardTitle>Batch Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Batch Settings */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="batch-name">Batch Name</Label>
                            <Input
                                id="batch-name"
                                placeholder="Enter batch name"
                                value={batchName}
                                onChange={(e) => setBatchName(e.target.value)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Output Format</Label>
                            <Select value={outputFormat} onValueChange={(value: "zip" | "individual") => setOutputFormat(value)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="zip">ZIP Archive</SelectItem>
                                    <SelectItem value="individual">Individual Files</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Additional Options */}
                    <div className="flex flex-col space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Include Manifest</Label>
                                <p className="text-sm text-slate-600">
                                    Include a manifest file with export details
                                </p>
                            </div>
                            <Switch
                                checked={includeManifest}
                                onCheckedChange={setIncludeManifest}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Compress Output</Label>
                                <p className="text-sm text-slate-600">
                                    Compress files to reduce download size
                                </p>
                            </div>
                            <Switch
                                checked={compressOutput}
                                onCheckedChange={setCompressOutput}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Export Configurations */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                        <span>Export Configurations</span>
                        <Button onClick={addExportConfig} size="sm">
                            <Plus className="w-4 h-4 mr-2" />
                            Add Export
                        </Button>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {exportConfigs.length === 0 ? (
                        <div className="text-center text-slate-500 py-8">
                            <Settings className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                            <h3 className="text-lg font-semibold mb-2">No Export Configurations</h3>
                            <p className="mb-4">Add export configurations to create a batch export.</p>
                            <Button onClick={addExportConfig}>
                                <Plus className="w-4 h-4 mr-2" />
                                Add First Export
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {exportConfigs.map((config, index) => {
                                const Icon = formatIcons[config.format] || File;
                                const selectedVersion = versions?.find(v => v.id === config.version_id);

                                return (
                                    <div key={index} className="p-4 border rounded-lg space-y-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <div className="w-10 h-10 bg-primary/10 text-primary rounded-lg flex items-center justify-center">
                                                    <Icon className="w-5 h-5" />
                                                </div>
                                                <div>
                                                    <h4 className="font-semibold">Export {index + 1}</h4>
                                                    <p className="text-sm text-slate-600">
                                                        {config.format.toUpperCase()} • {config.template}
                                                    </p>
                                                </div>
                                            </div>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => removeExportConfig(index)}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            {/* Version Selection */}
                                            <div className="space-y-2">
                                                <Label>Resume Version</Label>
                                                <Select
                                                    value={config.version_id}
                                                    onValueChange={(value) => updateExportConfig(index, { version_id: value })}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select version" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {versions?.map((version) => (
                                                            <SelectItem key={version.id} value={version.id}>
                                                                {version.name}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            {/* Format Selection */}
                                            <div className="space-y-2">
                                                <Label>Format</Label>
                                                <Select
                                                    value={config.format}
                                                    onValueChange={(value) => updateExportConfig(index, { format: value })}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {formats.map((format) => (
                                                            <SelectItem key={format.extension} value={format.extension}>
                                                                {format.name}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>

                                            {/* Template Selection */}
                                            <div className="space-y-2">
                                                <Label>Template</Label>
                                                <Select
                                                    value={config.template}
                                                    onValueChange={(value) => updateExportConfig(index, { template: value })}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {templates.map((template) => (
                                                            <SelectItem key={template.id} value={template.id}>
                                                                {template.name}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        </div>

                                        {/* Filename */}
                                        <div className="space-y-2">
                                            <Label>Filename</Label>
                                            <Input
                                                placeholder="Enter filename"
                                                value={config.filename}
                                                onChange={(e) => updateExportConfig(index, { filename: e.target.value })}
                                            />
                                        </div>

                                        {/* Options */}
                                        <div className="flex flex-wrap gap-4">
                                            <div className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`metadata-${index}`}
                                                    checked={config.include_metadata}
                                                    onCheckedChange={(checked) =>
                                                        updateExportConfig(index, { include_metadata: !!checked })
                                                    }
                                                />
                                                <Label htmlFor={`metadata-${index}`} className="text-sm">
                                                    Include Metadata
                                                </Label>
                                            </div>

                                            <div className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`ats-${index}`}
                                                    checked={config.ats_optimized}
                                                    onCheckedChange={(checked) =>
                                                        updateExportConfig(index, { ats_optimized: !!checked })
                                                    }
                                                />
                                                <Label htmlFor={`ats-${index}`} className="text-sm">
                                                    ATS Optimized
                                                </Label>
                                            </div>

                                            <div className="flex items-center space-x-2">
                                                <Checkbox
                                                    id={`optimizations-${index}`}
                                                    checked={config.apply_optimizations}
                                                    onCheckedChange={(checked) =>
                                                        updateExportConfig(index, { apply_optimizations: !!checked })
                                                    }
                                                />
                                                <Label htmlFor={`optimizations-${index}`} className="text-sm">
                                                    Apply AI Optimizations
                                                </Label>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Export Button */}
            {exportConfigs.length > 0 && (
                <Card>
                    <CardContent className="p-6">
                        <Button
                            onClick={handleBatchExport}
                            disabled={createBatchExportMutation.isPending || !batchName.trim()}
                            className="w-full h-12 text-lg"
                            size="lg"
                        >
                            {createBatchExportMutation.isPending ? (
                                <>
                                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                    Creating Batch Export...
                                </>
                            ) : (
                                <>
                                    <Archive className="w-5 h-5 mr-2" />
                                    Create Batch Export ({exportConfigs.length} items)
                                </>
                            )}
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}