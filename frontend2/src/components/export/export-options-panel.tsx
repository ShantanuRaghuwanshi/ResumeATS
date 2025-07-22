import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
    FileText,
    FileImage,
    File,
    Download,
    Palette,
    Type,
    Layout,
    Loader2,
    CheckCircle,
    AlertCircle
} from "lucide-react";

interface ExportFormat {
    name: string;
    extension: string;
    mime_type: string;
    description: string;
    supports_templates: boolean;
    supports_styling: boolean;
    ats_friendly: boolean;
}

interface ExportTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    industry: string;
    experience_level: string;
    preview_url: string;
    customizable_sections: string[];
    styling_options: {
        color_scheme: string[];
        font_family: string[];
        spacing: string[];
    };
}

interface ExportOptions {
    filename: string;
    include_metadata: boolean;
    ats_optimized: boolean;
    custom_styling: Record<string, any>;
    sections_to_include: string[];
    apply_optimizations: boolean;
}

interface ExportOptionsPanelProps {
    formats: ExportFormat[];
    templates: ExportTemplate[];
    selectedFormat: string;
    selectedTemplate: string;
    exportOptions: ExportOptions;
    onFormatChange: (format: string) => void;
    onTemplateChange: (template: string) => void;
    onOptionsChange: (options: ExportOptions) => void;
    onExport: () => void;
    isExporting: boolean;
}

const formatIcons: Record<string, React.ElementType> = {
    docx: FileText,
    pdf: FileImage,
    txt: File,
    json: File,
    html: FileText,
};

const availableSections = [
    { id: "personal_details", label: "Personal Details" },
    { id: "summary", label: "Summary" },
    { id: "work_experience", label: "Work Experience" },
    { id: "education", label: "Education" },
    { id: "skills", label: "Skills" },
    { id: "projects", label: "Projects" },
    { id: "certifications", label: "Certifications" },
    { id: "awards", label: "Awards" },
];

export function ExportOptionsPanel({
    formats,
    templates,
    selectedFormat,
    selectedTemplate,
    exportOptions,
    onFormatChange,
    onTemplateChange,
    onOptionsChange,
    onExport,
    isExporting
}: ExportOptionsPanelProps) {
    const [customStyling, setCustomStyling] = useState({
        color_scheme: "",
        font_family: "",
        spacing: "",
        primary_color: "",
        font_size: "",
        background_color: ""
    });

    const selectedFormatData = formats.find(f => f.extension === selectedFormat);
    const selectedTemplateData = templates.find(t => t.id === selectedTemplate);

    const updateExportOptions = (updates: Partial<ExportOptions>) => {
        onOptionsChange({ ...exportOptions, ...updates });
    };

    const updateCustomStyling = (key: string, value: string) => {
        const newStyling = { ...customStyling, [key]: value };
        setCustomStyling(newStyling);
        updateExportOptions({
            custom_styling: { ...exportOptions.custom_styling, ...newStyling }
        });
    };

    const toggleSection = (sectionId: string) => {
        const currentSections = exportOptions.sections_to_include;
        const newSections = currentSections.includes(sectionId)
            ? currentSections.filter(id => id !== sectionId)
            : [...currentSections, sectionId];

        updateExportOptions({ sections_to_include: newSections });
    };

    return (
        <div className="space-y-6">
            {/* Format Selection */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                        <FileText className="w-5 h-5" />
                        <span>Export Format</span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {formats.map((format) => {
                            const Icon = formatIcons[format.extension] || File;
                            const isSelected = selectedFormat === format.extension;

                            return (
                                <div
                                    key={format.extension}
                                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${isSelected
                                            ? "border-primary bg-primary/5"
                                            : "border-slate-200 hover:border-slate-300"
                                        }`}
                                    onClick={() => onFormatChange(format.extension)}
                                >
                                    <div className="flex items-start space-x-3">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isSelected ? "bg-primary text-white" : "bg-slate-100 text-slate-600"
                                            }`}>
                                            <Icon className="w-5 h-5" />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-semibold text-slate-800">{format.name}</h4>
                                            <p className="text-sm text-slate-600 mb-2">{format.description}</p>
                                            <div className="flex flex-wrap gap-1">
                                                {format.ats_friendly && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        <CheckCircle className="w-3 h-3 mr-1" />
                                                        ATS Friendly
                                                    </Badge>
                                                )}
                                                {format.supports_templates && (
                                                    <Badge variant="outline" className="text-xs">
                                                        Templates
                                                    </Badge>
                                                )}
                                                {format.supports_styling && (
                                                    <Badge variant="outline" className="text-xs">
                                                        Styling
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>

            {/* Template Selection */}
            {selectedFormatData?.supports_templates && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center space-x-2">
                            <Layout className="w-5 h-5" />
                            <span>Template Selection</span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {templates.map((template) => {
                                const isSelected = selectedTemplate === template.id;

                                return (
                                    <div
                                        key={template.id}
                                        className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${isSelected
                                                ? "border-primary bg-primary/5"
                                                : "border-slate-200 hover:border-slate-300"
                                            }`}
                                        onClick={() => onTemplateChange(template.id)}
                                    >
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <h4 className="font-semibold text-slate-800">{template.name}</h4>
                                                <Badge variant="outline" className="text-xs">
                                                    {template.category}
                                                </Badge>
                                            </div>
                                            <p className="text-sm text-slate-600">{template.description}</p>
                                            <div className="flex flex-wrap gap-1">
                                                <Badge variant="secondary" className="text-xs">
                                                    {template.industry}
                                                </Badge>
                                                <Badge variant="secondary" className="text-xs">
                                                    {template.experience_level}
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Export Options */}
            <Card>
                <CardHeader>
                    <CardTitle>Export Options</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Filename */}
                    <div className="space-y-2">
                        <Label htmlFor="filename">Filename</Label>
                        <Input
                            id="filename"
                            placeholder="Enter filename (without extension)"
                            value={exportOptions.filename}
                            onChange={(e) => updateExportOptions({ filename: e.target.value })}
                        />
                    </div>

                    {/* Basic Options */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Include Metadata</Label>
                                <p className="text-sm text-slate-600">
                                    Include export information and timestamps
                                </p>
                            </div>
                            <Switch
                                checked={exportOptions.include_metadata}
                                onCheckedChange={(checked) => updateExportOptions({ include_metadata: checked })}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>ATS Optimized</Label>
                                <p className="text-sm text-slate-600">
                                    Optimize formatting for Applicant Tracking Systems
                                </p>
                            </div>
                            <Switch
                                checked={exportOptions.ats_optimized}
                                onCheckedChange={(checked) => updateExportOptions({ ats_optimized: checked })}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label>Apply AI Optimizations</Label>
                                <p className="text-sm text-slate-600">
                                    Include AI-generated improvements and suggestions
                                </p>
                            </div>
                            <Switch
                                checked={exportOptions.apply_optimizations}
                                onCheckedChange={(checked) => updateExportOptions({ apply_optimizations: checked })}
                            />
                        </div>
                    </div>

                    <Separator />

                    {/* Section Selection */}
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Sections to Include</Label>
                            <p className="text-sm text-slate-600">
                                Leave empty to include all sections
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            {availableSections.map((section) => (
                                <div key={section.id} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={section.id}
                                        checked={exportOptions.sections_to_include.includes(section.id)}
                                        onCheckedChange={() => toggleSection(section.id)}
                                    />
                                    <Label htmlFor={section.id} className="text-sm">
                                        {section.label}
                                    </Label>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Custom Styling */}
                    {selectedFormatData?.supports_styling && selectedTemplateData && (
                        <>
                            <Separator />
                            <div className="space-y-4">
                                <div className="flex items-center space-x-2">
                                    <Palette className="w-5 h-5" />
                                    <Label className="text-base font-semibold">Custom Styling</Label>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Color Scheme */}
                                    {selectedTemplateData.styling_options.color_scheme.length > 0 && (
                                        <div className="space-y-2">
                                            <Label>Color Scheme</Label>
                                            <Select
                                                value={customStyling.color_scheme}
                                                onValueChange={(value) => updateCustomStyling("color_scheme", value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select color scheme" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {selectedTemplateData.styling_options.color_scheme.map((color) => (
                                                        <SelectItem key={color} value={color}>
                                                            {color.charAt(0).toUpperCase() + color.slice(1)}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    )}

                                    {/* Font Family */}
                                    {selectedTemplateData.styling_options.font_family.length > 0 && (
                                        <div className="space-y-2">
                                            <Label>Font Family</Label>
                                            <Select
                                                value={customStyling.font_family}
                                                onValueChange={(value) => updateCustomStyling("font_family", value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select font family" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {selectedTemplateData.styling_options.font_family.map((font) => (
                                                        <SelectItem key={font} value={font}>
                                                            {font}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    )}

                                    {/* Spacing */}
                                    {selectedTemplateData.styling_options.spacing.length > 0 && (
                                        <div className="space-y-2">
                                            <Label>Spacing</Label>
                                            <Select
                                                value={customStyling.spacing}
                                                onValueChange={(value) => updateCustomStyling("spacing", value)}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select spacing" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {selectedTemplateData.styling_options.spacing.map((spacing) => (
                                                        <SelectItem key={spacing} value={spacing}>
                                                            {spacing.charAt(0).toUpperCase() + spacing.slice(1)}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    )}

                                    {/* Custom Primary Color */}
                                    <div className="space-y-2">
                                        <Label>Primary Color</Label>
                                        <Input
                                            type="color"
                                            value={customStyling.primary_color}
                                            onChange={(e) => updateCustomStyling("primary_color", e.target.value)}
                                            className="h-10 w-full"
                                        />
                                    </div>

                                    {/* Font Size */}
                                    <div className="space-y-2">
                                        <Label>Font Size</Label>
                                        <Select
                                            value={customStyling.font_size}
                                            onValueChange={(value) => updateCustomStyling("font_size", value)}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select font size" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="small">Small (10pt)</SelectItem>
                                                <SelectItem value="medium">Medium (11pt)</SelectItem>
                                                <SelectItem value="large">Large (12pt)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Background Color */}
                                    <div className="space-y-2">
                                        <Label>Background Color</Label>
                                        <Input
                                            type="color"
                                            value={customStyling.background_color}
                                            onChange={(e) => updateCustomStyling("background_color", e.target.value)}
                                            className="h-10 w-full"
                                        />
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Export Button */}
            <Card>
                <CardContent className="p-6">
                    <Button
                        onClick={onExport}
                        disabled={isExporting}
                        className="w-full h-12 text-lg"
                        size="lg"
                    >
                        {isExporting ? (
                            <>
                                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                Generating Export...
                            </>
                        ) : (
                            <>
                                <Download className="w-5 h-5 mr-2" />
                                Export Resume
                            </>
                        )}
                    </Button>

                    {exportOptions.ats_optimized && (
                        <div className="flex items-center justify-center mt-3 text-sm text-slate-600">
                            <CheckCircle className="w-4 h-4 mr-1 text-green-600" />
                            ATS optimization enabled
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}