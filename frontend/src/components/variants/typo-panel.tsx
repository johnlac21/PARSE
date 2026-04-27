"use client";

/**
 * Typos tab content: select typo types, global word/char probability and seed, live preview.
 */

import * as React from "react";
import { Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import type { TypoFeature, VariantPreview } from "@/lib/types";
import { cn } from "@/lib/utils";

const WORD_P_DEFAULT = 0.15;
const CHAR_P_DEFAULT = 0.6;
const SEED_DEFAULT = 42;
const PREVIEW_DEBOUNCE_MS = 300;

export interface TypoPanelProps {
  /** First sample prompt text for live preview (e.g. from project upload). */
  samplePromptText?: string;
  /** Selected typo feature IDs (controlled). */
  selectedTypos: string[];
  /** Callback when selection changes. */
  onSelectedTyposChange: (ids: string[]) => void;
  /** Word probability (0–1). */
  wordP: number;
  onWordPChange: (v: number) => void;
  /** Character probability (0–1). */
  charP: number;
  onCharPChange: (v: number) => void;
  /** Seed for reproducibility. */
  seed: number;
  onSeedChange: (v: number) => void;
  className?: string;
}

export function TypoPanel({
  samplePromptText,
  selectedTypos,
  onSelectedTyposChange,
  wordP,
  onWordPChange,
  charP,
  onCharPChange,
  seed,
  onSeedChange,
  className,
}: TypoPanelProps) {
  const [features, setFeatures] = React.useState<TypoFeature[]>([]);
  const [featuresLoading, setFeaturesLoading] = React.useState(true);
  const [previewResults, setPreviewResults] = React.useState<VariantPreview[]>([]);
  const [previewLoading, setPreviewLoading] = React.useState(false);

  const selectedSet = React.useMemo(
    () => new Set(selectedTypos),
    [selectedTypos]
  );

  React.useEffect(() => {
    let cancelled = false;
    setFeaturesLoading(true);
    api
      .getTypoFeatures()
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

  const toggleTypo = React.useCallback(
    (id: string) => {
      if (selectedSet.has(id)) {
        onSelectedTyposChange(selectedTypos.filter((s) => s !== id));
      } else {
        onSelectedTyposChange([...selectedTypos, id]);
      }
    },
    [selectedSet, selectedTypos, onSelectedTyposChange]
  );

  const fetchPreview = React.useCallback(async () => {
    const text = (samplePromptText ?? "").trim();
    if (!text) {
      setPreviewResults([]);
      return;
    }
    setPreviewLoading(true);
    try {
      const { variants } = await api.previewVariants({
        texts: [text],
        typo_features: selectedTypos,
        typo_word_p: wordP,
        typo_char_p: charP,
        seed,
      });
      setPreviewResults(variants);
    } catch {
      setPreviewResults([]);
    } finally {
      setPreviewLoading(false);
    }
  }, [samplePromptText, selectedTypos, wordP, charP, seed]);

  const debouncedFetch = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(() => {
    if (debouncedFetch.current) clearTimeout(debouncedFetch.current);
    const text = (samplePromptText ?? "").trim();
    if (!text) {
      setPreviewResults([]);
      return;
    }
    debouncedFetch.current = setTimeout(() => {
      debouncedFetch.current = null;
      fetchPreview();
    }, PREVIEW_DEBOUNCE_MS);
    return () => {
      if (debouncedFetch.current) clearTimeout(debouncedFetch.current);
    };
  }, [samplePromptText, selectedTypos, wordP, charP, seed, fetchPreview]);

  const selectedCount = selectedTypos.length;

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Typo Types List */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="max-h-[320px] overflow-y-auto bg-card">
          {featuresLoading && (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              Loading typo features…
            </div>
          )}
          {!featuresLoading && features.length === 0 && (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No typo features available.
            </div>
          )}
          {!featuresLoading &&
            features.map((f) => (
              <div
                key={f.id}
                className="flex items-start gap-3 border-b border-border p-3 last:border-b-0"
              >
                <Switch
                  checked={selectedSet.has(f.id)}
                  onCheckedChange={() => toggleTypo(f.id)}
                  className="shrink-0 mt-0.5"
                />
                <div className="flex-1 min-w-0 space-y-1">
                  <span className="font-semibold text-sm">{f.name}</span>
                  <p className="text-xs text-muted-foreground">{f.description}</p>
                  {f.example && (
                    <p className="font-mono text-xs text-muted-foreground bg-muted/50 rounded px-1.5 py-0.5 inline-block">
                      {f.example}
                    </p>
                  )}
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Global Settings */}
      <div className="space-y-4 rounded-lg border border-border p-4 bg-card">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">
              Probability of each word being affected
            </Label>
            <span className="text-sm text-muted-foreground tabular-nums">
              {wordP}
            </span>
          </div>
          <Slider
            value={[wordP]}
            onValueChange={([v]) => onWordPChange(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">
              Probability of each character within a word being affected
            </Label>
            <span className="text-sm text-muted-foreground tabular-nums">
              {charP}
            </span>
          </div>
          <Slider
            value={[charP]}
            onValueChange={([v]) => onCharPChange(v)}
            min={0}
            max={1}
            step={0.05}
          />
        </div>
        <div className="space-y-2">
          <Label className="text-sm font-medium">Seed</Label>
          <Input
            type="number"
            value={seed}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") {
                onSeedChange(SEED_DEFAULT);
                return;
              }
              const n = parseInt(raw, 10);
              if (!Number.isNaN(n)) onSeedChange(n);
            }}
            className="w-24"
          />
          <p className="text-xs text-muted-foreground">
            Fixed seed ensures reproducible results
          </p>
        </div>
      </div>

      {/* Live Preview */}
      <div className="rounded-lg border border-border overflow-hidden bg-card">
        <div className="px-4 py-2 border-b border-border bg-muted/30">
          <span className="text-sm font-medium">Live preview</span>
        </div>
        <div className="p-4">
          {!samplePromptText?.trim() ? (
            <p className="text-sm text-muted-foreground">
              Upload prompts to see a live preview with your first sample.
            </p>
          ) : (
            <>
              {previewLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Updating preview…
                </div>
              )}
              {previewResults.length === 0 && !previewLoading && (
                <p className="text-sm text-muted-foreground">
                  Select at least one typo type to see preview.
                </p>
              )}
              {previewResults.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Typo type</TableHead>
                      <TableHead>Before</TableHead>
                      <TableHead>After</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {previewResults.map((v, i) => (
                      <TableRow key={`${v.variant_id}-${i}`}>
                        <TableCell className="font-medium">
                          {v.variant_type || v.variant_id}
                        </TableCell>
                        <TableCell className="font-mono text-xs max-w-[200px] truncate" title={v.original_text}>
                          {v.original_text}
                        </TableCell>
                        <TableCell className="font-mono text-xs max-w-[200px] truncate" title={v.transformed_text}>
                          {v.transformed_text}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </>
          )}
        </div>
      </div>

      {/* Summary Footer */}
      <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
        <span className="text-sm text-muted-foreground">
          {selectedCount} typo type{selectedCount !== 1 ? "s" : ""} selected | Word
          prob: {wordP}, Char prob: {charP}, Seed: {seed}
        </span>
      </div>
    </div>
  );
}
