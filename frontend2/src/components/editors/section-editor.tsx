import { useState, useEffect, useCallback, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
    Edit3,
    Save,
    Undo,
    Redo,
    Wand2,
    CheckCircle,
    AlertCircle,
    Eye,
    EyeOff,
    RefreshCw,
    Lightbulb
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import RealTimeFeedback from "./real-time-feedback";
import SuggestionPanel from "./suggestion-panel";
import type { Suggestion } from "../chat/section-chat";

interface SectionEditorProps {
    resumeId: string;
    section: string;
    initialData?: any;
    onSave?: (data: any) => void;
    onSuggestionApplied?: (suggestion: Suggestion) => void;
}

interface EditorState {
    data: any;
    timestamp: number;
}

interface ValidationResult {
    isValid: boolean;
    errors: string[];
    warnings: string[];
    suggestions: string[];
    score: number;
}

export default function SectionEditor({
    resumeId,
    section,
    initialData,
    onSave,
    onSuggestionApplied
}: SectionEditorProps) {
    const [data, setData] = useState(initialData || {});
    const [isEditing, setIsEditing] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [undoStack, setUndoStack] = useState<EditorState[]>([]);
    const [redoStack, setRedoStack] = useState<EditorState[]>([]);
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);
    const debounceRef = useRef<NodeJS.Timeout>();

    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Fetch section data
    const { data: sectionData, isLoading } = useQuery({
        queryKey: ["resume-section", resumeId, section],
        queryFn: async () => {
            const response = await apiRequest("GET", `/resume/${resumeId}/section/${section}`);
            return response.json();
        },
        enabled: !initialData,
    });

    // Real-time validation query
    const { data: validation, refetch: validateSection } = useQuery({
        queryKey: ["section-validation", resumeId, section, data],
        queryFn: async (): Promise<ValidationResult> => {
            const response = await apiRequest("POST", `/resume/${resumeId}/section/${section}/validate`, {
                data,
            });
            return response.json();
        },
        enabled: false, // Only run when explicitly called
    });

    // Save section mutation
    const saveSectionMutation = useMutation({
        mutationFn: async (sectionData: any) => {
            const response = await apiRequest("PUT", `/resume/${resumeId}/section/${section}`, {
                data: sectionData,
            });
            return response.json();
        },
        onSuccess: (result) => {
            setHasUnsavedChanges(false);
            toast({
                title: "Section saved",
                description: "Your changes have been saved successfully.",
            });

            if (onSave) {
                onSave(result);
            }

            queryClient.invalidateQueries({ queryKey: ["resume-section", resumeId, section] });
        },
        onError: (error) => {
            toast({
                title: "Failed to save section",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Generate AI suggestions mutation
    const generateSuggestionsMutation = useMutation({
        mutationFn: async () => {
            const response = await apiRequest("POST", `/resume/${resumeId}/section/${section}/suggestions`, {
                data,
            });
            return response.json();
        },
        onSuccess: (suggestions) => {
            setIsGeneratingSuggestions(false);
            toast({
                title: "Suggestions generated",
                description: `Generated ${suggestions.length} suggestions for improvement.`,
            });
        },
        onError: (error) => {
            setIsGeneratingSuggestions(false);
            toast({
                title: "Failed to generate suggestions",
                description: error.message || "Please try again.",
                variant: "destructive",
            });
        },
    });

    // Initialize data when section data loads
    useEffect(() => {
        if (sectionData && !initialData) {
            setData(sectionData);
        }
    }, [sectionData, initialData]);

    // Debounced validation
    useEffect(() => {
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        debounceRef.current = setTimeout(() => {
            if (isEditing && Object.keys(data).length > 0) {
                validateSection();
            }
        }, 1000);

        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        };
    }, [data, isEditing, validateSection]);

    // Save state for undo/redo
    const saveState = useCallback((newData: any) => {
        setUndoStack(prev => [...prev, { data, timestamp: Date.now() }]);
        setRedoStack([]); // Clear redo stack when new change is made
        setData(newData);
        setHasUnsavedChanges(true);
    }, [data]);

    const handleUndo = () => {
        if (undoStack.length === 0) return;

        const previousState = undoStack[undoStack.length - 1];
        setRedoStack(prev => [...prev, { data, timestamp: Date.now() }]);
        setUndoStack(prev => prev.slice(0, -1));
        setData(previousState.data);
        setHasUnsavedChanges(true);
    };

    const handleRedo = () => {
        if (redoStack.length === 0) return;

        const nextState = redoStack[redoStack.length - 1];
        setUndoStack(prev => [...prev, { data, timestamp: Date.now() }]);
        setRedoStack(prev => prev.slice(0, -1));
        setData(nextState.data);
        setHasUnsavedChanges(true);
    };

    const handleSave = () => {
        saveSectionMutation.mutate(data);
    };

    const handleGenerateSuggestions = () => {
        setIsGeneratingSuggestions(true);
        generateSuggestionsMutation.mutate();
    };

    const handleFieldChange = (field: string, value: any) => {
        const newData = { ...data, [field]: value };
        saveState(newData);
    };

    const handleArrayFieldChange = (field: string, index: number, value: any) => {
        const newData = { ...data };
        if (!newData[field]) newData[field] = [];
        newData[field][index] = value;
        saveState(newData);
    };

    const handleAddArrayItem = (field: string, defaultItem: any) => {
        const newData = { ...data };
        if (!newData[field]) newData[field] = [];
        newData[field].push(defaultItem);
        saveState(newData);
    };

    const handleRemoveArrayItem = (field: string, index: number) => {
        const newData = { ...data };
        if (newData[field]) {
            newData[field].splice(index, 1);
            saveState(newData);
        }
    };

    const renderSectionEditor = () => {
        switch (section) {
            case "personal":
                return <PersonalDetailsEditor data={data} onChange={handleFieldChange} />;
            case "summary":
                return <SummaryEditor data={data} onChange={handleFieldChange} />;
            case "experience":
                return (
                    <ExperienceEditor
                        data={data}
                        onChange={handleFieldChange}
                        onArrayChange={handleArrayFieldChange}
                        onAddItem={handleAddArrayItem}
                        onRemoveItem={handleRemoveArrayItem}
                    />
                );
            case "skills":
                return (
                    <SkillsEditor
                        data={data}
                        onChange={handleFieldChange}
                        onArrayChange={handleArrayFieldChange}
                        onAddItem={handleAddArrayItem}
                        onRemoveItem={handleRemoveArrayItem}
                    />
                );
            case "education":
                return (
                    <EducationEditor
                        data={data}
                        onChange={handleFieldChange}
                        onArrayChange={handleArrayFieldChange}
                        onAddItem={handleAddArrayItem}
                        onRemoveItem={handleRemoveArrayItem}
                    />
                );
            default:
                return <GenericEditor data={data} onChange={handleFieldChange} />;
        }
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <RefreshCw className="w-8 h-8 mx-auto mb-2 text-muted-foreground animate-spin" />
                        <p className="text-sm text-muted-foreground">Loading section data...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Editor */}
            <div className="lg:col-span-2 space-y-4">
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                                <Edit3 className="w-5 h-5 text-primary" />
                                {section.charAt(0).toUpperCase() + section.slice(1)} Editor
                            </CardTitle>

                            <div className="flex items-center gap-2">
                                {hasUnsavedChanges && (
                                    <Badge variant="outline" className="text-orange-600 border-orange-200">
                                        Unsaved changes
                                    </Badge>
                                )}

                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setShowPreview(!showPreview)}
                                >
                                    {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    {showPreview ? "Hide Preview" : "Show Preview"}
                                </Button>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleUndo}
                                disabled={undoStack.length === 0}
                            >
                                <Undo className="w-4 h-4 mr-1" />
                                Undo
                            </Button>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleRedo}
                                disabled={redoStack.length === 0}
                            >
                                <Redo className="w-4 h-4 mr-1" />
                                Redo
                            </Button>

                            <Separator orientation="vertical" className="h-6" />

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleGenerateSuggestions}
                                disabled={isGeneratingSuggestions}
                            >
                                <Wand2 className="w-4 h-4 mr-1" />
                                {isGeneratingSuggestions ? "Generating..." : "AI Suggestions"}
                            </Button>

                            <Button
                                onClick={handleSave}
                                disabled={!hasUnsavedChanges || saveSectionMutation.isPending}
                                size="sm"
                            >
                                <Save className="w-4 h-4 mr-1" />
                                {saveSectionMutation.isPending ? "Saving..." : "Save"}
                            </Button>
                        </div>
                    </CardHeader>

                    <CardContent>
                        {renderSectionEditor()}
                    </CardContent>
                </Card>

                {showPreview && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Preview</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <SectionPreview section={section} data={data} />
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
                <RealTimeFeedback
                    validation={validation}
                    isValidating={false}
                />

                <SuggestionPanel
                    resumeId={resumeId}
                    section={section}
                    suggestions={generateSuggestionsMutation.data || []}
                    onSuggestionApplied={onSuggestionApplied}
                />
            </div>
        </div>
    );
}

// Individual section editors
interface EditorProps {
    data: any;
    onChange: (field: string, value: any) => void;
    onArrayChange?: (field: string, index: number, value: any) => void;
    onAddItem?: (field: string, defaultItem: any) => void;
    onRemoveItem?: (field: string, index: number) => void;
}

function PersonalDetailsEditor({ data, onChange }: EditorProps) {
    return (
        <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                        id="name"
                        value={data.name || ""}
                        onChange={(e) => onChange("name", e.target.value)}
                        placeholder="Enter your full name"
                    />
                </div>

                <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                        id="email"
                        type="email"
                        value={data.email || ""}
                        onChange={(e) => onChange("email", e.target.value)}
                        placeholder="your.email@example.com"
                    />
                </div>

                <div>
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                        id="phone"
                        value={data.phone || ""}
                        onChange={(e) => onChange("phone", e.target.value)}
                        placeholder="+1 (555) 123-4567"
                    />
                </div>

                <div>
                    <Label htmlFor="location">Location</Label>
                    <Input
                        id="location"
                        value={data.location || ""}
                        onChange={(e) => onChange("location", e.target.value)}
                        placeholder="City, State, Country"
                    />
                </div>
            </div>

            <div>
                <Label htmlFor="summary">Professional Summary</Label>
                <Textarea
                    id="summary"
                    value={data.summary || ""}
                    onChange={(e) => onChange("summary", e.target.value)}
                    placeholder="Brief professional summary..."
                    rows={4}
                />
            </div>
        </div>
    );
}

function SummaryEditor({ data, onChange }: EditorProps) {
    return (
        <div>
            <Label htmlFor="summary">Professional Summary</Label>
            <Textarea
                id="summary"
                value={data.summary || ""}
                onChange={(e) => onChange("summary", e.target.value)}
                placeholder="Write a compelling professional summary that highlights your key strengths and career objectives..."
                rows={8}
                className="mt-2"
            />
            <p className="text-sm text-muted-foreground mt-2">
                Aim for 3-4 sentences that capture your professional identity and value proposition.
            </p>
        </div>
    );
}

function ExperienceEditor({ data, onChange, onArrayChange, onAddItem, onRemoveItem }: EditorProps) {
    const experiences = data.experience || [];

    return (
        <div className="space-y-6">
            {experiences.map((exp: any, index: number) => (
                <Card key={index} className="border-l-4 border-l-primary">
                    <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-4">
                            <h4 className="font-medium">Experience #{index + 1}</h4>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onRemoveItem?.("experience", index)}
                                className="text-destructive"
                            >
                                Remove
                            </Button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                                <Label>Job Title</Label>
                                <Input
                                    value={exp.title || ""}
                                    onChange={(e) => onArrayChange?.("experience", index, { ...exp, title: e.target.value })}
                                    placeholder="Software Engineer"
                                />
                            </div>

                            <div>
                                <Label>Company</Label>
                                <Input
                                    value={exp.company || ""}
                                    onChange={(e) => onArrayChange?.("experience", index, { ...exp, company: e.target.value })}
                                    placeholder="Company Name"
                                />
                            </div>

                            <div>
                                <Label>Duration</Label>
                                <Input
                                    value={exp.duration || ""}
                                    onChange={(e) => onArrayChange?.("experience", index, { ...exp, duration: e.target.value })}
                                    placeholder="Jan 2020 - Present"
                                />
                            </div>

                            <div>
                                <Label>Location</Label>
                                <Input
                                    value={exp.location || ""}
                                    onChange={(e) => onArrayChange?.("experience", index, { ...exp, location: e.target.value })}
                                    placeholder="City, State"
                                />
                            </div>
                        </div>

                        <div className="mb-4">
                            <Label>Description</Label>
                            <Textarea
                                value={exp.description || ""}
                                onChange={(e) => onArrayChange?.("experience", index, { ...exp, description: e.target.value })}
                                placeholder="Brief description of your role and responsibilities..."
                                rows={3}
                            />
                        </div>

                        <div>
                            <Label>Key Achievements</Label>
                            <Textarea
                                value={exp.achievements?.join("\n") || ""}
                                onChange={(e) => onArrayChange?.("experience", index, {
                                    ...exp,
                                    achievements: e.target.value.split("\n").filter(a => a.trim())
                                })}
                                placeholder="• Achievement 1&#10;• Achievement 2&#10;• Achievement 3"
                                rows={4}
                            />
                            <p className="text-sm text-muted-foreground mt-1">
                                Enter each achievement on a new line, starting with •
                            </p>
                        </div>
                    </CardContent>
                </Card>
            ))}

            <Button
                variant="outline"
                onClick={() => onAddItem?.("experience", {
                    title: "",
                    company: "",
                    duration: "",
                    location: "",
                    description: "",
                    achievements: []
                })}
                className="w-full"
            >
                Add Experience
            </Button>
        </div>
    );
}

function SkillsEditor({ data, onChange }: EditorProps) {
    return (
        <div className="space-y-4">
            <div>
                <Label htmlFor="technical">Technical Skills</Label>
                <Textarea
                    id="technical"
                    value={data.technical?.join(", ") || ""}
                    onChange={(e) => onChange("technical", e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean))}
                    placeholder="JavaScript, Python, React, Node.js, SQL..."
                    rows={3}
                />
                <p className="text-sm text-muted-foreground mt-1">
                    Separate skills with commas
                </p>
            </div>

            <div>
                <Label htmlFor="soft">Soft Skills</Label>
                <Textarea
                    id="soft"
                    value={data.soft?.join(", ") || ""}
                    onChange={(e) => onChange("soft", e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean))}
                    placeholder="Leadership, Communication, Problem Solving..."
                    rows={3}
                />
            </div>

            <div>
                <Label htmlFor="languages">Languages</Label>
                <Textarea
                    id="languages"
                    value={data.languages?.join(", ") || ""}
                    onChange={(e) => onChange("languages", e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean))}
                    placeholder="English (Native), Spanish (Fluent), French (Conversational)..."
                    rows={2}
                />
            </div>
        </div>
    );
}

function EducationEditor({ data, onChange, onArrayChange, onAddItem, onRemoveItem }: EditorProps) {
    const education = data.education || [];

    return (
        <div className="space-y-6">
            {education.map((edu: any, index: number) => (
                <Card key={index} className="border-l-4 border-l-primary">
                    <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-4">
                            <h4 className="font-medium">Education #{index + 1}</h4>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onRemoveItem?.("education", index)}
                                className="text-destructive"
                            >
                                Remove
                            </Button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label>Degree</Label>
                                <Input
                                    value={edu.degree || ""}
                                    onChange={(e) => onArrayChange?.("education", index, { ...edu, degree: e.target.value })}
                                    placeholder="Bachelor of Science in Computer Science"
                                />
                            </div>

                            <div>
                                <Label>Institution</Label>
                                <Input
                                    value={edu.institution || ""}
                                    onChange={(e) => onArrayChange?.("education", index, { ...edu, institution: e.target.value })}
                                    placeholder="University Name"
                                />
                            </div>

                            <div>
                                <Label>Year</Label>
                                <Input
                                    value={edu.year || ""}
                                    onChange={(e) => onArrayChange?.("education", index, { ...edu, year: e.target.value })}
                                    placeholder="2020"
                                />
                            </div>

                            <div>
                                <Label>GPA (Optional)</Label>
                                <Input
                                    value={edu.gpa || ""}
                                    onChange={(e) => onArrayChange?.("education", index, { ...edu, gpa: e.target.value })}
                                    placeholder="3.8/4.0"
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}

            <Button
                variant="outline"
                onClick={() => onAddItem?.("education", {
                    degree: "",
                    institution: "",
                    year: "",
                    gpa: ""
                })}
                className="w-full"
            >
                Add Education
            </Button>
        </div>
    );
}

function GenericEditor({ data, onChange }: EditorProps) {
    return (
        <div>
            <Label htmlFor="content">Content</Label>
            <Textarea
                id="content"
                value={JSON.stringify(data, null, 2)}
                onChange={(e) => {
                    try {
                        const parsed = JSON.parse(e.target.value);
                        onChange("content", parsed);
                    } catch {
                        // Invalid JSON, don't update
                    }
                }}
                rows={10}
                className="font-mono text-sm"
            />
        </div>
    );
}

interface SectionPreviewProps {
    section: string;
    data: any;
}

function SectionPreview({ section, data }: SectionPreviewProps) {
    // This would render a formatted preview of the section
    // For now, just show the JSON structure
    return (
        <div className="bg-muted/50 rounded-lg p-4">
            <pre className="text-sm overflow-auto">
                {JSON.stringify(data, null, 2)}
            </pre>
        </div>
    );
}