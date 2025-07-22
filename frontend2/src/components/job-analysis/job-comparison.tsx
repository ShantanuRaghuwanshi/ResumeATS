import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    GitCompare,
    TrendingUp,
    Target,
    Star,
    CheckCircle,
    AlertCircle,
    BarChart3,
    Filter,
    ArrowUpDown
} from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";

interface JobComparison {
    jobs: JobComparisonItem[];
    overallBestMatch: string;
    comparisonMatrix: ComparisonMatrix;
    recommendations: ComparisonRecommendation[];
}

interface JobComparisonItem {
    id: string;
    title: string;
    company: string;
    matchScore: number;
    skillsMatch: number;
    experienceMatch: number;
    salaryRange?: {
        min: number;
        max: number;
        currency: string;
    };
    location?: string;
    workType?: string;
    pros: string[];
    cons: string[];
    missingSkills: string[];
    matchingSkills: string[];
    priority: "high" | "medium" | "low";
}

interface ComparisonMatrix {
    categories: string[];
    jobs: {
        [jobId: string]: {
            [category: string]: number;
        };
    };
}

interface ComparisonRecommendation {
    type: "best_overall" | "skill_development" | "career_growth" | "compensation";
    title: string;
    description: string;
    jobIds: string[];
}

interface JobComparisonProps {
    resumeId: string;
    jobIds: string[];
    onJobSelect?: (jobId: string) => void;
}

export default function JobComparison({ resumeId, jobIds, onJobSelect }: JobComparisonProps) {
    const [selectedJobs, setSelectedJobs] = useState<string[]>(jobIds);
    const [sortBy, setSortBy] = useState<"match" | "skills" | "experience" | "salary">("match");
    const [filterPriority, setFilterPriority] = useState<string | null>(null);

    // Fetch job comparison data
    const { data: comparison, isLoading } = useQuery({
        queryKey: ["job-comparison", resumeId, selectedJobs],
        queryFn: async (): Promise<JobComparison> => {
            const response = await apiRequest("POST", `/resume/${resumeId}/job-comparison`, {
                jobIds: selectedJobs,
            });
            return response.json();
        },
        enabled: selectedJobs.length >= 2,
    });

    const handleJobSelection = (jobId: string, checked: boolean) => {
        if (checked) {
            setSelectedJobs(prev => [...prev, jobId]);
        } else {
            setSelectedJobs(prev => prev.filter(id => id !== jobId));
        }
    };

    const getSortedJobs = () => {
        if (!comparison) return [];

        let jobs = [...comparison.jobs];

        // Apply priority filter
        if (filterPriority) {
            jobs = jobs.filter(job => job.priority === filterPriority);
        }

        // Apply sorting
        jobs.sort((a, b) => {
            switch (sortBy) {
                case "match":
                    return b.matchScore - a.matchScore;
                case "skills":
                    return b.skillsMatch - a.skillsMatch;
                case "experience":
                    return b.experienceMatch - a.experienceMatch;
                case "salary":
                    const aSalary = a.salaryRange ? (a.salaryRange.min + a.salaryRange.max) / 2 : 0;
                    const bSalary = b.salaryRange ? (b.salaryRange.min + b.salaryRange.max) / 2 : 0;
                    return bSalary - aSalary;
                default:
                    return 0;
            }
        });

        return jobs;
    };

    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-green-600";
        if (score >= 60) return "text-yellow-600";
        return "text-red-600";
    };

    const getScoreBgColor = (score: number) => {
        if (score >= 80) return "bg-green-100";
        if (score >= 60) return "bg-yellow-100";
        return "bg-red-100";
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case "high": return "bg-red-100 text-red-800 border-red-200";
            case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
            case "low": return "bg-blue-100 text-blue-800 border-blue-200";
            default: return "bg-gray-100 text-gray-800 border-gray-200";
        }
    };

    if (selectedJobs.length < 2) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <GitCompare className="w-5 h-5 text-primary" />
                        Job Comparison
                    </CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                    <div className="space-y-4">
                        <GitCompare className="w-12 h-12 mx-auto text-muted-foreground" />
                        <div>
                            <h3 className="text-lg font-medium text-slate-800 mb-2">
                                Select Jobs to Compare
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                Choose at least 2 job descriptions to see a detailed comparison and ranking.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <BarChart3 className="w-8 h-8 mx-auto mb-2 text-muted-foreground animate-pulse" />
                        <p className="text-sm text-muted-foreground">Comparing job opportunities...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!comparison) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">Failed to load comparison data</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const sortedJobs = getSortedJobs();

    return (
        <div className="space-y-6">
            {/* Comparison Overview */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <GitCompare className="w-5 h-5 text-primary" />
                            Job Comparison Overview
                        </CardTitle>
                        <Badge variant="secondary">
                            {selectedJobs.length} jobs compared
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {comparison.jobs.find(j => j.id === comparison.overallBestMatch)?.title || "N/A"}
                            </div>
                            <div className="text-sm text-muted-foreground">Best Overall Match</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {Math.round(Math.max(...comparison.jobs.map(j => j.matchScore)))}%
                            </div>
                            <div className="text-sm text-muted-foreground">Highest Match Score</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-slate-800 mb-1">
                                {comparison.jobs.filter(j => j.matchScore >= 70).length}
                            </div>
                            <div className="text-sm text-muted-foreground">Strong Matches</div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Filters and Sorting */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="flex items-center gap-2">
                            <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Sort by:</span>
                            <div className="flex gap-1">
                                {[
                                    { key: "match", label: "Match Score" },
                                    { key: "skills", label: "Skills" },
                                    { key: "experience", label: "Experience" },
                                    { key: "salary", label: "Salary" },
                                ].map((option) => (
                                    <Button
                                        key={option.key}
                                        variant={sortBy === option.key ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setSortBy(option.key as any)}
                                        className="text-xs"
                                    >
                                        {option.label}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <Separator orientation="vertical" className="h-6" />

                        <div className="flex items-center gap-2">
                            <Filter className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Priority:</span>
                            <div className="flex gap-1">
                                <Button
                                    variant={filterPriority === null ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => setFilterPriority(null)}
                                    className="text-xs"
                                >
                                    All
                                </Button>
                                {["high", "medium", "low"].map((priority) => (
                                    <Button
                                        key={priority}
                                        variant={filterPriority === priority ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setFilterPriority(priority)}
                                        className="text-xs capitalize"
                                    >
                                        {priority}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Job Comparison Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {sortedJobs.map((job, index) => (
                    <JobComparisonCard
                        key={job.id}
                        job={job}
                        rank={index + 1}
                        isBestMatch={job.id === comparison.overallBestMatch}
                        onSelect={() => onJobSelect?.(job.id)}
                    />
                ))}
            </div>

            {/* Comparison Matrix */}
            <Card>
                <CardHeader>
                    <CardTitle>Detailed Comparison Matrix</CardTitle>
                </CardHeader>
                <CardContent>
                    <ComparisonMatrix
                        matrix={comparison.comparisonMatrix}
                        jobs={comparison.jobs}
                    />
                </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
                <CardHeader>
                    <CardTitle>Comparison Insights</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {comparison.recommendations.map((rec, index) => (
                            <ComparisonRecommendationCard key={index} recommendation={rec} jobs={comparison.jobs} />
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

interface JobComparisonCardProps {
    job: JobComparisonItem;
    rank: number;
    isBestMatch: boolean;
    onSelect: () => void;
}

function JobComparisonCard({ job, rank, isBestMatch, onSelect }: JobComparisonCardProps) {
    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-green-600";
        if (score >= 60) return "text-yellow-600";
        return "text-red-600";
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case "high": return "bg-red-100 text-red-800 border-red-200";
            case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
            case "low": return "bg-blue-100 text-blue-800 border-blue-200";
            default: return "bg-gray-100 text-gray-800 border-gray-200";
        }
    };

    return (
        <Card className={cn("cursor-pointer transition-all hover:shadow-md", isBestMatch && "ring-2 ring-primary")}>
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                            #{rank}
                        </Badge>
                        {isBestMatch && (
                            <Badge variant="default" className="bg-primary text-xs">
                                <Star className="w-3 h-3 mr-1" />
                                Best Match
                            </Badge>
                        )}
                        <Badge variant="outline" className={cn("text-xs", getPriorityColor(job.priority))}>
                            {job.priority} priority
                        </Badge>
                    </div>
                    <div className="text-right">
                        <div className={cn("text-2xl font-bold", getScoreColor(job.matchScore))}>
                            {Math.round(job.matchScore)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Match Score</div>
                    </div>
                </div>

                <div>
                    <h3 className="font-semibold text-lg">{job.title}</h3>
                    <p className="text-muted-foreground">{job.company}</p>
                </div>
            </CardHeader>

            <CardContent className="space-y-4">
                {/* Score Breakdown */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                        <span>Skills Match</span>
                        <span className={getScoreColor(job.skillsMatch)}>{Math.round(job.skillsMatch)}%</span>
                    </div>
                    <Progress value={job.skillsMatch} className="h-2" />

                    <div className="flex justify-between items-center text-sm">
                        <span>Experience Match</span>
                        <span className={getScoreColor(job.experienceMatch)}>{Math.round(job.experienceMatch)}%</span>
                    </div>
                    <Progress value={job.experienceMatch} className="h-2" />
                </div>

                {/* Job Details */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                    {job.location && (
                        <div>
                            <span className="text-muted-foreground">Location:</span>
                            <p className="font-medium">{job.location}</p>
                        </div>
                    )}
                    {job.workType && (
                        <div>
                            <span className="text-muted-foreground">Work Type:</span>
                            <p className="font-medium">{job.workType}</p>
                        </div>
                    )}
                    {job.salaryRange && (
                        <div className="col-span-2">
                            <span className="text-muted-foreground">Salary Range:</span>
                            <p className="font-medium">
                                {job.salaryRange.currency} {job.salaryRange.min.toLocaleString()} - {job.salaryRange.max.toLocaleString()}
                            </p>
                        </div>
                    )}
                </div>

                {/* Skills Summary */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-green-600">Matching Skills</span>
                        <Badge variant="outline" className="text-xs bg-green-50 text-green-800">
                            {job.matchingSkills.length}
                        </Badge>
                    </div>
                    <div className="flex flex-wrap gap-1">
                        {job.matchingSkills.slice(0, 4).map((skill, index) => (
                            <Badge key={index} variant="secondary" className="text-xs bg-green-100 text-green-800">
                                {skill}
                            </Badge>
                        ))}
                        {job.matchingSkills.length > 4 && (
                            <Badge variant="outline" className="text-xs">
                                +{job.matchingSkills.length - 4} more
                            </Badge>
                        )}
                    </div>
                </div>

                {job.missingSkills.length > 0 && (
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-red-600">Missing Skills</span>
                            <Badge variant="outline" className="text-xs bg-red-50 text-red-800">
                                {job.missingSkills.length}
                            </Badge>
                        </div>
                        <div className="flex flex-wrap gap-1">
                            {job.missingSkills.slice(0, 3).map((skill, index) => (
                                <Badge key={index} variant="destructive" className="text-xs">
                                    {skill}
                                </Badge>
                            ))}
                            {job.missingSkills.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                    +{job.missingSkills.length - 3} more
                                </Badge>
                            )}
                        </div>
                    </div>
                )}

                {/* Pros and Cons */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {job.pros.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium text-green-600 mb-2">Pros</h4>
                            <ul className="space-y-1">
                                {job.pros.slice(0, 3).map((pro, index) => (
                                    <li key={index} className="flex items-start gap-1 text-xs">
                                        <CheckCircle className="w-3 h-3 text-green-600 mt-0.5 flex-shrink-0" />
                                        {pro}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {job.cons.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium text-red-600 mb-2">Cons</h4>
                            <ul className="space-y-1">
                                {job.cons.slice(0, 3).map((con, index) => (
                                    <li key={index} className="flex items-start gap-1 text-xs">
                                        <AlertCircle className="w-3 h-3 text-red-600 mt-0.5 flex-shrink-0" />
                                        {con}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                <Button onClick={onSelect} className="w-full" size="sm">
                    View Detailed Analysis
                </Button>
            </CardContent>
        </Card>
    );
}

interface ComparisonMatrixProps {
    matrix: ComparisonMatrix;
    jobs: JobComparisonItem[];
}

function ComparisonMatrix({ matrix, jobs }: ComparisonMatrixProps) {
    const getScoreColor = (score: number) => {
        if (score >= 80) return "bg-green-100 text-green-800";
        if (score >= 60) return "bg-yellow-100 text-yellow-800";
        return "bg-red-100 text-red-800";
    };

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b">
                        <th className="text-left p-2 font-medium">Category</th>
                        {jobs.map((job) => (
                            <th key={job.id} className="text-center p-2 font-medium min-w-32">
                                <div className="truncate">{job.title}</div>
                                <div className="text-xs text-muted-foreground truncate">{job.company}</div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {matrix.categories.map((category) => (
                        <tr key={category} className="border-b">
                            <td className="p-2 font-medium capitalize">{category}</td>
                            {jobs.map((job) => {
                                const score = matrix.jobs[job.id]?.[category] || 0;
                                return (
                                    <td key={job.id} className="text-center p-2">
                                        <Badge variant="outline" className={cn("text-xs", getScoreColor(score))}>
                                            {Math.round(score)}%
                                        </Badge>
                                    </td>
                                );
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

interface ComparisonRecommendationCardProps {
    recommendation: ComparisonRecommendation;
    jobs: JobComparisonItem[];
}

function ComparisonRecommendationCard({ recommendation, jobs }: ComparisonRecommendationCardProps) {
    const getTypeIcon = (type: string) => {
        switch (type) {
            case "best_overall": return Star;
            case "skill_development": return Target;
            case "career_growth": return TrendingUp;
            case "compensation": return BarChart3;
            default: return CheckCircle;
        }
    };

    const Icon = getTypeIcon(recommendation.type);
    const relevantJobs = jobs.filter(job => recommendation.jobIds.includes(job.id));

    return (
        <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-primary/10 rounded-full">
                <Icon className="w-5 h-5 text-primary" />
            </div>

            <div className="flex-1">
                <h4 className="font-medium text-sm mb-1">{recommendation.title}</h4>
                <p className="text-sm text-muted-foreground mb-2">{recommendation.description}</p>

                {relevantJobs.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {relevantJobs.map((job) => (
                            <Badge key={job.id} variant="outline" className="text-xs">
                                {job.title} - {job.company}
                            </Badge>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}