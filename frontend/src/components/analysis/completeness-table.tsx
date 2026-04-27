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
import type { CompletenessResult } from "@/lib/types";
import { ExportButtons, type ExportTableType } from "@/components/analysis/export-buttons";

export interface CompletenessRow {
  model: string;
  variant: string;
  total: number;
  valid: number;
  invalid: number;
  refusals: number;
  validRate: number;
}

export interface CompletenessTableProps {
  rows: CompletenessRow[];
  loading?: boolean;
  projectId?: string;
  runIds?: string[];
  tableType?: ExportTableType;
  onExportLatex?: () => void;
  onExportCsv?: () => void;
  className?: string;
}

type SortKey = keyof CompletenessRow;
type SortDir = "asc" | "desc";

function validRateColor(rate: number): string {
  if (rate >= 0.95) return "text-green-600 dark:text-green-400 font-medium";
  if (rate >= 0.8) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400 font-medium";
}

export function CompletenessTable({
  rows,
  loading,
  projectId,
  runIds = [],
  onExportLatex,
  onExportCsv,
  className,
}: CompletenessTableProps) {
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

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {projectId && runIds.length > 0 ? (
          <ExportButtons
            projectId={projectId}
            runIds={runIds}
            tableType="completeness"
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
              {header("total", "Total")}
              {header("valid", "Valid")}
              {header("invalid", "Invalid")}
              {header("refusals", "Refusals")}
              {header("validRate", "Valid Rate")}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center text-muted-foreground"
                >
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {!loading && sortedRows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center text-muted-foreground"
                >
                  No completeness data. Select completed runs above.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              sortedRows.map((r, i) => (
                <TableRow key={`${r.model}-${r.variant}-${i}`}>
                  <TableCell className="font-mono text-sm">{r.model}</TableCell>
                  <TableCell className="font-mono text-sm">{r.variant}</TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {r.total}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {r.valid}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {r.invalid}
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {r.refusals}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "font-mono text-sm tabular-nums",
                      validRateColor(r.validRate)
                    )}
                  >
                    {(r.validRate * 100).toFixed(1)}%
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export function flattenCompleteness(
  data: Record<string, Record<string, CompletenessResult>>
): CompletenessRow[] {
  const rows: CompletenessRow[] = [];
  for (const [model, variants] of Object.entries(data)) {
    if (!variants || typeof variants !== "object") continue;
    for (const [variant, v] of Object.entries(variants)) {
      if (!v || typeof v !== "object") continue;
      rows.push({
        model,
        variant,
        total: v.total ?? 0,
        valid: v.valid ?? 0,
        invalid: v.invalid ?? 0,
        refusals: v.refusals ?? 0,
        validRate: v.valid_rate ?? 0,
      });
    }
  }
  return rows;
}
