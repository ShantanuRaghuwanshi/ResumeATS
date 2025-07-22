import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
    BarChart3,
    Eye,
    Edit,
    Download,
    Share,
    Clock,
    TrendingUp,
    Users,
    Target,
    Award
} from 'lucide-react';

interface VersionAnalyticsProps {
    userId: string;
    versionId: string;
}

interface VersionAnalytics {
    version_id: string;
    usage_metrics: {
        view_count: number;
        edit_count: number;
        download_count: number;
        share_count: number;
    };
    performance_metrics: {
        average_session_duration: number;
        bounce_rate: number;
        completion_rate: number;
    };
    success_metrics: {
        job_applications: number;
        interview_callbacks: number;
        job_offers: number;
    };
    tracking_period: {
        tracking_start: string;
        last_updated: string;
    };
}

export default function VersionAnalytics({ userId, versionId }: VersionAnalyticsProps) {
    const { data: analyticsData, isLoading, error } = useQuery({
        queryKey: ['version-analytics', userId, versionId],
        queryFn: async () => {
            const response = await fetch(`/api/v1/versions/${versionId}/analytics?user_id=${userId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch analytics');
            }
            return response.json();
        },
    });

    const analytics: VersionAnalytics = analyticsData?.analytics;

    const formatDuration = (seconds: number) => {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (error || !analytics) {
        return (
            <div className="text-center p-8">
                <p className="text-red-600">Failed to load analytics. Please try again.</p>
            </div>
        );
    }

    const successRate = analytics.success_metrics.job_applications > 0
        ? (analytics.success_metrics.interview_callbacks / analytics.success_metrics.job_applications) * 100
        : 0;

    const conversionRate = analytics.success_metrics.interview_callbacks > 0
        ? (analytics.success_metrics.job_offers / analytics.success_metrics.interview_callbacks) * 100
        : 0;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                <h3 className="text-lg font-semibold">Version Analytics</h3>
            </div>

            {/* Usage Metrics */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Usage Metrics</CardTitle>
                    <CardDescription>
                        How this version has been used since {formatDate(analytics.tracking_period.tracking_start)}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                            <Eye className="w-5 h-5 text-blue-600" />
                            <div>
                                <p className="text-2xl font-bold text-blue-600">
                                    {analytics.usage_metrics.view_count}
                                </p>
                                <p className="text-sm text-gray-600">Views</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                            <Edit className="w-5 h-5 text-green-600" />
                            <div>
                                <p className="text-2xl font-bold text-green-600">
                                    {analytics.usage_metrics.edit_count}
                                </p>
                                <p className="text-sm text-gray-600">Edits</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                            <Download className="w-5 h-5 text-purple-600" />
                            <div>
                                <p className="text-2xl font-bold text-purple-600">
                                    {analytics.usage_metrics.download_count}
                                </p>
                                <p className="text-sm text-gray-600">Downloads</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                            <Share className="w-5 h-5 text-orange-600" />
                            <div>
                                <p className="text-2xl font-bold text-orange-600">
                                    {analytics.usage_metrics.share_count}
                                </p>
                                <p className="text-sm text-gray-600">Shares</p>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Performance Metrics */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Performance Metrics</CardTitle>
                    <CardDescription>
                        User engagement and interaction patterns
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-gray-600" />
                            <span className="text-sm font-medium">Average Session Duration</span>
                        </div>
                        <span className="text-sm font-bold">
                            {formatDuration(analytics.performance_metrics.average_session_duration)}
                        </span>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">Completion Rate</span>
                            <span className="text-sm font-bold">
                                {Math.round(analytics.performance_metrics.completion_rate * 100)}%
                            </span>
                        </div>
                        <Progress value={analytics.performance_metrics.completion_rate * 100} className="h-2" />
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">Bounce Rate</span>
                            <span className="text-sm font-bold">
                                {Math.round(analytics.performance_metrics.bounce_rate * 100)}%
                            </span>
                        </div>
                        <Progress
                            value={analytics.performance_metrics.bounce_rate * 100}
                            className="h-2"
                        />
                    </div>
                </CardContent>
            </Card>

            {/* Success Metrics */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Success Metrics</CardTitle>
                    <CardDescription>
                        Job application outcomes and success rates
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                            <Target className="w-5 h-5 text-blue-600" />
                            <div>
                                <p className="text-2xl font-bold text-blue-600">
                                    {analytics.success_metrics.job_applications}
                                </p>
                                <p className="text-sm text-gray-600">Applications</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                            <Users className="w-5 h-5 text-green-600" />
                            <div>
                                <p className="text-2xl font-bold text-green-600">
                                    {analytics.success_metrics.interview_callbacks}
                                </p>
                                <p className="text-sm text-gray-600">Interviews</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg">
                            <Award className="w-5 h-5 text-yellow-600" />
                            <div>
                                <p className="text-2xl font-bold text-yellow-600">
                                    {analytics.success_metrics.job_offers}
                                </p>
                                <p className="text-sm text-gray-600">Offers</p>
                            </div>
                        </div>
                    </div>

                    {/* Success Rates */}
                    <div className="space-y-3">
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Interview Success Rate</span>
                                <div className="flex items-center gap-2">
                                    <Badge variant={successRate >= 20 ? "default" : successRate >= 10 ? "secondary" : "destructive"}>
                                        {Math.round(successRate)}%
                                    </Badge>
                                    {successRate > 0 && (
                                        <TrendingUp className="w-4 h-4 text-green-600" />
                                    )}
                                </div>
                            </div>
                            <Progress value={successRate} className="h-2" />
                        </div>

                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Offer Conversion Rate</span>
                                <div className="flex items-center gap-2">
                                    <Badge variant={conversionRate >= 30 ? "default" : conversionRate >= 15 ? "secondary" : "destructive"}>
                                        {Math.round(conversionRate)}%
                                    </Badge>
                                    {conversionRate > 0 && (
                                        <TrendingUp className="w-4 h-4 text-green-600" />
                                    )}
                                </div>
                            </div>
                            <Progress value={conversionRate} className="h-2" />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Tracking Period */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-center justify-between text-sm text-gray-600">
                        <span>Tracking since: {formatDate(analytics.tracking_period.tracking_start)}</span>
                        <span>Last updated: {formatDate(analytics.tracking_period.last_updated)}</span>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}