import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
    FileText,
    Calendar,
    Tag,
    Target,
    BarChart3,
    Download,
    Edit,
    History,
    Settings,
    Info
} from 'lucide-react';
import VersionAnalytics from './version-analytics';

interface ResumeVersion {
    id: string;
    name: string;
    description?: string;
    version_number: number;
    is_current: boolean;
    is_template: boolean;
    job_target?: string;
    target_industry?: string;
    optimization_type?: string;
    overall_score?: number;
    ats_score?: number;
    keyword_score?: number;
    created_at: string;
    last_modified: string;
    download_count: number;
    last_downloaded?: string;
    tags: string[];
    category?: string;
}

interface VersionDetailsModalProps {
    isOpen: boolean;
    onClose: () => void;
    version: ResumeVersion | null;
    userId: string;
}

export default function VersionDetailsModal({
    isOpen,
    onClose,
    version,
    userId
}: VersionDetailsModalProps) {
    const [activeTab, setActiveTab] = useState('overview');

    // Fetch detailed version data
    const { data: versionDetails, isLoading } = useQuery({
        queryKey: ['version-details', version?.id],
        queryFn: async () => {
            if (!version?.id) return null;
            const response = await fetch(`/api/v1/versions/${version.id}?user_id=${userId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch version details');
            }
            return response.json();
        },
        enabled: !!version?.id && isOpen,
    });

    // Fetch version history
    const { data: versionHistory } = useQuery({
        queryKey: ['version-history', version?.id],
        queryFn: async () => {
            if (!version?.id) return null;
            const response = await fetch(`/api/v1/versions/${version.id}/history?user_id=${userId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch version history');
            }
            return response.json();
        },
        enabled: !!version?.id && isOpen,
    });

    if (!version) return null;

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

    const getScoreBadgeVariant = (score?: number) => {
        if (!score) return 'secondary';
        if (score >= 0.8) return 'default';
        if (score >= 0.6) return 'secondary';
        return 'destructive';
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileText className="w-5 h-5" />
                        {version.name}
                        {version.is_current && (
                            <Badge variant="default" className="text-xs">Current</Badge>
                        )}
                        {version.is_template && (
                            <Badge variant="secondary" className="text-xs">Template</Badge>
                        )}
                    </DialogTitle>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-4">
                        <TabsTrigger value="overview">Overview</TabsTrigger>
                        <TabsTrigger value="analytics">Analytics</TabsTrigger>
                        <TabsTrigger value="history">History</TabsTrigger>
                        <TabsTrigger value="content">Content</TabsTrigger>
                    </TabsList>

                    {/* Overview Tab */}
                    <TabsContent value="overview" className="space-y-4">
                        <ScrollArea className="h-[500px] pr-4">
                            <div className="space-y-4">
                                {/* Basic Information */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <Info className="w-4 h-4" />
                                            Basic Information
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Version Number</p>
                                                <p className="text-sm">{version.version_number}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Category</p>
                                                <p className="text-sm">{version.category || 'No category'}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Created</p>
                                                <p className="text-sm">{formatDate(version.created_at)}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Last Modified</p>
                                                <p className="text-sm">{formatDate(version.last_modified)}</p>
                                            </div>
                                        </div>

                                        {version.description && (
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Description</p>
                                                <p className="text-sm">{version.description}</p>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {/* Optimization Details */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <Target className="w-4 h-4" />
                                            Optimization Details
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Job Target</p>
                                                <p className="text-sm">{version.job_target || 'Not specified'}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Target Industry</p>
                                                <p className="text-sm">{version.target_industry || 'Not specified'}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Optimization Type</p>
                                                <p className="text-sm">{version.optimization_type || 'General'}</p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Quality Scores */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <BarChart3 className="w-4 h-4" />
                                            Quality Scores
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-3 gap-4">
                                            {version.overall_score && (
                                                <div className="text-center">
                                                    <Badge variant={getScoreBadgeVariant(version.overall_score)} className="mb-2">
                                                        Overall: {Math.round(version.overall_score * 100)}%
                                                    </Badge>
                                                    <p className="text-xs text-gray-600">Overall Quality</p>
                                                </div>
                                            )}
                                            {version.ats_score && (
                                                <div className="text-center">
                                                    <Badge variant={getScoreBadgeVariant(version.ats_score)} className="mb-2">
                                                        ATS: {Math.round(version.ats_score * 100)}%
                                                    </Badge>
                                                    <p className="text-xs text-gray-600">ATS Compatibility</p>
                                                </div>
                                            )}
                                            {version.keyword_score && (
                                                <div className="text-center">
                                                    <Badge variant={getScoreBadgeVariant(version.keyword_score)} className="mb-2">
                                                        Keywords: {Math.round(version.keyword_score * 100)}%
                                                    </Badge>
                                                    <p className="text-xs text-gray-600">Keyword Optimization</p>
                                                </div>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Tags */}
                                {version.tags.length > 0 && (
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <Tag className="w-4 h-4" />
                                                Tags
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="flex flex-wrap gap-2">
                                                {version.tags.map((tag) => (
                                                    <Badge key={tag} variant="outline">
                                                        {tag}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Usage Statistics */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base flex items-center gap-2">
                                            <Download className="w-4 h-4" />
                                            Usage Statistics
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Download Count</p>
                                                <p className="text-sm">{version.download_count}</p>
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-gray-600">Last Downloaded</p>
                                                <p className="text-sm">
                                                    {version.last_downloaded
                                                        ? formatDate(version.last_downloaded)
                                                        : 'Never'
                                                    }
                                                </p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        </ScrollArea>
                    </TabsContent>

                    {/* Analytics Tab */}
                    <TabsContent value="analytics">
                        <ScrollArea className="h-[500px] pr-4">
                            <VersionAnalytics userId={userId} versionId={version.id} />
                        </ScrollArea>
                    </TabsContent>

                    {/* History Tab */}
                    <TabsContent value="history">
                        <ScrollArea className="h-[500px] pr-4">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <History className="w-4 h-4" />
                                        Version History
                                    </CardTitle>
                                    <CardDescription>
                                        Track of changes and modifications to this version
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {versionHistory?.history ? (
                                        <div className="space-y-4">
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                <div className="text-center">
                                                    <p className="text-2xl font-bold text-blue-600">
                                                        {versionHistory.history.total_changes}
                                                    </p>
                                                    <p className="text-sm text-gray-600">Total Changes</p>
                                                </div>
                                                <div className="text-center">
                                                    <p className="text-2xl font-bold text-green-600">
                                                        {versionHistory.history.major_revisions}
                                                    </p>
                                                    <p className="text-sm text-gray-600">Major Revisions</p>
                                                </div>
                                                <div className="text-center">
                                                    <p className="text-2xl font-bold text-yellow-600">
                                                        {versionHistory.history.minor_revisions}
                                                    </p>
                                                    <p className="text-sm text-gray-600">Minor Revisions</p>
                                                </div>
                                                <div className="text-center">
                                                    <p className="text-2xl font-bold text-purple-600">
                                                        {versionHistory.history.sections_modified?.length || 0}
                                                    </p>
                                                    <p className="text-sm text-gray-600">Sections Modified</p>
                                                </div>
                                            </div>

                                            <Separator />

                                            {versionHistory.history.modification_timeline?.length > 0 && (
                                                <div>
                                                    <h4 className="font-medium mb-3">Recent Changes</h4>
                                                    <div className="space-y-2">
                                                        {versionHistory.history.modification_timeline.slice(0, 10).map((change: any, index: number) => (
                                                            <div key={index} className="flex items-center gap-3 p-2 bg-gray-50 rounded">
                                                                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                                                <div className="flex-1">
                                                                    <p className="text-sm font-medium">{change.type || 'Change'}</p>
                                                                    <p className="text-xs text-gray-600">
                                                                        {change.timestamp ? formatDate(change.timestamp) : 'Unknown time'}
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <p className="text-gray-600 text-center py-8">
                                            No history data available for this version.
                                        </p>
                                    )}
                                </CardContent>
                            </Card>
                        </ScrollArea>
                    </TabsContent>

                    {/* Content Tab */}
                    <TabsContent value="content">
                        <ScrollArea className="h-[500px] pr-4">
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-base flex items-center gap-2">
                                        <FileText className="w-4 h-4" />
                                        Resume Content
                                    </CardTitle>
                                    <CardDescription>
                                        Preview of the resume content in this version
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {isLoading ? (
                                        <div className="flex items-center justify-center py-8">
                                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                                        </div>
                                    ) : versionDetails?.version?.resume_data ? (
                                        <div className="space-y-4">
                                            {Object.entries(versionDetails.version.resume_data.sections || {}).map(([sectionName, sectionData]: [string, any]) => (
                                                <div key={sectionName} className="border rounded-lg p-4">
                                                    <h4 className="font-medium mb-2 capitalize">
                                                        {sectionName.replace('_', ' ')}
                                                    </h4>
                                                    <pre className="text-sm text-gray-600 whitespace-pre-wrap">
                                                        {JSON.stringify(sectionData, null, 2)}
                                                    </pre>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-gray-600 text-center py-8">
                                            No content data available for this version.
                                        </p>
                                    )}
                                </CardContent>
                            </Card>
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}