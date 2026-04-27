"use client";

import { create } from "zustand";
import type {
  Project,
  Prompt,
  Run,
  RunProgress,
  ApplicabilityResult,
} from "@/lib/types";
import type {
  StoreGrammarConfig,
  StoreTypoConfig,
  DialectConfig,
} from "@/lib/types";

const defaultGrammarConfig: StoreGrammarConfig = {
  selectedFeatures: [],
  mode: "individual",
  applicabilityResults: {},
  scanned: false,
  scanLoading: false,
};

const defaultTypoConfig: StoreTypoConfig = {
  selectedTypos: [],
  wordP: 0.15,
  charP: 0.6,
  seed: 42,
};

const defaultDialectConfig: DialectConfig = {
  selectedDialects: [],
  apiProvider: "openai",
  apiKey: "",
  generationModel: "gpt-4o-mini",
  baseUrl: "",
  constrained: false,
  parameterColumns: [],
};

export interface ProjectStore {
  // Project
  currentProject: Project | null;
  prompts: Prompt[];
  promptCount: number;
  samplePrompts: Prompt[];
  /** True after generate variants has completed for this project. */
  variantsGenerated: boolean;
  /** True while project/prompts are being fetched in layout. */
  projectLoading: boolean;

  // Variant Config
  grammarConfig: StoreGrammarConfig;
  typoConfig: StoreTypoConfig;
  dialectConfig: DialectConfig;

  // Runs
  runs: Run[];
  activeRunIds: string[];

  // Analysis
  selectedRunIds: string[];

  // Actions
  setProject: (project: Project | null) => void;
  setPrompts: (prompts: Prompt[]) => void;
  setPromptCount: (n: number) => void;
  setSamplePrompts: (prompts: Prompt[]) => void;
  setVariantsGenerated: (v: boolean) => void;
  setProjectLoading: (v: boolean) => void;
  updateGrammarConfig: (partial: Partial<StoreGrammarConfig>) => void;
  updateTypoConfig: (partial: Partial<StoreTypoConfig>) => void;
  updateDialectConfig: (partial: Partial<DialectConfig>) => void;
  addRun: (run: Run) => void;
  setRuns: (runs: Run[]) => void;
  updateRunProgress: (runId: string, progress: RunProgress) => void;
  setActiveRunIds: (ids: string[]) => void;
  setSelectedRuns: (runIds: string[]) => void;
  reset: () => void;
}

const initialState = {
  currentProject: null as Project | null,
  prompts: [],
  promptCount: 0,
  samplePrompts: [],
  variantsGenerated: false,
  projectLoading: true,
  grammarConfig: defaultGrammarConfig,
  typoConfig: defaultTypoConfig,
  dialectConfig: defaultDialectConfig,
  runs: [],
  activeRunIds: [],
  selectedRunIds: [],
};

export const useProjectStore = create<ProjectStore>((set) => ({
  ...initialState,

  setProject: (project) =>
    set({ currentProject: project, promptCount: project?.prompt_count ?? 0 }),

  setPrompts: (prompts) => set({ prompts }),

  setPromptCount: (promptCount) => set({ promptCount }),

  setSamplePrompts: (samplePrompts) => set({ samplePrompts }),

  setVariantsGenerated: (variantsGenerated) => set({ variantsGenerated }),

  setProjectLoading: (projectLoading) => set({ projectLoading }),

  updateGrammarConfig: (partial) =>
    set((state) => ({
      grammarConfig: { ...state.grammarConfig, ...partial },
    })),

  updateTypoConfig: (partial) =>
    set((state) => ({
      typoConfig: { ...state.typoConfig, ...partial },
    })),

  updateDialectConfig: (partial) =>
    set((state) => ({
      dialectConfig: { ...state.dialectConfig, ...partial },
    })),

  addRun: (run) =>
    set((state) => ({
      runs: [run, ...state.runs],
      activeRunIds: [...state.activeRunIds, run.id],
    })),

  setRuns: (runs) => set({ runs }),

  updateRunProgress: (runId, progress) =>
    set((state) => {
      const finished =
        progress.status === "completed" ||
        progress.status === "failed" ||
        progress.status === "cancelled";
      return {
        runs: state.runs.map((r) =>
          r.id === runId
            ? {
                ...r,
                status: progress.status as Run["status"],
                completed_prompts: progress.completed_prompts,
                error_count: progress.error_count,
                completed_at:
                  progress.status === "completed"
                    ? new Date().toISOString()
                    : r.completed_at,
                progress_message: progress.message ?? undefined,
              }
            : r
        ),
        activeRunIds: finished
          ? state.activeRunIds.filter((id) => id !== runId)
          : state.activeRunIds,
      };
    }),

  setActiveRunIds: (activeRunIds) => set({ activeRunIds }),

  setSelectedRuns: (selectedRunIds) => set({ selectedRunIds }),

  reset: () => set(initialState),
}));
