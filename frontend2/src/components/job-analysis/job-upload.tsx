import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
    Upload,
    FileText,
    Link,
    Trash2,
    Plus,
    CheckCircle,
    AlertCircle,
    Briefcase
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";

interface JobDescription {
    id: string;
    title: string;
    company: string;
    content: string;
    source: "manual" | "file" | "url";
    createdAt: Date;
    wordCount: number;
    isAnalyzed: boolean;
}

interface JobUploadProps {
    resumeId: string;
    onJobUploaded?: (job: JobDescription) => void;
    onJobsChanged?: (jobs: JobDescription[]) => void;
}

export default function JobUpload({ resumeId, onJobUploaded, onJobsChanged }: JobUploadProps) {
    const [activeTab, setActiveTab] = useState<"manual" | "file" | "url">("manual");
    const [manualInput, setManualInput] = useState("");
    const [jobTitle, setJobTitle] = useState("");
    const [company, setCompany] = useState("");
    const [urlInput, setUrlInput] = useState("");
    const [uploadedJobs, setUploadedJobs] = useState<JobDescription[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Upload job description mutation
    const uploadJobMutation = useMutation({
        mutationFn: async (jobData: {
            title: string;
            company: string;
            content: string;
            source: "manual" | "file" | "url";
        }) => {
            const response = await apiRequest("POST", `/resume/${resumeId}/job-descriptions`, jobData);
            return response.json();
        },
        onSuccess: (newJob) => {
            const updatedJobs = [...uploadedJobs, newJob];
            setUploadedJobs(updatedJobs);

            // Clear form
            setManualInput("");
            setJobTitle("");
            setCompany("");
            setUrlInput("");

            toast({
                title: "Job description uploaded",
                description: "Ready for analysis and matching.",
            });

            if (onJobUploaded) {
                onJobUploaded(newJob);
            }

            if (onJobsChanged) {
                onJobsChanged(updatedJobs);
            }
        },
        onError: (error) => {
            toast({
                title: "Failed to upload job description",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Extract from URL mutation
    const extractFromUrlMutation = useMutation({
        mutationFn: async (url: string) => {
            const response = await apiRequest("POST", `/job-descriptions/extract-from-url`, { url });
            return response.json();
        },
        onSuccess: (extractedData) => {
            setJobTitle(extractedData.title || "");
            setCompany(extractedData.company || "");
            setManualInput(extractedData.content || "");

            toast({
                title: "Job description extracted",
                description: "Please review and submit the extracted content.",
            });
        },
        onError: (error) => {
            toast({
                title: "Failed to extract job description",
                description: error.message || "Please try manual input instead.",
                variant: "destructive",
            });
        },
    });

    // Delete job mutation
    const deleteJobMutation = useMutation({
        mutationFn: async (jobId: string) => {
            await apiRequest("DELETE", `/job-descriptions/${jobId}`);
        },
        onSuccess: (_, jobId) => {
            const updatedJobs = uploadedJobs.filter(job => job.id !== jobId);
            setUploadedJobs(updatedJobs);

            toast({
                title: "Job description deleted",
                description: "The job description has been removed.",
            });

            if (onJobsChanged) {
                onJobsChanged(updatedJobs);
            }
        },
    });

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target?.result as string;
            setManualInput(content);
            setJobTitle(file.name.replace(/\.[^/.]+$/, "")); // Remove file extension

            toast({
                title: "File loaded",
                description: "Please review the content and add job details.",
            });
        };

        reader.onerror = () => {
            toast({
                title: "Failed to read file",
                description: "Please try again or use manual input.",
                variant: "destructive",
            });
        };

        reader.readAsText(file);
    };

    const handleSubmit = () => {
        if (!manualInput.trim()) {
            toast({
                title: "Content required",
                description: "Please enter or upload job description content.",
                variant: "destructive",
            });
            return;
        }

        if (!jobTitle.trim()) {
            toast({
                title: "Job title required",
                description: "Please enter the job title.",
                variant: "destructive",
            });
            return;
        }

        uploadJobMutation.mutate({
            title: jobTitle.trim(),
            company: company.trim() || "Unknown Company",
            content: manualInput.trim(),
            source: activeTab,
        });
    };

    const handleExtractFromUrl = () => {
        if (!urlInput.trim()) {
            toast({
                title: "URL required",
                description: "Please enter a valid job posting URL.",
                variant: "destructive",
            });
            return;
        }

        extractFromUrlMutation.mutate(urlInput.trim());
    };

    const wordCount = manualInput.trim().split(/\s+/).filter(word => word.length > 0).length;

    return (
        <div className="space-y-6">
            {/* Upload Interface */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Briefcase className="w-5 h-5 text-primary" />
                        Upload Job Description
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Tab Selection */}
                    <div className="flex gap-2">
                        <Button
                            variant={activeTab === "manual" ? "default" : "outline"}
                            size="sm"
                            onClick={() => setActiveTab("manual")}
                        >
                            <FileText className="w-4 h-4 mr-1" />
                            Manual Input
                        </Button>
                        <Button
                            variant={activeTab === "file" ? "default" : "outline"}
                            size="sm"
                            onClick={() => setActiveTab("file")}
                        >
                            <Upload className="w-4 h-4 mr-1" />
                            Upload File
                        </Button>
                        <Button
                            variant={activeTab === "url" ? "default" : "outline"}
                            size="sm"
                            onClick={() => setActiveTab("url")}
                        >
                            <Link className="w-4 h-4 mr-1" />
                            From URL
                        </Button>
                    </div>

                    {/* URL Tab */}
                    {activeTab === "url" && (
                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="job-url">Job Posting URL</Label>
                                <div className="flex gap-2 mt-1">
                                    <Input
                                        id="job-url"
                                        value={urlInput}
                                        onChange={(e) => setUrlInput(e.target.value)}
                                        placeholder="https://company.com/careers/job-posting"
                                    />
                                    <Button
                                        onClick={handleExtractFromUrl}
                                        disabled={extractFromUrlMutation.isPending}
                                    >
                                        {extractFromUrlMutation.isPending ? "Extracting..." : "Extract"}
                                    </Button>
                                </div>
                                <p className="text-sm text-muted-foreground mt-1">
                                    We'll try to extract the job description from the URL
                                </p>
                            </div>
                        </div>
                    )}

                    {/* File Tab */}
                    {activeTab === "file" && (
                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="job-file">Upload File</Label>
                                <div className="mt-1">
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept=".txt,.doc,.docx,.pdf"
                                        onChange={handleFileUpload}
                                        className="hidden"
                                    />
                                    <Button
                                        variant="outline"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="w-full"
                                    >
                                        <Upload className="w-4 h-4 mr-2" />
                                        Choose File
                                    </Button>
                                </div>
                                <p className="text-sm text-muted-foreground mt-1">
                                    Supported formats: TXT, DOC, DOCX, PDF
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Job Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <Label htmlFor="job-title">Job Title *</Label>
                            <Input
                                id="job-title"
                                value={jobTitle}
                                onChange={(e) => setJobTitle(e.target.value)}
                                placeholder="Software Engineer"
                            />
                        </div>
                        <div>
                            <Label htmlFor="company">Company</Label>
                            <Input
                                id="company"
                                value={company}
                                onChange={(e) => setCompany(e.target.value)}
                                placeholder="Company Name"
                            />
                        </div>
                    </div>

                    {/* Content Input */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <Label htmlFor="job-content">Job Description Content *</Label>
                            <Badge variant="outline" className="text-xs">
                                {wordCount} words
                            </Badge>
                        </div>
                        <Textarea
                            id="job-content"
                            value={manualInput}
                            onChange={(e) => setManualInput(e.target.value)}
                            placeholder="Paste the complete job description here..."
                            rows={12}
                            className="resize-none"
                        />
                        <div className="flex items-center justify-between mt-2">
                            <p className="text-sm text-muted-foreground">
                                Include requirements, responsibilities, and qualifications
                            </p>
                            {wordCount > 0 && (
                                <div className="flex items-center gap-1 text-sm">
                                    {wordCount >= 100 ? (
                                        <CheckCircle className="w-4 h-4 text-green-600" />
                                    ) : (
                                        <AlertCircle className="w-4 h-4 text-yellow-600" />
                                    )}
                                    <span className={wordCount >= 100 ? "text-green-600" : "text-yellow-600"}>
                                        {wordCount >= 100 ? "Good length" : "Consider adding more detail"}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <Button
                        onClick={handleSubmit}
                        disabled={uploadJobMutation.isPending || !manualInput.trim() || !jobTitle.trim()}
                        className="w-full"
                    >
                        {uploadJobMutation.isPending ? "Uploading..." : "Upload Job Description"}
                    </Button>
                </CardContent>
            </Card>

            {/* Uploaded Jobs */}
            {uploadedJobs.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                            <span>Uploaded Job Descriptions</span>
                            <Badge variant="secondary">{uploadedJobs.length}</Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {uploadedJobs.map((job) => (
                                <JobDescriptionItem
                                    key={job.id}
                                    job={job}
                                    onDelete={() => deleteJobMutation.mutate(job.id)}
                                    isDeleting={deleteJobMutation.isPending}
                                />
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

interface JobDescriptionItemProps {
    job: JobDescription;
    onDelete: () => void;
    isDeleting: boolean;
}

function JobDescriptionItem({ job, onDelete, isDeleting }: JobDescriptionItemProps) {
    const getSourceIcon = (source: string) => {
        switch (source) {
            case "file": return Upload;
            case "url": return Link;
            default: return FileText;
        }
    };

    const SourceIcon = getSourceIcon(job.source);

    return (
        <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-background rounded-full">
                <SourceIcon className="w-4 h-4 text-primary" />
            </div>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-sm truncate">{job.title}</h4>
                    <Badge variant="outline" className="text-xs">
                        {job.company}
                    </Badge>
                    {job.isAnalyzed && (
                        <Badge variant="default" className="bg-green-100 text-green-800 text-xs">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Analyzed
                        </Badge>
                    )}
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{job.wordCount} words</span>
                    <span>Added {new Date(job.createdAt).toLocaleDateString()}</span>
                    <span className="capitalize">{job.source} input</span>
                </div>
            </div>

            <Button
                variant="ghost"
                size="sm"
                onClick={onDelete}
                disabled={isDeleting}
                className="text-destructive hover:text-destructive"
            >
                <Trash2 className="w-4 h-4" />
            </Button>
        </div>
    );
}