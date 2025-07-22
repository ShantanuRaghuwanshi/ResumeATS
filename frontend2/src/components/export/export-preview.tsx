import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    Eye,
    Loader2,
    RefreshCw,
    ZoomIn,
    ZoomOut,
    Maximize2,
    Download,
    AlertCircle
} from "lucide-react";

interface ExportPreviewProps {
    previewData: string | null;
    selectedTemplate: string;
    onGeneratePreview: () => void;
    isGenerating: boolean;
}

export function ExportPreview({
    previewData,
    selectedTemplate,
    onGeneratePreview,
    isGenerating
}: ExportPreviewProps) {
    const [zoomLevel, setZoomLevel] = useState(100);
    const [isFullscreen, setIsFullscreen] = useState(false);

    const handleZoomIn = () => {
        setZoomLevel(prev => Math.min(prev + 25, 200));
    };

    const handleZoomOut = () => {
        setZoomLevel(prev => Math.max(prev - 25, 50));
    };

    const handleFullscreen = () => {
        setIsFullscreen(!isFullscreen);
    };

    const PreviewContent = () => {
        if (!previewData) {
            return (
                <div className="flex flex-col items-center justify-center h-96 text-slate-500">
                    <Eye className="w-16 h-16 mb-4 text-slate-300" />
                    <h3 className="text-lg font-semibold mb-2">No Preview Available</h3>
                    <p className="text-center mb-4">
                        Generate a preview to see how your resume will look with the selected template and styling options.
                    </p>
                    <Button onClick={onGeneratePreview} disabled={isGenerating}>
                        {isGenerating ? (
                            <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Generating Preview...
                            </>
                        ) : (
                            <>
                                <Eye className="w-4 h-4 mr-2" />
                                Generate Preview
                            </>
                        )}
                    </Button>
                </div>
            );
        }

        return (
            <div className="space-y-4">
                {/* Preview Controls */}
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                    <div className="flex items-center space-x-2">
                        <Badge variant="outline">
                            Template: {selectedTemplate}
                        </Badge>
                        <Badge variant="secondary">
                            Zoom: {zoomLevel}%
                        </Badge>
                    </div>

                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleZoomOut}
                            disabled={zoomLevel <= 50}
                        >
                            <ZoomOut className="w-4 h-4" />
                        </Button>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleZoomIn}
                            disabled={zoomLevel >= 200}
                        >
                            <ZoomIn className="w-4 h-4" />
                        </Button>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleFullscreen}
                        >
                            <Maximize2 className="w-4 h-4" />
                        </Button>

                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onGeneratePreview}
                            disabled={isGenerating}
                        >
                            {isGenerating ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <RefreshCw className="w-4 h-4" />
                            )}
                        </Button>
                    </div>
                </div>

                {/* Preview Frame */}
                <div className="border-2 border-slate-200 rounded-lg overflow-hidden bg-white">
                    <div
                        className="preview-container overflow-auto"
                        style={{
                            height: isFullscreen ? "80vh" : "600px",
                            transform: `scale(${zoomLevel / 100})`,
                            transformOrigin: "top left",
                            width: `${10000 / zoomLevel}%`,
                        }}
                    >
                        <div
                            className="preview-content p-8"
                            dangerouslySetInnerHTML={{ __html: previewData }}
                            style={{
                                minHeight: "100%",
                                backgroundColor: "white"
                            }}
                        />
                    </div>
                </div>

                {/* Preview Actions */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-sm text-slate-600">
                        <AlertCircle className="w-4 h-4" />
                        <span>This is a preview. Actual export may vary slightly.</span>
                    </div>

                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            onClick={onGeneratePreview}
                            disabled={isGenerating}
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Updating...
                                </>
                            ) : (
                                <>
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Update Preview
                                </>
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        );
    };

    if (isFullscreen) {
        return (
            <div className="fixed inset-0 z-50 bg-white">
                <div className="h-full flex flex-col">
                    {/* Fullscreen Header */}
                    <div className="flex items-center justify-between p-4 border-b">
                        <div className="flex items-center space-x-2">
                            <Eye className="w-5 h-5" />
                            <span className="font-semibold">Resume Preview</span>
                            <Badge variant="outline">
                                Template: {selectedTemplate}
                            </Badge>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleZoomOut}
                                disabled={zoomLevel <= 50}
                            >
                                <ZoomOut className="w-4 h-4" />
                            </Button>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleZoomIn}
                                disabled={zoomLevel >= 200}
                            >
                                <ZoomIn className="w-4 h-4" />
                            </Button>

                            <Badge variant="secondary">
                                {zoomLevel}%
                            </Badge>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleFullscreen}
                            >
                                Exit Fullscreen
                            </Button>
                        </div>
                    </div>

                    {/* Fullscreen Content */}
                    <div className="flex-1 overflow-hidden">
                        <div
                            className="h-full overflow-auto bg-slate-50 p-8"
                            style={{
                                transform: `scale(${zoomLevel / 100})`,
                                transformOrigin: "top left",
                                width: `${10000 / zoomLevel}%`,
                            }}
                        >
                            <div
                                className="bg-white shadow-lg mx-auto"
                                style={{ maxWidth: "8.5in", minHeight: "11in" }}
                                dangerouslySetInnerHTML={{ __html: previewData || "" }}
                            />
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                        <Eye className="w-5 h-5" />
                        <span>Resume Preview</span>
                    </CardTitle>
                </CardHeader>
            </Card>

            {/* Preview Content */}
            <Card>
                <CardContent className="p-6">
                    <PreviewContent />
                </CardContent>
            </Card>

            {/* Preview Information */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <span className="font-medium">Template:</span>
                                <Badge variant="outline">{selectedTemplate}</Badge>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="font-medium">Format:</span>
                                <Badge variant="secondary">HTML Preview</Badge>
                            </div>
                        </div>

                        <div className="text-slate-600">
                            Preview generated for visual reference only
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}