import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, ArrowRight, Brain, Bot, Star, Server } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { cn, getApiUrl } from "@/lib/utils";
import { useLLMConfig } from "@/contexts/llm-context";

interface LLMConfigProps {
  onNext: () => void;
  onBack: () => void;
}

type LLMProvider = "ollama" | "openai" | "claude" | "gemini";

const openaiSchema = z.object({
  provider: z.literal("openai"),
  apiKey: z.string().min(1, "API Key is required"),
  model: z.string().default("gpt-4o"),
  organizationId: z.string().optional(),
  deploymentName: z.string().optional(),
});

const claudeSchema = z.object({
  provider: z.literal("claude"),
  apiKey: z.string().min(1, "API Key is required"),
  model: z.string().default("claude-sonnet-4-20250514"),
});

const geminiSchema = z.object({
  provider: z.literal("gemini"),
  apiKey: z.string().min(1, "API Key is required").default("AIzaSyCP3-LNqJFeIz1SyzGv-HruWItCgx55hKU"),
  model: z.string().default("gemini-2.5-flash"),
});

const ollamaSchema = z.object({
  provider: z.literal("ollama"),
  url: z.string().url("Please enter a valid URL"),
  model: z.string().min(1, "Model name is required"),
});

export default function LLMConfig({ onNext, onBack }: LLMConfigProps) {
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>("ollama");
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const { toast } = useToast();
  const { setLLMConfig } = useLLMConfig();

  const providers = [
    {
      id: "ollama" as LLMProvider,
      name: "Ollama",
      description: "Local deployment",
      icon: Server,
      color: "bg-purple-500"
    },
    {
      id: "openai" as LLMProvider,
      name: "OpenAI",
      description: "GPT-4, GPT-3.5 Turbo",
      icon: Brain,
      color: "bg-green-500"
    },
    {
      id: "claude" as LLMProvider,
      name: "Claude",
      description: "Claude-3, Claude-2",
      icon: Bot,
      color: "bg-orange-500"
    },
    {
      id: "gemini" as LLMProvider,
      name: "Gemini",
      description: "Gemini Pro, Ultra",
      icon: Star,
      color: "bg-blue-500"
    },
  ];

  const getSchema = () => {
    switch (selectedProvider) {
      case "ollama": return ollamaSchema;
      case "openai": return openaiSchema;
      case "claude": return claudeSchema;
      case "gemini": return geminiSchema;
      default: return openaiSchema;
    }
  };

  type LLMFormValues = {
    provider: LLMProvider;
    url?: string;
    model?: string;
    apiKey?: string;
    organizationId?: string;
    deploymentName?: string;
  };

  const form = useForm<LLMFormValues>({
    resolver: zodResolver(getSchema()),
    defaultValues: {
      provider: selectedProvider,
      ...(selectedProvider === "ollama" && { url: "http://localhost:11434", model: "gemma3n:e4b" }),
      ...(selectedProvider === "openai" && { model: "gpt-4o" }),
      ...(selectedProvider === "claude" && { model: "claude-sonnet-4-20250514" }),
      ...(selectedProvider === "gemini" && { model: "gemini-2.5-flash" }),
    },
  });

  const handleProviderChange = (provider: LLMProvider) => {
    setSelectedProvider(provider);
    form.reset({
      provider,
      ...(provider === "ollama" && { url: "http://localhost:11434", model: "gemma3n:e4b" }),
      ...(provider === "openai" && { model: "gpt-4o" }),
      ...(provider === "claude" && { model: "claude-sonnet-4-20250514" }),
      ...(provider === "gemini" && { model: "gemini-2.5-flash" }),
    });
  };

  const onSubmit = async (data: any) => {
    setIsTestingConnection(true);
    try {
      // Create session with LLM config (this will test and create session)
      await setLLMConfig({
        provider: data.provider,
        apiKey: data.apiKey,
        url: data.url,
        model: data.model,
        organizationId: data.organizationId,
        deploymentName: data.deploymentName,
      });

      toast({
        title: "Configuration saved",
        description: "LLM configuration has been saved and session created successfully.",
      });

      onNext();
    } catch (error) {
      toast({
        title: "Configuration failed",
        description: (error instanceof Error ? error.message : "Failed to test or save LLM configuration."),
        variant: "destructive",
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const renderConfigForm = () => {
    switch (selectedProvider) {

      case "ollama":
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Ollama URL</FormLabel>
                  <FormControl>
                    <Input placeholder={import.meta.env.VITE_API_URL || "http://localhost:11434"} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model Name</FormLabel>
                  <FormControl>
                    <Input placeholder="llama2" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );

      case "openai":
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="apiKey"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Key</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="sk-..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                      <SelectItem value="gpt-4">GPT-4</SelectItem>
                      <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="organizationId"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Organization ID (Optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="org-..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="deploymentName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Deployment Name (Azure)</FormLabel>
                  <FormControl>
                    <Input placeholder="my-gpt-4-deployment" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );

      case "claude":
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="apiKey"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Key</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="sk-ant-..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="claude-sonnet-4-20250514">Claude Sonnet 4</SelectItem>
                      <SelectItem value="claude-3-7-sonnet-20250219">Claude 3.7 Sonnet</SelectItem>
                      <SelectItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );

      case "gemini":
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="apiKey"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>API Key</FormLabel>
                  <FormControl>
                    <Input type="password" placeholder="AIza..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                      <SelectItem value="gemini-2.5-pro">Gemini 2.5 Pro</SelectItem>
                      <SelectItem value="gemini-pro">Gemini Pro</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );


      default:
        return null;
    }
  };

  return (
    <Card className="bg-white rounded-xl shadow-sm border border-slate-200">
      <CardContent className="p-8">
        <h3 className="text-2xl font-bold text-slate-800 mb-6">Configure AI Model</h3>

        {/* Provider Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {providers.map((provider) => {
            const Icon = provider.icon;
            const isSelected = selectedProvider === provider.id;

            return (
              <div
                key={provider.id}
                onClick={() => handleProviderChange(provider.id)}
                className={cn(
                  "border-2 rounded-xl p-4 cursor-pointer transition-all",
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-slate-200 hover:border-slate-300"
                )}
              >
                <div className="flex items-center space-x-3 mb-3">
                  <div className={`w-10 h-10 ${provider.color} rounded-lg flex items-center justify-center`}>
                    <Icon className="text-white w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-slate-800">{provider.name}</h4>
                </div>
                <p className="text-sm text-slate-600">{provider.description}</p>
              </div>
            );
          })}
        </div>

        {/* Configuration Form */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="bg-slate-50 rounded-xl p-6">
              <h4 className="font-semibold text-slate-800 mb-4">
                {providers.find(p => p.id === selectedProvider)?.name} Configuration
              </h4>
              {renderConfigForm()}
            </div>

            <div className="flex justify-between">
              <Button type="button" variant="outline" onClick={onBack}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <Button
                type="submit"
                className="bg-primary text-white hover:bg-blue-600"
                disabled={isTestingConnection}
              >
                {isTestingConnection ? "Testing..." : "Test & Continue"}
                {!isTestingConnection && <ArrowRight className="w-4 h-4 ml-2" />}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
