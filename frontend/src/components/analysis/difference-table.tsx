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
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";
import { ExportButtons, type ExportTableType } from "@/components/analysis/export-buttons";

export interface DifferenceRow {
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

export interface DifferenceTableProps {
  rows: DifferenceRow[];
  loading?: boolean;
  projectId?: string;
  runIds?: string[];
  tableType?: ExportTableType;
  onExportLatex?: () => void;
  onExportCsv?: () => void;
  className?: string;
}

type SortKey = keyof DifferenceRow;
type SortDir = "asc" | "desc";

function differenceRateColor(rate: number): string {
  if (rate < 0.05) return "text-green-600 dark:text-green-400 font-medium";
  if (rate <= 0.15) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400 font-medium";
}

export function DifferenceTable({
  rows,
  loading,
  projectId,
  runIds = [],
  tableType = "difference",
  onExportLatex,
  onExportCsv,
  className,
}: DifferenceTableProps) {
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
            tableType="difference"
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
              {header("differenceRate", "Difference Rate")}
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
                  colSpan={8}
                  className="text-center text-muted-foreground"
                >
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {!loading && sortedRows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground"
                >
                  No difference data. Select completed runs above.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              sortedRows.map((r, i) => (
                <TableRow key={`${r.model}-${r.variant}-${i}`}>
                  <TableCell className="font-mono text-sm">{r.model}</TableCell>
                  <TableCell className="font-mono text-sm">{r.variant}</TableCell>
                  <TableCell
                    className={cn(
                      "font-mono text-sm tabular-nums",
                      differenceRateColor(r.differenceRate)
                    )}
                  >
                    {(r.differenceRate * 100).toFixed(1)}%
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

export function flattenDifference(
  data: Record<string, Record<string, AnalysisResult>>
): DifferenceRow[] {
  const rows: DifferenceRow[] = [];
  for (const [model, variants] of Object.entries(data)) {
    if (!variants || typeof variants !== "object") continue;
    for (const [variant, v] of Object.entries(variants)) {
      if (!v || typeof v !== "object") continue;
      rows.push({
        model,
        variant,
        differenceRate: v.difference_rate ?? 0,
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
