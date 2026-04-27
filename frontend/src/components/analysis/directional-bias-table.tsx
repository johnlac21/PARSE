"use client";

import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";
import { ExportButtons, type ExportTableType } from "@/components/analysis/export-buttons";

export interface DirectionalBiasRow {
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

export interface DirectionalBiasTableProps {
  rows: DirectionalBiasRow[];
  loading?: boolean;
  projectId?: string;
  runIds?: string[];
  tableType?: ExportTableType;
  onExportLatex?: () => void;
  onExportCsv?: () => void;
  className?: string;
}

type SortKey = keyof DirectionalBiasRow;
type SortDir = "asc" | "desc";

function DirectionCell({ direction }: { direction: string }) {
  const d = (direction || "").toLowerCase();
  if (d === "higher")
    return (
      <span className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">
        <ArrowUp className="h-4 w-4" /> ↑
      </span>
    );
  if (d === "lower")
    return (
      <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
        <ArrowDown className="h-4 w-4" /> ↓
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <Minus className="h-4 w-4" /> —
    </span>
  );
}

export function DirectionalBiasTable({
  rows,
  loading,
  projectId,
  runIds = [],
  onExportLatex,
  onExportCsv,
  className,
}: DirectionalBiasTableProps) {
  const [sortKey, setSortKey] = React.useState<SortKey>("model");
  const [sortDir, setSortDir] = React.useState<SortDir>("asc");

  const sortedRows = React.useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === "string" && typeof bVal === "string")
        return sortDir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      const cmp = Number(aVal) - Number(bVal);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [rows, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const header = (key: SortKey, label: string) => (
    <TableHead
      className="cursor-pointer select-none font-medium hover:bg-muted/50"
      onClick={() => toggleSort(key)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortKey === key && (
          <span className="text-muted-foreground">
            {sortDir === "asc" ? "↑" : "↓"}
          </span>
        )}
      </span>
    </TableHead>
  );

  const fmt = (x: number, decimals = 3) =>
    Number.isFinite(x) ? x.toFixed(decimals) : "—";

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {projectId && runIds.length > 0 ? (
          <ExportButtons
            projectId={projectId}
            runIds={runIds}
            tableType="directional_bias"
            rows={rows}
            disabled={loading}
          />
        ) : (
          <>
            {onExportLatex && (
              <Button variant="outline" size="sm" onClick={onExportLatex}>
                Export LaTeX
              </Button>
            )}
            {onExportCsv && (
              <Button variant="outline" size="sm" onClick={onExportCsv}>
                Export CSV
              </Button>
            )}
          </>
        )}
      </div>
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              {header("model", "Model")}
              {header("variant", "Variant")}
              {header("meanDiff", "Mean Diff")}
              {header("direction", "Direction")}
              {header("se", "SE")}
              {header("tStat", "t-stat")}
              {header("pValue", "p-value")}
              {header("ciLower", "95% CI")}
              {header("significance", "Sig")}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="text-center text-muted-foreground"
                >
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {!loading && sortedRows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={9}
                  className="text-center text-muted-foreground"
                >
                  No directional bias data. Select completed runs above.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              sortedRows.map((r, i) => (
                <TableRow key={`${r.model}-${r.variant}-${i}`}>
                  <TableCell className="font-mono text-sm">{r.model}</TableCell>
                  <TableCell className="font-mono text-sm">{r.variant}</TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {fmt(r.meanDiff)}
                  </TableCell>
                  <TableCell>
                    <DirectionCell direction={r.direction} />
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {fmt(r.se)}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {fmt(r.tStat)}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {fmt(r.pValue)}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    [{fmt(r.ciLower)}, {fmt(r.ciUpper)}]
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {r.significance || "—"}
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export function flattenDirectionalBias(
  data: Record<string, Record<string, AnalysisResult>>
): DirectionalBiasRow[] {
  const rows: DirectionalBiasRow[] = [];
  for (const [model, variants] of Object.entries(data)) {
    if (!variants || typeof variants !== "object") continue;
    for (const [variant, v] of Object.entries(variants)) {
      if (!v || typeof v !== "object") continue;
      rows.push({
        model,
        variant,
        meanDiff: v.mean_difference ?? 0,
        direction: v.direction ?? "neutral",
        se: v.se ?? 0,
        tStat: v.t_stat ?? 0,
        pValue: v.p_value ?? 0,
        ciLower: v.ci_lower ?? 0,
        ciUpper: v.ci_upper ?? 0,
        significance: v.significance ?? "",
      });
    }
  }
  return rows;
}
