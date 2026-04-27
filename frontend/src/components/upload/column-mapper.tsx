"use client";

/**
 * Column mapping UI: dropdown per column to assign role (prompt_id, prompt_text, variant, metadata, ignore).
 * Auto-suggests based on column names. Preview of first 3 rows. "Confirm Mapping" calls onMap with mapping.
 */

import * as React from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type ColumnRole = "prompt_id" | "prompt_text" | "variant" | "metadata" | "ignore";

export interface ColumnMappingResult {
  prompt_id_column: string;
  prompt_text_column: string;
  variant_column: string | null;
  metadata_columns: string[];
}

const ROLES: { value: ColumnRole; label: string }[] = [
  { value: "ignore", label: "Ignore" },
  { value: "prompt_id", label: "Prompt ID" },
  { value: "prompt_text", label: "Prompt text" },
  { value: "variant", label: "Variant" },
  { value: "metadata", label: "Metadata" },
];

function suggestRole(columnName: string): ColumnRole {
  const lower = columnName.toLowerCase().trim();
  if (["prompt_id", "id", "prompt id"].some((c) => lower.includes(c.replace(/\s/g, "_")) || lower === c)) return "prompt_id";
  if (["prompt_text", "text", "prompt", "prompt text", "content", "body"].some((c) => lower.includes(c.replace(/\s/g, "_")) || lower === c)) return "prompt_text";
  if (["variant", "dialect", "style"].some((c) => lower.includes(c))) return "variant";
  return "ignore";
}

export interface ColumnMapperProps {
  columns: string[];
  sample: Record<string, unknown>[];
  onMap: (mapping: ColumnMappingResult) => void;
  className?: string;
}

export function ColumnMapper({
  columns,
  sample,
  onMap,
  className,
}: ColumnMapperProps) {
  const [roleByColumn, setRoleByColumn] = React.useState<Record<string, ColumnRole>>(() => {
    const initial: Record<string, ColumnRole> = {};
    columns.forEach((col) => {
      initial[col] = suggestRole(col);
    });
    return initial;
  });

  const setRole = (col: string, role: ColumnRole) => {
    setRoleByColumn((prev) => ({ ...prev, [col]: role }));
  };

  const handleConfirm = () => {
    const prompt_id_column = columns.find((c) => roleByColumn[c] === "prompt_id") ?? columns[0];
    const prompt_text_column = columns.find((c) => roleByColumn[c] === "prompt_text");
    if (!prompt_text_column) return; // required
    const variant_column = columns.find((c) => roleByColumn[c] === "variant") ?? null;
    const metadata_columns = columns.filter((c) => roleByColumn[c] === "metadata");
    onMap({
      prompt_id_column,
      prompt_text_column,
      variant_column,
      metadata_columns,
    });
  };

  const promptTextCol = columns.find((c) => roleByColumn[c] === "prompt_text");
  const canConfirm = Boolean(promptTextCol);

  const previewRows = sample.slice(0, 3);

  return (
    <div className={cn("space-y-4", className)}>
      <p className="text-sm text-muted-foreground">
        Assign a role to each column. At least &quot;Prompt text&quot; is required.
      </p>
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col} className="min-w-[120px]">
                  <Select
                    value={roleByColumn[col] ?? "ignore"}
                    onValueChange={(v) => setRole(col, v as ColumnRole)}
                  >
                    <SelectTrigger className="h-9 w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="mt-1 block truncate text-xs font-normal text-muted-foreground">
                    {col}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {previewRows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((col) => (
                  <TableCell key={col} className="max-w-[200px] truncate">
                    {row[col] != null ? String(row[col]) : "—"}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button onClick={handleConfirm} disabled={!canConfirm}>
        Confirm Mapping
      </Button>
    </div>
  );
}
