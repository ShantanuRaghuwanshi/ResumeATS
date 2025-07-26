import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Briefcase,
    Upload,
    BarChart3,
    GitCompare,
    Plus,
    FileText,
    Target,
    CheckCircle,
    AlertCircle,
    Info,
    TrendingUp,
    Users,
    Clock,
    Star,
    ArrowRight
} from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import JobUpload from "./job-upload";
import JobAnalyzer from "./job-analyzer";
import JobComparison from "./job-comparison";

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

interface MatchingSummary {
    averageScore: number;
    topMatches: number;
    totalJobs: number;
    missingSkills: string[];
    recommendations: string[];
}

interface EnhancedJobAnalysisInterfaceProps {
    resumeId: string;
    onNext?: () => void;
    onBack?: () => void;
}

export default function EnhancedJobAnalysisInterface({
    resumeId,
    onNext,
    onBack
}: EnhancedJobAnalysisInterfaceProps) {
    const [activeTab, setActiveTab] = useState("overview");
    const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
    const [comparisonJobIds, setComparisonJobIds] = useState<string[]>([]);
    const [analysisProgress, setAnalysisProgress] = useState(0);

    // Fetch uploaded job descriptions
    const { data: jobDescriptions, isLoading, refetch } = useQuery({
        queryKey: ["job-descriptions", resumeId],
        queryFn: async (): Promise<JobDescription[]> => {
            const response = await apiRequest("GET", `/resume/${resumeId}/job-descriptions`);
            return response.json();
        },
    });

    // Fetch matching summary
    const { data: matchingSummary } = useQuery({
        queryKey: ["matching-summary", resumeId],
        queryFn: async (): Promise<MatchingSummary> => {
            const response = await apiRequest("GET", `/resume/${resumeId}/matching-summary`);
            return response.json();
        },
        enabled: jobDescriptions && jobDescriptions.some(j => j.isAnalyzed),
    });

    // Calculate analysis progress
    useEffect(() => {
        if (jobDescriptions) {
            const analyzedCount = jobDescriptions.filter(j => j.isAnalyzed).length;
            const progress = jobDescriptions.length > 0 ? (analyzedCount / jobDescriptions.length) * 100 : 0;
            setAnalysisProgress(progress);
        }
    }, [jobDescriptions]);

    const handleJobUploaded = (job: JobDescription) => {
        setSelectedJobId(job.id);
        setActiveTab("analysis");
        refetch(); // Refresh the job list
    };

    const handleJobSelect = (jobId: string) => {
        setSelectedJobId(jobId);
        setActiveTab("analysis");
    };

    const handleComparisonToggle = (jobId: string, selected: boolean) => {
        if (selected) {
            setComparisonJobIds(prev => [...prev, jobId]);
        } else {
            setComparisonJobIds(prev => prev.filter(id => id !== jobId));
        }
    };

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="text-center py-12">
                    <Briefcase className="w-12 h-12 mx-auto mb-4 text-muted-foreground animate-pulse" />
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">Loading Job Analysis</h2>
                    <p className="text-muted-foreground">Setting up your job analysis workspace...</p>
                </div>
            </div>
        );
    }

    const analyzedJobs = jobDescriptions?.filter(j => j.isAnalyzed) || [];
    const hasJobs = jobDescriptions && jobDescriptions.length > 0;
    const hasAnalyzedJobs = analyzedJobs.length > 0;

    return (
        <div className="space-y-6">
            {/* Enhanced Header with Progress */}
            <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-slate-800 mb-2">Job Analysis & Matching</h2>
                <p className="text-lg text-muted-foreground">
                    Upload job descriptions and get AI-powered matching recommendations
                </p>

                {hasJobs && (
                    <div className="mt-6 bg-white p-6 rounded-lg border border-slate-200">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm font-medium text-slate-700">Analysis Progress</span>
                            <span className="text-sm text-slate-600">{analyzedJobs.length} of {jobDescriptions.length} jobs analyzed</span>
                        </div>
                        <Progress value={analysisProgress} className="w-full mb-4" />

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                            <div className="flex flex-col items-center">
                                <FileText className="w-5 h-5 text-blue-600 mb-1" />
                                <span className="text-lg font-bold text-slate-800">{jobDescriptions.length}</span>
                                <span className="text-xs text-slate-600">Jobs Uploaded</span>
                            </div>
                            <div className="flex flex-col items-center">
                                <Target className="w-5 h-5 text-green-600 mb-1" />
                                <span className="text-lg font-bold text-slate-800">{analyzedJobs.length}</span>
                                <span className="text-xs text-slate-600">Analyzed</span>
                            </div>
                            {matchingSummary && (
                                <>
                                    <div className="flex flex-col items-center">
                                        <TrendingUp className="w-5 h-5 text-purple-600 mb-1" />
                                        <span className="text-lg font-bold text-slate-800">{matchingSummary.averageScore}%</span>
                                        <span className="text-xs text-slate-600">Avg. Match</span>
                                    </div>
                                    <div className="flex flex-col items-center">
                                        <Star className="w-5 h-5 text-yellow-600 mb-1" />
                                        <span className="text-lg font-bold text-slate-800">{matchingSummary.topMatches}</span>
                                        <span className="text-xs text-slate-600">Top Matches</span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Enhanced Tabs Interface */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <div className="flex items-center justify-between mb-6">
                    <TabsList className="grid w-full max-w-lg grid-cols-4">
                        <TabsTrigger value="overview" className="flex items-center gap-2 text-xs">
                            <BarChart3 className="w-3 h-3" />
                            Overview
                        </TabsTrigger>
                        <TabsTrigger value="upload" className="flex items-center gap-2 text-xs">
                            <Upload className="w-3 h-3" />
                            Upload
                        </TabsTrigger>
                        <TabsTrigger value="analysis" className="flex items-center gap-2 text-xs">
                            <Target className="w-3 h-3" />
                            Analysis
                        </TabsTrigger>
                        <TabsTrigger value="comparison" className="flex items-center gap-2 text-xs">
                            <GitCompare className="w-3 h-3" />
                            Compare
                        </TabsTrigger>
                    </TabsList>

                    {hasAnalyzedJobs && onNext && (
                        <Button onClick={onNext} className="ml-4">
                            Continue to AI Suggestions
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                    )}
                </div>

                {/* Overview Tab */}
                <TabsContent value="overview" className="mt-6">
                    {hasJobs ? (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Jobs Overview */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Briefcase className="w-5 h-5 text-blue-600" />
                                        Your Job Portfolio
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-64">
                                        <div className="space-y-3">
                                            {jobDescriptions.map((job) => (
                                                <div
                                                    key={job.id}
                                                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors"
                                                    onClick={() => handleJobSelect(job.id)}
                                                >
                                                    <div className="flex-1">
                                                        <h4 className="font-medium text-slate-800">{job.title}</h4>
                                                        <p className="text-sm text-slate-600">{job.company}</p>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <Badge variant="outline" className="text-xs">
                                                                {job.source}
                                                            </Badge>
                                                            <span className="text-xs text-slate-500">{job.wordCount} words</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        {job.isAnalyzed ? (
                                                            <CheckCircle className="w-5 h-5 text-green-600" />
                                                        ) : (
                                                            <Clock className="w-5 h-5 text-yellow-600" />
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>

                            {/* Matching Insights */}
                            {matchingSummary && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <TrendingUp className="w-5 h-5 text-purple-600" />
                                            Matching Insights
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            <div className="text-center p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg">
                                                <div className="text-2xl font-bold text-purple-600 mb-1">
                                                    {matchingSummary.averageScore}%
                                                </div>
                                                <p className="text-sm text-slate-600">Average Match Score</p>
                                            </div>

                                            {matchingSummary.missingSkills.length > 0 && (
                                                <div>
                                                    <h5 className="font-medium text-slate-800 mb-2">Skills to Develop:</h5>
                                                    <div className="flex flex-wrap gap-1">
                                                        {matchingSummary.missingSkills.slice(0, 6).map((skill, index) => (
                                                            <Badge key={index} variant="outline" className="text-xs bg-red-50 text-red-700">
                                                                {skill}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {matchingSummary.recommendations.length > 0 && (
                                                <div>
                                                    <h5 className="font-medium text-slate-800 mb-2">Quick Wins:</h5>
                                                    <ul className="text-sm text-slate-600 space-y-1">
                                                        {matchingSummary.recommendations.slice(0, 3).map((rec, index) => (
                                                            <li key={index} className="flex items-start gap-2">
                                                                <span className="text-blue-500 mt-1">•</span>
                                                                {rec}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    ) : (
                        <Card>
                            <CardContent className="text-center py-12">
                                <Briefcase className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                                <h3 className="text-xl font-semibold text-slate-800 mb-2">
                                    Ready to Start Job Analysis?
                                </h3>
                                <p className="text-slate-600 mb-6">
                                    Upload job descriptions to get personalized matching insights and recommendations.
                                </p>
                                <Button onClick={() => setActiveTab("upload")}>
                                    <Plus className="w-4 h-4 mr-2" />
                                    Upload Your First Job
                                </Button>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                {/* Upload Tab */}
                <TabsContent value="upload" className="mt-6">
                    <JobUpload
                        resumeId={resumeId}
                        onJobUploaded={handleJobUploaded}
                        onJobsChanged={(jobs) => {
                            const validIds = jobs.map(j => j.id);
                            setComparisonJobIds(prev => prev.filter(id => validIds.includes(id)));
                        }}
                    />
                </TabsContent>

                {/* Analysis Tab */}
                <TabsContent value="analysis" className="mt-6">
                    {selectedJobId ? (
                        <JobAnalyzer
                            resumeId={resumeId}
                            jobDescriptionId={selectedJobId}
                            onAnalysisComplete={(analysis, match) => {
                                console.log('Analysis complete:', { analysis, match });
                                refetch(); // Refresh job data to update analysis status
                            }}
                        />
                    ) : (
                        <Card>
                            <CardContent className="text-center py-12">
                                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                                <h3 className="text-xl font-semibold text-slate-800 mb-2">
                                    Select a Job to Analyze
                                </h3>
                                <p className="text-slate-600 mb-6">
                                    Choose a job description to see detailed analysis and matching recommendations.
                                </p>
                                {hasJobs ? (
                                    <div className="space-y-3 max-w-md mx-auto">
                                        {jobDescriptions.map((job) => (
                                            <Button
                                                key={job.id}
                                                variant="outline"
                                                className="w-full justify-start"
                                                onClick={() => handleJobSelect(job.id)}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <Briefcase className="w-4 h-4" />
                                                    <div className="text-left">
                                                        <div className="font-medium">{job.title}</div>
                                                        <div className="text-sm text-slate-500">{job.company}</div>
                                                    </div>
                                                    {job.isAnalyzed && <CheckCircle className="w-4 h-4 text-green-600 ml-auto" />}
                                                </div>
                                            </Button>
                                        ))}
                                    </div>
                                ) : (
                                    <Button onClick={() => setActiveTab("upload")}>
                                        <Plus className="w-4 h-4 mr-2" />
                                        Upload Your First Job Description
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                {/* Comparison Tab */}
                <TabsContent value="comparison" className="mt-6">
                    {hasJobs && jobDescriptions.length >= 2 ? (
                        <div className="space-y-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <GitCompare className="w-5 h-5 text-primary" />
                                        Select Jobs to Compare
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {jobDescriptions.map((job) => (
                                            <div
                                                key={job.id}
                                                className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-slate-50"
                                            >
                                                <input
                                                    type="checkbox"
                                                    id={`job-${job.id}`}
                                                    checked={comparisonJobIds.includes(job.id)}
                                                    onChange={(e) => handleComparisonToggle(job.id, e.target.checked)}
                                                    className="rounded"
                                                />
                                                <label htmlFor={`job-${job.id}`} className="flex-1 cursor-pointer">
                                                    <div className="font-medium text-sm">{job.title}</div>
                                                    <div className="text-xs text-slate-500">{job.company}</div>
                                                </label>
                                                {job.isAnalyzed && (
                                                    <CheckCircle className="w-4 h-4 text-green-600" />
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                    {comparisonJobIds.length > 0 && (
                                        <Alert className="mt-4 bg-blue-50 border-blue-200">
                                            <Info className="h-4 w-4" />
                                            <AlertDescription>
                                                {comparisonJobIds.length} job{comparisonJobIds.length !== 1 ? 's' : ''} selected for comparison
                                            </AlertDescription>
                                        </Alert>
                                    )}
                                </CardContent>
                            </Card>

                            <JobComparison
                                resumeId={resumeId}
                                jobIds={comparisonJobIds}
                                onJobSelect={handleJobSelect}
                            />
                        </div>
                    ) : (
                        <Card>
                            <CardContent className="text-center py-12">
                                <GitCompare className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                                <h3 className="text-xl font-semibold text-slate-800 mb-2">
                                    Upload More Jobs to Compare
                                </h3>
                                <p className="text-slate-600 mb-6">
                                    You need at least 2 job descriptions to use the comparison feature.
                                </p>
                                <Button onClick={() => setActiveTab("upload")}>
                                    <Plus className="w-4 h-4 mr-2" />
                                    Upload More Job Descriptions
                                </Button>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>
            </Tabs>

            {/* Navigation Footer */}
            {(onNext || onBack) && (
                <div className="flex justify-between items-center mt-8 pt-6 border-t border-slate-200">
                    {onBack ? (
                        <Button variant="outline" onClick={onBack} className="flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                            Back to Resume Analysis
                        </Button>
                    ) : <div />}

                    {onNext && hasAnalyzedJobs && (
                        <div className="flex items-center gap-4">
                            <Alert className="bg-green-50 border-green-200 px-4 py-2">
                                <CheckCircle className="h-4 w-4" />
                                <AlertDescription className="text-sm">
                                    Ready for AI suggestions! {analyzedJobs.length} job{analyzedJobs.length !== 1 ? 's' : ''} analyzed.
                                </AlertDescription>
                            </Alert>
                            <Button onClick={onNext} className="flex items-center gap-2">
                                Continue to AI Suggestions
                                <ArrowRight className="w-4 h-4" />
                            </Button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
