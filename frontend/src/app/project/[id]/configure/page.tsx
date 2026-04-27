"use client";

/**
 * Configure page: Upload section (top) + Variant Configuration (below, only after prompts uploaded).
 * Upload can be full (drop zone) or collapsed ("X prompts loaded" + Re-upload).
 * Variant config is 3 tabs: Grammar | Typos | Dialect.
 * Sticky bottom bar: summary + Preview Variants + Generate & Continue.
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, FileSpreadsheet, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { CsvUpload } from "@/components/upload/csv-upload";
import {
  GrammarPanel,
  type CombinationMode,
} from "@/components/variants/grammar-panel";
import { TypoPanel } from "@/components/variants/typo-panel";
import { DialectPanel } from "@/components/variants/dialect-panel";
import { VariantPreviewModal } from "@/components/variants/variant-preview";
import { useProjectStore } from "@/store/project-store";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { api } from "@/lib/api-client";
import type { ApplicabilityResult } from "@/lib/types";

export default function ConfigurePage() {
  const params = useParams();
  const projectId = (params?.id as string) ?? "";
  const router = useRouter();
  const {
    currentProject: project,
    promptCount,
    projectLoading,
    grammarConfig,
    typoConfig,
    dialectConfig,
    updateGrammarConfig,
    updateTypoConfig,
    updateDialectConfig,
    setProject,
    setPromptCount,
    setVariantsGenerated,
  } = useProjectStore();

  const [showUploadExpanded, setShowUploadExpanded] = React.useState(false);
  /** Local sample from last upload for preview text (raw row). */
  const [uploadSample, setUploadSample] = React.useState<Record<string, unknown>[]>([]);
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [generateLoading, setGenerateLoading] = React.useState(false);
  const [reuploadConfirmOpen, setReuploadConfirmOpen] = React.useState(false);

  const hasPrompts = promptCount > 0;

  const grammarFeatureCount = grammarConfig.selectedFeatures.length;
  const typoCount = typoConfig.selectedTypos.length;
  const dialectCount = dialectConfig.selectedDialects.length;
  const summaryText =
    `Grammar: ${grammarFeatureCount} feature${grammarFeatureCount !== 1 ? "s" : ""} | Typos: ${typoCount} type${typoCount !== 1 ? "s" : ""} | Dialects: ${dialectCount}`;

  const handleDialectSelectionChange = React.useCallback(
    (ids: string[]) => updateDialectConfig({ selectedDialects: ids }),
    [updateDialectConfig]
  );

  const handleGenerateAndContinue = React.useCallback(async () => {
    setGenerateLoading(true);
    try {
      const res = await api.generateVariants({
        project_id: projectId,
        grammar_features: grammarConfig.selectedFeatures,
        grammar_mode: grammarConfig.mode,
        typo_features: typoConfig.selectedTypos,
        typo_word_p: typoConfig.wordP,
        typo_char_p: typoConfig.charP,
        seed: typoConfig.seed,
      });
      setVariantsGenerated(true);
      toast.success(`Generated ${res.variants_generated} variants`);
      router.push(`/project/${projectId}/run`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Variant generation failed";
      toast.error(msg);
    } finally {
      setGenerateLoading(false);
    }
  }, [projectId, grammarConfig, typoConfig, setVariantsGenerated, router]);

  const samplePromptText = React.useMemo(() => {
    const sample = uploadSample[0];
    if (!sample || typeof sample !== "object") return undefined;
    const obj = sample as Record<string, unknown>;
    const promptKeys = ["prompt_text", "prompt", "text", "content", "body"];
    for (const key of promptKeys) {
      const v = obj[key];
      if (typeof v === "string" && v.trim()) return v;
    }
    const first = Object.values(obj).find((v) => typeof v === "string" && (v as string).trim());
    return first as string | undefined;
  }, [uploadSample]);

  const showFullUpload = !hasPrompts || showUploadExpanded;

  useKeyboardShortcuts({
    onSave: () => {
      if (hasPrompts) toast.info("Config is applied when you click Generate & Continue.");
    },
    onSubmit: hasPrompts && !generateLoading ? () => handleGenerateAndContinue() : undefined,
    enabled: !!project && !projectLoading,
  });

  // When page has prompts but no applicability scan yet (e.g. opened project with existing prompts), run scan from here so it isn't cancelled when switching tabs.
  // scanLoading omitted from deps so that setting it to true doesn't re-run and cancel the in-flight request.
  React.useEffect(() => {
    if (
      !projectId ||
      promptCount === 0 ||
      grammarConfig.scanned
    ) {
      return;
    }
    if (grammarConfig.scanLoading) return; // already in progress (e.g. from handleUploadSuccess)
    let cancelled = false;
    updateGrammarConfig({ scanLoading: true });
    (async () => {
      try {
        const features = await api.getGrammarFeatures();
        const ids = features.map((f) => f.id);
        const { features: results } = await api.checkApplicability(projectId, ids);
        if (cancelled) return;
        const record: Record<string, ApplicabilityResult> = {};
        results.forEach((r) => {
          record[r.feature_id] = r;
        });
        updateGrammarConfig({ applicabilityResults: record, scanned: true, scanLoading: false });
      } catch {
        if (!cancelled) updateGrammarConfig({ scanLoading: false });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, promptCount, grammarConfig.scanned, updateGrammarConfig]);

  const handleUploadSuccess = React.useCallback(
    async (result: { prompts_loaded: number; columns_detected: string[]; sample: Record<string, unknown>[] }) => {
      setPromptCount(result.prompts_loaded);
      setUploadSample(result.sample.slice(0, 10));
      updateDialectConfig({ parameterColumns: result.columns_detected });
      updateGrammarConfig({ scanned: false, applicabilityResults: {}, scanLoading: true });
      setShowUploadExpanded(false);
      toast.success(`Loaded ${result.prompts_loaded} prompts`);
      try {
        const p = await api.getProject(projectId);
        setProject(p);
      } catch {
        // keep store as-is
      }
      // Run applicability scan in background so results persist across tab switches and aren't cancelled when leaving Grammar tab.
      (async () => {
        try {
          const features = await api.getGrammarFeatures();
          const ids = features.map((f) => f.id);
          const { features: results } = await api.checkApplicability(projectId, ids);
          const record: Record<string, ApplicabilityResult> = {};
          results.forEach((r) => {
            record[r.feature_id] = r;
          });
          updateGrammarConfig({ applicabilityResults: record, scanned: true, scanLoading: false });
        } catch {
          updateGrammarConfig({ scanLoading: false });
        }
      })();
    },
    [projectId, setPromptCount, setProject, updateDialectConfig, updateGrammarConfig]
  );

  if (projectLoading) {
    return (
      <div className="space-y-8">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-full max-w-md" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-10 w-40" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-full max-w-lg" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-full max-w-xs" />
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="space-y-8">
        <p className="text-sm text-muted-foreground">Project not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ——— Upload Section (always visible) ——— */}
      <Card>
        <CardHeader>
          <CardTitle>Prompts</CardTitle>
          <p className="text-sm text-muted-foreground">
            Upload a CSV or JSONL file with prompt IDs and prompt text. Columns can be mapped if auto-detection fails.
          </p>
        </CardHeader>
        <CardContent>
          {showFullUpload ? (
            <div className="space-y-2">
              {hasPrompts && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowUploadExpanded(false)}
                >
                  Cancel
                </Button>
              )}
              {!hasPrompts && (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 py-8 px-4 text-center">
                  <FileSpreadsheet className="h-12 w-12 text-muted-foreground mb-3" aria-hidden />
                  <p className="text-sm font-medium text-foreground">Upload a CSV to get started</p>
                  <p className="mt-1 text-xs text-muted-foreground max-w-sm">
                    Drop a .csv or .jsonl file with prompt text (and optional prompt_id, variant columns).
                  </p>
                </div>
              )}
              <CsvUpload
                projectId={projectId}
                onSuccess={handleUploadSuccess}
              />
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-muted/20 p-4">
              <p className="text-sm text-foreground">
                {promptCount} prompts loaded
                {dialectConfig.parameterColumns?.length
                  ? ` · Columns: ${dialectConfig.parameterColumns.join(", ")}`
                  : ""}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReuploadConfirmOpen(true)}
              >
                Re-upload
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ——— Variant Configuration (only when prompts exist) ——— */}
      {hasPrompts && (
        <Card>
          <CardHeader>
            <CardTitle>Variant configuration</CardTitle>
            <p className="text-sm text-muted-foreground">
              Configure grammar, typos, and dialect variants. Then generate variants to run queries.
            </p>
            {grammarFeatureCount === 0 && typoCount === 0 && dialectCount === 0 && (
              <div className="flex items-center gap-2 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
                <Sparkles className="h-4 w-4 shrink-0" />
                Configure and generate variants to continue to Run Queries.
              </div>
            )}
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="grammar" className="space-y-4">
              <TabsList>
                <TabsTrigger value="grammar">Grammar</TabsTrigger>
                <TabsTrigger value="typos">Typos</TabsTrigger>
                <TabsTrigger value="dialect">Dialect</TabsTrigger>
              </TabsList>
              <TabsContent value="grammar" className="space-y-4">
                <GrammarPanel
                  projectId={projectId}
                  promptCount={promptCount}
                  selectedFeatureIds={grammarConfig.selectedFeatures}
                  onSelectionChange={(ids) => updateGrammarConfig({ selectedFeatures: ids })}
                  combinationMode={grammarConfig.mode as CombinationMode}
                  onCombinationModeChange={(mode) => updateGrammarConfig({ mode })}
                  onPreviewClick={() => setPreviewOpen(true)}
                  storedApplicabilityResults={grammarConfig.applicabilityResults}
                  storedScanned={grammarConfig.scanned}
                  storedScanLoading={grammarConfig.scanLoading}
                  onGrammarConfigUpdate={updateGrammarConfig}
                />
              </TabsContent>
              <TabsContent value="typos" className="space-y-4">
                <TypoPanel
                  samplePromptText={samplePromptText}
                  selectedTypos={typoConfig.selectedTypos}
                  onSelectedTyposChange={(v) => updateTypoConfig({ selectedTypos: v })}
                  wordP={typoConfig.wordP}
                  onWordPChange={(v) => updateTypoConfig({ wordP: v })}
                  charP={typoConfig.charP}
                  onCharPChange={(v) => updateTypoConfig({ charP: v })}
                  seed={typoConfig.seed}
                  onSeedChange={(v) => updateTypoConfig({ seed: v })}
                />
              </TabsContent>
              <TabsContent value="dialect" className="space-y-4">
                <DialectPanel
                  promptCount={promptCount}
                  parameterColumns={dialectConfig.parameterColumns}
                  onSelectionChange={handleDialectSelectionChange}
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Sticky bottom action bar (when prompts exist) */}
      {hasPrompts && (
        <div className="sticky bottom-0 left-0 right-0 z-10 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 py-3 px-4 -mx-6 -mb-6 rounded-t-lg shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="flex flex-wrap items-center justify-between gap-4 max-w-4xl mx-auto">
            <p className="text-sm text-muted-foreground">{summaryText}</p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setPreviewOpen(true)}
              >
                Preview Variants
              </Button>
              <Button
                onClick={handleGenerateAndContinue}
                disabled={generateLoading}
              >
                {generateLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Generating…
                  </>
                ) : (
                  "Generate & Continue →"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Re-upload confirmation: overwrites existing prompts */}
      <Dialog open={reuploadConfirmOpen} onOpenChange={setReuploadConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Re-upload prompts?</DialogTitle>
            <DialogDescription>
              This will replace all existing prompts and any runs/results for this project. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReuploadConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setReuploadConfirmOpen(false);
                setShowUploadExpanded(true);
              }}
            >
              Re-upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Full variant preview modal (first 3 prompts, table, Generate All) */}
      <VariantPreviewModal
        projectId={projectId}
        grammarConfig={{
          grammarFeatures: grammarConfig.selectedFeatures,
          grammarMode: grammarConfig.mode,
        }}
        typoConfig={{
          typoFeatures: typoConfig.selectedTypos,
          wordP: typoConfig.wordP,
          charP: typoConfig.charP,
          seed: typoConfig.seed,
        }}
        totalPromptCount={promptCount}
        open={previewOpen}
        onOpenChange={setPreviewOpen}
      />
    </div>
  );
}
