import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Briefcase,
  Upload,
  BarChart3,
  GitCompare,
  Plus,
  FileText,
  Target
} from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import JobUpload from "./job-upload";
import JobAnalyzer from "./job-analyzer";
import JobComparison from "./job-comparison";

interface JobDescription {
  id: string;
  title: string;
  company: string;
  content: string;
  source: "manual" | "file" | "url";
  createdAt: Date;
  wordCount: number;
  isAnalyzed: boolean;
}

interface JobAnalysisInterfaceProps {
  resumeId: string;
}

export default function JobAnalysisInterface({ resumeId }: JobAnalysisInterfaceProps) {
  const [activeTab, setActiveTab] = useState("upload");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [comparisonJobIds, setComparisonJobIds] = useState<string[]>([]);

  // Fetch uploaded job descriptions
  const { data: jobDescriptions, isLoading } = useQuery({
    queryKey: ["job-descriptions", resumeId],
    queryFn: async (): Promise<JobDescription[]> => {
      const response = await apiRequest("GET", `/resume/${resumeId}/job-descriptions`);
      return response.json();
    },
  });

  const handleJobUploaded = (job: JobDescription) => {
    // Automatically switch to analysis tab and select the new job
    setSelectedJobId(job.id);
    setActiveTab("analysis");
  };

  const handleJobsChanged = (jobs: JobDescription[]) => {
    // Update comparison selection if needed
    const validIds = jobs.map(j => j.id);
    setComparisonJobIds(prev => prev.filter(id => validIds.includes(id)));
  };

  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId);
    setActiveTab("analysis");
  };

  const handleComparisonToggle = (jobId: string, selected: boolean) => {
    if (selected) {
      setComparisonJobIds(prev => [...prev, jobId]);
    } else {
      setComparisonJobIds(prev => prev.filter(id => id !== jobId));
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <Briefcase className="w-12 h-12 mx-auto mb-4 text-muted-foreground animate-pulse" />
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Loading Job Analysis</h2>
          <p className="text-muted-foreground">Setting up your job analysis workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-slate-800 mb-2">Job Description Analysis</h2>
        <p className="text-lg text-muted-foreground">
          Upload job descriptions and get AI-powered matching recommendations for your resume
        </p>
      </div>

      {/* Main Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex items-center justify-between mb-6">
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload
            </TabsTrigger>
            <TabsTrigger value="analysis" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Analysis
            </TabsTrigger>
            <TabsTrigger value="comparison" className="flex items-center gap-2">
              <GitCompare className="w-4 h-4" />
              Compare
            </TabsTrigger>
          </TabsList>

          {jobDescriptions && jobDescriptions.length > 0 && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="flex items-center gap-1">
                <FileText className="w-3 h-3" />
                {jobDescriptions.length} job{jobDescriptions.length !== 1 ? 's' : ''}
              </Badge>
              {jobDescriptions.filter(j => j.isAnalyzed).length > 0 && (
                <Badge variant="default" className="bg-green-100 text-green-800 flex items-center gap-1">
                  <Target className="w-3 h-3" />
                  {jobDescriptions.filter(j => j.isAnalyzed).length} analyzed
                </Badge>
              )}
            </div>
          )}
        </div>

        <TabsContent value="upload" className="mt-6">
          <JobUpload
            resumeId={resumeId}
            onJobUploaded={handleJobUploaded}
            onJobsChanged={handleJobsChanged}
          />
        </TabsContent>

        <TabsContent value="analysis" className="mt-6">
          {selectedJobId ? (
            <JobAnalyzer
              resumeId={resumeId}
              jobDescriptionId={selectedJobId}
              onAnalysisComplete={(analysis, match) => {
                // Could trigger notifications or updates here
                console.log('Analysis complete:', { analysis, match });
              }}
            />
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-xl font-semibold text-slate-800 mb-2">
                  Select a Job to Analyze
                </h3>
                <p className="text-muted-foreground mb-6">
                  Choose a job description from your uploads to see detailed analysis and matching recommendations.
                </p>
                {jobDescriptions && jobDescriptions.length > 0 ? (
                  <div className="space-y-3 max-w-md mx-auto">
                    {jobDescriptions.map((job) => (
                      <Button
                        key={job.id}
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => handleJobSelect(job.id)}
                      >
                        <div className="flex items-center gap-3">
                          <Briefcase className="w-4 h-4" />
                          <div className="text-left">
                            <div className="font-medium">{job.title}</div>
                            <div className="text-sm text-muted-foreground">{job.company}</div>
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                ) : (
                  <Button onClick={() => setActiveTab("upload")} className="mt-4">
                    <Plus className="w-4 h-4 mr-2" />
                    Upload Your First Job Description
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="comparison" className="mt-6">
          {jobDescriptions && jobDescriptions.length >= 2 ? (
            <div className="space-y-6">
              {/* Job Selection for Comparison */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GitCompare className="w-5 h-5 text-primary" />
                    Select Jobs to Compare
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {jobDescriptions.map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50"
                      >
                        <input
                          type="checkbox"
                          id={`job-${job.id}`}
                          checked={comparisonJobIds.includes(job.id)}
                          onChange={(e) => handleComparisonToggle(job.id, e.target.checked)}
                          className="rounded"
                        />
                        <label htmlFor={`job-${job.id}`} className="flex-1 cursor-pointer">
                          <div className="font-medium text-sm">{job.title}</div>
                          <div className="text-xs text-muted-foreground">{job.company}</div>
                        </label>
                        {job.isAnalyzed && (
                          <Badge variant="outline" className="text-xs bg-green-50 text-green-800">
                            Analyzed
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                  {comparisonJobIds.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                      <Badge variant="secondary">
                        {comparisonJobIds.length} job{comparisonJobIds.length !== 1 ? 's' : ''} selected for comparison
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Comparison Results */}
              <JobComparison
                resumeId={resumeId}
                jobIds={comparisonJobIds}
                onJobSelect={handleJobSelect}
              />
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <GitCompare className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="text-xl font-semibold text-slate-800 mb-2">
                  Upload More Jobs to Compare
                </h3>
                <p className="text-muted-foreground mb-6">
                  You need at least 2 job descriptions to use the comparison feature.
                </p>
                <Button onClick={() => setActiveTab("upload")}>
                  <Plus className="w-4 h-4 mr-2" />
                  Upload More Job Descriptions
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}