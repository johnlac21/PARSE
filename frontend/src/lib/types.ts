/**
 * TypeScript interfaces mirroring backend Pydantic models and domain types.
 */

export interface Project {
  id: string;
  name: string;
  task_modality: 'likert' | 'recommendation_list' | 'free_text';
  created_at: string;
  prompt_count?: number;
  run_count?: number;
  config?: Record<string, any>;
}

export interface Prompt {
  id: number;
  project_id: string;
  prompt_id: number;
  prompt_text: string;
  variant: string;
  features_applied: string[];
  metadata: Record<string, any>;
}

export interface GrammarFeature {
  id: string;
  name: string;
  description: string;
  example_std: string;
  example_var: string;
  category: string;
  dialects: string[];
  requires_pos_tags: boolean;
  tier: number;
}

export interface TypoFeature {
  id: string;
  name: string;
  description: string;
  example: string;
  default_word_p: number;
  default_char_p: number;
}

export interface ApplicabilityResult {
  feature_id: string;
  name: string;
  total_applicable: number;
  total_prompts: number;
  applicability_rate: number;
}

export interface VariantPreview {
  original_text: string;
  variant_id: string;
  variant_type: string;
  transformed_text: string;
  features_applied: string[];
  changes_made: boolean;
}

export interface Run {
  id: string;
  project_id: string;
  model_provider: string;
  model_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  total_prompts: number;
  completed_prompts: number;
  error_count: number;
  started_at: string;
  completed_at?: string;
  progress_message?: string | null;
}

export interface RunProgress {
  run_id: string;
  status: string;
  total_prompts: number;
  completed_prompts: number;
  error_count: number;
  progress_pct: number;
  eta_seconds?: number;
  message?: string | null;
}

export interface ModelOption {
  provider: string;
  model: string;
  display_name: string;
}

export interface AnalysisResult {
  difference_rate?: number;
  mean_difference?: number;
  se: number;
  t_stat: number;
  p_value: number;
  n_obs: number;
  ci_lower: number;
  ci_upper: number;
  significance: string;
  direction?: string;
}

export interface CompletenessResult {
  total: number;
  valid: number;
  invalid: number;
  refusals: number;
  empty: number;
  valid_rate: number;
  refusal_rate: number;
}

/** Grammar tab config for variant preview/generate. */
export interface GrammarConfig {
  grammarFeatures: string[];
  grammarMode: string;
}

/** Typos tab config for variant preview/generate. */
export interface TypoConfig {
  typoFeatures: string[];
  wordP: number;
  charP: number;
  seed: number;
}

/** Full variant config (grammar + typos + dialect count for display). */
export interface VariantConfig {
  grammarFeatures: string[];
  grammarMode: string;
  typoFeatures: string[];
  wordP: number;
  charP: number;
  seed: number;
  dialectCount: number;
}

/** Store grammar config (selected features, mode, applicability scan). */
export interface StoreGrammarConfig {
  selectedFeatures: string[];
  mode: 'individual' | 'all_combinations' | 'bundle';
  applicabilityResults: Record<string, ApplicabilityResult>;
  scanned: boolean;
  /** True while an applicability scan is in progress (upload-triggered or manual). */
  scanLoading: boolean;
}

/** Store typo config. */
export interface StoreTypoConfig {
  selectedTypos: string[];
  wordP: number;
  charP: number;
  seed: number;
}

/** Store dialect config (selection + API settings). */
export interface DialectConfig {
  selectedDialects: string[];
  apiProvider: string;
  apiKey: string;
  generationModel: string;
  baseUrl: string;
  constrained: boolean;
  parameterColumns: string[];
}
