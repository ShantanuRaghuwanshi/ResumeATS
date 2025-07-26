import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ArrowRight, Eye } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn, getApiUrl, fetchWithSession } from "@/lib/utils";

interface TemplateSelectorProps {
  resumeId: number;
  onNext: () => void;
  onBack: () => void;
}

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  preview: JSX.Element;
}

export default function TemplateSelector({ resumeId, onNext, onBack }: TemplateSelectorProps) {
  // Fetch resume sections
  const { data: resume, isLoading } = useQuery({
    queryKey: ["/resume_sections/"],
    queryFn: async () => {
      const res = await fetchWithSession("/api/v1/resume_sections/");
      if (!res.ok) throw new Error("Failed to fetch resume sections");
      return res.json();
    },
    enabled: !!resumeId,
  });
  const [selectedTemplate, setSelectedTemplate] = useState<string>("modern");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const templates: Template[] = [
    {
      id: "modern",
      name: "Modern Professional",
      description: "Clean and contemporary design perfect for tech roles",
      category: "ATS Friendly",
      preview: (
        <div className="aspect-[8.5/11] bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg p-4 text-xs leading-relaxed overflow-hidden">
          <div className="space-y-2">
            <div className="h-3 bg-slate-800 w-2/3 rounded"></div>
            <div className="h-2 bg-slate-600 w-1/2 rounded"></div>
            <div className="h-px bg-slate-300 my-3"></div>
            <div className="space-y-1">
              <div className="h-2 bg-slate-400 w-full rounded"></div>
              <div className="h-2 bg-slate-400 w-4/5 rounded"></div>
              <div className="h-2 bg-slate-400 w-3/4 rounded"></div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "creative",
      name: "Creative Design",
      description: "Eye-catching layout for creative professionals",
      category: "Visual Impact",
      preview: (
        <div className="aspect-[8.5/11] bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg p-4 text-xs leading-relaxed overflow-hidden">
          <div className="space-y-2">
            <div className="h-3 bg-purple-800 w-2/3 rounded"></div>
            <div className="h-2 bg-purple-600 w-1/2 rounded"></div>
            <div className="h-px bg-purple-300 my-3"></div>
            <div className="grid grid-cols-3 gap-1">
              <div className="h-2 bg-purple-400 rounded"></div>
              <div className="h-2 bg-purple-400 rounded"></div>
              <div className="h-2 bg-purple-400 rounded"></div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "executive",
      name: "Executive Classic",
      description: "Traditional and professional for senior roles",
      category: "Traditional",
      preview: (
        <div className="aspect-[8.5/11] bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg p-4 text-xs leading-relaxed overflow-hidden">
          <div className="space-y-2">
            <div className="h-3 bg-gray-800 w-2/3 rounded"></div>
            <div className="h-2 bg-gray-600 w-1/2 rounded"></div>
            <div className="h-px bg-gray-300 my-3"></div>
            <div className="space-y-1">
              <div className="h-2 bg-gray-400 w-full rounded"></div>
              <div className="h-2 bg-gray-400 w-5/6 rounded"></div>
            </div>
          </div>
        </div>
      ),
    },
  ];

  const applyTemplateMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const apiUrl = getApiUrl();
      const response = await apiRequest("POST", `${apiUrl}/resume/${resumeId}/template`, {
        templateId,
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/resume", resumeId] });
      toast({
        title: "Template applied",
        description: "Your resume template has been updated successfully.",
      });
      onNext();
    },
    onError: (error) => {
      toast({
        title: "Failed to apply template",
        description: error.message || "An error occurred while applying the template.",
        variant: "destructive",
      });
    },
  });

  const handleApplyTemplate = () => {
    applyTemplateMutation.mutate(selectedTemplate);
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "ATS Friendly":
        return "bg-green-100 text-green-800";
      case "Visual Impact":
        return "bg-blue-100 text-blue-800";
      case "Traditional":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-slate-100 text-slate-800";
    }
  };

  return (
    <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
      <CardContent className="p-8">
        <h3 className="text-2xl font-bold text-slate-800 mb-6">Choose Resume Template</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <div
              key={template.id}
              onClick={() => setSelectedTemplate(template.id)}
              className={cn(
                "border-2 rounded-xl p-4 cursor-pointer transition-all group",
                selectedTemplate === template.id
                  ? "border-primary bg-primary/5"
                  : "border-slate-200 hover:border-primary"
              )}
            >
              {template.preview}

              <div className="mt-4">
                <h4 className="font-semibold text-slate-800 mb-2">{template.name}</h4>
                <p className="text-sm text-slate-600 mb-3">{template.description}</p>

                <div className="flex items-center justify-between">
                  <Badge className={getCategoryColor(template.category)}>
                    {template.category}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-primary hover:text-blue-600 font-medium group-hover:underline"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Preview functionality can be added here
                      toast({
                        title: "Preview",
                        description: `Previewing ${template.name} template`,
                      });
                    }}
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    Preview
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-between mt-8">
          <Button variant="outline" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Analysis
          </Button>
          <Button
            onClick={handleApplyTemplate}
            className="bg-primary text-white hover:bg-blue-600"
            disabled={applyTemplateMutation.isPending}
          >
            {applyTemplateMutation.isPending ? "Applying..." : "Apply Template"}
            {!applyTemplateMutation.isPending && <ArrowRight className="w-4 h-4 ml-2" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
