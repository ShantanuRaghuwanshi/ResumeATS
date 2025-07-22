import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    BarChart3,
    Target,
    TrendingUp,
    AlertCircle,
    CheckCircle,
    Brain,
    Zap,
    Users,
    Building,
    Clock,
    Star
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";

interface JobAnalysis {
    id: string;
    jobTitle: string;
    company: string;
    requiredSkills: string[];
    preferredSkills: string[];
    experienceLevel: string;
    keyResponsibilities: string[];
    industryKeywords: string[];
    companyValues: string[];
    salaryRange?: {
        min: number;
        max: number;
        currency: string;
    };
    location?: string;
    workType?: string;
    analysisScore: number;
    createdAt: Date;
}

interface MatchResult {
    overallScore: number;
    sectionScores: {
        skills: number;
        experience: number;
        education: number;
        keywords: number;
    };
    missingSkills: string[];
    matchingSkills: string[];
    recommendations: Recommendation[];
    strengthAreas: string[];
    improvementAreas: string[];
}

interface Recommendation {
    id: string;
    section: string;
    type: "add" | "modify" | "remove" | "emphasize";
    title: string;
    description: string;
    priority: "high" | "medium" | "low";
    impactScore: number;
    specificSuggestion?: string;
}

interface JobAnalyzerProps {
    resumeId: string;
    jobDescriptionId: string;
    onAnalysisComplete?: (analysis: JobAnalysis, match: MatchResult) => void;
}

export default function JobAnalyzer({ resumeId, jobDescriptionId, onAnalysisComplete }: JobAnalyzerProps) {
    const [activeTab, setActiveTab] = useState("analysis");
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Fetch job analysis
    const { data: analysis, isLoading: analysisLoading } = useQuery({
        queryKey: ["job-analysis", jobDescriptionId],
        queryFn: async (): Promise<JobAnalysis> => {
            const response = await apiRequest("GET", `/job-descriptions/${jobDescriptionId}/analysis`);
            return response.json();
        },
    });

    // Fetch match result
    const { data: matchResult, isLoading: matchLoading } = useQuery({
        queryKey: ["job-match", resumeId, jobDescriptionId],
        queryFn: async (): Promise<MatchResult> => {
            const response = await apiRequest("GET", `/resume/${resumeId}/job-match/${jobDescriptionId}`);
            return response.json();
        },
        enabled: !!analysis,
    });

    // Analyze job description mutation
    const analyzeJobMutation = useMutation({
        mutationFn: async () => {
            const response = await apiRequest("POST", `/job-descriptions/${jobDescriptionId}/analyze`);
            return response.json();
        },
        onSuccess: (result) => {
            queryClient.invalidateQueries({ queryKey: ["job-analysis", jobDescriptionId] });
            toast({
                title: "Analysis complete",
                description: "Job description has been analyzed successfully.",
            });
        },
        onError: (error) => {
            toast({
                title: "Analysis failed",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Generate match report mutation
    const generateMatchMutation = useMutation({
        mutationFn: async () => {
            const response = await apiRequest("POST", `/resume/${resumeId}/job-match/${jobDescriptionId}`);
            return response.json();
        },
        onSuccess: (result) => {
            queryClient.invalidateQueries({ queryKey: ["job-match", resumeId, jobDescriptionId] });

            if (onAnalysisComplete && analysis) {
                onAnalysisComplete(analysis, result);
            }

            toast({
                title: "Match analysis complete",
                description: "Resume matching report has been generated.",
            });
        },
        onError: (error) => {
            toast({
                title: "Match analysis failed",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    const handleAnalyzeJob = () => {
        analyzeJobMutation.mutate();
    };

    const handleGenerateMatch = () => {
        generateMatchMutation.mutate();
    };

    if (analysisLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <Brain className="w-8 h-8 mx-auto mb-2 text-muted-foreground animate-pulse" />
                        <p className="text-sm text-muted-foreground">Loading job analysis...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!analysis) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="w-5 h-5 text-primary" />
                        Job Analysis Required
                    </CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                    <div className="space-y-4">
                        <p className="text-muted-foreground">
                            This job description needs to be analyzed before we can generate matching recommendations.
                        </p>
                        <Button
                            onClick={handleAnalyzeJob}
                            disabled={analyzeJobMutation.isPending}
                            className="w-full"
                        >
                            <Brain className="w-4 h-4 mr-2" />
                            {analyzeJobMutation.isPending ? "Analyzing..." : "Analyze Job Description"}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Analysis Overview */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-primary" />
                            Job Analysis Overview
                        </CardTitle>
                        <Badge variant="default" className="bg-green-100 text-green-800">
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Analyzed
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {analysis.requiredSkills.length}
                            </div>
                            <div className="text-sm text-muted-foreground">Required Skills</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {analysis.keyResponsibilities.length}
                            </div>
                            <div className="text-sm text-muted-foreground">Key Responsibilities</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {Math.round(analysis.analysisScore)}%
                            </div>
                            <div className="text-sm text-muted-foreground">Analysis Quality</div>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                    <Building className="w-4 h-4" />
                                    Job Details
                                </h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Position:</span>
                                        <span className="font-medium">{analysis.jobTitle}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Company:</span>
                                        <span className="font-medium">{analysis.company}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Experience Level:</span>
                                        <Badge variant="outline" className="text-xs">
                                            {analysis.experienceLevel}
                                        </Badge>
                                    </div>
                                    {analysis.location && (
                                        <div className="flex justify-between">
                                            <span className="text-muted-foreground">Location:</span>
                                            <span className="font-medium">{analysis.location}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div>
                                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                    <Target className="w-4 h-4" />
                                    Key Requirements
                                </h4>
                                <div className="space-y-2">
                                    <div>
                                        <span className="text-xs text-muted-foreground">Top Skills:</span>
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {analysis.requiredSkills.slice(0, 6).map((skill, index) => (
                                                <Badge key={index} variant="secondary" className="text-xs">
                                                    {skill}
                                                </Badge>
                                            ))}
                                            {analysis.requiredSkills.length > 6 && (
                                                <Badge variant="outline" className="text-xs">
                                                    +{analysis.requiredSkills.length - 6} more
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Detailed Analysis Tabs */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Detailed Analysis</CardTitle>
                        {!matchResult && (
                            <Button
                                onClick={handleGenerateMatch}
                                disabled={generateMatchMutation.isPending}
                                size="sm"
                            >
                                <Zap className="w-4 h-4 mr-2" />
                                {generateMatchMutation.isPending ? "Generating..." : "Generate Match Report"}
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="grid w-full grid-cols-4">
                            <TabsTrigger value="analysis">Job Analysis</TabsTrigger>
                            <TabsTrigger value="skills">Skills</TabsTrigger>
                            <TabsTrigger value="match" disabled={!matchResult}>
                                Match Report
                            </TabsTrigger>
                            <TabsTrigger value="recommendations" disabled={!matchResult}>
                                Recommendations
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="analysis" className="mt-4">
                            <JobAnalysisTab analysis={analysis} />
                        </TabsContent>

                        <TabsContent value="skills" className="mt-4">
                            <SkillsAnalysisTab analysis={analysis} />
                        </TabsContent>

                        <TabsContent value="match" className="mt-4">
                            {matchResult ? (
                                <MatchReportTab matchResult={matchResult} />
                            ) : (
                                <div className="text-center py-8">
                                    <TrendingUp className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                                    <p className="text-sm text-muted-foreground">
                                        Generate a match report to see how your resume aligns with this job.
                                    </p>
                                </div>
                            )}
                        </TabsContent>

                        <TabsContent value="recommendations" className="mt-4">
                            {matchResult ? (
                                <RecommendationsTab recommendations={matchResult.recommendations} />
                            ) : (
                                <div className="text-center py-8">
                                    <Target className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                                    <p className="text-sm text-muted-foreground">
                                        Generate a match report to see personalized recommendations.
                                    </p>
                                </div>
                            )}
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    );
}

// Tab Components
function JobAnalysisTab({ analysis }: { analysis: JobAnalysis }) {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg">Key Responsibilities</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ScrollArea className="h-48">
                            <ul className="space-y-2">
                                {analysis.keyResponsibilities.map((responsibility, index) => (
                                    <li key={index} className="flex items-start gap-2 text-sm">
                                        <div className="w-1.5 h-1.5 bg-primary rounded-full mt-2 flex-shrink-0" />
                                        {responsibility}
                                    </li>
                                ))}
                            </ul>
                        </ScrollArea>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg">Industry Keywords</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {analysis.industryKeywords.map((keyword, index) => (
                                <Badge key={index} variant="outline" className="text-xs">
                                    {keyword}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {analysis.companyValues.length > 0 && (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Users className="w-5 h-5" />
                            Company Values & Culture
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {analysis.companyValues.map((value, index) => (
                                <Badge key={index} variant="secondary" className="text-xs">
                                    {value}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

function SkillsAnalysisTab({ analysis }: { analysis: JobAnalysis }) {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg text-red-600">Required Skills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {analysis.requiredSkills.map((skill, index) => (
                                <div key={index} className="flex items-center justify-between p-2 bg-red-50 rounded">
                                    <span className="text-sm font-medium">{skill}</span>
                                    <Badge variant="destructive" className="text-xs">
                                        Required
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg text-blue-600">Preferred Skills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {analysis.preferredSkills.map((skill, index) => (
                                <div key={index} className="flex items-center justify-between p-2 bg-blue-50 rounded">
                                    <span className="text-sm font-medium">{skill}</span>
                                    <Badge variant="outline" className="text-xs border-blue-200 text-blue-800">
                                        Preferred
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function MatchReportTab({ matchResult }: { matchResult: MatchResult }) {
    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-green-600";
        if (score >= 60) return "text-yellow-600";
        return "text-red-600";
    };

    return (
        <div className="space-y-6">
            {/* Overall Score */}
            <Card>
                <CardContent className="pt-6">
                    <div className="text-center">
                        <div className="text-4xl font-bold mb-2">
                            <span className={getScoreColor(matchResult.overallScore)}>
                                {Math.round(matchResult.overallScore)}%
                            </span>
                        </div>
                        <p className="text-muted-foreground mb-4">Overall Match Score</p>
                        <Progress value={matchResult.overallScore} className="h-3" />
                    </div>
                </CardContent>
            </Card>

            {/* Section Scores */}
            <Card>
                <CardHeader>
                    <CardTitle>Section Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {Object.entries(matchResult.sectionScores).map(([section, score]) => (
                            <div key={section} className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm font-medium capitalize">{section}</span>
                                    <span className={cn("text-sm font-bold", getScoreColor(score))}>
                                        {Math.round(score)}%
                                    </span>
                                </div>
                                <Progress value={score} className="h-2" />
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Skills Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg text-green-600">Matching Skills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {matchResult.matchingSkills.map((skill, index) => (
                                <Badge key={index} variant="default" className="bg-green-100 text-green-800 text-xs">
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    {skill}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg text-red-600">Missing Skills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {matchResult.missingSkills.map((skill, index) => (
                                <Badge key={index} variant="destructive" className="text-xs">
                                    <AlertCircle className="w-3 h-3 mr-1" />
                                    {skill}
                                </Badge>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function RecommendationsTab({ recommendations }: { recommendations: Recommendation[] }) {
    const groupedRecommendations = recommendations.reduce((acc, rec) => {
        if (!acc[rec.section]) {
            acc[rec.section] = [];
        }
        acc[rec.section].push(rec);
        return acc;
    }, {} as Record<string, Recommendation[]>);

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case "high": return "border-red-200 bg-red-50";
            case "medium": return "border-yellow-200 bg-yellow-50";
            case "low": return "border-blue-200 bg-blue-50";
            default: return "border-gray-200 bg-gray-50";
        }
    };

    const getPriorityBadge = (priority: string) => {
        switch (priority) {
            case "high": return "destructive";
            case "medium": return "secondary";
            case "low": return "outline";
            default: return "outline";
        }
    };

    return (
        <div className="space-y-6">
            {Object.entries(groupedRecommendations).map(([section, sectionRecs]) => (
                <Card key={section}>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-lg capitalize">{section} Recommendations</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {sectionRecs.map((rec) => (
                                <div
                                    key={rec.id}
                                    className={cn("p-4 rounded-lg border-l-4", getPriorityColor(rec.priority))}
                                >
                                    <div className="flex items-start justify-between gap-3 mb-2">
                                        <h4 className="font-medium text-sm">{rec.title}</h4>
                                        <div className="flex items-center gap-2">
                                            <Badge variant={getPriorityBadge(rec.priority) as any} className="text-xs">
                                                {rec.priority} priority
                                            </Badge>
                                            <Badge variant="outline" className="text-xs">
                                                {Math.round(rec.impactScore * 100)}% impact
                                            </Badge>
                                        </div>
                                    </div>
                                    <p className="text-sm text-muted-foreground mb-2">{rec.description}</p>
                                    {rec.specificSuggestion && (
                                        <div className="bg-background p-2 rounded text-xs">
                                            <strong>Suggestion:</strong> {rec.specificSuggestion}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}