"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api } from "@/lib/api-client";

export type ExportTableType = "difference" | "directional_bias" | "completeness";

/** Row shape for difference table */
export interface DifferenceExportRow {
  model: string;
  variant: string;
  differenceRate: number;
  se: number;
  tStat: number;
  pValue: number;
  ciLower: number;
  ciUpper: number;
  significance: string;
}

/** Row shape for directional bias table */
export interface DirectionalBiasExportRow {
  model: string;
  variant: string;
  meanDiff: number;
  direction: string;
  se: number;
  tStat: number;
  pValue: number;
  ciLower: number;
  ciUpper: number;
  significance: string;
}

/** Row shape for completeness table */
export interface CompletenessExportRow {
  model: string;
  variant: string;
  total: number;
  valid: number;
  invalid: number;
  refusals: number;
  validRate: number;
}

export type ExportRow =
  | DifferenceExportRow
  | DirectionalBiasExportRow
  | CompletenessExportRow;

function fmtNum(x: number, decimals = 3): string {
  return Number.isFinite(x) ? x.toFixed(decimals) : "—";
}

/** Build markdown table string from rows and table type */
export function rowsToMarkdown(
  rows: ExportRow[],
  tableType: ExportTableType
): string {
  if (rows.length === 0) return "";

  if (tableType === "difference") {
    const r = rows as DifferenceExportRow[];
    const header = "| Model | Variant | Difference Rate | SE | t-stat | p-value | 95% CI | Sig |";
    const sep = "|-------|---------|-----------------|-----|--------|---------|--------|-----|";
    const body = r
      .map(
        (row) =>
          `| ${row.model} | ${row.variant} | ${(row.differenceRate * 100).toFixed(1)}% | ${fmtNum(row.se)} | ${fmtNum(row.tStat)} | ${fmtNum(row.pValue)} | [${fmtNum(row.ciLower)}, ${fmtNum(row.ciUpper)}] | ${row.significance || "—"} |`
      )
      .join("\n");
    return [header, sep, body].join("\n");
  }

  if (tableType === "directional_bias") {
    const r = rows as DirectionalBiasExportRow[];
    const header = "| Model | Variant | Mean Diff | Direction | SE | t-stat | p-value | 95% CI | Sig |";
    const sep = "|-------|---------|-----------|-----------|-----|--------|---------|--------|-----|";
    const body = r
      .map(
        (row) =>
          `| ${row.model} | ${row.variant} | ${fmtNum(row.meanDiff)} | ${row.direction} | ${fmtNum(row.se)} | ${fmtNum(row.tStat)} | ${fmtNum(row.pValue)} | [${fmtNum(row.ciLower)}, ${fmtNum(row.ciUpper)}] | ${row.significance || "—"} |`
      )
      .join("\n");
    return [header, sep, body].join("\n");
  }

  if (tableType === "completeness") {
    const r = rows as CompletenessExportRow[];
    const header = "| Model | Variant | Total | Valid | Invalid | Refusals | Valid Rate |";
    const sep = "|-------|---------|-------|-------|---------|----------|------------|";
    const body = r
      .map(
        (row) =>
          `| ${row.model} | ${row.variant} | ${row.total} | ${row.valid} | ${row.invalid} | ${row.refusals} | ${(row.validRate * 100).toFixed(1)}% |`
      )
      .join("\n");
    return [header, sep, body].join("\n");
  }

  return "";
}

export interface ExportButtonsProps {
  projectId: string;
  runIds: string[];
  tableType: ExportTableType;
  /** Optional rows for "Copy as Markdown" (client-side only) */
  rows?: ExportRow[];
  className?: string;
  disabled?: boolean;
}

export function ExportButtons({
  projectId,
  runIds,
  tableType,
  rows = [],
  className,
  disabled = false,
}: ExportButtonsProps) {
  const [loading, setLoading] = React.useState<"latex" | "csv" | null>(null);

  const canExport = Boolean(projectId && runIds.length > 0 && !disabled);

  const downloadBlob = React.useCallback(
    (blob: Blob, filename: string) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    },
    []
  );

  const handleExportLaTeX = React.useCallback(async () => {
    if (!canExport) return;
    setLoading("latex");
    try {
      const result = await api.exportResults(
        projectId,
        runIds,
        tableType,
        "latex"
      );
      const blob =
        result instanceof Blob
          ? result
          : new Blob([result as string], { type: "application/x-latex" });
      downloadBlob(blob, `analysis_${tableType}.tex`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    } finally {
      setLoading(null);
    }
  }, [canExport, projectId, runIds, tableType, downloadBlob]);

  const handleExportCsv = React.useCallback(async () => {
    if (!canExport) return;
    setLoading("csv");
    try {
      const result = await api.exportResults(
        projectId,
        runIds,
        tableType,
        "csv"
      );
      const blob =
        result instanceof Blob
          ? result
          : new Blob([result as string], { type: "text/csv" });
      downloadBlob(blob, `analysis_${tableType}.csv`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    } finally {
      setLoading(null);
    }
  }, [canExport, projectId, runIds, tableType, downloadBlob]);

  const handleCopyLaTeX = React.useCallback(async () => {
    if (!canExport) return;
    setLoading("latex");
    try {
      const result = await api.exportResults(
        projectId,
        runIds,
        tableType,
        "latex"
      );
      const text =
        result instanceof Blob ? await result.text() : (result as string);
      await navigator.clipboard.writeText(text);
      toast.success("LaTeX table copied to clipboard");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Copy failed");
    } finally {
      setLoading(null);
    }
  }, [canExport, projectId, runIds, tableType]);

  const handleCopyMarkdown = React.useCallback(async () => {
    const md = rowsToMarkdown(rows, tableType);
    if (!md) {
      toast.error("No data to copy as Markdown");
      return;
    }
    try {
      await navigator.clipboard.writeText(md);
      toast.success("Markdown table copied to clipboard");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Copy failed");
    }
  }, [rows, tableType]);

  return (
    <div className={className ?? "flex flex-wrap gap-2"}>
      <Button
        variant="outline"
        size="sm"
        onClick={handleExportLaTeX}
        disabled={!canExport || loading !== null}
      >
        {loading === "latex" ? "…" : "Export LaTeX"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleExportCsv}
        disabled={!canExport || loading !== null}
      >
        {loading === "csv" ? "…" : "Export CSV"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleCopyLaTeX}
        disabled={!canExport || loading !== null}
      >
        Copy LaTeX
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleCopyMarkdown}
        disabled={rows.length === 0}
      >
        Copy as Markdown
      </Button>
    </div>
  );
}
