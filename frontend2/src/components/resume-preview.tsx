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

    const { personal_details, work_experience, education, skills, projects } = parsedData;

    return (
      <div className="space-y-6" style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
        {/* Header */}
        {personal_details && (
          <div className="text-center border-b border-slate-200 pb-4">
            <h1 className="text-2xl font-bold text-slate-800 mb-2">
              {personal_details.name || "Your Name"}
            </h1>
            <div className="text-slate-600 space-y-1">
              {personal_details.email && (
                <p>{personal_details.email}</p>
              )}
              <p>
                {[personal_details.phone, personal_details.address]
                  .filter(Boolean)
                  .join(" | ")}
              </p>
              {personal_details.linkedin && (
                <p>LinkedIn: {personal_details.linkedin}</p>
              )}
              {personal_details.github && (
                <p>GitHub: {personal_details.github}</p>
              )}
            </div>
          </div>
        )}

        {/* Professional Summary */}
        {personal_details?.summary && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Professional Summary
            </h2>
            <p className="text-slate-700 leading-relaxed">{personal_details.summary}</p>
          </div>
        )}

        {/* Work Experience */}
        {work_experience && work_experience.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Work Experience
            </h2>
            <div className="space-y-4">
              {work_experience.map((exp: any, index: number) => (
                <div key={index}>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-slate-800">
                        {exp.title || "Position Title"}
                      </h3>
                      <p className="text-slate-600">{exp.company || "Company Name"}</p>
                      {exp.location && (
                        <p className="text-slate-500 text-sm">{exp.location}</p>
                      )}
                    </div>
                    <span className="text-slate-500 text-sm">
                      {exp.from_year && exp.to_year ? `${exp.from_year} - ${exp.to_year}` : "Duration"}
                    </span>
                  </div>
                  {exp.summary && (
                    <p className="text-slate-700 mb-2">{exp.summary}</p>
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
              {education.map((edu: any, index: number) => (
                <div key={index} className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-slate-800">
                      {edu.degree || "Degree"}
                    </h3>
                    <p className="text-slate-600">{edu.university || "University"}</p>
                    {edu.location && (
                      <p className="text-slate-500 text-sm">{edu.location}</p>
                    )}
                    {edu.gpa && (
                      <p className="text-slate-500 text-sm">GPA: {edu.gpa}</p>
                    )}
                  </div>
                  <span className="text-slate-500 text-sm">
                    {edu.from_year && edu.to_year ? `${edu.from_year} - ${edu.to_year}` : "Year"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        {skills && skills.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-3">
              Skills
            </h2>
            <div className="space-y-2">
              <div>
                <p className="text-slate-600">{skills.join(", ")}</p>
              </div>
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
              {projects.map((project: any, index: number) => (
                <div key={index}>
                  <h3 className="font-semibold text-slate-800">{project.name}</h3>
                  {project.bullets && project.bullets.length > 0 && (
                    <ul className="text-slate-700 space-y-1 ml-4 mt-2">
                      {project.bullets.map((bullet: string, i: number) => (
                        <li key={i}>• {bullet}</li>
                      ))}
                    </ul>
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
