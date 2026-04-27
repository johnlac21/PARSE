"use client";

import * as React from "react";
import { api } from "@/lib/api-client";
import type { Project, Prompt, VariantConfig } from "@/lib/types";

export interface UploadResult {
  promptCount: number;
  samplePrompts: Record<string, unknown>[];
  columnsDetected: string[];
}

export interface ProjectContextValue {
  project: Project | null;
  prompts: Prompt[];
  loading: boolean;
  refreshProject: () => void;
  loadPrompts: () => Promise<void>;
  /** Set after a successful prompts upload (or map-columns). Used for configure page preview/summary. */
  uploadResult: UploadResult | null;
  setUploadResult: (result: UploadResult | null) => void;
  /** Variant configuration (grammar, typos, dialects) set from configure page. */
  variantConfig: VariantConfig | null;
  setVariantConfig: (config: VariantConfig | null) => void;
  /** True after generate variants has completed successfully. */
  variantsGenerated: boolean;
  setVariantsGenerated: (v: boolean) => void;
  /** Number of variants generated (set after generate completes). */
  variantCount: number;
  setVariantCount: (n: number) => void;
}

const ProjectContext = React.createContext<ProjectContextValue | null>(null);

export interface ProjectProviderProps {
  projectId: string | null;
  children: React.ReactNode;
}

/**
 * Fetches project on mount and provides project, lazy prompts, loading, and refreshProject.
 */
export function ProjectProvider({ projectId, children }: ProjectProviderProps) {
  const [project, setProject] = React.useState<Project | null>(null);
  const [prompts, setPrompts] = React.useState<Prompt[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [uploadResult, setUploadResult] = React.useState<UploadResult | null>(null);
  const [variantConfig, setVariantConfig] = React.useState<VariantConfig | null>(null);
  const [variantsGenerated, setVariantsGenerated] = React.useState(false);
  const [variantCount, setVariantCount] = React.useState(0);

  const refreshProject = React.useCallback(async () => {
    if (!projectId) {
      setProject(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const p = await api.getProject(projectId);
      setProject(p);
    } catch {
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  React.useEffect(() => {
    refreshProject();
  }, [refreshProject]);

  const loadPrompts = React.useCallback(async () => {
    if (!projectId) return;
    try {
      const { prompts: list } = await api.getPrompts(projectId);
      setPrompts(list);
    } catch {
      setPrompts([]);
    }
  }, [projectId]);

  const value: ProjectContextValue = React.useMemo(
    () => ({
      project,
      prompts,
      loading,
      refreshProject,
      loadPrompts,
      uploadResult,
      setUploadResult,
      variantConfig,
      setVariantConfig,
      variantsGenerated,
      setVariantsGenerated,
      variantCount,
      setVariantCount,
    }),
    [
      project,
      prompts,
      loading,
      refreshProject,
      loadPrompts,
      uploadResult,
      variantConfig,
      variantsGenerated,
      variantCount,
    ]
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export interface UseProjectOptions {
  projectId?: string | null;
}

/**
 * Consume ProjectContext. Use inside ProjectProvider (e.g. under project/[id] layout).
 */
export function useProject(_options?: UseProjectOptions): ProjectContextValue {
  const ctx = React.useContext(ProjectContext);
  if (!ctx) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return ctx;
}
