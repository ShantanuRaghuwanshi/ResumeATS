import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
    FileText,
    Plus,
    Edit,
    Trash2,
    Download,
    Star,
    Clock,
    Tag,
    Filter,
    Search,
    MoreHorizontal,
    GitBranch,
    History,
    Copy,
    Archive
} from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { toast } from '@/hooks/use-toast';
import CreateVersionDialog from './create-version-dialog';
import VersionDetailsModal from './version-details-modal';

interface ResumeVersion {
    id: string;
    name: string;
    description?: string;
    version_number: number;
    is_current: boolean;
    is_template: boolean;
    job_target?: string;
    optimization_type?: string;
    overall_score?: number;
    ats_score?: number;
    keyword_score?: number;
    created_at: string;
    last_modified: string;
    download_count: number;
    tags: string[];
    category?: string;
}

interface VersionManagerProps {
    userId: string;
    resumeId?: string;
    onVersionSelect?: (version: ResumeVersion) => void;
}

export default function VersionManager({ userId, resumeId, onVersionSelect }: VersionManagerProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [sortBy, setSortBy] = useState<'created_at' | 'name' | 'overall_score' | 'version_number'>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [editingVersion, setEditingVersion] = useState<ResumeVersion | null>(null);
    const [selectedVersionForDetails, setSelectedVersionForDetails] = useState<ResumeVersion | null>(null);

    const queryClient = useQueryClient();

    // Fetch versions
    const { data: versionsData, isLoading, error } = useQuery({
        queryKey: ['versions', userId, { sortBy, sortOrder, tags: selectedTags, category: selectedCategory }],
        queryFn: async () => {
            const params = new URLSearchParams({
                sort_by: sortBy,
                sort_order: sortOrder,
            });

            if (selectedTags.length > 0) {
                params.append('tags', selectedTags.join(','));
            }

            if (selectedCategory) {
                params.append('category', selectedCategory);
            }

            const response = await fetch(`/api/v1/users/${userId}/versions?${params}`);
            if (!response.ok) {
                throw new Error('Failed to fetch versions');
            }
            return response.json();
        },
    });

    const versions: ResumeVersion[] = versionsData?.versions || [];

    // Filter versions by search term
    const filteredVersions = versions.filter(version =>
        version.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        version.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        version.job_target?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Delete version mutation
    const deleteVersionMutation = useMutation({
        mutationFn: async (versionId: string) => {
            const response = await fetch(`/api/v1/versions/${versionId}?user_id=${userId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                throw new Error('Failed to delete version');
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', userId] });
            toast({
                title: "Version deleted",
                description: "The version has been successfully deleted.",
            });
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to delete version. Please try again.",
                variant: "destructive",
            });
        },
    });

    // Update version mutation
    const updateVersionMutation = useMutation({
        mutationFn: async ({ versionId, updates }: { versionId: string; updates: Partial<ResumeVersion> }) => {
            const response = await fetch(`/api/v1/versions/${versionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId, ...updates }),
            });
            if (!response.ok) {
                throw new Error('Failed to update version');
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', userId] });
            setEditingVersion(null);
            toast({
                title: "Version updated",
                description: "The version has been successfully updated.",
            });
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to update version. Please try again.",
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

    const handleDeleteVersion = (versionId: string) => {
        deleteVersionMutation.mutate(versionId);
    };

    const handleUpdateVersion = (updates: Partial<ResumeVersion>) => {
        if (editingVersion) {
            updateVersionMutation.mutate({ versionId: editingVersion.id, updates });
        }
    };

    const handleRestoreVersion = (versionId: string) => {
        restoreVersionMutation.mutate(versionId);
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

    const getScoreBadgeVariant = (score?: number) => {
        if (!score) return 'secondary';
        if (score >= 0.8) return 'default';
        if (score >= 0.6) return 'secondary';
        return 'destructive';
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center p-8">
                <p className="text-red-600">Failed to load versions. Please try again.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Version Management</h2>
                    <p className="text-gray-600">Manage and organize your resume versions</p>
                </div>
                <Button onClick={() => setIsCreateDialogOpen(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Version
                </Button>
            </div>

            {/* Filters and Search */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                                <Input
                                    placeholder="Search versions..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                                <SelectTrigger className="w-40">
                                    <SelectValue placeholder="Sort by" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="created_at">Date Created</SelectItem>
                                    <SelectItem value="name">Name</SelectItem>
                                    <SelectItem value="overall_score">Score</SelectItem>
                                    <SelectItem value="version_number">Version #</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={sortOrder} onValueChange={(value: any) => setSortOrder(value)}>
                                <SelectTrigger className="w-32">
                                    <SelectValue placeholder="Order" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="desc">Newest</SelectItem>
                                    <SelectItem value="asc">Oldest</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Versions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredVersions.map((version) => (
                    <Card key={version.id} className={`relative ${version.is_current ? 'ring-2 ring-primary' : ''}`}>
                        <CardHeader className="pb-3">
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <FileText className="w-4 h-4" />
                                        {version.name}
                                        {version.is_current && (
                                            <Badge variant="default" className="text-xs">
                                                Current
                                            </Badge>
                                        )}
                                        {version.is_template && (
                                            <Badge variant="secondary" className="text-xs">
                                                Template
                                            </Badge>
                                        )}
                                    </CardTitle>
                                    <CardDescription className="mt-1">
                                        Version {version.version_number} • {formatDate(version.created_at)}
                                    </CardDescription>
                                </div>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" size="sm">
                                            <MoreHorizontal className="w-4 h-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuItem onClick={() => setSelectedVersionForDetails(version)}>
                                            <FileText className="w-4 h-4 mr-2" />
                                            View Details
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => setEditingVersion(version)}>
                                            <Edit className="w-4 h-4 mr-2" />
                                            Edit
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleRestoreVersion(version.id)}>
                                            <GitBranch className="w-4 h-4 mr-2" />
                                            Restore
                                        </DropdownMenuItem>
                                        <DropdownMenuItem>
                                            <Download className="w-4 h-4 mr-2" />
                                            Download
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                                                    <Trash2 className="w-4 h-4 mr-2" />
                                                    Delete
                                                </DropdownMenuItem>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>Delete Version</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        Are you sure you want to delete "{version.name}"? This action cannot be undone.
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                    <AlertDialogAction
                                                        onClick={() => handleDeleteVersion(version.id)}
                                                        className="bg-red-600 hover:bg-red-700"
                                                    >
                                                        Delete
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {version.description && (
                                <p className="text-sm text-gray-600 line-clamp-2">{version.description}</p>
                            )}

                            {/* Scores */}
                            <div className="flex gap-2">
                                {version.overall_score && (
                                    <Badge variant={getScoreBadgeVariant(version.overall_score)}>
                                        Overall: {Math.round(version.overall_score * 100)}%
                                    </Badge>
                                )}
                                {version.ats_score && (
                                    <Badge variant={getScoreBadgeVariant(version.ats_score)}>
                                        ATS: {Math.round(version.ats_score * 100)}%
                                    </Badge>
                                )}
                            </div>

                            {/* Job Target */}
                            {version.job_target && (
                                <div className="flex items-center gap-1 text-sm text-gray-600">
                                    <Tag className="w-3 h-3" />
                                    {version.job_target}
                                </div>
                            )}

                            {/* Tags */}
                            {version.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                    {version.tags.slice(0, 3).map((tag) => (
                                        <Badge key={tag} variant="outline" className="text-xs">
                                            {tag}
                                        </Badge>
                                    ))}
                                    {version.tags.length > 3 && (
                                        <Badge variant="outline" className="text-xs">
                                            +{version.tags.length - 3}
                                        </Badge>
                                    )}
                                </div>
                            )}

                            {/* Stats */}
                            <div className="flex items-center justify-between text-xs text-gray-500">
                                <div className="flex items-center gap-1">
                                    <Download className="w-3 h-3" />
                                    {version.download_count} downloads
                                </div>
                                <div className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatDate(version.last_modified)}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {filteredVersions.length === 0 && (
                <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No versions found</h3>
                    <p className="text-gray-600 mb-4">
                        {searchTerm ? 'No versions match your search criteria.' : 'Create your first resume version to get started.'}
                    </p>
                    <Button onClick={() => setIsCreateDialogOpen(true)}>
                        <Plus className="w-4 h-4 mr-2" />
                        Create Version
                    </Button>
                </div>
            )}

            {/* Create Version Dialog */}
            <CreateVersionDialog
                isOpen={isCreateDialogOpen}
                onClose={() => setIsCreateDialogOpen(false)}
                userId={userId}
                resumeId={resumeId}
            />

            {/* Version Details Modal */}
            <VersionDetailsModal
                isOpen={!!selectedVersionForDetails}
                onClose={() => setSelectedVersionForDetails(null)}
                version={selectedVersionForDetails}
                userId={userId}
            />

            {/* Edit Version Dialog */}
            <Dialog open={!!editingVersion} onOpenChange={() => setEditingVersion(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Edit Version</DialogTitle>
                        <DialogDescription>
                            Update the details for this resume version.
                        </DialogDescription>
                    </DialogHeader>
                    {editingVersion && (
                        <EditVersionForm
                            version={editingVersion}
                            onSave={handleUpdateVersion}
                            onCancel={() => setEditingVersion(null)}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

// Edit Version Form Component
interface EditVersionFormProps {
    version: ResumeVersion;
    onSave: (updates: Partial<ResumeVersion>) => void;
    onCancel: () => void;
}

function EditVersionForm({ version, onSave, onCancel }: EditVersionFormProps) {
    const [name, setName] = useState(version.name);
    const [description, setDescription] = useState(version.description || '');
    const [jobTarget, setJobTarget] = useState(version.job_target || '');
    const [category, setCategory] = useState(version.category || '');
    const [tags, setTags] = useState(version.tags.join(', '));

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave({
            name,
            description: description || undefined,
            job_target: jobTarget || undefined,
            category: category || undefined,
            tags: tags.split(',').map(tag => tag.trim()).filter(Boolean),
        });
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <Label htmlFor="name">Name</Label>
                <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
            </div>

            <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                />
            </div>

            <div>
                <Label htmlFor="jobTarget">Job Target</Label>
                <Input
                    id="jobTarget"
                    value={jobTarget}
                    onChange={(e) => setJobTarget(e.target.value)}
                    placeholder="e.g., Software Engineer, Marketing Manager"
                />
            </div>

            <div>
                <Label htmlFor="category">Category</Label>
                <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger>
                        <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="">No category</SelectItem>
                        <SelectItem value="tech">Technology</SelectItem>
                        <SelectItem value="marketing">Marketing</SelectItem>
                        <SelectItem value="finance">Finance</SelectItem>
                        <SelectItem value="healthcare">Healthcare</SelectItem>
                        <SelectItem value="education">Education</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                    id="tags"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    placeholder="e.g., senior, remote, startup"
                />
            </div>

            <DialogFooter>
                <Button type="button" variant="outline" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit">
                    Save Changes
                </Button>
            </DialogFooter>
        </form>
    );
}