"use client";

import * as React from "react";
import Link from "next/link";
import { BarChart3 } from "lucide-react";
import { SummaryCards } from "@/components/analysis/summary-cards";
import { RunSelector } from "@/components/analysis/run-selector";
import { DifferenceTable, flattenDifference } from "@/components/analysis/difference-table";
import { DirectionalBiasTable, flattenDirectionalBias } from "@/components/analysis/directional-bias-table";
import { CompletenessTable, flattenCompleteness } from "@/components/analysis/completeness-table";
import { RawDataTable } from "@/components/analysis/raw-data-table";
import { HeatmapChart } from "@/components/analysis/heatmap-chart";
import { DifferenceBarChart } from "@/components/analysis/bar-chart";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useProjectStore } from "@/store/project-store";
import { api } from "@/lib/api-client";

export default function ResultsPage() {
  const project = useProjectStore((s) => s.currentProject);
  const projectLoading = useProjectStore((s) => s.projectLoading);
  const runs = useProjectStore((s) => s.runs);
  const selectedRunIds = useProjectStore((s) => s.selectedRunIds);
  const setSelectedRuns = useProjectStore((s) => s.setSelectedRuns);

  const [completenessData, setCompletenessData] = React.useState<
    Record<string, Record<string, { total: number; valid: number; valid_rate: number }>>
  >({});
  const [completenessLoading, setCompletenessLoading] = React.useState(false);
  const [differenceData, setDifferenceData] = React.useState<
    Record<string, Record<string, unknown>>
  >({});
  const [differenceLoading, setDifferenceLoading] = React.useState(false);
  const [directionalData, setDirectionalData] = React.useState<
    Record<string, Record<string, unknown>>
  >({});
  const [directionalLoading, setDirectionalLoading] = React.useState(false);
  const [visualizationModel, setVisualizationModel] = React.useState<string | null>(null);

  const projectId = project?.id ?? null;
  const selectedRunIdsSet = React.useMemo(() => new Set(selectedRunIds), [selectedRunIds]);
  const selectedIdsArray = selectedRunIds;

  const completedRuns = React.useMemo(
    () => runs.filter((r) => r.status === "completed"),
    [runs]
  );

  // When there are completed runs and none selected, auto-select them so data loads immediately
  React.useEffect(() => {
    if (completedRuns.length > 0 && selectedRunIds.length === 0) {
      setSelectedRuns(completedRuns.map((r) => r.id));
    }
  }, [completedRuns.length, selectedRunIds.length, setSelectedRuns, completedRuns]);

  const handleSelectionChange = React.useCallback(
    (ids: Set<string>) => {
      setSelectedRuns(Array.from(ids));
    },
    [setSelectedRuns]
  );

  // Fetch completeness when selection changes (for summary stats + table)
  React.useEffect(() => {
    if (!projectId || selectedIdsArray.length === 0) {
      setCompletenessData({});
      return;
    }
    setCompletenessLoading(true);
    api
      .runCompleteness(projectId, selectedIdsArray)
      .then((data) => {
        setCompletenessData(data as Record<string, Record<string, { total: number; valid: number; valid_rate: number }>>);
      })
      .catch(() => setCompletenessData({}))
      .finally(() => setCompletenessLoading(false));
  }, [projectId, selectedIdsArray.join(",")]);

  // Fetch difference when selection changes
  React.useEffect(() => {
    if (!projectId || selectedIdsArray.length === 0) {
      setDifferenceData({});
      return;
    }
    setDifferenceLoading(true);
    api
      .runDifference(projectId, selectedIdsArray)
      .then(setDifferenceData)
      .catch(() => setDifferenceData({}))
      .finally(() => setDifferenceLoading(false));
  }, [projectId, selectedIdsArray.join(",")]);

  // Fetch directional bias when selection changes
  React.useEffect(() => {
    if (!projectId || selectedIdsArray.length === 0) {
      setDirectionalData({});
      return;
    }
    setDirectionalLoading(true);
    api
      .runDirectionalBias(projectId, selectedIdsArray)
      .then(setDirectionalData)
      .catch(() => setDirectionalData({}))
      .finally(() => setDirectionalLoading(false));
  }, [projectId, selectedIdsArray.join(",")]);

  const completenessRows = React.useMemo(
    () => flattenCompleteness(completenessData as Parameters<typeof flattenCompleteness>[0]),
    [completenessData]
  );
  const differenceRows = React.useMemo(
    () => flattenDifference(differenceData as Parameters<typeof flattenDifference>[0]),
    [differenceData]
  );
  const directionalRows = React.useMemo(
    () => flattenDirectionalBias(directionalData as Parameters<typeof flattenDirectionalBias>[0]),
    [directionalData]
  );

  const summaryStats = React.useMemo(() => {
    let totalPrompts = 0;
    const models = new Set<string>();
    const variants = new Set<string>();
    let totalValid = 0;
    for (const [modelId, variantsMap] of Object.entries(completenessData)) {
      if (!variantsMap || typeof variantsMap !== "object") continue;
      models.add(modelId);
      for (const [variantId, v] of Object.entries(variantsMap)) {
        if (!v || typeof v !== "object") continue;
        variants.add(variantId);
        const total = (v as { total?: number }).total ?? 0;
        const valid = (v as { valid?: number }).valid ?? 0;
        totalPrompts += total;
        totalValid += valid;
      }
    }
    const completionPct =
      totalPrompts > 0 ? Math.round((totalValid / totalPrompts) * 100) : 0;
    return [
      { label: "Total Prompts", value: totalPrompts, sub: "In selected runs" },
      { label: "Models Tested", value: models.size, sub: "" },
      { label: "Variant Types", value: variants.size, sub: "" },
      { label: "Completion Rate", value: `${completionPct}%`, sub: "Valid responses" },
    ];
  }, [completenessData]);

  if (projectLoading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-56" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-10 w-full max-w-xs" />
            <Skeleton className="h-48 w-full" />
          </CardContent>
        </Card>
        <Skeleton className="h-24 w-full max-w-2xl" />
        <div className="flex gap-2">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-10 w-32" />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <p className="text-sm text-muted-foreground">Project not found.</p>
    );
  }

  if (completedRuns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 py-16 px-6 text-center">
        <BarChart3 className="h-14 w-14 text-muted-foreground mb-4" aria-hidden />
        <h2 className="text-lg font-medium text-foreground">No results yet</h2>
        <p className="mt-1 text-sm text-muted-foreground max-w-sm">
          Complete a run to see results here. Go to Run Queries to start.
        </p>
        <Link href={`/project/${projectId}/run`}>
          <Button variant="outline" className="mt-6">Go to Run Queries</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <RunSelector
        runs={runs}
        selectedRunIds={selectedRunIdsSet}
        onSelectionChange={handleSelectionChange}
      />
      <SummaryCards stats={summaryStats} />

      <Tabs defaultValue="completeness" className="space-y-4">
        <TabsList>
          <TabsTrigger value="completeness">Completeness</TabsTrigger>
          <TabsTrigger value="difference">Difference</TabsTrigger>
          <TabsTrigger value="directional">Directional Bias</TabsTrigger>
          <TabsTrigger value="visualizations">Visualizations</TabsTrigger>
          <TabsTrigger value="raw">Raw Data</TabsTrigger>
        </TabsList>

        <TabsContent value="completeness" className="space-y-4">
          <CompletenessTable
            rows={completenessRows}
            loading={completenessLoading}
            projectId={projectId ?? undefined}
            runIds={selectedIdsArray}
          />
        </TabsContent>

        <TabsContent value="difference" className="space-y-4">
          <DifferenceTable
            rows={differenceRows}
            loading={differenceLoading}
            projectId={projectId ?? undefined}
            runIds={selectedIdsArray}
          />
        </TabsContent>

        <TabsContent value="directional" className="space-y-4">
          <DirectionalBiasTable
            rows={directionalRows}
            loading={directionalLoading}
            projectId={projectId ?? undefined}
            runIds={selectedIdsArray}
          />
        </TabsContent>

        <TabsContent value="visualizations" className="space-y-6">
          <HeatmapChart
            differenceRows={differenceRows}
            directionalRows={directionalRows}
            completenessRows={completenessRows}
            loading={
              differenceLoading ||
              directionalLoading ||
              completenessLoading
            }
          />
          <div>
            <h3 className="mb-2 text-sm font-medium">
              Difference by variant (select model)
            </h3>
            <DifferenceBarChart
              rows={differenceRows}
              selectedModel={visualizationModel}
              onModelChange={setVisualizationModel}
              loading={differenceLoading}
            />
          </div>
        </TabsContent>

        <TabsContent value="raw" className="space-y-4">
          <RawDataTable
            projectId={project.id}
            selectedRunIds={selectedIdsArray}
            variantOptions={Array.from(
              new Set(completenessRows.map((r) => r.variant))
            ).sort()}
            modelOptions={Array.from(
              new Set(completenessRows.map((r) => r.model))
            ).sort()}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
