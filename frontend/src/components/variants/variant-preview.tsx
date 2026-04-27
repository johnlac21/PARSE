"use client";

/**
 * Modal that shows generated variant samples: preview with first 3 prompts,
 * table grouped by original prompt, summary stats, and "Generate All Variants" action.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Check, Minus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import type { GrammarConfig, TypoConfig, VariantPreview } from "@/lib/types";
import { useProjectStore } from "@/store/project-store";
import { cn } from "@/lib/utils";

const PREVIEW_SAMPLE_SIZE = 3;

export interface VariantPreviewProps {
  projectId: string;
  grammarConfig: GrammarConfig;
  typoConfig: TypoConfig;
  totalPromptCount: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Highlight differing words between original and transformed (simple word-level diff). */
function TransformedWithHighlight({
  original,
  transformed,
  changed,
}: {
  original: string;
  transformed: string;
  changed: boolean;
}) {
  if (!changed || original === transformed) {
    return <span className="font-mono text-sm">{transformed}</span>;
  }
  const oWords = original.split(/\s+/);
  const tWords = transformed.split(/\s+/);
  const maxLen = Math.max(oWords.length, tWords.length);
  const parts: React.ReactNode[] = [];
  for (let i = 0; i < maxLen; i++) {
    const ow = oWords[i] ?? "";
    const tw = tWords[i] ?? "";
    const isDiff = ow !== tw;
    if (tw) {
      if (isDiff) {
        parts.push(
          <strong
            key={i}
            className="font-semibold text-amber-700 dark:text-amber-400 bg-amber-100/80 dark:bg-amber-900/30 rounded px-0.5"
          >
            {tw}
          </strong>
        );
      } else {
        parts.push(<span key={i}>{tw}</span>);
      }
      if (i < maxLen - 1) parts.push(" ");
    }
  }
  return <span className="font-mono text-sm">{parts}</span>;
}

/** Group variants by original_text. */
function groupByOriginalPrompt(variants: VariantPreview[]): Map<string, VariantPreview[]> {
  const map = new Map<string, VariantPreview[]>();
  for (const v of variants) {
    const key = v.original_text;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(v);
  }
  return map;
}

export function VariantPreviewModal({
  projectId,
  grammarConfig,
  typoConfig,
  totalPromptCount,
  open,
  onOpenChange,
}: VariantPreviewProps) {
  const router = useRouter();
  const setVariantsGenerated = useProjectStore((s) => s.setVariantsGenerated);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [previewData, setPreviewData] = React.useState<{
    variants: VariantPreview[];
    total_variant_count: number;
    sampleTexts: string[];
  } | null>(null);
  const [generateConfirmOpen, setGenerateConfirmOpen] = React.useState(false);
  const [generating, setGenerating] = React.useState(false);
  const [generateSuccess, setGenerateSuccess] = React.useState<number | null>(null);

  const fetchPreview = React.useCallback(async () => {
    if (!open || !projectId) return;
    setLoading(true);
    setError(null);
    setPreviewData(null);
    setGenerateSuccess(null);
    try {
      const { prompts } = await api.getPrompts(projectId, 1);
      const sampleTexts = prompts
        .slice(0, PREVIEW_SAMPLE_SIZE)
        .map((p) => p.prompt_text)
        .filter(Boolean);
      if (sampleTexts.length === 0) {
        setError("No prompts found to preview.");
        setLoading(false);
        return;
      }
      const res = await api.previewVariants({
        texts: sampleTexts,
        grammar_features: grammarConfig.grammarFeatures,
        grammar_mode: grammarConfig.grammarMode,
        typo_features: typoConfig.typoFeatures,
        typo_word_p: typoConfig.wordP,
        typo_char_p: typoConfig.charP,
        seed: typoConfig.seed,
      });
      setPreviewData({
        variants: res.variants,
        total_variant_count: res.total_variant_count,
        sampleTexts,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load preview.");
    } finally {
      setLoading(false);
    }
  }, [open, projectId, grammarConfig, typoConfig]);

  React.useEffect(() => {
    if (open) fetchPreview();
  }, [open, fetchPreview]);

  const grouped = React.useMemo(() => {
    if (!previewData?.variants.length) return new Map<string, VariantPreview[]>();
    return groupByOriginalPrompt(previewData.variants);
  }, [previewData?.variants]);

  const variantTypeCount = React.useMemo(() => {
    if (!previewData?.variants.length) return 0;
    const types = new Set(previewData.variants.map((v) => v.variant_type || v.variant_id));
    return types.size;
  }, [previewData?.variants]);

  const totalToGenerate = variantTypeCount * totalPromptCount;

  const handleGenerateAll = React.useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await api.generateVariants({
        project_id: projectId,
        grammar_features: grammarConfig.grammarFeatures,
        grammar_mode: grammarConfig.grammarMode,
        typo_features: typoConfig.typoFeatures,
        typo_word_p: typoConfig.wordP,
        typo_char_p: typoConfig.charP,
        seed: typoConfig.seed,
      });
      setVariantsGenerated(true);
      setGenerateSuccess(res.variants_generated);
      toast.success(`Generated ${res.variants_generated} variants`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to generate variants.";
      setError(msg);
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  }, [projectId, grammarConfig, typoConfig, setVariantsGenerated]);

  const handleClose = React.useCallback(() => {
    onOpenChange(false);
    if (generateSuccess != null) {
      router.push(`/project/${projectId}/run`);
    }
  }, [onOpenChange, generateSuccess, projectId, router]);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Variant preview</DialogTitle>
          </DialogHeader>

          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 p-3">{error}</p>
          )}

          {!loading && !error && previewData && (
            <div className="flex flex-col gap-4 overflow-hidden">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-muted-foreground">
                <p>
                  Previewing {Math.min(PREVIEW_SAMPLE_SIZE, previewData.sampleTexts.length)} of{" "}
                  {totalPromptCount} prompts
                </p>
                <p>
                  {variantTypeCount} variant type{variantTypeCount !== 1 ? "s" : ""} × {totalPromptCount}{" "}
                  prompts = {totalToGenerate} total variants to generate
                </p>
              </div>

              <div className="border rounded-md overflow-auto flex-1 min-h-0 max-h-[50vh]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[18%]">Original prompt</TableHead>
                      <TableHead className="w-[12%]">Variant type</TableHead>
                      <TableHead className="w-[18%]">Feature(s) applied</TableHead>
                      <TableHead className="w-[42%]">Transformed text</TableHead>
                      <TableHead className="w-[10%] text-center">Changed?</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.from(grouped.entries()).map(([originalText, rows]) => (
                      <React.Fragment key={originalText.slice(0, 80)}>
                        {rows.map((v, i) => (
                          <TableRow
                            key={`${v.variant_id}-${v.original_text.slice(0, 40)}-${i}`}
                            className={cn(i === 0 && "border-t-2 border-t-border")}
                          >
                            {i === 0 ? (
                              <TableCell
                                rowSpan={rows.length}
                                className="align-top font-mono text-xs bg-muted/30 border-r"
                              >
                                {originalText.length > 120
                                  ? `${originalText.slice(0, 120)}…`
                                  : originalText}
                              </TableCell>
                            ) : null}
                            <TableCell className="font-mono text-xs">
                              {v.variant_type || v.variant_id}
                            </TableCell>
                            <TableCell className="text-xs">
                              {v.features_applied?.length
                                ? v.features_applied.join(", ")
                                : "—"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              <TransformedWithHighlight
                                original={v.original_text}
                                transformed={v.transformed_text}
                                changed={v.changes_made}
                              />
                            </TableCell>
                            <TableCell className="text-center">
                              {v.changes_made ? (
                                <Check className="h-4 w-4 text-green-600 dark:text-green-400 inline" />
                              ) : (
                                <Minus className="h-4 w-4 text-muted-foreground inline" />
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          <DialogFooter className="flex-shrink-0 gap-2">
            {generateSuccess != null ? (
              <>
                <p className="text-sm text-muted-foreground mr-auto">
                  Generated {generateSuccess} variants! Proceed to Run Queries →
                </p>
                <Button onClick={handleClose}>Proceed to Run Queries</Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Close
                </Button>
                <Button
                  disabled={!previewData || generating}
                  onClick={() => setGenerateConfirmOpen(true)}
                >
                  {generating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Generating…
                    </>
                  ) : (
                    "Generate All Variants"
                  )}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation dialog for Generate All */}
      <Dialog open={generateConfirmOpen} onOpenChange={setGenerateConfirmOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Generate all variants?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will generate {totalToGenerate} variants for {totalPromptCount} prompts. Continue?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGenerateConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                setGenerateConfirmOpen(false);
                handleGenerateAll();
              }}
              disabled={generating}
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Generating…
                </>
              ) : (
                "Continue"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
