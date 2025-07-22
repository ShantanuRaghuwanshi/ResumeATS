import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
    Merge,
    ArrowRight,
    FileText,
    CheckCircle,
    AlertTriangle,
    Info
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';

interface ResumeVersion {
    id: string;
    name: string;
    description?: string;
    version_number: number;
    created_at: string;
    overall_score?: number;
    resume_data?: any;
}

interface VersionComparison {
    version1: ResumeVersion;
    version2: ResumeVersion;
    section_differences: Record<string, {
        changed: boolean;
        similarity: number;
        added_in_v2?: boolean;
        removed_in_v2?: boolean;
    }>;
    recommendations: {
        merge_suggestions: string[];
    };
}

interface VersionMergeDialogProps {
    isOpen: boolean;
    onClose: () => void;
    comparison: VersionComparison | null;
    userId: string;
}

interface MergeSelection {
    [sectionName: string]: 'version1' | 'version2' | 'both' | 'skip';
}

export default function VersionMergeDialog({
    isOpen,
    onClose,
    comparison,
    userId
}: VersionMergeDialogProps) {
    const [mergeName, setMergeName] = useState('');
    const [mergeDescription, setMergeDescription] = useState('');
    const [mergeSelections, setMergeSelections] = useState<MergeSelection>({});
    const [autoResolveConflicts, setAutoResolveConflicts] = useState(true);

    const queryClient = useQueryClient();

    // Create merged version mutation
    const createMergedVersionMutation = useMutation({
        mutationFn: async (mergeData: any) => {
            const response = await fetch('/api/v1/versions/merge', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(mergeData),
            });
            if (!response.ok) {
                throw new Error('Failed to create merged version');
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', userId] });
            toast({
                title: "Merge successful",
                description: "The merged version has been created successfully.",
            });
            handleClose();
        },
        onError: (error) => {
            toast({
                title: "Merge failed",
                description: "Failed to create merged version. Please try again.",
                variant: "destructive",
            });
        },
    });

    const handleClose = () => {
        setMergeName('');
        setMergeDescription('');
        setMergeSelections({});
        setAutoResolveConflicts(true);
        onClose();
    };

    const handleSelectionChange = (section: string, selection: 'version1' | 'version2' | 'both' | 'skip') => {
        setMergeSelections(prev => ({
            ...prev,
            [section]: selection
        }));
    };

    const handleMerge = () => {
        if (!comparison || !mergeName.trim()) {
            toast({
                title: "Invalid input",
                description: "Please provide a name for the merged version.",
                variant: "destructive",
            });
            return;
        }

        // Create merged resume data based on selections
        const mergedResumeData = createMergedResumeData();

        createMergedVersionMutation.mutate({
            user_id: userId,
            version1_id: comparison.version1.id,
            version2_id: comparison.version2.id,
            merge_selections: mergeSelections,
            merged_resume_data: mergedResumeData,
            name: mergeName.trim(),
            description: mergeDescription.trim() || undefined,
            auto_resolve_conflicts: autoResolveConflicts,
        });
    };

    const createMergedResumeData = () => {
        if (!comparison) return {};

        const version1Data = comparison.version1.resume_data || {};
        const version2Data = comparison.version2.resume_data || {};
        const mergedData = { sections: {} };

        // Process each section based on merge selections
        const allSections = new Set([
            ...Object.keys(version1Data.sections || {}),
            ...Object.keys(version2Data.sections || {})
        ]);

        allSections.forEach(section => {
            const selection = mergeSelections[section] || 'version2'; // Default to newer version
            const section1 = version1Data.sections?.[section];
            const section2 = version2Data.sections?.[section];

            switch (selection) {
                case 'version1':
                    if (section1) mergedData.sections[section] = section1;
                    break;
                case 'version2':
                    if (section2) mergedData.sections[section] = section2;
                    break;
                case 'both':
                    // Attempt to merge both sections (implementation depends on section structure)
                    mergedData.sections[section] = mergeSectionData(section1, section2);
                    break;
                case 'skip':
                    // Skip this section entirely
                    break;
            }
        });

        return mergedData;
    };

    const mergeSectionData = (data1: any, data2: any) => {
        // Simple merge strategy - in production, this would be more sophisticated
        if (Array.isArray(data1) && Array.isArray(data2)) {
            return [...data1, ...data2];
        } else if (typeof data1 === 'object' && typeof data2 === 'object') {
            return { ...data1, ...data2 };
        } else {
            return data2 || data1; // Prefer data2 (newer version)
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    const getSelectionColor = (selection: string) => {
        switch (selection) {
            case 'version1': return 'text-blue-600';
            case 'version2': return 'text-green-600';
            case 'both': return 'text-purple-600';
            case 'skip': return 'text-gray-600';
            default: return 'text-gray-600';
        }
    };

    const getSelectionBadge = (selection: string) => {
        switch (selection) {
            case 'version1': return <Badge variant="outline" className="text-blue-600">Version 1</Badge>;
            case 'version2': return <Badge variant="default" className="text-green-600">Version 2</Badge>;
            case 'both': return <Badge variant="secondary" className="text-purple-600">Both</Badge>;
            case 'skip': return <Badge variant="destructive" className="text-gray-600">Skip</Badge>;
            default: return null;
        }
    };

    if (!comparison) return null;

    // Initialize merge selections with smart defaults
    React.useEffect(() => {
        if (comparison && Object.keys(mergeSelections).length === 0) {
            const initialSelections: MergeSelection = {};

            Object.entries(comparison.section_differences).forEach(([section, diff]) => {
                if (diff.added_in_v2) {
                    initialSelections[section] = 'version2';
                } else if (diff.removed_in_v2) {
                    initialSelections[section] = 'version1';
                } else if (diff.changed) {
                    // For changed sections, default to version2 (newer)
                    initialSelections[section] = 'version2';
                } else {
                    // For unchanged sections, use version2
                    initialSelections[section] = 'version2';
                }
            });

            setMergeSelections(initialSelections);
        }
    }, [comparison, mergeSelections]);

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="max-w-4xl max-h-[90vh]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Merge className="w-5 h-5" />
                        Merge Versions
                    </DialogTitle>
                    <DialogDescription>
                        Create a new version by combining elements from both versions
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6">
                    {/* Version Information */}
                    <div className="grid grid-cols-2 gap-4">
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm text-blue-600">Version 1 (Baseline)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="font-medium">{comparison.version1.name}</p>
                                <p className="text-sm text-gray-600">
                                    {formatDate(comparison.version1.created_at)}
                                </p>
                                {comparison.version1.overall_score && (
                                    <Badge variant="outline" className="mt-2">
                                        Score: {Math.round(comparison.version1.overall_score * 100)}%
                                    </Badge>
                                )}
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm text-green-600">Version 2 (Comparison)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="font-medium">{comparison.version2.name}</p>
                                <p className="text-sm text-gray-600">
                                    {formatDate(comparison.version2.created_at)}
                                </p>
                                {comparison.version2.overall_score && (
                                    <Badge variant="default" className="mt-2">
                                        Score: {Math.round(comparison.version2.overall_score * 100)}%
                                    </Badge>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Merge Configuration */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Merge Configuration</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <Label htmlFor="mergeName">Merged Version Name *</Label>
                                    <Input
                                        id="mergeName"
                                        value={mergeName}
                                        onChange={(e) => setMergeName(e.target.value)}
                                        placeholder="e.g., Merged - Best of Both"
                                        required
                                    />
                                </div>
                                <div className="flex items-center space-x-2">
                                    <Checkbox
                                        id="autoResolve"
                                        checked={autoResolveConflicts}
                                        onCheckedChange={(checked) => setAutoResolveConflicts(!!checked)}
                                    />
                                    <Label htmlFor="autoResolve" className="text-sm">
                                        Auto-resolve conflicts
                                    </Label>
                                </div>
                            </div>

                            <div>
                                <Label htmlFor="mergeDescription">Description</Label>
                                <Textarea
                                    id="mergeDescription"
                                    value={mergeDescription}
                                    onChange={(e) => setMergeDescription(e.target.value)}
                                    placeholder="Describe the purpose of this merged version..."
                                    rows={2}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Section Selection */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Section Selection</CardTitle>
                            <DialogDescription>
                                Choose which version to use for each section, or combine both
                            </DialogDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-64">
                                <div className="space-y-3">
                                    {Object.entries(comparison.section_differences).map(([section, diff]) => (
                                        <div key={section} className="border rounded-lg p-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="flex items-center gap-2">
                                                    <FileText className="w-4 h-4" />
                                                    <span className="font-medium capitalize">
                                                        {section.replace('_', ' ')}
                                                    </span>
                                                    {diff.added_in_v2 && (
                                                        <Badge variant="default" className="text-xs">New</Badge>
                                                    )}
                                                    {diff.removed_in_v2 && (
                                                        <Badge variant="destructive" className="text-xs">Removed</Badge>
                                                    )}
                                                    {diff.changed && !diff.added_in_v2 && !diff.removed_in_v2 && (
                                                        <Badge variant="secondary" className="text-xs">Modified</Badge>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm text-gray-600">
                                                        {Math.round(diff.similarity * 100)}% similar
                                                    </span>
                                                    {getSelectionBadge(mergeSelections[section])}
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-4 gap-2">
                                                <Button
                                                    variant={mergeSelections[section] === 'version1' ? 'default' : 'outline'}
                                                    size="sm"
                                                    onClick={() => handleSelectionChange(section, 'version1')}
                                                    disabled={diff.removed_in_v2}
                                                >
                                                    Use V1
                                                </Button>
                                                <Button
                                                    variant={mergeSelections[section] === 'version2' ? 'default' : 'outline'}
                                                    size="sm"
                                                    onClick={() => handleSelectionChange(section, 'version2')}
                                                    disabled={diff.added_in_v2 === false && !comparison.version2.resume_data?.sections?.[section]}
                                                >
                                                    Use V2
                                                </Button>
                                                <Button
                                                    variant={mergeSelections[section] === 'both' ? 'default' : 'outline'}
                                                    size="sm"
                                                    onClick={() => handleSelectionChange(section, 'both')}
                                                    disabled={diff.added_in_v2 || diff.removed_in_v2}
                                                >
                                                    Merge Both
                                                </Button>
                                                <Button
                                                    variant={mergeSelections[section] === 'skip' ? 'destructive' : 'outline'}
                                                    size="sm"
                                                    onClick={() => handleSelectionChange(section, 'skip')}
                                                >
                                                    Skip
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>

                    {/* Merge Suggestions */}
                    {comparison.recommendations.merge_suggestions.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Info className="w-4 h-4" />
                                    AI Recommendations
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-2">
                                    {comparison.recommendations.merge_suggestions.map((suggestion, index) => (
                                        <div key={index} className="flex items-start gap-2 p-2 bg-blue-50 rounded">
                                            <CheckCircle className="w-4 h-4 text-blue-600 mt-0.5" />
                                            <p className="text-sm">{suggestion}</p>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleMerge}
                        disabled={createMergedVersionMutation.isPending || !mergeName.trim()}
                    >
                        {createMergedVersionMutation.isPending ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                Merging...
                            </>
                        ) : (
                            <>
                                <Merge className="w-4 h-4 mr-2" />
                                Create Merged Version
                            </>
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}