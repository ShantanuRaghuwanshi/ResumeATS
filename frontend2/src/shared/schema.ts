import { pgTable, text, serial, integer, boolean, jsonb, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const resumes = pgTable("resumes", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  filename: text("filename").notNull(),
  originalContent: text("original_content").notNull(),
  parsedData: jsonb("parsed_data"),
  analysisResults: jsonb("analysis_results"),
  selectedTemplate: text("selected_template"),
  finalContent: text("final_content"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const llmConfigs = pgTable("llm_configs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  provider: text("provider").notNull(), // openai, claude, gemini, ollama
  config: jsonb("config").notNull(), // stores API keys, model names, etc
  isActive: boolean("is_active").default(false),
});

export const jobDescriptions = pgTable("job_descriptions", {
  id: serial("id").primaryKey(),
  resumeId: integer("resume_id").references(() => resumes.id),
  content: text("content").notNull(),
  matchAnalysis: jsonb("match_analysis"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Zod schemas
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertResumeSchema = createInsertSchema(resumes).omit({
  id: true,
  createdAt: true,
});

export const insertLLMConfigSchema = createInsertSchema(llmConfigs).omit({
  id: true,
});

export const insertJobDescriptionSchema = createInsertSchema(jobDescriptions).omit({
  id: true,
  createdAt: true,
});

// Additional validation schemas
export const fileUploadSchema = z.object({
  filename: z.string().min(1),
  content: z.string().min(1),
  type: z.enum(["pdf", "doc", "docx"]),
});

export const llmProviderConfigSchema = z.object({
  provider: z.enum(["openai", "claude", "gemini", "ollama"]),
  config: z.record(z.string()),
});

export const personalDetailsSchema = z.object({
  name: z.string().optional(),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  location: z.string().optional(),
  summary: z.string().optional(),
});

export const experienceSchema = z.object({
  title: z.string(),
  company: z.string(),
  duration: z.string(),
  description: z.string(),
  achievements: z.array(z.string()).optional(),
});

export const educationSchema = z.object({
  degree: z.string(),
  institution: z.string(),
  year: z.string(),
  gpa: z.string().optional(),
});

export const skillsSchema = z.object({
  technical: z.array(z.string()).optional(),
  soft: z.array(z.string()).optional(),
  languages: z.array(z.string()).optional(),
});

export const parsedResumeSchema = z.object({
  personalDetails: personalDetailsSchema.optional(),
  experience: z.array(experienceSchema).optional(),
  education: z.array(educationSchema).optional(),
  skills: skillsSchema.optional(),
  projects: z.array(z.object({
    name: z.string(),
    description: z.string(),
    technologies: z.array(z.string()).optional(),
  })).optional(),
});

export const analysisResultSchema = z.object({
  score: z.number().min(0).max(100),
  suggestions: z.array(z.object({
    type: z.enum(["warning", "info", "success"]),
    title: z.string(),
    description: z.string(),
    section: z.string().optional(),
  })),
  keywords: z.array(z.string()).optional(),
  atsCompatibility: z.number().min(0).max(100).optional(),
});

// Types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertResume = z.infer<typeof insertResumeSchema>;
export type Resume = typeof resumes.$inferSelect;
export type InsertLLMConfig = z.infer<typeof insertLLMConfigSchema>;
export type LLMConfig = typeof llmConfigs.$inferSelect;
export type InsertJobDescription = z.infer<typeof insertJobDescriptionSchema>;
export type JobDescription = typeof jobDescriptions.$inferSelect;
export type ParsedResume = z.infer<typeof parsedResumeSchema>;
export type AnalysisResult = z.infer<typeof analysisResultSchema>;
export type FileUpload = z.infer<typeof fileUploadSchema>;
export type LLMProviderConfig = z.infer<typeof llmProviderConfigSchema>;
