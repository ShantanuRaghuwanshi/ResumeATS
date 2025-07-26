import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    CheckCircle,
    Clock,
    AlertCircle,
    FileText,
    Target,
    TrendingUp
} from "lucide-react";

interface AnalysisStatusProps {
    totalJobs: number;
    analyzedJobs: number;
    averageMatch?: number;
    pendingJobs: number;
}

export default function AnalysisStatus({
    totalJobs,
    analyzedJobs,
    averageMatch,
    pendingJobs
}: AnalysisStatusProps) {
    const completionRate = totalJobs > 0 ? (analyzedJobs / totalJobs) * 100 : 0;

    const getStatusColor = () => {
        if (completionRate === 100) return "bg-green-50 border-green-200";
        if (completionRate >= 50) return "bg-blue-50 border-blue-200";
        return "bg-yellow-50 border-yellow-200";
    };

    const getStatusIcon = () => {
        if (completionRate === 100) return <CheckCircle className="w-5 h-5 text-green-600" />;
        if (pendingJobs > 0) return <Clock className="w-5 h-5 text-yellow-600" />;
        return <AlertCircle className="w-5 h-5 text-blue-600" />;
    };

    const getStatusText = () => {
        if (completionRate === 100) return "All jobs analyzed";
        if (analyzedJobs > 0) return "Analysis in progress";
        return "Ready to start analysis";
    };

    return (
        <Card className={`${getStatusColor()} border-2`}>
            <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        {getStatusIcon()}
                        <span className="font-medium text-slate-800">{getStatusText()}</span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                        {Math.round(completionRate)}% Complete
                    </Badge>
                </div>

                <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                        <div className="flex items-center justify-center gap-1 mb-1">
                            <FileText className="w-4 h-4 text-blue-600" />
                            <span className="text-lg font-bold text-slate-800">{totalJobs}</span>
                        </div>
                        <span className="text-xs text-slate-600">Total Jobs</span>
                    </div>

                    <div>
                        <div className="flex items-center justify-center gap-1 mb-1">
                            <Target className="w-4 h-4 text-green-600" />
                            <span className="text-lg font-bold text-slate-800">{analyzedJobs}</span>
                        </div>
                        <span className="text-xs text-slate-600">Analyzed</span>
                    </div>

                    <div>
                        <div className="flex items-center justify-center gap-1 mb-1">
                            <TrendingUp className="w-4 h-4 text-purple-600" />
                            <span className="text-lg font-bold text-slate-800">
                                {averageMatch ? `${averageMatch}%` : '-'}
                            </span>
                        </div>
                        <span className="text-xs text-slate-600">Avg Match</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
