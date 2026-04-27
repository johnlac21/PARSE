/**
 * Typed API client for PARSE backend.
 * Base URL: NEXT_PUBLIC_API_URL if set; otherwise "" (same-origin, proxied via next.config.js to backend).
 */

import type {
  AnalysisResult,
  ApplicabilityResult,
  CompletenessResult,
  GrammarFeature,
  ModelOption,
  Prompt,
  Project,
  Run,
  RunProgress,
  TypoFeature,
  VariantPreview,
} from './types';

const API_BASE =
  typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL?.trim()
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')
    : '';

/** Exposed so UI can show which backend URL is being used (e.g. in errors). */
export const apiBaseUrl = API_BASE || '(same origin, proxied to backend)';

class ApiClient {
  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const message = typeof error === 'object' && error !== null && 'detail' in error
        ? (typeof (error as { detail: unknown }).detail === 'string'
            ? (error as { detail: string }).detail
            : JSON.stringify((error as { detail: unknown }).detail))
        : 'API Error';
      throw new Error(message);
    }
    return res.json() as Promise<T>;
  }

  private async fetchBlob(path: string, options?: RequestInit): Promise<Blob> {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const message = typeof error === 'object' && error !== null && 'detail' in error
        ? (typeof (error as { detail: unknown }).detail === 'string'
            ? (error as { detail: string }).detail
            : JSON.stringify((error as { detail: unknown }).detail))
        : 'API Error';
      throw new Error(message);
    }
    return res.blob();
  }

  private async fetchText(path: string, options?: RequestInit): Promise<string> {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      const message = typeof error === 'object' && error !== null && 'detail' in error
        ? (typeof (error as { detail: unknown }).detail === 'string'
            ? (error as { detail: string }).detail
            : JSON.stringify((error as { detail: unknown }).detail))
        : 'API Error';
      throw new Error(message);
    }
    return res.text();
  }

  // ——— Projects ———
  async createProject(name: string, taskModality: string): Promise<Project> {
    const data = await this.fetch<Project>('/api/projects/', {
      method: 'POST',
      body: JSON.stringify({ name, task_modality: taskModality }),
    });
    return {
      ...data,
      created_at: typeof data.created_at === 'string' ? data.created_at : (data as { created_at: { toString?: () => string } }).created_at?.toString?.() ?? '',
    };
  }

  async getProjects(): Promise<Project[]> {
    const list = await this.fetch<Array<Project & { created_at?: string | { isoformat?: () => string } }>>('/api/projects/');
    return list.map((p) => ({
      ...p,
      created_at: typeof p.created_at === 'string' ? p.created_at : (p.created_at as { isoformat?: () => string })?.isoformat?.() ?? '',
    }));
  }

  async getProject(id: string): Promise<Project> {
    const data = await this.fetch<Project & { created_at?: string | { isoformat?: () => string } }>(`/api/projects/${id}`);
    const createdAt =
      typeof data.created_at === 'string'
        ? data.created_at
        : (data.created_at as { isoformat?: () => string } | undefined)?.isoformat?.() ?? '';
    return { ...data, created_at: createdAt };
  }

  async deleteProject(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/projects/${id}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((error as { detail?: string }).detail ?? 'API Error');
    }
  }

  async uploadPrompts(
    projectId: string,
    file: File
  ): Promise<{ prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }> {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/upload`, {
      method: 'POST',
      body: form,
      headers: {}, // no Content-Type so browser sets multipart boundary
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((error as { detail?: string }).detail ?? 'API Error');
    }
    return res.json() as Promise<{ prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }>;
  }

  async loadDefaultDataset(
    projectId: string,
    dataset: 'movie_prompts' | 'privacy_bias'
  ): Promise<{ prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }> {
    return this.fetch<{
      prompts_loaded: number;
      columns_detected: string[];
      sample: Record<string, unknown>[];
    }>(`/api/projects/${projectId}/upload/default`, {
      method: 'POST',
      body: JSON.stringify({ dataset }),
    });
  }

  async mapColumnsUpload(
    projectId: string,
    mapping: {
      prompt_id_column: string;
      prompt_text_column: string;
      variant_column?: string | null;
      metadata_columns?: string[];
    }
  ): Promise<{ prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }> {
    return this.fetch<{ prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }>(
      `/api/projects/${projectId}/upload/map-columns`,
      {
        method: 'POST',
        body: JSON.stringify({
          prompt_id_column: mapping.prompt_id_column,
          prompt_text_column: mapping.prompt_text_column,
          variant_column: mapping.variant_column ?? null,
          metadata_columns: mapping.metadata_columns ?? [],
        }),
      }
    );
  }

  async getPrompts(
    projectId: string,
    page?: number
  ): Promise<{ prompts: Prompt[]; total: number }> {
    const pageNum = page ?? 1;
    const data = await this.fetch<{
      items: Array<{
        id: number;
        prompt_id: string;
        prompt_text: string;
        variant: string;
        metadata?: Record<string, unknown> | null;
        features_applied?: string[];
      }>;
      total: number;
    }>(`/api/projects/${projectId}/prompts?page=${pageNum}&per_page=50`);
    const prompts: Prompt[] = data.items.map((item) => ({
      id: item.id,
      project_id: projectId,
      prompt_id: parseInt(item.prompt_id, 10) || item.id,
      prompt_text: item.prompt_text,
      variant: item.variant,
      features_applied: item.features_applied ?? [],
      metadata: item.metadata ?? {},
    }));
    return { prompts, total: data.total };
  }

  // ——— Variants ———
  async getGrammarFeatures(): Promise<GrammarFeature[]> {
    return this.fetch<GrammarFeature[]>('/api/variants/grammar-features');
  }

  async getTypoFeatures(): Promise<TypoFeature[]> {
    return this.fetch<TypoFeature[]>('/api/variants/typo-features');
  }

  async checkApplicability(
    projectId: string,
    featureIds: string[]
  ): Promise<{ features: ApplicabilityResult[] }> {
    const data = await this.fetch<{ features: ApplicabilityResult[] }>('/api/variants/check-applicability', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, feature_ids: featureIds }),
    });
    return data;
  }

  async previewVariants(request: {
    texts: string[];
    grammar_features?: string[];
    grammar_mode?: string;
    typo_features?: string[];
    typo_word_p?: number;
    typo_char_p?: number;
    seed?: number;
  }): Promise<{ variants: VariantPreview[]; total_variant_count: number }> {
    const data = await this.fetch<{
      variants: VariantPreview[];
      total_variant_count: number;
    }>('/api/variants/preview', {
      method: 'POST',
      body: JSON.stringify({
        texts: request.texts,
        grammar_features: request.grammar_features ?? [],
        grammar_mode: request.grammar_mode ?? 'individual',
        typo_features: request.typo_features ?? [],
        typo_word_p: request.typo_word_p ?? 0.15,
        typo_char_p: request.typo_char_p ?? 0.6,
        seed: request.seed ?? 42,
      }),
    });
    return { variants: data.variants, total_variant_count: data.total_variant_count };
  }

  async generateVariants(request: {
    project_id: string;
    grammar_features?: string[];
    grammar_mode?: string;
    typo_features?: string[];
    typo_word_p?: number;
    typo_char_p?: number;
    seed?: number;
  }): Promise<{ variants_generated: number }> {
    const data = await this.fetch<{ variants_generated: number }>('/api/variants/generate', {
      method: 'POST',
      body: JSON.stringify({
        project_id: request.project_id,
        grammar_features: request.grammar_features ?? [],
        grammar_mode: request.grammar_mode ?? 'individual',
        typo_features: request.typo_features ?? [],
        typo_word_p: request.typo_word_p ?? 0.15,
        typo_char_p: request.typo_char_p ?? 0.6,
        seed: request.seed ?? 42,
      }),
    });
    return data;
  }

  // ——— Runs ———
  async getModels(): Promise<ModelOption[]> {
    return this.fetch<ModelOption[]>('/api/runs/models');
  }

  async createRun(request: {
    project_id: string;
    model_provider: string;
    model_id: string;
    system_prompt?: string | null;
    temperature?: number | null;
    max_tokens?: number | null;
    base_url?: string | null;
    api_key?: string | null;
  }): Promise<Run> {
    const data = await this.fetch<Run & { started_at?: string | { isoformat?: () => string } }>('/api/runs/create', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return {
      ...data,
      started_at: typeof data.started_at === 'string' ? data.started_at : (data.started_at as { isoformat?: () => string })?.isoformat?.() ?? '',
      completed_at: data.completed_at != null
        ? (typeof data.completed_at === 'string' ? data.completed_at : (data.completed_at as { isoformat?: () => string })?.isoformat?.() ?? '')
        : undefined,
    };
  }

  async getRunProgress(runId: string): Promise<RunProgress> {
    return this.fetch<RunProgress>(`/api/runs/${runId}/progress`);
  }

  async cancelRun(runId: string): Promise<void> {
    await this.fetch<{ run_id: string; status: string }>(`/api/runs/${runId}/cancel`, { method: 'POST' });
  }

  async getProjectRuns(projectId: string): Promise<Run[]> {
    const list = await this.fetch<Array<Run & { started_at?: string | { isoformat?: () => string }; completed_at?: string | null | { isoformat?: () => string } }>>(
      `/api/runs/project/${projectId}`
    );
    return list.map((r) => ({
      ...r,
      started_at: typeof r.started_at === 'string' ? r.started_at : (r.started_at as { isoformat?: () => string })?.isoformat?.() ?? '',
      completed_at: r.completed_at != null
        ? (typeof r.completed_at === 'string' ? r.completed_at : (r.completed_at as { isoformat?: () => string })?.isoformat?.() ?? '')
        : undefined,
    }));
  }

  subscribeToProgress(
    runId: string,
    onProgress: (data: RunProgress) => void,
    onComplete: () => void,
    onError: (err: string) => void
  ): () => void {
    const url = `${API_BASE}/api/runs/${runId}/progress/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('progress', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data ?? '{}') as RunProgress;
        onProgress(data);
      } catch {
        onError('Invalid progress data');
      }
    });

    eventSource.addEventListener('complete', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data ?? '{}') as RunProgress;
        onProgress(data);
      } catch {
        // ignore
      }
      onComplete();
      eventSource.close();
    });

    eventSource.addEventListener('error', (event: MessageEvent) => {
      try {
        const data = JSON.parse((event as unknown as { data?: string }).data ?? '{}');
        onError(data?.error ?? 'Stream error');
      } catch {
        onError('Stream error');
      }
      eventSource.close();
    });

    eventSource.onerror = () => {
      onError('Connection error');
      eventSource.close();
    };

    return () => eventSource.close();
  }

  // ——— Analysis ———
  async runDifference(
    projectId: string,
    runIds: string[],
    baselineVariant?: string
  ): Promise<Record<string, Record<string, AnalysisResult>>> {
    return this.fetch<Record<string, Record<string, AnalysisResult>>>('/api/analysis/difference', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        run_ids: runIds,
        baseline_variant: baselineVariant ?? 'standard',
      }),
    });
  }

  async runDirectionalBias(
    projectId: string,
    runIds: string[],
    baselineVariant?: string
  ): Promise<Record<string, Record<string, AnalysisResult>>> {
    return this.fetch<Record<string, Record<string, AnalysisResult>>>('/api/analysis/directional-bias', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        run_ids: runIds,
        baseline_variant: baselineVariant ?? 'standard',
      }),
    });
  }

  async runCompleteness(
    projectId: string,
    runIds: string[]
  ): Promise<Record<string, Record<string, CompletenessResult>>> {
    return this.fetch<Record<string, Record<string, CompletenessResult>>>('/api/analysis/completeness', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, run_ids: runIds }),
    });
  }

  async exportResults(
    projectId: string,
    runIds: string[],
    tableType: string,
    format: string
  ): Promise<string | Blob> {
    const res = await fetch(`${API_BASE}/api/analysis/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        run_ids: runIds,
        table_type: tableType,
        format,
      }),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((error as { detail?: string }).detail ?? 'API Error');
    }
    if (format === 'json') {
      return res.text();
    }
    return res.blob();
  }

  async getRawResults(
    projectId: string,
    params?: { run_id?: string; variant?: string; model_id?: string; page?: number; per_page?: number }
  ): Promise<{
    items: unknown[];
    total: number;
    page: number;
    per_page: number;
  }> {
    const search = new URLSearchParams();
    if (params?.run_id) search.set('run_id', params.run_id);
    if (params?.variant) search.set('variant', params.variant);
    if (params?.model_id) search.set('model_id', params.model_id);
    if (params?.page != null) search.set('page', String(params.page));
    if (params?.per_page != null) search.set('per_page', String(params.per_page));
    const qs = search.toString();
    const path = qs ? `/api/analysis/results/${projectId}?${qs}` : `/api/analysis/results/${projectId}`;
    return this.fetch(path);
  }
}

export const api = new ApiClient();
