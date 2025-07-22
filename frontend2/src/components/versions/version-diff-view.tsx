import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
    FileText,
    Plus,
    Minus,
    Edit,
    ArrowRight,
    Equal
} from 'lucide-react';

interface ResumeVersion {
    id: string;
    name: string;
    resume_data?: any;
}

interface VersionDiffViewProps {
    version1: ResumeVersion;
    version2: ResumeVersion;
    sectionDifferences: Record<string, {
        changed: boolean;
        similarity: number;
        added_in_v2?: boolean;
        removed_in_v2?: boolean;
    }>;
}

export default function VersionDiffView({
    version1,
    version2,
    sectionDifferences
}: VersionDiffViewProps) {
    const renderSectionContent = (sectionData: any) => {
        if (!sectionData) return <p className="text-gray-500 italic">No content</p>;

        if (typeof sectionData === 'string') {
            return <p className="text-sm">{sectionData}</p>;
        }

        if (Array.isArray(sectionData)) {
            return (
                <div className="space-y-2">
                    {sectionData.map((item, index) => (
                        <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                            {typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
                        </div>
                    ))}
                </div>
            );
        }

        if (typeof sectionData === 'object') {
            return (
                <div className="space-y-2">
                    {Object.entries(sectionData).map(([key, value]) => (
                        <div key={key} className="text-sm">
                            <span className="font-medium">{key}:</span>{' '}
                            <span className="text-gray-600">
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                        </div>
                    ))}
                </div>
            );
        }

        return <p className="text-sm">{String(sectionData)}</p>;
    };

    const getDiffIcon = (section: string, diff: any) => {
        if (diff.added_in_v2) return <Plus className="w-4 h-4 text-green-600" />;
        if (diff.removed_in_v2) return <Minus className="w-4 h-4 text-red-600" />;
        if (diff.changed) return <Edit className="w-4 h-4 text-blue-600" />;
        return <Equal className="w-4 h-4 text-gray-600" />;
    };

    const getDiffColor = (section: string, diff: any) => {
        if (diff.added_in_v2) return 'border-green-200 bg-green-50';
        if (diff.removed_in_v2) return 'border-red-200 bg-red-50';
        if (diff.changed) return 'border-blue-200 bg-blue-50';
        return 'border-gray-200 bg-gray-50';
    };

    const sections1 = version1.resume_data?.sections || {};
    const sections2 = version2.resume_data?.sections || {};
    const allSections = new Set([...Object.keys(sections1), ...Object.keys(sections2)]);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Side-by-Side Comparison</h3>
                <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                        <Plus className="w-3 h-3 text-green-600" />
                        <span>Added</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Minus className="w-3 h-3 text-red-600" />
                        <span>Removed</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Edit className="w-3 h-3 text-blue-600" />
                        <span>Modified</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Equal className="w-3 h-3 text-gray-600" />
                        <span>Unchanged</span>
                    </div>
                </div>
            </div>

            <ScrollArea className="h-[600px]">
                <div className="space-y-4">
                    {Array.from(allSections).map((section) => {
                        const diff = sectionDifferences[section] || { changed: false, similarity: 1.0 };
                        const section1Data = sections1[section];
                        const section2Data = sections2[section];

                        return (
                            <Card key={section} className={`${getDiffColor(section, diff)}`}>
                                <CardHeader className="pb-3">
                                    <CardTitle className="text-base flex items-center gap-2">
                                        {getDiffIcon(section, diff)}
                                        <span className="capitalize">{section.replace('_', ' ')}</span>
                                        <Badge variant="outline" className="text-xs">
                                            {Math.round(diff.similarity * 100)}% similar
                                        </Badge>
                                        {diff.added_in_v2 && (
                                            <Badge variant="default" className="text-xs bg-green-100 text-green-800">
                                                New in V2
                                            </Badge>
                                        )}
                                        {diff.removed_in_v2 && (
                                            <Badge variant="destructive" className="text-xs">
                                                Removed in V2
                                            </Badge>
                                        )}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {/* Version 1 */}
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <FileText className="w-4 h-4 text-blue-600" />
                                                <span className="font-medium text-blue-600">
                                                    {version1.name}
                                                </span>
                                            </div>
                                            <div className="p-3 bg-white rounded border min-h-[100px]">
                                                {renderSectionContent(section1Data)}
                                            </div>
                                        </div>

                                        {/* Arrow */}
                                        <div className="hidden md:flex items-center justify-center">
                                            <ArrowRight className="w-5 h-5 text-gray-400" />
                                        </div>

                                        {/* Version 2 */}
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2">
                                                <FileText className="w-4 h-4 text-green-600" />
                                                <span className="font-medium text-green-600">
                                                    {version2.name}
                                                </span>
                                            </div>
                                            <div className="p-3 bg-white rounded border min-h-[100px]">
                                                {renderSectionContent(section2Data)}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Change Summary */}
                                    {diff.changed && (
                                        <div className="mt-4 pt-4 border-t">
                                            <div className="flex items-center gap-2 text-sm text-gray-600">
                                                <Edit className="w-3 h-3" />
                                                <span>
                                                    This section has been modified with {Math.round((1 - diff.similarity) * 100)}% changes
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            </ScrollArea>
        </div>
    );
}