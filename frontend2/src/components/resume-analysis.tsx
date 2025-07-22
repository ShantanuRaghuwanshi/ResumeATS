import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, ArrowRight, User, Code, Briefcase, GraduationCap, Edit, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import type { Resume, ParsedResume, AnalysisResult } from "@/shared/schema";
import { cn, getApiUrl } from "@/lib/utils";

interface ResumeAnalysisProps {
  resumeId: number;
  onNext: () => void;
  onBack: () => void;
}

export default function ResumeAnalysis({ resumeId, onNext, onBack }: ResumeAnalysisProps) {
  const [jobDescription, setJobDescription] = useState("");
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch resume data
  // Fetch resume sections
  const { data: resume, isLoading: resumeLoading } = useQuery({
    queryKey: ["/resume_sections/"],
    queryFn: async () => {
      const apiUrl = getApiUrl();
      const res = await fetch(`${apiUrl}/resume_sections/`);
      if (!res.ok) throw new Error("Failed to fetch resume sections");
      return res.json();
    },
    enabled: !!resumeId,
  });

  // Analyze resume mutation
  const analyzeResumeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", `/resume/${resumeId}/analyze`, {});
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/resume", resumeId] });
      toast({
        title: "Analysis complete",
        description: "Your resume has been analyzed successfully.",
      });
    },
    onError: (error) => {
      toast({
        title: "Analysis failed",
        description: error.message || "Failed to analyze resume.",
        variant: "destructive",
      });
    },
  });

  // Job match analysis mutation
  const jobMatchMutation = useMutation({
    mutationFn: async (jobDesc: string) => {
      const response = await apiRequest("POST", `/resume/${resumeId}/job-match`, {
        jobDescription: jobDesc,
      });
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Job match analysis complete",
        description: "Your resume has been analyzed against the job description.",
      });
    },
    onError: (error) => {
      toast({
        title: "Job match analysis failed",
        description: error.message || "Failed to analyze job match.",
        variant: "destructive",
      });
    },
  });

  // Update resume data mutation
  const updateResumeMutation = useMutation({
    mutationFn: async (updatedData: ParsedResume) => {
      const response = await apiRequest("PUT", `/resume/${resumeId}/data`, updatedData);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/resume", resumeId] });
      setEditingSection(null);
      toast({
        title: "Resume updated",
        description: "Your changes have been saved.",
      });
    },
  });

  // Auto-analyze when component mounts
  useEffect(() => {
    if (resume && !resume.analysisResults) {
      analyzeResumeMutation.mutate();
    }
  }, [resume]);

  const handleJobMatch = () => {
    if (!jobDescription.trim()) {
      toast({
        title: "Job description required",
        description: "Please enter a job description to analyze the match.",
        variant: "destructive",
      });
      return;
    }
    jobMatchMutation.mutate(jobDescription);
  };

  const renderPersonalDetails = () => {
    const personalDetails = resume?.parsedData?.personalDetails || {};

    return (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-slate-800 flex items-center">
            <User className="text-primary mr-2 w-5 h-5" />
            Personal Details
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditingSection(editingSection === "personal" ? null : "personal")}
          >
            <Edit className="w-4 h-4 mr-1" />
            {editingSection === "personal" ? "Cancel" : "Edit"}
          </Button>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-slate-600">Full Name</label>
            <p className="text-slate-800">{personalDetails.name || "Not specified"}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Email</label>
            <p className="text-slate-800">{personalDetails.email || "Not specified"}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Phone</label>
            <p className="text-slate-800">{personalDetails.phone || "Not specified"}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Location</label>
            <p className="text-slate-800">{personalDetails.location || "Not specified"}</p>
          </div>
        </div>
      </div>
    );
  };

  const renderSkills = () => {
    const skills = resume?.parsedData?.skills || {};
    const allSkills = [
      ...(skills.technical || []),
      ...(skills.soft || []),
      ...(skills.languages || [])
    ];

    return (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-slate-800 flex items-center">
            <Code className="text-primary mr-2 w-5 h-5" />
            Skills
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditingSection(editingSection === "skills" ? null : "skills")}
          >
            <Edit className="w-4 h-4 mr-1" />
            {editingSection === "skills" ? "Cancel" : "Edit"}
          </Button>
        </div>
        <div className="bg-slate-50 rounded-lg p-4">
          <div className="flex flex-wrap gap-2">
            {allSkills.map((skill, index) => (
              <Badge key={index} variant="secondary" className="bg-primary/10 text-primary">
                {skill}
              </Badge>
            ))}
            {allSkills.length === 0 && (
              <p className="text-slate-500">No skills found</p>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderExperience = () => {
    const experience = resume?.parsedData?.experience || [];

    return (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-slate-800 flex items-center">
            <Briefcase className="text-primary mr-2 w-5 h-5" />
            Work Experience
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditingSection(editingSection === "experience" ? null : "experience")}
          >
            <Edit className="w-4 h-4 mr-1" />
            {editingSection === "experience" ? "Cancel" : "Edit"}
          </Button>
        </div>
        {experience.map((exp, index) => (
          <div key={index} className="bg-slate-50 rounded-lg p-4 mb-4">
            <div className="flex justify-between items-start mb-2">
              <div>
                <h5 className="font-semibold text-slate-800">{exp.title || "Position not specified"}</h5>
                <p className="text-primary font-medium">{exp.company || "Company not specified"}</p>
              </div>
              <Badge variant="outline" className="bg-white">
                {exp.duration || "Duration not specified"}
              </Badge>
            </div>
            <p className="text-slate-700 text-sm mb-2">{exp.description || "No description available"}</p>
            {exp.achievements && exp.achievements.length > 0 && (
              <ul className="text-slate-700 text-sm space-y-1">
                {exp.achievements.map((achievement, i) => (
                  <li key={i}>• {achievement}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {experience.length === 0 && (
          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-slate-500">No work experience found</p>
          </div>
        )}
      </div>
    );
  };

  const renderEducation = () => {
    const education = resume?.parsedData?.education || [];

    return (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-slate-800 flex items-center">
            <GraduationCap className="text-primary mr-2 w-5 h-5" />
            Education
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditingSection(editingSection === "education" ? null : "education")}
          >
            <Edit className="w-4 h-4 mr-1" />
            {editingSection === "education" ? "Cancel" : "Edit"}
          </Button>
        </div>
        {education.map((edu, index) => (
          <div key={index} className="bg-slate-50 rounded-lg p-4 mb-4">
            <div className="flex justify-between items-start">
              <div>
                <h5 className="font-semibold text-slate-800">{edu.degree || "Degree not specified"}</h5>
                <p className="text-primary font-medium">{edu.institution || "Institution not specified"}</p>
              </div>
              <Badge variant="outline" className="bg-white">
                {edu.year || "Year not specified"}
              </Badge>
            </div>
          </div>
        ))}
        {education.length === 0 && (
          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-slate-500">No education found</p>
          </div>
        )}
      </div>
    );
  };

  if (resumeLoading || !resume) {
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Parsed Resume Data */}
      <div className="lg:col-span-2 space-y-6">
        <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-slate-800">Parsed Resume Data</h3>
              <Badge variant="default" className="bg-green-100 text-green-800">
                <CheckCircle className="w-4 h-4 mr-1" />
                Parsed Successfully
              </Badge>
            </div>

            {renderPersonalDetails()}
            {renderSkills()}
            {renderExperience()}
            {renderEducation()}
          </CardContent>
        </Card>
      </div>

      {/* AI Insights */}
      <div className="space-y-6">
        {/* Resume Score */}
        {analysisResults && (
          <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
            <CardContent className="p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Resume Score</h3>
              <div className="text-center">
                <div className="relative w-24 h-24 mx-auto mb-4">
                  <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-slate-200"
                      stroke="currentColor"
                      strokeWidth="3"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-green-500"
                      stroke="currentColor"
                      strokeWidth="3"
                      fill="none"
                      strokeDasharray={`${analysisResults.score}, 100`}
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-slate-800">{analysisResults.score}</span>
                  </div>
                </div>
                <p className="text-sm text-slate-600">
                  {analysisResults.score >= 80 ? "Excellent resume!" :
                    analysisResults.score >= 60 ? "Good resume with room for improvement" :
                      "Needs significant improvement"}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Suggestions */}
        {analysisResults?.suggestions && (
          <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
            <CardContent className="p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Quick Suggestions</h3>
              <div className="space-y-3">
                {analysisResults.suggestions.slice(0, 5).map((suggestion, index) => (
                  <div
                    key={index}
                    className={`flex items-start space-x-3 p-3 rounded-lg border ${suggestion.type === "warning" ? "bg-yellow-50 border-yellow-200" :
                      suggestion.type === "success" ? "bg-green-50 border-green-200" :
                        "bg-blue-50 border-blue-200"
                      }`}
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-800">{suggestion.title}</p>
                      <p className="text-xs text-slate-600">{suggestion.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Job Description Analysis */}
        <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
          <CardContent className="p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Job Description Analysis</h3>
            <Textarea
              placeholder="Paste job description here for targeted analysis..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="min-h-32 mb-4"
            />
            <Button
              onClick={handleJobMatch}
              className="w-full bg-violet-600 text-white hover:bg-violet-700"
              disabled={jobMatchMutation.isPending || !jobDescription.trim()}
            >
              {jobMatchMutation.isPending ? "Analyzing..." : "Analyze Match"}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Navigation */}
      <div className="lg:col-span-3 flex justify-between">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={onNext}
          className="bg-primary text-white hover:bg-blue-600"
          disabled={!analysisResults}
        >
          Continue to Suggestions
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}
