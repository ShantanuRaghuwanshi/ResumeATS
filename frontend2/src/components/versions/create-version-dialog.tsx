import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { X, Plus } from 'lucide-react';
import { toast } from '@/hooks/use-toast';

interface CreateVersionDialogProps {
    isOpen: boolean;
    onClose: () => void;
    userId: string;
    resumeId?: string;
    currentResumeData?: any;
}

export default function CreateVersionDialog({
    isOpen,
    onClose,
    userId,
    resumeId,
    currentResumeData
}: CreateVersionDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [jobTarget, setJobTarget] = useState('');
    const [optimizationType, setOptimizationType] = useState('');
    const [category, setCategory] = useState('');
    const [tags, setTags] = useState<string[]>([]);
    const [newTag, setNewTag] = useState('');

    const queryClient = useQueryClient();

    // Create version mutation
    const createVersionMutation = useMutation({
        mutationFn: async (versionData: any) => {
            const response = await fetch('/api/v1/versions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(versionData),
            });
            if (!response.ok) {
                throw new Error('Failed to create version');
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['versions', userId] });
            toast({
                title: "Version created",
                description: "Your resume version has been created successfully.",
            });
            handleClose();
        },
        onError: (error) => {
            toast({
                title: "Error",
                description: "Failed to create version. Please try again.",
                variant: "destructive",
            });
        },
    });

    const handleClose = () => {
        setName('');
        setDescription('');
        setJobTarget('');
        setOptimizationType('');
        setCategory('');
        setTags([]);
        setNewTag('');
        onClose();
    };

    const handleAddTag = () => {
        if (newTag.trim() && !tags.includes(newTag.trim())) {
            setTags([...tags, newTag.trim()]);
            setNewTag('');
        }
    };

    const handleRemoveTag = (tagToRemove: string) => {
        setTags(tags.filter(tag => tag !== tagToRemove));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (!name.trim()) {
            toast({
                title: "Name required",
                description: "Please enter a name for the version.",
                variant: "destructive",
            });
            return;
        }

        // Use current resume data or fetch it if resumeId is provided
        let resumeData = currentResumeData;
        if (!resumeData && resumeId) {
            // In a real implementation, you would fetch the current resume data
            // For now, we'll use a placeholder
            resumeData = { sections: {} };
        }

        createVersionMutation.mutate({
            user_id: userId,
            resume_data: resumeData || { sections: {} },
            name: name.trim(),
            description: description.trim() || undefined,
            job_target: jobTarget.trim() || undefined,
            optimization_type: optimizationType || undefined,
            tags: tags,
        });
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && newTag.trim()) {
            e.preventDefault();
            handleAddTag();
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Create New Version</DialogTitle>
                    <DialogDescription>
                        Create a new version of your resume with custom settings and metadata.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Name */}
                    <div>
                        <Label htmlFor="name">Version Name *</Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., Software Engineer - Tech Startup"
                            required
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <Label htmlFor="description">Description</Label>
                        <Textarea
                            id="description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Brief description of this version's purpose or target..."
                            rows={3}
                        />
                    </div>

                    {/* Job Target */}
                    <div>
                        <Label htmlFor="jobTarget">Job Target</Label>
                        <Input
                            id="jobTarget"
                            value={jobTarget}
                            onChange={(e) => setJobTarget(e.target.value)}
                            placeholder="e.g., Senior Software Engineer, Product Manager"
                        />
                    </div>

                    {/* Optimization Type */}
                    <div>
                        <Label htmlFor="optimizationType">Optimization Type</Label>
                        <Select value={optimizationType} onValueChange={setOptimizationType}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select optimization type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="">No specific optimization</SelectItem>
                                <SelectItem value="general">General optimization</SelectItem>
                                <SelectItem value="job_specific">Job-specific optimization</SelectItem>
                                <SelectItem value="ats_friendly">ATS-friendly optimization</SelectItem>
                                <SelectItem value="keyword_focused">Keyword-focused optimization</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Category */}
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
                                <SelectItem value="consulting">Consulting</SelectItem>
                                <SelectItem value="sales">Sales</SelectItem>
                                <SelectItem value="other">Other</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Tags */}
                    <div>
                        <Label htmlFor="tags">Tags</Label>
                        <div className="space-y-2">
                            <div className="flex gap-2">
                                <Input
                                    id="tags"
                                    value={newTag}
                                    onChange={(e) => setNewTag(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="Add a tag..."
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={handleAddTag}
                                    disabled={!newTag.trim() || tags.includes(newTag.trim())}
                                >
                                    <Plus className="w-4 h-4" />
                                </Button>
                            </div>
                            {tags.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {tags.map((tag) => (
                                        <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                                            {tag}
                                            <button
                                                type="button"
                                                onClick={() => handleRemoveTag(tag)}
                                                className="ml-1 hover:text-red-600"
                                            >
                                                <X className="w-3 h-3" />
                                            </button>
                                        </Badge>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={handleClose}>
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={createVersionMutation.isPending || !name.trim()}
                        >
                            {createVersionMutation.isPending ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Creating...
                                </>
                            ) : (
                                'Create Version'
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}