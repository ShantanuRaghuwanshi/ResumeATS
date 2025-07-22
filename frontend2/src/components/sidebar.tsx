import { cn } from "@/lib/utils";
import { FileUp, Settings, Search, Lightbulb, Palette, Download, Briefcase, GitBranch } from "lucide-react";
import type { Step } from "@/pages/dashboard";

interface SidebarProps {
  activeStep: Step;
  onStepChange: (step: Step) => void;
}

export default function Sidebar({ activeStep, onStepChange }: SidebarProps) {
  const steps = [
    { id: "llm-config" as Step, label: "LLM Configuration", icon: Settings },
    { id: "upload" as Step, label: "Upload Resume", icon: FileUp },
    { id: "parsing" as Step, label: "Resume Analysis", icon: Search },
    { id: "job-analysis" as Step, label: "Job Analysis", icon: Briefcase },
    { id: "suggestions" as Step, label: "AI Suggestions", icon: Lightbulb },
    { id: "templates" as Step, label: "Templates", icon: Palette },
    { id: "versions" as Step, label: "Version Management", icon: GitBranch },
    { id: "download" as Step, label: "Download", icon: Download },
  ];

  return (
    <div className="w-64 bg-white shadow-sm border-r border-slate-200 fixed h-full z-10">
      <div className="p-6">
        <div className="flex items-center space-x-3 mb-8">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <FileUp className="text-white text-sm" />
          </div>
          <h1 className="text-xl font-bold text-slate-800">ResumeAI</h1>
        </div>

        <nav className="space-y-2">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = activeStep === step.id;

            return (
              <button
                key={step.id}
                onClick={() => onStepChange(step.id)}
                className={cn(
                  "flex items-center space-x-3 px-3 py-2 rounded-lg w-full text-left transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-slate-600 hover:bg-slate-100"
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{step.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
