"use client";

/**
 * Grammar tab content: browse, search, select grammar features, check applicability, configure combination mode.
 */

import * as React from "react";
import { Search, Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api } from "@/lib/api-client";
import type { GrammarFeature, ApplicabilityResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const CATEGORY_OPTIONS = [
  "All",
  "morphosyntactic",
  "verbal",
  "nominal",
  "negation",
  "phonological",
  "pronominal",
] as const;

const TIER_OPTIONS = [
  { value: "all", label: "All" },
  { value: "1", label: "Tier 1 (Regex)" },
  { value: "2", label: "Tier 2 (Advanced)" },
] as const;

export type CombinationMode = "individual" | "all_combinations" | "bundle";

export interface GrammarPanelProps {
  projectId: string;
  promptCount: number;
  selectedFeatureIds: string[];
  onSelectionChange: (ids: string[]) => void;
  combinationMode: CombinationMode;
  onCombinationModeChange: (mode: CombinationMode) => void;
  onPreviewClick?: () => void;
  /** When provided, scan state is persisted (e.g. in project store) so it survives tab switches. */
  storedApplicabilityResults?: Record<string, ApplicabilityResult>;
  storedScanned?: boolean;
  storedScanLoading?: boolean;
  onGrammarConfigUpdate?: (update: {
    applicabilityResults?: Record<string, ApplicabilityResult>;
    scanned?: boolean;
    scanLoading?: boolean;
  }) => void;
  className?: string;
}

function ApplicabilityBadge({
  result,
  totalPrompts,
}: {
  result: ApplicabilityResult | undefined;
  totalPrompts: number;
}) {
  if (result == null) {
    return (
      <span className="text-xs text-muted-foreground">Not scanned</span>
    );
  }
  const { total_applicable, total_prompts } = result;
  const pct = total_prompts > 0 ? (total_applicable / total_prompts) * 100 : 0;
  const variant =
    pct > 80 ? "green" : pct >= 30 ? "yellow" : pct > 0 ? "red" : "gray";
  const colorClass =
    variant === "green"
      ? "text-emerald-600 dark:text-emerald-400"
      : variant === "yellow"
        ? "text-amber-600 dark:text-amber-400"
        : variant === "red"
          ? "text-red-600 dark:text-red-400"
          : "text-muted-foreground";
  return (
    <span className={cn("text-xs font-medium", colorClass)}>
      Applies to {total_applicable}/{total_prompts} prompts
    </span>
  );
}

export function GrammarPanel({
  projectId,
  promptCount,
  selectedFeatureIds,
  onSelectionChange,
  combinationMode,
  onCombinationModeChange,
  onPreviewClick,
  storedApplicabilityResults,
  storedScanned = false,
  storedScanLoading = false,
  onGrammarConfigUpdate,
  className,
}: GrammarPanelProps) {
  const [features, setFeatures] = React.useState<GrammarFeature[]>([]);
  const [featuresLoading, setFeaturesLoading] = React.useState(true);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [categoryFilter, setCategoryFilter] = React.useState<string>("All");
  const [tierFilter, setTierFilter] = React.useState<string>("all");
  const [localApplicabilityResults, setLocalApplicabilityResults] = React.useState<
    Map<string, ApplicabilityResult>
  >(new Map());
  const [localScanned, setLocalScanned] = React.useState(false);
  const [localScanLoading, setLocalScanLoading] = React.useState(false);

  const useStore = onGrammarConfigUpdate != null;
  const applicabilityResultsMap = React.useMemo(() => {
    const record = useStore ? storedApplicabilityResults : null;
    if (record && Object.keys(record).length > 0) {
      return new Map(Object.entries(record));
    }
    return useStore ? new Map() : localApplicabilityResults;
  }, [useStore, storedApplicabilityResults, localApplicabilityResults]);
  const scanned = useStore ? storedScanned : localScanned;
  const scanLoading = useStore ? storedScanLoading : localScanLoading;

  const selectedSet = React.useMemo(
    () => new Set(selectedFeatureIds),
    [selectedFeatureIds]
  );

  const runScan = React.useCallback(
    async (ids: string[]) => {
      if (useStore) {
        onGrammarConfigUpdate?.({ scanLoading: true });
      } else {
        setLocalScanLoading(true);
        setLocalScanned(false);
      }
      try {
        const { features: results } = await api.checkApplicability(projectId, ids);
        const record: Record<string, ApplicabilityResult> = {};
        results.forEach((r) => {
          record[r.feature_id] = r;
        });
        if (useStore) {
          onGrammarConfigUpdate?.({ applicabilityResults: record, scanned: true, scanLoading: false });
        } else {
          const map = new Map(Object.entries(record));
          setLocalApplicabilityResults(map);
          setLocalScanned(true);
        }
      } catch {
        if (useStore) {
          onGrammarConfigUpdate?.({ scanLoading: false });
        } else {
          setLocalApplicabilityResults(new Map());
        }
      } finally {
        if (!useStore) {
          setLocalScanLoading(false);
        }
      }
    },
    [projectId, useStore, onGrammarConfigUpdate]
  );

  // When not using store, auto-scan when we have prompts and features but no scan yet. When using store, the parent (configure page) runs the scan so it isn't cancelled on tab switch.
  React.useEffect(() => {
    if (useStore) return;
    if (
      promptCount === 0 ||
      features.length === 0 ||
      scanned ||
      scanLoading
    ) {
      return;
    }
    runScan(features.map((f) => f.id));
  }, [useStore, promptCount, features, scanned, scanLoading, runScan]);

  React.useEffect(() => {
    let cancelled = false;
    setFeaturesLoading(true);
    api
      .getGrammarFeatures()
      .then((list) => {
        if (!cancelled) setFeatures(list);
      })
      .catch(() => {
        if (!cancelled) setFeatures([]);
      })
      .finally(() => {
        if (!cancelled) setFeaturesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredFeatures = React.useMemo(() => {
    return features.filter((f) => {
      const q = searchQuery.trim().toLowerCase();
      if (q) {
        const match =
          f.name.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q);
        if (!match) return false;
      }
      if (categoryFilter !== "All" && f.category !== categoryFilter)
        return false;
      if (tierFilter !== "all") {
        const tierNum = parseInt(tierFilter, 10);
        if (f.tier !== tierNum) return false;
      }
      return true;
    });
  }, [features, searchQuery, categoryFilter, tierFilter]);

  const toggleFeature = React.useCallback(
    (id: string) => {
      if (selectedSet.has(id)) {
        onSelectionChange(selectedFeatureIds.filter((s) => s !== id));
      } else {
        onSelectionChange([...selectedFeatureIds, id]);
      }
    },
    [selectedSet, selectedFeatureIds, onSelectionChange]
  );

  const handleScan = React.useCallback(() => {
    const ids = selectedFeatureIds.length > 0 ? selectedFeatureIds : features.map((f) => f.id);
    runScan(ids);
  }, [selectedFeatureIds, features, runScan]);

  const selectedCount = selectedFeatureIds.length;
  const applicableCount = selectedFeatureIds.filter((id) => {
    const r = applicabilityResultsMap.get(id);
    return r && r.total_applicable > 0;
  }).length;
  /** How many of all grammar variants (features) apply to at least one prompt — for the prominent summary. */
  const totalVariantsApplicable = features.filter(
    (f) => (applicabilityResultsMap.get(f.id)?.total_applicable ?? 0) > 0
  ).length;
  const totalVariants = features.length;

  const variantCountPerPrompt =
    combinationMode === "individual"
      ? selectedCount
      : combinationMode === "all_combinations"
        ? selectedCount <= 0
          ? 0
          : Math.pow(2, selectedCount)
        : 1;
  const totalVariantsEstimate = promptCount * variantCountPerPrompt;

  const showCombinationsWarning =
    combinationMode === "all_combinations" && selectedCount > 10;

  return (
    <TooltipProvider>
      <div className={cn("flex flex-col gap-4", className)}>
        {/* Prominent applicability summary — how many grammar variants apply to prompts */}
        <div className="rounded-lg border border-border bg-muted/30 px-4 py-3">
          {scanLoading ? (
            <span className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              Checking which grammar variants apply to your prompts…
            </span>
          ) : scanned && promptCount > 0 ? (
            <p className="text-sm font-medium text-foreground">
              <span className="font-semibold tabular-nums">
                {totalVariantsApplicable} of {totalVariants}
              </span>{" "}
              grammar variants apply to your prompts
            </p>
          ) : promptCount > 0 ? (
            <p className="text-sm text-muted-foreground">
              Grammar applicability not yet scanned.
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Upload prompts to see how many grammar variants apply.
            </p>
          )}
        </div>

        {/* Search + Filter Bar */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search grammar features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
          <Select
            value={categoryFilter}
            onValueChange={setCategoryFilter}
          >
            <SelectTrigger className="w-[180px] h-9">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORY_OPTIONS.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={tierFilter} onValueChange={setTierFilter}>
            <SelectTrigger className="w-[160px] h-9">
              <SelectValue placeholder="Tier" />
            </SelectTrigger>
            <SelectContent>
              {TIER_OPTIONS.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Feature List */}
        <div className="rounded-lg border border-border overflow-hidden">
          <div className="max-h-[320px] overflow-y-auto bg-card">
            {featuresLoading && (
              <div className="flex items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                Loading features…
              </div>
            )}
            {!featuresLoading && filteredFeatures.length === 0 && (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No grammar features match your filters.
              </div>
            )}
            {!featuresLoading &&
              filteredFeatures.map((f) => {
                const result = applicabilityResultsMap.get(f.id);
                const applies = result ? result.total_applicable > 0 : null;
                const dimmed = applies === false;

                const row = (
                  <div
                    className={cn(
                      "flex items-start gap-3 border-b border-border p-3 last:border-b-0 transition-opacity",
                      dimmed && "opacity-60"
                    )}
                  >
                    <Switch
                      checked={selectedSet.has(f.id)}
                      onCheckedChange={() => toggleFeature(f.id)}
                      className="shrink-0 mt-0.5"
                    />
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-sm">{f.name}</span>
                        <Badge variant="secondary" className="text-xs">
                          {f.category}
                        </Badge>
                        {f.requires_pos_tags && (
                          <Badge variant="outline" className="text-xs text-amber-600 dark:text-amber-400 border-amber-300">
                            Requires spaCy
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {f.description}
                      </p>
                      {(f.example_std || f.example_var) && (
                        <p className="font-mono text-xs text-muted-foreground bg-muted/50 rounded px-1.5 py-0.5 inline-block">
                          SAE: {f.example_std || "—"} → Variant: {f.example_var || "—"}
                        </p>
                      )}
                      <ApplicabilityBadge
                        result={result}
                        totalPrompts={promptCount}
                      />
                    </div>
                  </div>
                );

                if (dimmed) {
                  return (
                    <Tooltip key={f.id}>
                      <TooltipTrigger asChild>
                        <div className="cursor-default w-full">{row}</div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>No matches in your prompts</p>
                      </TooltipContent>
                    </Tooltip>
                  );
                }
                return <React.Fragment key={f.id}>{row}</React.Fragment>;
              })}
          </div>
        </div>

        {/* Re-scan option (scan runs automatically; manual re-scan if needed) */}
        {promptCount > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <button
              type="button"
              onClick={handleScan}
              disabled={scanLoading}
              className="underline underline-offset-2 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring rounded"
            >
              Re-scan applicability
            </button>
            {scanned && selectedCount > 0 && (
              <span>
                · {applicableCount} of {selectedCount} selected apply
              </span>
            )}
          </div>
        )}

        {/* Combination Mode */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Combination mode</Label>
          <div
            role="radiogroup"
            aria-label="Combination mode"
            className="flex flex-col gap-2"
          >
            {(
              [
                {
                  value: "individual" as const,
                  label: "Individual (one variant per feature)",
                },
                {
                  value: "all_combinations" as const,
                  label: "All Combinations (2^n)",
                },
                { value: "bundle" as const, label: "Bundle (all at once)" },
              ] as const
            ).map(({ value, label }) => (
              <label
                key={value}
                className={cn(
                  "flex items-center gap-2 rounded-md border border-border px-3 py-2 cursor-pointer transition-colors hover:bg-muted/50",
                  combinationMode === value && "border-primary bg-primary/5"
                )}
              >
                <input
                  type="radio"
                  name="combinationMode"
                  value={value}
                  checked={combinationMode === value}
                  onChange={() => onCombinationModeChange(value)}
                  className="h-4 w-4 text-primary border-input"
                />
                <span className="text-sm">{label}</span>
              </label>
            ))}
          </div>
          {showCombinationsWarning && (
            <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
              This will generate {variantCountPerPrompt} variants per prompt.
              Consider reducing features.
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            Estimated variants per prompt: {variantCountPerPrompt} · Total:{" "}
            {totalVariantsEstimate.toLocaleString()}
          </p>
        </div>

        {/* Selection Summary (sticky footer) */}
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
          <span className="text-sm text-muted-foreground">
            {selectedCount} features selected | Mode:{" "}
            {combinationMode === "individual"
              ? "Individual"
              : combinationMode === "all_combinations"
                ? "All Combinations"
                : "Bundle"}{" "}
            | Estimated: {variantCountPerPrompt} per prompt,{" "}
            {totalVariantsEstimate.toLocaleString()} total
          </span>
          {onPreviewClick && (
            <Button variant="outline" size="sm" onClick={onPreviewClick}>
              Preview
            </Button>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
