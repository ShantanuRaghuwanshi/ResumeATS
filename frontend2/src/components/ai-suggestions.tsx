import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ArrowRight, AlertTriangle, Info, CheckCircle } from "lucide-react";
import type { Resume, AnalysisResult } from "@/shared/schema";
import { cn, getApiUrl } from "@/lib/utils";

interface AISuggestionsProps {
  resumeId: number;
  onNext: () => void;
  onBack: () => void;
}

export default function AISuggestions({ resumeId, onNext, onBack }: AISuggestionsProps) {
  // Fetch resume sections
  const { data: resume, isLoading } = useQuery({
    queryKey: ["/resume_sections/"],
    queryFn: async () => {
      const apiUrl = getApiUrl();
      const res = await fetch(`${apiUrl}/resume_sections/`);
      if (!res.ok) throw new Error("Failed to fetch resume sections");
      return res.json();
    },
    enabled: !!resumeId,
  });

  if (isLoading || !resume) {
    return (
      <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
        <CardContent className="p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-32 bg-slate-200 rounded"></div>
            <div className="h-32 bg-slate-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const analysisResults = resume.analysisResults as AnalysisResult | null;

  if (!analysisResults) {
    return (
      <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
        <CardContent className="p-8">
          <h3 className="text-2xl font-bold text-slate-800 mb-4">AI Suggestions</h3>
          <p className="text-slate-600">No analysis results available. Please go back and analyze your resume first.</p>
          <div className="flex justify-between mt-8">
            <Button variant="outline" onClick={onBack}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Analysis
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const groupedSuggestions = {
    warning: analysisResults.suggestions?.filter(s => s.type === "warning") || [],
    info: analysisResults.suggestions?.filter(s => s.type === "info") || [],
    success: analysisResults.suggestions?.filter(s => s.type === "success") || [],
  };

  const getSectionIcon = (type: string) => {
    switch (type) {
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case "info":
        return <Info className="w-5 h-5 text-blue-600" />;
      case "success":
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      default:
        return <Info className="w-5 h-5 text-blue-600" />;
    }
  };

  const getSectionTitle = (type: string) => {
    switch (type) {
      case "warning":
        return "Critical Improvements";
      case "info":
        return "Enhancement Opportunities";
      case "success":
        return "Strengths";
      default:
        return "Suggestions";
    }
  };

  const getSectionColor = (type: string) => {
    switch (type) {
      case "warning":
        return "bg-yellow-50 border-yellow-200";
      case "info":
        return "bg-blue-50 border-blue-200";
      case "success":
        return "bg-green-50 border-green-200";
      default:
        return "bg-slate-50 border-slate-200";
    }
  };

  return (
    <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
      <CardContent className="p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-2xl font-bold text-slate-800 mb-2">AI-Powered Suggestions</h3>
            <p className="text-slate-600">Review and implement these suggestions to improve your resume</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary mb-1">{analysisResults.score}</div>
            <div className="text-sm text-slate-600">Current Score</div>
          </div>
        </div>

        {/* ATS Compatibility Score */}
        {analysisResults.atsCompatibility && (
          <Card className="mb-8 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-lg font-semibold text-slate-800 mb-2">ATS Compatibility</h4>
                  <p className="text-slate-600">How well your resume will perform in Applicant Tracking Systems</p>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600 mb-1">
                    {analysisResults.atsCompatibility}%
                  </div>
                  <Badge variant={analysisResults.atsCompatibility >= 80 ? "default" : "secondary"}>
                    {analysisResults.atsCompatibility >= 80 ? "ATS Friendly" : "Needs Improvement"}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Keywords Analysis */}
        {analysisResults.keywords && analysisResults.keywords.length > 0 && (
          <Card className="mb-8">
            <CardContent className="p-6">
              <h4 className="text-lg font-semibold text-slate-800 mb-4">Important Keywords</h4>
              <div className="flex flex-wrap gap-2">
                {analysisResults.keywords.slice(0, 20).map((keyword, index) => (
                  <Badge key={index} variant="outline" className="bg-blue-50 text-blue-800 border-blue-200">
                    {keyword}
                  </Badge>
                ))}
              </div>
              <p className="text-sm text-slate-600 mt-3">
                These keywords are important for your industry. Consider incorporating missing ones into your resume.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Suggestions by Type */}
        <div className="space-y-6">
          {Object.entries(groupedSuggestions).map(([type, suggestions]) => {
            if (suggestions.length === 0) return null;

            return (
              <Card key={type} className={getSectionColor(type)}>
                <CardContent className="p-6">
                  <div className="flex items-center mb-4">
                    {getSectionIcon(type)}
                    <h4 className="text-lg font-semibold text-slate-800 ml-2">
                      {getSectionTitle(type)} ({suggestions.length})
                    </h4>
                  </div>

                  <div className="space-y-4">
                    {suggestions.map((suggestion, index) => (
                      <div key={index} className="bg-white rounded-lg p-4 border border-white/50">
                        <div className="flex items-start justify-between mb-2">
                          <h5 className="font-medium text-slate-800">{suggestion.title}</h5>
                          {suggestion.section && (
                            <Badge variant="outline" className="text-xs">
                              {suggestion.section}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-slate-600">{suggestion.description}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* No suggestions case */}
        {(!analysisResults.suggestions || analysisResults.suggestions.length === 0) && (
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
              <h4 className="text-lg font-semibold text-slate-800 mb-2">Excellent Resume!</h4>
              <p className="text-slate-600">
                Your resume looks great! No major improvements are needed at this time.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Action Summary */}
        <Card className="mt-8 bg-slate-900 text-white">
          <CardContent className="p-6">
            <h4 className="text-lg font-semibold mb-4">Summary & Next Steps</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-400 mb-1">
                  {groupedSuggestions.warning.length}
                </div>
                <div className="text-sm opacity-90">Critical Issues</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400 mb-1">
                  {groupedSuggestions.info.length}
                </div>
                <div className="text-sm opacity-90">Enhancements</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400 mb-1">
                  {groupedSuggestions.success.length}
                </div>
                <div className="text-sm opacity-90">Strengths</div>
              </div>
            </div>
            <p className="text-sm opacity-90">
              Focus on addressing critical issues first, then work on enhancements to maximize your resume's impact.
            </p>
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex justify-between mt-8">
          <Button variant="outline" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Analysis
          </Button>
          <Button onClick={onNext} className="bg-primary text-white hover:bg-blue-600">
            Continue to Templates
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
