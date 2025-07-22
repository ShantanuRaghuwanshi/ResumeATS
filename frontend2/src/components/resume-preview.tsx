import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ZoomIn, ZoomOut } from "lucide-react";
import { useState } from "react";
import { getApiUrl } from "@/lib/utils";
import type { Resume, ParsedResume } from "@/shared/schema";

interface ResumePreviewProps {
  resumeId: number;
}

export default function ResumePreview({ resumeId }: ResumePreviewProps) {
  const [zoom, setZoom] = useState(1);

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

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.1, 2));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.1, 0.5));
  };

  if (isLoading || !resume) {
    return (
      <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-96 bg-slate-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const parsedData = resume.parsedData as ParsedResume;

  const renderResumeContent = () => {
    if (!parsedData) {
      return (
        <div className="text-center text-slate-500 py-12">
          <p>No resume data available for preview</p>
        </div>
      );
    }

    const { personalDetails, experience, education, skills, projects } = parsedData;

    return (
      <div className="space-y-6" style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
        {/* Header */}
        {personalDetails && (
          <div className="text-center border-b border-slate-200 pb-4">
            <h1 className="text-2xl font-bold text-slate-800 mb-2">
              {personalDetails.name || "Your Name"}
            </h1>
            <div className="text-slate-600 space-y-1">
              {personalDetails.email && (
                <p>{personalDetails.email}</p>
              )}
              <p>
                {[personalDetails.phone, personalDetails.location]
                  .filter(Boolean)
                  .join(" | ")}
              </p>
            </div>
          </div>
        )}

        {/* Professional Summary */}
        {personalDetails?.summary && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Professional Summary
            </h2>
            <p className="text-slate-700 leading-relaxed">{personalDetails.summary}</p>
          </div>
        )}

        {/* Work Experience */}
        {experience && experience.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Work Experience
            </h2>
            <div className="space-y-4">
              {experience.map((exp, index) => (
                <div key={index}>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-slate-800">
                        {exp.title || "Position Title"}
                      </h3>
                      <p className="text-slate-600">{exp.company || "Company Name"}</p>
                    </div>
                    <span className="text-slate-500 text-sm">
                      {exp.duration || "Duration"}
                    </span>
                  </div>
                  {exp.description && (
                    <p className="text-slate-700 mb-2">{exp.description}</p>
                  )}
                  {exp.achievements && exp.achievements.length > 0 && (
                    <ul className="text-slate-700 space-y-1 ml-4">
                      {exp.achievements.map((achievement, i) => (
                        <li key={i}>• {achievement}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Education */}
        {education && education.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Education
            </h2>
            <div className="space-y-3">
              {education.map((edu, index) => (
                <div key={index} className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-slate-800">
                      {edu.degree || "Degree"}
                    </h3>
                    <p className="text-slate-600">{edu.institution || "Institution"}</p>
                  </div>
                  <span className="text-slate-500 text-sm">
                    {edu.year || "Year"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        {skills && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Skills
            </h2>
            <div className="space-y-2">
              {skills.technical && skills.technical.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-700 mb-1">Technical Skills</h4>
                  <p className="text-slate-600">{skills.technical.join(", ")}</p>
                </div>
              )}
              {skills.soft && skills.soft.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-700 mb-1">Soft Skills</h4>
                  <p className="text-slate-600">{skills.soft.join(", ")}</p>
                </div>
              )}
              {skills.languages && skills.languages.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-700 mb-1">Languages</h4>
                  <p className="text-slate-600">{skills.languages.join(", ")}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Projects */}
        {projects && projects.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Projects
            </h2>
            <div className="space-y-4">
              {projects.map((project, index) => (
                <div key={index}>
                  <h3 className="font-semibold text-slate-800">{project.name}</h3>
                  <p className="text-slate-700 mb-1">{project.description}</p>
                  {project.technologies && project.technologies.length > 0 && (
                    <p className="text-slate-600 text-sm">
                      <strong>Technologies:</strong> {project.technologies.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-800">Resume Preview</h3>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              disabled={zoom <= 0.5}
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-sm text-slate-600 min-w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              disabled={zoom >= 2}
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div
          className="bg-white border border-slate-200 rounded-lg p-8 overflow-auto text-sm"
          style={{
            maxHeight: "700px",
            minHeight: "600px"
          }}
        >
          {renderResumeContent()}
        </div>
      </CardContent>
    </Card>
  );
}
