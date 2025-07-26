import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Download, FileText, FileImage, File, Settings } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { getApiUrl, fetchWithSession } from "@/lib/utils";
import { AdvancedExportInterface } from "@/components/export";
import type { Resume, AnalysisResult } from "@/shared/schema";

interface DownloadOptionsProps {
  resumeId: number;
  onBack: () => void;
}

interface DownloadFormat {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  mimeType: string;
}

export default function DownloadOptions({ resumeId, onBack }: DownloadOptionsProps) {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"simple" | "advanced">("simple");
  const { toast } = useToast();

  // Fetch resume sections
  const { data: resume, isLoading } = useQuery({
    queryKey: ["/resume_sections/"],
    queryFn: async () => {
      const res = await fetchWithSession("/api/v1/resume_sections/");
      if (!res.ok) throw new Error("Failed to fetch resume sections");
      return res.json();
    },
    enabled: !!resumeId,
  });

  const downloadFormats: DownloadFormat[] = [
    {
      id: "pdf",
      name: "PDF Format",
      description: "Best for applications and printing",
      icon: FileImage,
      color: "bg-red-100 text-red-600",
      mimeType: "application/pdf",
    },
    {
      id: "docx",
      name: "Word Document",
      description: "Editable format for future updates",
      icon: FileText,
      color: "bg-blue-100 text-blue-600",
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
      id: "txt",
      name: "Plain Text",
      description: "ATS-friendly text format",
      icon: File,
      color: "bg-gray-100 text-gray-600",
      mimeType: "text/plain",
    },
  ];

  const handleDownload = async (format: DownloadFormat) => {
    if (!resume) return;

    setDownloadingFormat(format.id);

    try {
      // Use /download/{filename} endpoint
      const baseFilename = resume.filename?.replace(/\.[^/.]+$/, "") || "resume";
      const filename = `${baseFilename}.${format.id}`;
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/download/${filename}`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Download failed");
      }

      // Create download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      // Extract filename from resume or use default
      link.download = filename;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: "Download successful",
        description: `Your resume has been downloaded as ${format.name}.`,
      });
    } catch (error) {
      let message = "Failed to download resume. Please try again.";
      if (error instanceof Error) message = error.message;
      toast({
        title: "Download failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setDownloadingFormat(null);
    }
  };

  const startNewAnalysis = () => {
    // Reload the page to start fresh
    window.location.reload();
  };

  const saveProject = () => {
    toast({
      title: "Project saved",
      description: "Your resume project has been saved successfully.",
    });
  };

  if (isLoading || !resume) {
    return (
      <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
        <CardContent className="p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-32 bg-slate-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const analysisResults = resume.analysisResults as AnalysisResult | null;
  const finalScore = analysisResults?.score || 0;
  const totalSuggestions = analysisResults?.suggestions?.length || 0;

  return (
    <div className="space-y-6">
      {/* Download Options Tabs */}
      <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
        <CardContent className="p-6">
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "simple" | "advanced")}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="simple" className="flex items-center space-x-2">
                <Download className="w-4 h-4" />
                <span>Quick Download</span>
              </TabsTrigger>
              <TabsTrigger value="advanced" className="flex items-center space-x-2">
                <Settings className="w-4 h-4" />
                <span>Advanced Export</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="simple" className="mt-6">
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-slate-800 mb-6">Quick Download Options</h3>

                {downloadFormats.map((format) => {
                  const Icon = format.icon;
                  const isDownloading = downloadingFormat === format.id;
                  const isPrimary = format.id === "pdf";

                  return (
                    <Button
                      key={format.id}
                      onClick={() => handleDownload(format)}
                      disabled={isDownloading}
                      className={`w-full flex items-center justify-between p-4 h-auto ${isPrimary
                        ? "border-2 border-primary bg-primary/5 hover:bg-primary/10"
                        : "border-2 border-slate-200 bg-white hover:border-slate-300"
                        }`}
                      variant="outline"
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`w-12 h-12 ${format.color} rounded-lg flex items-center justify-center`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="text-left">
                          <h4 className="font-semibold text-slate-800">{format.name}</h4>
                          <p className="text-sm text-slate-600">{format.description}</p>
                        </div>
                      </div>
                      {isDownloading ? (
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
                      ) : (
                        <Download className={isPrimary ? "text-primary" : "text-slate-400"} />
                      )}
                    </Button>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="advanced" className="mt-6">
              <AdvancedExportInterface
                resumeId={resumeId}
                onBack={() => setActiveTab("simple")}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Final Summary */}
      <Card className="bg-gradient-to-r from-primary to-secondary rounded-xl text-white">
        <CardContent className="p-6">
          <h3 className="text-xl font-bold mb-4">Analysis Complete!</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{finalScore}</div>
              <div className="text-sm opacity-90">Final Score</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{totalSuggestions}</div>
              <div className="text-sm opacity-90">
                {totalSuggestions === 1 ? "Improvement" : "Improvements"}
              </div>
            </div>
          </div>
          <p className="text-sm opacity-90">
            Your resume has been optimized with AI-powered suggestions and is now ready for applications!
          </p>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex space-x-4">
        <Button
          variant="outline"
          className="flex-1"
          onClick={startNewAnalysis}
        >
          Start New Analysis
        </Button>
        <Button
          className="flex-1 bg-primary text-white hover:bg-blue-600"
          onClick={saveProject}
        >
          Save Project
        </Button>
      </div>

      {/* Back Button */}
      <div className="flex justify-start">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Templates
        </Button>
      </div>
    </div>
  );
}
