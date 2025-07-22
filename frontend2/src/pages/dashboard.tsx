import { useState } from "react";
import Sidebar from "@/components/sidebar";
import FileUpload from "@/components/file-upload";
import LLMConfig from "@/components/llm-config";
import ResumeAnalysis from "@/components/resume-analysis";
import AISuggestions from "@/components/ai-suggestions";
import TemplateSelector from "@/components/template-selector";
import ResumePreview from "@/components/resume-preview";
import DownloadOptions from "@/components/download-options";
import JobAnalysisInterface from "@/components/job-analysis/job-analysis-interface";
import { VersionManager, VersionCompare } from "@/components/versions";
import SystemStatusComponent from "@/components/system-status";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { HelpCircle, Activity } from "lucide-react";

export type Step = "llm-config" | "upload" | "parsing" | "job-analysis" | "suggestions" | "templates" | "versions" | "download" | "system-status";

export default function Dashboard() {
  const [activeStep, setActiveStep] = useState<Step>("llm-config");
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [progress, setProgress] = useState(1);

  const steps: { id: Step; label: string }[] = [
    { id: "llm-config", label: "LLM Configuration" },
    { id: "upload", label: "Upload Resume" },
    { id: "parsing", label: "Resume Analysis" },
    { id: "job-analysis", label: "Job Analysis" },
    { id: "suggestions", label: "AI Suggestions" },
    { id: "templates", label: "Templates" },
    { id: "versions", label: "Version Management" },
    { id: "download", label: "Download" },
    { id: "system-status", label: "System Status" },
  ];

  const currentStepIndex = steps.findIndex(step => step.id === activeStep);
  const progressPercentage = ((currentStepIndex + 1) / steps.length) * 100;

  const handleStepChange = (step: Step) => {
    setActiveStep(step);
    setProgress(steps.findIndex(s => s.id === step) + 1);
  };

  const handleResumeUploaded = (id: number) => {
    setResumeId(id);
    setActiveStep("parsing");
    setProgress(3);
  };

  const renderCurrentStep = () => {
    switch (activeStep) {
      case "llm-config":
        return <LLMConfig onNext={() => handleStepChange("upload")} onBack={() => handleStepChange("llm-config")} />;
      case "upload":
        return <FileUpload onResumeUploaded={handleResumeUploaded} onNext={() => handleStepChange("parsing")} />;
      case "parsing":
        return resumeId ? (
          <ResumeAnalysis
            resumeId={resumeId}
            onNext={() => handleStepChange("job-analysis")}
            onBack={() => handleStepChange("llm-config")}
          />
        ) : null;
      case "job-analysis":
        return resumeId ? (
          <JobAnalysisInterface
            resumeId={resumeId.toString()}
          />
        ) : null;
      case "suggestions":
        return resumeId ? (
          <AISuggestions
            resumeId={resumeId}
            onNext={() => handleStepChange("templates")}
            onBack={() => handleStepChange("job-analysis")}
          />
        ) : null;
      case "templates":
        return resumeId ? (
          <TemplateSelector
            resumeId={resumeId}
            onNext={() => handleStepChange("versions")}
            onBack={() => handleStepChange("suggestions")}
          />
        ) : null;
      case "versions":
        return (
          <VersionManager
            userId="user-1" // TODO: Replace with actual user ID from auth context
            resumeId={resumeId?.toString()}
          />
        );
      case "download":
        return resumeId ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ResumePreview resumeId={resumeId} />
            <DownloadOptions resumeId={resumeId} onBack={() => handleStepChange("versions")} />
          </div>
        ) : null;
      case "system-status":
        return <SystemStatusComponent showDetailed={true} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      <Sidebar activeStep={activeStep} onStepChange={handleStepChange} />

      <div className="flex-1 ml-64">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-800">Resume Analysis Dashboard</h2>
              <p className="text-slate-600 mt-1">Upload and optimize your resume with AI-powered insights</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 bg-slate-100 rounded-full px-4 py-2">
                <div className="w-2 h-2 bg-primary rounded-full"></div>
                <span className="text-sm font-medium text-slate-700">
                  Step {progress} of {steps.length - 1}
                </span>
              </div>
              <SystemStatusComponent showDetailed={false} />
              <Button variant="outline" size="sm" onClick={() => handleStepChange("system-status")}>
                <Activity className="w-4 h-4 mr-2" />
                Status
              </Button>
              <Button variant="outline" size="sm">
                <HelpCircle className="w-4 h-4 mr-2" />
                Help
              </Button>
            </div>
          </div>
          <div className="mt-4">
            <Progress value={progressPercentage} className="w-full" />
          </div>
        </header>

        {/* Content */}
        <main className="p-8">
          {renderCurrentStep()}
        </main>
      </div>
    </div>
  );
}
