import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import {
    GitCompare,
    ArrowRight,
    TrendingUp,
    TrendingDown,
    Minus,
    Plus,
    Edit,
    FileText,
    BarChart3,
    AlertTriangle,
    CheckCircle,
    Info,
    Merge,
    RotateCcw,
    Download
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import VersionMergeDialog from './version-merge-dialog';
import VersionDiffView from './version-diff-view';

interface ResumeVersion {
    id: string;
    name: string;
    description?: string;
    version_number: number;
    is_current: boolean;
    overall_score?: number;
    ats_score?: number;
    keyword_score?: number;
    created_at: string;
    tags: string[];
    job_target?: string;
}

interface VersionComparison {
    id: string;
    version1_id: string;
    version2_id: string;
    overall_similarity: number;
    quality_difference?: number;
    section_differences: Record<string, {
        changed: boolean;
        similarity: number;
        added_in_v2?: boolean;
        removed_in_v2?: boolean;
    }>;
    changes: {
        additions: string[];
        deletions: string[];
        modifications: string[];
    };
    analysis: {
        improvements: string[];
        regressions: string[];
        neutral_changes: string[];
    };
    recommendations: {
        merge_suggestions: string[];
        rollback_recommendations: string[];
    };
    comparison_date: string;
}

interface VersionCompareProps {
    userId: string;
    version1?: ResumeVersion;
    version2?: ResumeVersion;
    onClose?: () => void;
}

export default function VersionCompare({ userId, version1, version2, onClose }: VersionCompareProps) {
    const [selectedVersion1, setSelectedVersion1] = useState<string>(version1?.id || '');
    const [selectedVersion2, setSelectedVersion2] = useState<string>(version2?.id || '');
    const [comparison, setComparison] = useState<VersionComparison | null>(null);
    const [isComparing, setIsComparing] = useState(false);
    const [isMergeDialogOpen, setIsMergeDialogOpen] = useState(false);

    const queryClient = useQueryClient();

    // Fetch available versions
    const { data: versionsData } = useQuery({
        queryKey: ['versions', userId],
        queryFn: async () => {
            const response = await fetch(`/api/v1/users/${userId}/versions?sort_by=created_at&sort_order=desc`);
            if (!response.ok) {
                throw new Error('Failed to fetch versions');
            }
            return response.json();
        },
    });

    const versions: ResumeVersion[] = versionsData?.versions || [];

    // Compare versions mutation
    const compareVersionsMutation = useMutation({
        mutationFn: async ({ version1Id, version2Id }: { version1Id: string; version2Id: string }) => {
            const response = await fetch('/api/v1/versions/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    version1_id: version1Id,
                    version2_id: version2Id,
                    user_id: userId,
                }),
            });
            if (!response.ok) {
                throw new Error('Failed to compare versions');
            }
            return response.json();
        },
        onSuccess: (data) => {
            setComparison(data.comparison);
            setIsComparing(false);
            toast({
                title: "Comparison complete",
                description: "Version comparison has been generated successfully.",
            });
        },
        onError: (error) => {
            setIsComparing(false);
            toast({
                title: "Error",
                description: "Failed to compare versions. Please try again.",
                variant: "destructive",
            });
        },
    });

    // Restore version mutation
    const restoreVersionMutation = useMutation({
        mutationFn: async (versionId: string) => {
            const response = await fetch(`/api/v1/versions/${versionId}/restore`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId, create_backup: true }),
            });
            if (!response.ok) {
                throw new Error('Failed to restore version');
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', userId] });
            toast({
                title: "Version restored",
                description: "The version has been successfully restored as current.",
            });
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to restore version. Please try again.",
                variant: "destructive",
            });
        },
    });

    const handleCompare = () => {
        if (!selectedVersion1 || !selectedVersion2) {
            toast({
                title: "Selection required",
                description: "Please select two versions to compare.",
                variant: "destructive",
            });
            return;
        }

        if (selectedVersion1 === selectedVersion2) {
            toast({
                title: "Invalid selection",
                description: "Please select two different versions to compare.",
                variant: "destructive",
            });
            return;
        }

        setIsComparing(true);
        compareVersionsMutation.mutate({
            version1Id: selectedVersion1,
            version2Id: selectedVersion2,
        });
    };

    const handleRestoreVersion = (versionId: string) => {
        restoreVersionMutation.mutate(versionId);
    };

    const getVersion = (versionId: string) => {
        return versions.find(v => v.id === versionId);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getScoreColor = (score?: number) => {
        if (!score) return 'text-gray-500';
        if (score >= 0.8) return 'text-green-600';
        if (score >= 0.6) return 'text-yellow-600';
        return 'text-red-600';
    };

    const getChangeIcon = (type: 'addition' | 'deletion' | 'modification') => {
        switch (type) {
            case 'addition':
                return <Plus className="w-4 h-4 text-green-600" />;
            case 'deletion':
                return <Minus className="w-4 h-4 text-red-600" />;
            case 'modification':
                return <Edit className="w-4 h-4 text-blue-600" />;
        }
    };

    const getAnalysisIcon = (type: 'improvement' | 'regression' | 'neutral') => {
        switch (type) {
            case 'improvement':
                return <TrendingUp className="w-4 h-4 text-green-600" />;
            case 'regression':
                return <TrendingDown className="w-4 h-4 text-red-600" />;
            case 'neutral':
                return <Minus className="w-4 h-4 text-gray-600" />;
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <GitCompare className="w-6 h-6" />
                        Version Comparison
                    </h2>
                    <p className="text-gray-600">Compare two resume versions to see differences and improvements</p>
                </div>
                {onClose && (
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                )}
            </div>

            {/* Version Selection */}
            <Card>
                <CardHeader>
                    <CardTitle>Select Versions to Compare</CardTitle>
                    <CardDescription>
                        Choose two different versions to analyze their differences
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">Version 1 (Baseline)</label>
                            <Select value={selectedVersion1} onValueChange={setSelectedVersion1}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select first version" />
                                </SelectTrigger>
                                <SelectContent>
                                    {versions.map((version) => (
                                        <SelectItem key={version.id} value={version.id}>
                                            <div className="flex items-center gap-2">
                                                <span>{version.name}</span>
                                                {version.is_current && (
                                                    <Badge variant="default" className="text-xs">Current</Badge>
                                                )}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Version 2 (Comparison)</label>
                            <Select value={selectedVersion2} onValueChange={setSelectedVersion2}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select second version" />
                                </SelectTrigger>
                                <SelectContent>
                                    {versions.map((version) => (
                                        <SelectItem key={version.id} value={version.id}>
                                            <div className="flex items-center gap-2">
                                                <span>{version.name}</span>
                                                {version.is_current && (
                                                    <Badge variant="default" className="text-xs">Current</Badge>
                                                )}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <Button
                            onClick={handleCompare}
                            disabled={!selectedVersion1 || !selectedVersion2 || isComparing}
                            className="min-w-32"
                        >
                            {isComparing ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Comparing...
                                </>
                            ) : (
                                <>
                                    <GitCompare className="w-4 h-4 mr-2" />
                                    Compare Versions
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Comparison Results */}
            {comparison && (
                <div className="space-y-6">
                    {/* Overview */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <BarChart3 className="w-5 h-5" />
                                Comparison Overview
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Version Details */}
                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-900">Version Details</h4>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <div>
                                                <p className="font-medium">{getVersion(comparison.version1_id)?.name}</p>
                                                <p className="text-sm text-gray-600">
                                                    Version {getVersion(comparison.version1_id)?.version_number} •
                                                    {formatDate(getVersion(comparison.version1_id)?.created_at || '')}
                                                </p>
                                            </div>
                                            <Badge variant="outline">Baseline</Badge>
                                        </div>

                                        <div className="flex justify-center">
                                            <ArrowRight className="w-5 h-5 text-gray-400" />
                                        </div>

                                        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                                            <div>
                                                <p className="font-medium">{getVersion(comparison.version2_id)?.name}</p>
                                                <p className="text-sm text-gray-600">
                                                    Version {getVersion(comparison.version2_id)?.version_number} •
                                                    {formatDate(getVersion(comparison.version2_id)?.created_at || '')}
                                                </p>
                                            </div>
                                            <Badge variant="default">Comparison</Badge>
                                        </div>
                                    </div>
                                </div>

                                {/* Similarity & Quality */}
                                <div className="space-y-4">
                                    <h4 className="font-medium text-gray-900">Similarity & Quality</h4>
                                    <div className="space-y-3">
                                        <div>
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-sm font-medium">Overall Similarity</span>
                                                <span className="text-sm font-bold">
                                                    {Math.round(comparison.overall_similarity * 100)}%
                                                </span>
                                            </div>
                                            <Progress value={comparison.overall_similarity * 100} className="h-2" />
                                        </div>

                                        {comparison.quality_difference !== null && comparison.quality_difference !== undefined && (
                                            <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                                                <span className="text-sm font-medium">Quality Change</span>
                                                <div className="flex items-center gap-2">
                                                    {comparison.quality_difference > 0 ? (
                                                        <>
                                                            <TrendingUp className="w-4 h-4 text-green-600" />
                                                            <span className="text-green-600 font-medium">
                                                                +{Math.round(comparison.quality_difference * 100)}%
                                                            </span>
                                                        </>
                                                    ) : comparison.quality_difference < 0 ? (
                                                        <>
                                                            <TrendingDown className="w-4 h-4 text-red-600" />
                                                            <span className="text-red-600 font-medium">
                                                                {Math.round(comparison.quality_difference * 100)}%
                                                            </span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Minus className="w-4 h-4 text-gray-600" />
                                                            <span className="text-gray-600 font-medium">No change</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Detailed Analysis */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Detailed Analysis</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <Tabs defaultValue="changes" className="w-full">
                                <TabsList className="grid w-full grid-cols-5">
                                    <TabsTrigger value="changes">Changes</TabsTrigger>
                                    <TabsTrigger value="sections">Sections</TabsTrigger>
                                    <TabsTrigger value="diff">Side-by-Side</TabsTrigger>
                                    <TabsTrigger value="analysis">Impact</TabsTrigger>
                                    <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
                                </TabsList>

                                {/* Changes Tab */}
                                <TabsContent value="changes" className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {/* Additions */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-green-600">
                                                    <Plus className="w-4 h-4" />
                                                    Additions ({comparison.changes.additions.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.changes.additions.map((addition, index) => (
                                                            <div key={index} className="text-sm p-2 bg-green-50 rounded border-l-2 border-green-200">
                                                                {addition}
                                                            </div>
                                                        ))}
                                                        {comparison.changes.additions.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No additions</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>

                                        {/* Deletions */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-red-600">
                                                    <Minus className="w-4 h-4" />
                                                    Deletions ({comparison.changes.deletions.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.changes.deletions.map((deletion, index) => (
                                                            <div key={index} className="text-sm p-2 bg-red-50 rounded border-l-2 border-red-200">
                                                                {deletion}
                                                            </div>
                                                        ))}
                                                        {comparison.changes.deletions.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No deletions</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>

                                        {/* Modifications */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-blue-600">
                                                    <Edit className="w-4 h-4" />
                                                    Modifications ({comparison.changes.modifications.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.changes.modifications.map((modification, index) => (
                                                            <div key={index} className="text-sm p-2 bg-blue-50 rounded border-l-2 border-blue-200">
                                                                {modification}
                                                            </div>
                                                        ))}
                                                        {comparison.changes.modifications.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No modifications</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </TabsContent>

                                {/* Sections Tab */}
                                <TabsContent value="sections" className="space-y-4">
                                    <div className="space-y-3">
                                        {Object.entries(comparison.section_differences).map(([section, diff]) => (
                                            <Card key={section}>
                                                <CardContent className="p-4">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <FileText className="w-4 h-4" />
                                                            <span className="font-medium capitalize">{section.replace('_', ' ')}</span>
                                                            {diff.added_in_v2 && (
                                                                <Badge variant="default" className="text-xs bg-green-100 text-green-800">
                                                                    Added
                                                                </Badge>
                                                            )}
                                                            {diff.removed_in_v2 && (
                                                                <Badge variant="destructive" className="text-xs">
                                                                    Removed
                                                                </Badge>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-sm text-gray-600">
                                                                {Math.round(diff.similarity * 100)}% similar
                                                            </span>
                                                            <Progress value={diff.similarity * 100} className="w-20 h-2" />
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                </TabsContent>

                                {/* Side-by-Side Diff Tab */}
                                <TabsContent value="diff" className="space-y-4">
                                    <VersionDiffView
                                        version1={comparison.version1}
                                        version2={comparison.version2}
                                        sectionDifferences={comparison.section_differences}
                                    />
                                </TabsContent>

                                {/* Impact Analysis Tab */}
                                <TabsContent value="analysis" className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {/* Improvements */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-green-600">
                                                    <TrendingUp className="w-4 h-4" />
                                                    Improvements ({comparison.analysis.improvements.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.analysis.improvements.map((improvement, index) => (
                                                            <div key={index} className="text-sm p-2 bg-green-50 rounded border-l-2 border-green-200">
                                                                {improvement}
                                                            </div>
                                                        ))}
                                                        {comparison.analysis.improvements.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No improvements identified</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>

                                        {/* Regressions */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-red-600">
                                                    <TrendingDown className="w-4 h-4" />
                                                    Regressions ({comparison.analysis.regressions.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.analysis.regressions.map((regression, index) => (
                                                            <div key={index} className="text-sm p-2 bg-red-50 rounded border-l-2 border-red-200">
                                                                {regression}
                                                            </div>
                                                        ))}
                                                        {comparison.analysis.regressions.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No regressions identified</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>

                                        {/* Neutral Changes */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-gray-600">
                                                    <Minus className="w-4 h-4" />
                                                    Neutral ({comparison.analysis.neutral_changes.length})
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-32">
                                                    <div className="space-y-2">
                                                        {comparison.analysis.neutral_changes.map((change, index) => (
                                                            <div key={index} className="text-sm p-2 bg-gray-50 rounded border-l-2 border-gray-200">
                                                                {change}
                                                            </div>
                                                        ))}
                                                        {comparison.analysis.neutral_changes.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No neutral changes</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </TabsContent>

                                {/* Recommendations Tab */}
                                <TabsContent value="recommendations" className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {/* Merge Suggestions */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-blue-600">
                                                    <Merge className="w-4 h-4" />
                                                    Merge Suggestions
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-40">
                                                    <div className="space-y-2">
                                                        {comparison.recommendations.merge_suggestions.map((suggestion, index) => (
                                                            <div key={index} className="text-sm p-2 bg-blue-50 rounded border-l-2 border-blue-200">
                                                                {suggestion}
                                                            </div>
                                                        ))}
                                                        {comparison.recommendations.merge_suggestions.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No merge suggestions</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>

                                        {/* Rollback Recommendations */}
                                        <Card>
                                            <CardHeader className="pb-3">
                                                <CardTitle className="text-sm flex items-center gap-2 text-orange-600">
                                                    <RotateCcw className="w-4 h-4" />
                                                    Rollback Recommendations
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <ScrollArea className="h-40">
                                                    <div className="space-y-2">
                                                        {comparison.recommendations.rollback_recommendations.map((recommendation, index) => (
                                                            <div key={index} className="text-sm p-2 bg-orange-50 rounded border-l-2 border-orange-200">
                                                                {recommendation}
                                                            </div>
                                                        ))}
                                                        {comparison.recommendations.rollback_recommendations.length === 0 && (
                                                            <p className="text-sm text-gray-500 italic">No rollback recommendations</p>
                                                        )}
                                                    </div>
                                                </ScrollArea>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </TabsContent>
                            </Tabs>
                        </CardContent>
                    </Card>

                    {/* Actions */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Actions</CardTitle>
                            <CardDescription>
                                Take action based on the comparison results
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-wrap gap-3">
                                <Button
                                    onClick={() => handleRestoreVersion(comparison.version1_id)}
                                    variant="outline"
                                    disabled={restoreVersionMutation.isPending}
                                >
                                    <RotateCcw className="w-4 h-4 mr-2" />
                                    Restore Version 1
                                </Button>
                                <Button
                                    onClick={() => handleRestoreVersion(comparison.version2_id)}
                                    variant="outline"
                                    disabled={restoreVersionMutation.isPending}
                                >
                                    <RotateCcw className="w-4 h-4 mr-2" />
                                    Restore Version 2
                                </Button>
                                <Button
                                    onClick={() => setIsMergeDialogOpen(true)}
                                    variant="default"
                                >
                                    <Merge className="w-4 h-4 mr-2" />
                                    Merge Versions
                                </Button>
                                <Button variant="outline">
                                    <Download className="w-4 h-4 mr-2" />
                                    Export Comparison
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Merge Dialog */}
            <VersionMergeDialog
                isOpen={isMergeDialogOpen}
                onClose={() => setIsMergeDialogOpen(false)}
                comparison={comparison}
                userId={userId}
            />
        </div>
    );
}