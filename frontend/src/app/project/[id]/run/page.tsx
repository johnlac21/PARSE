"use client";

/**
 * Run Queries: configure models, system prompt, launch runs, and show progress via SSE.
 */

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import type { ModelOption, Run, RunProgress } from "@/lib/types";
import { useProjectStore } from "@/store/project-store";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Plus, X, ChevronDown, ChevronRight, Play, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "ollama", label: "Ollama" },
  { value: "gemini", label: "Gemini" },
  { value: "custom", label: "Custom" },
] as const;

const DEFAULT_SYSTEM_PROMPTS: Record<string, string> = {
  likert:
    "You are evaluating the acceptability of social actions. Rate on a scale of 1-5 where 1 is 'strongly unacceptable' and 5 is 'strongly acceptable'. Respond with ONLY the number.",
  recommendation_list:
    "You are a movie recommendation system. Recommend exactly 10 movies. List one per line.",
  free_text: "",
};

interface ModelConfigRow {
  id: string;
  provider: string;
  modelId: string;
  apiKey: string;
  baseUrl: string;
}

type RunWithProgress = Run & { progress?: RunProgress; errorLog?: string };

export default function RunPage() {
  const params = useParams();
  const projectId = (params?.id as string) ?? "";
  const project = useProjectStore((s) => s.currentProject);
  const projectLoading = useProjectStore((s) => s.projectLoading);
  const promptCount = useProjectStore((s) => s.promptCount);
  const variantsGenerated = useProjectStore((s) => s.variantsGenerated);
  const runs = useProjectStore((s) => s.runs);
  const activeRunIds = useProjectStore((s) => s.activeRunIds);
  const addRun = useProjectStore((s) => s.addRun);
  const updateRunProgress = useProjectStore((s) => s.updateRunProgress);

  const [modelOptions, setModelOptions] = React.useState<ModelOption[]>([]);
  const [modelConfigs, setModelConfigs] = React.useState<ModelConfigRow[]>([]);
  const [systemPrompt, setSystemPrompt] = React.useState("");
  const [temperature, setTemperature] = React.useState(0);
  const [maxTokens, setMaxTokens] = React.useState(150);
  const [launchConfirmOpen, setLaunchConfirmOpen] = React.useState(false);
  const [launchMode, setLaunchMode] = React.useState<"one" | "all" | null>(null);
  const [launchingIndex, setLaunchingIndex] = React.useState<number | null>(null);
  const [runErrorLogs, setRunErrorLogs] = React.useState<Record<string, string>>({});
  const [selectedPastRunId, setSelectedPastRunId] = React.useState<string | null>(null);
  const [expandedErrors, setExpandedErrors] = React.useState<Set<string>>(new Set());
  const [cancelRunId, setCancelRunId] = React.useState<string | null>(null);
  const [isLaunching, setIsLaunching] = React.useState(false);

  const defaultSystemPrompt =
    project?.task_modality != null ? DEFAULT_SYSTEM_PROMPTS[project.task_modality] ?? "" : "";

  const activeRuns = React.useMemo(
    () => runs.filter((r) => activeRunIds.includes(r.id)),
    [runs, activeRunIds]
  );
  const previousRuns = React.useMemo(
    () => runs.filter((r) => !activeRunIds.includes(r.id)),
    [runs, activeRunIds]
  );

  React.useEffect(() => {
    if (!systemPrompt && defaultSystemPrompt) setSystemPrompt(defaultSystemPrompt);
  }, [defaultSystemPrompt, systemPrompt]);

  React.useEffect(() => {
    let cancelled = false;
    api
      .getModels()
      .then((list) => {
        if (!cancelled) setModelOptions(list);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Runs are loaded by project layout; new runs added via addRun

  const addModelConfig = React.useCallback(() => {
    setModelConfigs((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        provider: "openai",
        modelId: "gpt-4o-mini",
        apiKey: "",
        baseUrl: "",
      },
    ]);
  }, []);

  const removeModelConfig = React.useCallback((id: string) => {
    setModelConfigs((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const updateModelConfig = React.useCallback(
    (id: string, patch: Partial<ModelConfigRow>) => {
      setModelConfigs((prev) =>
        prev.map((c) => (c.id === id ? { ...c, ...patch } : c))
      );
    },
    []
  );

  const modelsByProvider = React.useMemo(() => {
    const map = new Map<string, ModelOption[]>();
    for (const opt of modelOptions) {
      const list = map.get(opt.provider) ?? [];
      list.push(opt);
      map.set(opt.provider, list);
    }
    return map;
  }, [modelOptions]);

  const needsBaseUrl = (provider: string) =>
    provider === "ollama" || provider === "custom";

  const startRun = React.useCallback(
    async (config: ModelConfigRow) => {
      if (!projectId) return;
      try {
        const run = await api.createRun({
          project_id: projectId,
          model_provider: config.provider,
          model_id: config.modelId,
          system_prompt: systemPrompt || undefined,
          temperature: temperature ?? 0,
          max_tokens: maxTokens ?? 150,
          api_key: config.apiKey || undefined,
          base_url: needsBaseUrl(config.provider) ? config.baseUrl || undefined : undefined,
        });
        addRun(run);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to start run";
        toast.error(msg);
      }
    },
    [projectId, systemPrompt, temperature, maxTokens, addRun]
  );

  const handleLaunchOne = (index: number) => {
    setLaunchMode("one");
    setLaunchingIndex(index);
    setLaunchConfirmOpen(true);
  };

  const handleLaunchAll = () => {
    setLaunchMode("all");
    setLaunchingIndex(null);
    setLaunchConfirmOpen(true);
  };

  const confirmLaunch = React.useCallback(async () => {
    setIsLaunching(true);
    try {
      if (launchMode === "one" && launchingIndex !== null && modelConfigs[launchingIndex]) {
        await startRun(modelConfigs[launchingIndex]);
      } else if (launchMode === "all") {
        await Promise.all(modelConfigs.map((config) => startRun(config)));
      }
      setLaunchConfirmOpen(false);
      setLaunchMode(null);
      setLaunchingIndex(null);
    } finally {
      setIsLaunching(false);
    }
  }, [launchMode, launchingIndex, modelConfigs, startRun]);

  React.useEffect(() => {
    if (modelConfigs.length === 0) {
      addModelConfig();
    }
  }, [addModelConfig, modelConfigs.length]);

  const runningRunIds = activeRuns.filter(
    (r) => r.status === "running" || r.status === "pending"
  ).map((r) => r.id);

  // SSE for progress (and completion/failure)
  React.useEffect(() => {
    const unsubs: (() => void)[] = [];
    runningRunIds.forEach((runId) => {
      const unsub = api.subscribeToProgress(
        runId,
        (data: RunProgress) => {
          updateRunProgress(runId, data);
          if (data.status === "completed") {
            toast.success(
              `Run completed: ${data.completed_prompts}/${data.total_prompts} prompts processed`
            );
          }
        },
        () => {},
        (err) => {
          setRunErrorLogs((prev) => ({ ...prev, [runId]: err }));
          updateRunProgress(runId, {
            run_id: runId,
            status: "failed",
            total_prompts: 0,
            completed_prompts: 0,
            error_count: 0,
            progress_pct: 0,
          });
          toast.error(err);
        }
      );
      unsubs.push(unsub);
    });
    return () => unsubs.forEach((u) => u());
  }, [runningRunIds.join(","), updateRunProgress]);

  // Poll progress every 2s as fallback (SSE can be unreliable with some proxies/browsers)
  React.useEffect(() => {
    if (runningRunIds.length === 0) return;
    const interval = setInterval(() => {
      runningRunIds.forEach((runId) => {
        api.getRunProgress(runId).then((data) => {
          updateRunProgress(runId, data);
        }).catch(() => {});
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [runningRunIds.join(","), updateRunProgress]);

  const cancelRun = React.useCallback(async (runId: string) => {
    try {
      await api.cancelRun(runId);
      updateRunProgress(runId, {
        run_id: runId,
        status: "cancelled",
        total_prompts: 0,
        completed_prompts: 0,
        error_count: 0,
        progress_pct: 0,
      });
    } catch {
      // ignore
    } finally {
      setCancelRunId(null);
    }
  }, [updateRunProgress]);

  const confirmCancelRun = React.useCallback(() => {
    if (cancelRunId) {
      cancelRun(cancelRunId);
    }
  }, [cancelRunId, cancelRun]);

  const allRunsComplete =
    activeRuns.length > 0 &&
    activeRuns.every((r) =>
      ["completed", "failed", "cancelled"].includes(r.status)
    );

  useKeyboardShortcuts({
    onSubmit:
      launchConfirmOpen
        ? confirmLaunch
        : modelConfigs.length > 0 && !launchingIndex && projectId && promptCount > 0
          ? () => handleLaunchOne(0)
          : undefined,
    enabled: !!project && variantsGenerated && !projectLoading,
  });

  const toggleErrorExpand = (runId: string) => {
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  if (projectLoading) {
    return (
      <div className="max-w-3xl space-y-8">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-full max-w-md" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }
  if (!project) {
    return (
      <div className="max-w-3xl">
        <p className="text-sm text-muted-foreground">Project not found.</p>
      </div>
    );
  }

  if (!variantsGenerated) {
    return (
      <div className="max-w-3xl space-y-4">
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 py-12 px-6 text-center">
          <Sparkles className="h-12 w-12 text-muted-foreground mb-3" aria-hidden />
          <h2 className="text-lg font-medium text-foreground">Configure and generate variants</h2>
          <p className="mt-1 text-sm text-muted-foreground max-w-sm">
            Generate variants from the Configure page first, then return here to run queries.
          </p>
          <Link href={`/project/${projectId}/configure`}>
            <Button variant="outline" className="mt-4">Go to Configure</Button>
          </Link>
        </div>
      </div>
    );
  }

  const noRunsYet = runs.length === 0;

  return (
    <div className="max-w-3xl space-y-8">
      {/* Section 1: Configure & Launch Run */}
      <Card>
        <CardHeader>
          <CardTitle>Configure & Launch Run</CardTitle>
          <CardDescription>
            Add one or more models, set system prompt and parameters, then start runs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Model Configuration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Models</Label>
              <Button type="button" variant="outline" size="sm" onClick={addModelConfig}>
                <Plus className="h-4 w-4 mr-1" />
                Add Model
              </Button>
            </div>
            <div className="space-y-4">
              {modelConfigs.map((row) => (
                <div
                  key={row.id}
                  className="flex flex-wrap items-end gap-3 rounded-lg border p-4 bg-muted/30"
                >
                  <div className="w-[120px]">
                    <Label className="text-xs">Provider</Label>
                    <Select
                      value={row.provider}
                      onValueChange={(v) => {
                        const opts = modelsByProvider.get(v);
                        updateModelConfig(row.id, {
                          provider: v,
                          modelId: opts?.[0]?.model ?? "",
                        });
                      }}
                    >
                      <SelectTrigger className="h-9 mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PROVIDERS.map((p) => (
                          <SelectItem key={p.value} value={p.value}>
                            {p.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1 min-w-[140px]">
                    <Label className="text-xs">Model</Label>
                    {row.provider === "custom" ? (
                      <Input
                        className="h-9 mt-1 font-mono text-sm"
                        placeholder="e.g. custom/model-name"
                        value={row.modelId}
                        onChange={(e) =>
                          updateModelConfig(row.id, { modelId: e.target.value })
                        }
                      />
                    ) : (
                      <Select
                        value={row.modelId}
                        onValueChange={(v) => updateModelConfig(row.id, { modelId: v })}
                      >
                        <SelectTrigger className="h-9 mt-1">
                          <SelectValue placeholder="Model" />
                        </SelectTrigger>
                        <SelectContent>
                          {(modelsByProvider.get(row.provider) ?? []).map((m) => (
                            <SelectItem key={`${m.provider}-${m.model}`} value={m.model}>
                              {m.display_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  <div className="w-[180px]">
                    <Label className="text-xs">API Key</Label>
                    <Input
                      type="password"
                      className="h-9 mt-1 font-mono"
                      placeholder="Or set on server (e.g. OPENAI_API_KEY)"
                      value={row.apiKey}
                      onChange={(e) =>
                        updateModelConfig(row.id, { apiKey: e.target.value })
                      }
                    />
                  </div>
                  {needsBaseUrl(row.provider) && (
                    <div className="w-[200px]">
                      <Label className="text-xs">Base URL</Label>
                      <Input
                        className="h-9 mt-1 font-mono"
                        placeholder="http://localhost:11434"
                        value={row.baseUrl}
                        onChange={(e) =>
                          updateModelConfig(row.id, { baseUrl: e.target.value })
                        }
                      />
                    </div>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 shrink-0"
                    onClick={() => removeModelConfig(row.id)}
                    disabled={modelConfigs.length <= 1}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* System Prompt */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>System Prompt</Label>
              {defaultSystemPrompt && (
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => setSystemPrompt(defaultSystemPrompt)}
                >
                  Reset to default
                </button>
              )}
            </div>
            <Textarea
              className="min-h-[120px] font-mono text-sm"
              placeholder="Optional system prompt..."
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
            />
          </div>

          {/* Settings */}
          <div className="flex flex-wrap gap-6">
            <div className="w-28">
              <Label className="text-xs">Temperature</Label>
              <Input
                type="number"
                min={0}
                max={2}
                step={0.1}
                className="h-9 mt-1"
                value={temperature}
                onChange={(e) =>
                  setTemperature(Number(e.target.value) || 0)
                }
              />
            </div>
            <div className="w-28">
              <Label className="text-xs">Max tokens</Label>
              <Input
                type="number"
                min={1}
                max={4096}
                className="h-9 mt-1"
                value={maxTokens}
                onChange={(e) =>
                  setMaxTokens(Number(e.target.value) || 150)
                }
              />
            </div>
          </div>

          {/* Launch */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            {modelConfigs.map((config, idx) => (
              <Button
                key={config.id}
                onClick={() => handleLaunchOne(idx)}
                disabled={!projectId || promptCount === 0}
              >
                Start Run ({config.provider}/{config.modelId})
              </Button>
            ))}
            {modelConfigs.length > 1 && (
              <Button
                variant="secondary"
                onClick={handleLaunchAll}
                disabled={!projectId || promptCount === 0}
              >
                Start All
              </Button>
            )}
          </div>
          {promptCount > 0 && (
            <p className="text-xs text-muted-foreground">
              Will query {modelConfigs.length} model(s) with {promptCount} prompts at
              temperature {temperature}.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Cancel run confirmation */}
      <Dialog open={!!cancelRunId} onOpenChange={(open) => !open && setCancelRunId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel running job?</DialogTitle>
            <DialogDescription>
              This run will stop and partial results will not be saved.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelRunId(null)}>
              Keep running
            </Button>
            <Button variant="destructive" onClick={confirmCancelRun}>
              Cancel job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation dialog */}
      <Dialog open={launchConfirmOpen} onOpenChange={setLaunchConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start run?</DialogTitle>
            <DialogDescription>
              {launchMode === "all"
                ? `Run ${modelConfigs.length} model(s) with ${promptCount} prompts at temperature ${temperature}.`
                : launchingIndex !== null && modelConfigs[launchingIndex]
                  ? `Run ${modelConfigs[launchingIndex].provider}/${modelConfigs[launchingIndex].modelId} with ${promptCount} prompts at temperature ${temperature}.`
                  : "Start this run?"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLaunchConfirmOpen(false)} disabled={isLaunching}>
              Cancel
            </Button>
            <Button onClick={confirmLaunch} disabled={isLaunching}>
              {isLaunching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Starting…
                </>
              ) : (
                "Start Run"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Empty state: no runs yet */}
      {noRunsYet && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 py-12 px-6 text-center">
          <Play className="h-12 w-12 text-muted-foreground mb-3" aria-hidden />
          <h2 className="text-lg font-medium text-foreground">Configure and run your first query</h2>
          <p className="mt-1 text-sm text-muted-foreground max-w-sm">
            Add a model above, set your system prompt, and click Start Run to begin.
          </p>
        </div>
      )}

      {/* Section 2: Run Progress */}
      {activeRuns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Run Progress</CardTitle>
            <CardDescription>
              Live progress for current runs. Results appear when runs complete.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {activeRuns.map((run) => {
              const total = run.total_prompts;
              const completed = run.completed_prompts;
              const errorCount = run.error_count;
              const progressPct = total > 0 ? (completed / total) * 100 : 0;
              const isRunning = run.status === "running" || run.status === "pending";
              const errorLog = runErrorLogs[run.id];
              return (
                <Card key={run.id} className="bg-muted/20">
                  <CardContent className="pt-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">
                          {run.model_provider}/{run.model_id}
                        </span>
                        <Badge
                          variant={
                            run.status === "completed"
                              ? "default"
                              : run.status === "failed"
                                ? "destructive"
                                : run.status === "cancelled"
                                  ? "secondary"
                                  : "secondary"
                          }
                          className={cn(
                            isRunning && "animate-pulse bg-blue-500 text-white border-0"
                          )}
                        >
                          {run.status}
                        </Badge>
                      </div>
                      {isRunning && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCancelRunId(run.id)}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                    <Progress value={progressPct} className="h-2" />
                    <p className="text-sm text-muted-foreground">
                      {completed}/{total} completed
                      {errorCount > 0 && ` | ${errorCount} errors`}
                    </p>
                    {(run.progress_message || (isRunning && total > 0)) && (
                      <p className={cn(
                        "text-sm",
                        run.status === "failed" ? "text-destructive font-medium" : "text-muted-foreground"
                      )}>
                        {run.progress_message ||
                          (isRunning && completed === 0 ? "Starting…" : "Running…")}
                      </p>
                    )}
                    {(errorLog || (errorCount > 0 && run.status !== "running")) && (
                      <div>
                        <button
                          type="button"
                          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                          onClick={() => toggleErrorExpand(run.id)}
                        >
                          {expandedErrors.has(run.id) ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          Error log
                        </button>
                        {expandedErrors.has(run.id) && (
                          <pre className="mt-1 p-2 rounded bg-destructive/10 text-destructive text-xs overflow-auto max-h-32">
                            {errorLog ??
                              `${errorCount} error(s) occurred during the run.`}
                          </pre>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
            {allRunsComplete && (
              <div className="pt-2">
                <Link href={`/project/${projectId}/results`}>
                  <Button>View Results →</Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Previous runs */}
      <Card>
        <CardHeader>
          <CardTitle>Previous Runs</CardTitle>
          <CardDescription>
            Past runs for this project. Click to see details.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {previousRuns.length === 0 ? (
            <p className="text-sm text-muted-foreground">No runs yet.</p>
          ) : (
            <ul className="space-y-2">
              {previousRuns.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className={cn(
                      "w-full text-left rounded-md border p-3 transition-colors hover:bg-muted/50",
                      selectedPastRunId === r.id && "ring-2 ring-primary"
                    )}
                    onClick={() =>
                      setSelectedPastRunId((id) => (id === r.id ? null : r.id))
                    }
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-sm">
                        {r.model_provider}/{r.model_id}
                      </span>
                      <Badge
                        variant={
                          r.status === "completed"
                            ? "default"
                            : r.status === "failed"
                              ? "destructive"
                              : r.status === "cancelled"
                                ? "secondary"
                                : "secondary"
                        }
                      >
                        {r.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {r.completed_prompts}/{r.total_prompts} prompts
                      {r.error_count > 0 && ` · ${r.error_count} errors`} ·{" "}
                      {r.started_at
                        ? new Date(r.started_at).toLocaleString()
                        : "—"}
                    </div>
                    {selectedPastRunId === r.id && (
                      <div className="mt-2 text-xs text-muted-foreground">
                        Run ID: {r.id}
                      </div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
