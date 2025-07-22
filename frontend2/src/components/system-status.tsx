/**
 * System status monitoring component
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    CheckCircle,
    XCircle,
    AlertTriangle,
    RefreshCw,
    Activity,
    Wifi,
    WifiOff,
    Server,
    Database,
    Zap
} from 'lucide-react';
import { integrationService, SystemStatus } from '@/services/integration-service';
import { useToast } from '@/hooks/use-toast';

interface SystemStatusProps {
    showDetailed?: boolean;
    autoRefresh?: boolean;
    refreshInterval?: number;
}

export function SystemStatusComponent({
    showDetailed = false,
    autoRefresh = true,
    refreshInterval = 30000
}: SystemStatusProps) {
    const { toast } = useToast();
    const [isRefreshing, setIsRefreshing] = useState(false);

    // Query system health
    const {
        data: systemStatus,
        isLoading,
        error,
        refetch
    } = useQuery<SystemStatus>({
        queryKey: ['system-status'],
        queryFn: () => integrationService.checkSystemHealth(),
        refetchInterval: autoRefresh ? refreshInterval : false,
        refetchIntervalInBackground: true,
        onError: (error) => {
            console.error('Failed to fetch system status:', error);
            toast({
                title: 'Status Check Failed',
                description: 'Unable to check system status. Some features may be unavailable.',
                variant: 'destructive',
            });
        },
    });

    // Query system metrics if detailed view
    const { data: metrics } = useQuery({
        queryKey: ['system-metrics'],
        queryFn: () => integrationService.getSystemMetrics(),
        enabled: showDetailed,
        refetchInterval: autoRefresh ? refreshInterval * 2 : false,
    });

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await refetch();
            toast({
                title: 'Status Updated',
                description: 'System status has been refreshed.',
            });
        } catch (error) {
            toast({
                title: 'Refresh Failed',
                description: 'Failed to refresh system status.',
                variant: 'destructive',
            });
        } finally {
            setIsRefreshing(false);
        }
    };

    const getServiceIcon = (serviceName: string) => {
        switch (serviceName) {
            case 'websocket_manager':
                return <Wifi className="w-4 h-4" />;
            case 'cache_service':
                return <Database className="w-4 h-4" />;
            case 'background_jobs':
                return <Zap className="w-4 h-4" />;
            default:
                return <Server className="w-4 h-4" />;
        }
    };

    const getStatusBadge = (healthy: boolean) => {
        return (
            <Badge variant={healthy ? 'default' : 'destructive'} className="ml-2">
                {healthy ? (
                    <>
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Healthy
                    </>
                ) : (
                    <>
                        <XCircle className="w-3 h-3 mr-1" />
                        Unhealthy
                    </>
                )}
            </Badge>
        );
    };

    const getOverallStatusIcon = () => {
        if (isLoading) return <RefreshCw className="w-5 h-5 animate-spin" />;
        if (error) return <WifiOff className="w-5 h-5 text-red-500" />;
        if (systemStatus?.overall_healthy) return <CheckCircle className="w-5 h-5 text-green-500" />;
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    };

    if (!showDetailed) {
        // Compact status indicator
        return (
            <div className="flex items-center space-x-2">
                {getOverallStatusIcon()}
                <span className="text-sm text-slate-600">
                    {isLoading ? 'Checking...' :
                        error ? 'Offline' :
                            systemStatus?.overall_healthy ? 'All systems operational' : 'Some issues detected'}
                </span>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                >
                    <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Overall Status Header */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            {getOverallStatusIcon()}
                            <div>
                                <CardTitle className="text-xl">System Status</CardTitle>
                                <CardDescription>
                                    {isLoading ? 'Checking system health...' :
                                        error ? 'Unable to connect to monitoring service' :
                                            systemStatus?.overall_healthy ? 'All systems are operational' : 'Some services are experiencing issues'}
                                </CardDescription>
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            onClick={handleRefresh}
                            disabled={isRefreshing}
                        >
                            <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                            Refresh
                        </Button>
                    </div>
                </CardHeader>
            </Card>

            {systemStatus && (
                <Tabs defaultValue="services" className="space-y-4">
                    <TabsList>
                        <TabsTrigger value="services">Services</TabsTrigger>
                        <TabsTrigger value="connections">Connections</TabsTrigger>
                        <TabsTrigger value="performance">Performance</TabsTrigger>
                        <TabsTrigger value="circuit-breakers">Circuit Breakers</TabsTrigger>
                    </TabsList>

                    {/* Services Tab */}
                    <TabsContent value="services">
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {Object.entries(systemStatus.services).map(([serviceName, serviceStatus]) => (
                                <Card key={serviceName}>
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-2">
                                                {getServiceIcon(serviceName)}
                                                <CardTitle className="text-sm font-medium">
                                                    {serviceName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                </CardTitle>
                                            </div>
                                            {getStatusBadge(serviceStatus.healthy)}
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Last Check:</span>
                                                <span>{new Date(serviceStatus.last_check).toLocaleTimeString()}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-slate-600">Error Count:</span>
                                                <span className={serviceStatus.error_count > 0 ? 'text-red-600' : 'text-green-600'}>
                                                    {serviceStatus.error_count}
                                                </span>
                                            </div>
                                            {serviceStatus.last_error && (
                                                <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700">
                                                    {serviceStatus.last_error}
                                                </div>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </TabsContent>

                    {/* Connections Tab */}
                    <TabsContent value="connections">
                        <Card>
                            <CardHeader>
                                <CardTitle>WebSocket Connections</CardTitle>
                                <CardDescription>Real-time connection statistics</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium">Active Connections:</span>
                                        <Badge variant="outline">
                                            {systemStatus.websocket_connections.active_connections}
                                        </Badge>
                                    </div>

                                    <div className="space-y-2">
                                        <span className="text-sm font-medium">By Type:</span>
                                        {Object.entries(systemStatus.websocket_connections.connections_by_type).map(([type, count]) => (
                                            <div key={type} className="flex items-center justify-between text-sm">
                                                <span className="text-slate-600 capitalize">{type}:</span>
                                                <span>{count}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Performance Tab */}
                    <TabsContent value="performance">
                        <Card>
                            <CardHeader>
                                <CardTitle>Performance Metrics</CardTitle>
                                <CardDescription>System performance overview</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {metrics ? (
                                    <div className="space-y-4">
                                        <div className="text-sm text-slate-600">
                                            Performance metrics would be displayed here based on the metrics data structure.
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="text-center">
                                            <Activity className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                                            <p className="text-sm text-slate-600">Performance metrics loading...</p>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Circuit Breakers Tab */}
                    <TabsContent value="circuit-breakers">
                        <Card>
                            <CardHeader>
                                <CardTitle>Circuit Breakers</CardTitle>
                                <CardDescription>Service circuit breaker status</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {Object.entries(systemStatus.circuit_breakers).map(([service, breaker]) => (
                                        <div key={service} className="flex items-center justify-between p-3 border rounded">
                                            <div className="flex items-center space-x-3">
                                                {getServiceIcon(service)}
                                                <span className="font-medium">
                                                    {service.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                </span>
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                <Badge variant={breaker.state === 'closed' ? 'default' : 'destructive'}>
                                                    {breaker.state}
                                                </Badge>
                                                <span className="text-sm text-slate-600">
                                                    Failures: {breaker.failure_count}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            )}
        </div>
    );
}

export default SystemStatusComponent;