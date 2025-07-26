import { Badge } from "@/components/ui/badge";
import { CheckCircle, Circle, AlertCircle } from "lucide-react";

interface StepIndicatorProps {
    currentStep: string;
    steps: Array<{
        id: string;
        label: string;
        status?: "completed" | "current" | "pending" | "error";
    }>;
    compact?: boolean;
}

export default function StepIndicator({ currentStep, steps, compact = false }: StepIndicatorProps) {
    const getStepStatus = (stepId: string): "completed" | "current" | "pending" | "error" => {
        const currentIndex = steps.findIndex(step => step.id === currentStep);
        const stepIndex = steps.findIndex(step => step.id === stepId);

        if (stepIndex < currentIndex) return "completed";
        if (stepIndex === currentIndex) return "current";
        return "pending";
    };

    const getStepIcon = (status: string) => {
        switch (status) {
            case "completed":
                return <CheckCircle className="w-4 h-4 text-green-600" />;
            case "current":
                return <Circle className="w-4 h-4 text-blue-600 fill-current" />;
            case "error":
                return <AlertCircle className="w-4 h-4 text-red-600" />;
            default:
                return <Circle className="w-4 h-4 text-slate-400" />;
        }
    };

    const getStepColor = (status: string) => {
        switch (status) {
            case "completed":
                return "bg-green-50 text-green-800 border-green-200";
            case "current":
                return "bg-blue-50 text-blue-800 border-blue-200";
            case "error":
                return "bg-red-50 text-red-800 border-red-200";
            default:
                return "bg-slate-50 text-slate-600 border-slate-200";
        }
    };

    if (compact) {
        const currentStepData = steps.find(step => step.id === currentStep);
        const currentIndex = steps.findIndex(step => step.id === currentStep);
        const completedSteps = currentIndex;
        const totalSteps = steps.length;

        return (
            <div className="flex items-center gap-3">
                <Badge variant="outline" className="bg-blue-50 text-blue-800 border-blue-200">
                    Step {currentIndex + 1} of {totalSteps}
                </Badge>
                <span className="text-sm font-medium text-slate-700">
                    {currentStepData?.label}
                </span>
                <div className="flex items-center gap-1">
                    {Array.from({ length: totalSteps }, (_, i) => (
                        <div
                            key={i}
                            className={`w-2 h-2 rounded-full ${i < currentIndex
                                    ? "bg-green-500"
                                    : i === currentIndex
                                        ? "bg-blue-500"
                                        : "bg-slate-300"
                                }`}
                        />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {steps.map((step, index) => {
                const status = step.status || getStepStatus(step.id);
                const isLast = index === steps.length - 1;

                return (
                    <div key={step.id} className="flex items-center gap-2 flex-shrink-0">
                        <Badge
                            variant="outline"
                            className={`flex items-center gap-2 px-3 py-1 ${getStepColor(status)}`}
                        >
                            {getStepIcon(status)}
                            <span className="text-sm font-medium">{step.label}</span>
                        </Badge>
                        {!isLast && (
                            <div className="w-8 h-px bg-slate-200" />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
