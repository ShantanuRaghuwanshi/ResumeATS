import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ArrowLeft, ArrowRight, Upload, FileText, AlertTriangle, Cloud, File, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn, getApiUrl } from "@/lib/utils";
import { useLLMConfig } from "@/contexts/llm-context";
import { apiUpload } from "@/lib/queryClient";

interface FileUploadProps {
  onResumeUploaded: (resumeData: any) => void;
  onNext: () => void;
}

interface UploadedFile {
  name: string;
  size: string;
  file: File;
}

export default function FileUpload({ onResumeUploaded, onNext }: FileUploadProps) {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();
  const { isSessionValid, clearSession } = useLLMConfig();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain"
    ];

    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF, DOC, DOCX, or TXT file.",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Please upload a file smaller than 10MB.",
        variant: "destructive",
      });
      return;
    }

    const sizeStr = file.size < 1024 * 1024
      ? `${(file.size / 1024).toFixed(1)} KB`
      : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;

    setUploadedFile({
      name: file.name,
      size: sizeStr,
      file,
    });

    // Upload file immediately
    setIsUploading(true);
    try {
      // Check if session is valid
      if (!isSessionValid) {
        clearSession();
        throw new Error("Session expired. Please configure LLM again.");
      }

      const formData = new FormData();
      formData.append("file", file);

      // Use session-based upload (no need to pass LLM config)
      const response = await apiUpload("/upload_resume/", formData);
      const result = await response.json();

      toast({
        title: "Upload successful",
        description: "Your resume has been uploaded and parsed.",
      });

      onResumeUploaded(result);
    } catch (error) {
      if (error instanceof Error && error.message.includes("401")) {
        // Session expired or invalid
        clearSession();
        toast({
          title: "Session expired",
          description: "Please configure your LLM settings again.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Upload failed",
          description: (error instanceof Error && error.message) ? error.message : "Failed to upload resume. Please try again.",
          variant: "destructive",
        });
      }
      setUploadedFile(null);
    } finally {
      setIsUploading(false);
    }
  }, [toast, onResumeUploaded, isSessionValid, clearSession]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    multiple: false,
  });

  const removeFile = () => {
    setUploadedFile(null);
  };

  return (
    <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
      <CardContent className="p-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Cloud className="text-primary w-8 h-8" />
            </div>
            <h3 className="text-2xl font-bold text-slate-800 mb-2">Upload Your Resume</h3>
            <p className="text-slate-600">Upload your resume in PDF or DOC format to get started with AI-powered analysis</p>
          </div>

          {!uploadedFile && (
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${isDragActive
                ? "border-primary bg-primary/5"
                : "border-slate-300 hover:border-primary hover:bg-primary/5"
                }`}
            >
              <input {...getInputProps()} />
              <Cloud className="text-slate-400 w-12 h-12 mx-auto mb-4" />
              <p className="text-lg font-medium text-slate-700 mb-2">
                {isDragActive ? "Drop your resume here" : "Drag and drop your resume here"}
              </p>
              <p className="text-slate-500 mb-4">or click to browse files</p>
              <Button className="bg-primary text-white hover:bg-blue-600">
                Choose File
              </Button>
              <p className="text-sm text-slate-400 mt-4">Supports PDF, DOC, DOCX up to 10MB</p>
            </div>
          )}

          {uploadedFile && (
            <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <File className="text-red-500 w-6 h-6" />
                  <div>
                    <p className="font-medium text-slate-800">{uploadedFile.name}</p>
                    <p className="text-sm text-slate-600">{uploadedFile.size}</p>
                  </div>
                </div>
                {!isUploading && (
                  <Button variant="ghost" size="sm" onClick={removeFile}>
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
              {isUploading && (
                <div className="mt-3">
                  <div className="animate-pulse">
                    <p className="text-sm text-slate-600">Uploading and parsing resume...</p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-center mt-8">
            <Button
              onClick={onNext}
              className="bg-primary text-white hover:bg-blue-600"
              disabled={!uploadedFile || isUploading}
            >
              <span>Continue to Resume Analysis</span>
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
