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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const TRUNCATE_LEN = 60;

export interface RawResultItem {
  id: number;
  run_id: string;
  prompt_id: string;
  prompt_text?: string;
  variant: string;
  model_id: string;
  raw_response: string | null;
  parsed_label: string | null;
  parsed_index: number | null;
  is_valid: boolean | null;
}

export interface RawDataTableProps {
  projectId: string;
  selectedRunIds: string[];
  /** Optional list of variant names to show in filter (e.g. from analysis data). */
  variantOptions?: string[];
  /** Optional list of model IDs to show in filter (e.g. from analysis data). */
  modelOptions?: string[];
  className?: string;
}

export function RawDataTable({
  projectId,
  selectedRunIds,
  variantOptions,
  modelOptions,
  className,
}: RawDataTableProps) {
  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [variantFilter, setVariantFilter] = React.useState<string>("all");
  const [modelFilter, setModelFilter] = React.useState<string>("all");
  const [validFilter, setValidFilter] = React.useState<"all" | "valid" | "invalid">("all");
  const [expandedId, setExpandedId] = React.useState<number | null>(null);
  const [data, setData] = React.useState<{
    items: RawResultItem[];
    total: number;
    page: number;
    per_page: number;
  } | null>(null);
  const [loading, setLoading] = React.useState(false);

  const runId =
    selectedRunIds.length > 0 ? selectedRunIds[0] : undefined;

  const fetchResults = React.useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const { api } = await import("@/lib/api-client");
      const res = await api.getRawResults(projectId, {
        run_id: runId,
        variant: variantFilter === "all" ? undefined : variantFilter,
        model_id: modelFilter === "all" ? undefined : modelFilter,
        page,
        per_page: 50,
      });
      setData({
        items: (res.items as RawResultItem[]) || [],
        total: res.total ?? 0,
        page: res.page ?? 1,
        per_page: res.per_page ?? 50,
      });
    } catch {
      setData({ items: [], total: 0, page: 1, per_page: 50 });
    } finally {
      setLoading(false);
    }
  }, [projectId, runId, variantFilter, modelFilter, page]);

  React.useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const filteredItems = React.useMemo(() => {
    if (!data?.items) return [];
    let list = data.items;
    if (validFilter === "valid") list = list.filter((r) => r.is_valid === true);
    else if (validFilter === "invalid")
      list = list.filter((r) => r.is_valid === false || r.is_valid == null);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (r) =>
          (r.prompt_text ?? "").toLowerCase().includes(q) ||
          (r.prompt_id ?? "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [data?.items, validFilter, search]);

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.per_page))
    : 1;

  const variants = React.useMemo(() => {
    if (variantOptions?.length) return variantOptions;
    const set = new Set<string>();
    data?.items?.forEach((r) => set.add(r.variant));
    return Array.from(set).sort();
  }, [variantOptions, data?.items]);

  const models = React.useMemo(() => {
    if (modelOptions?.length) return modelOptions;
    const set = new Set<string>();
    data?.items?.forEach((r) => set.add(r.model_id));
    return Array.from(set).sort();
  }, [modelOptions, data?.items]);

  const truncate = (s: string | null | undefined) => {
    if (s == null) return "—";
    const t = String(s).trim();
    if (t.length <= TRUNCATE_LEN) return t;
    return t.slice(0, TRUNCATE_LEN) + "…";
  };

  if (selectedRunIds.length === 0) {
    return (
      <div
        className={cn(
          "rounded-md border border-border p-6 text-center text-sm text-muted-foreground",
          className
        )}
      >
        Select at least one completed run above to view raw data.
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search by prompt text…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select value={variantFilter} onValueChange={setVariantFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Variant" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All variants</SelectItem>
            {variants.map((v) => (
              <SelectItem key={v} value={v}>
                {v}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={modelFilter} onValueChange={setModelFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All models</SelectItem>
            {models.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={validFilter} onValueChange={(v: "all" | "valid" | "invalid") => setValidFilter(v)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Valid" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="valid">Valid only</SelectItem>
            <SelectItem value="invalid">Invalid only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead className="font-medium">Prompt ID</TableHead>
              <TableHead className="font-medium max-w-[200px]">Prompt Text</TableHead>
              <TableHead className="font-medium">Variant</TableHead>
              <TableHead className="font-medium">Model</TableHead>
              <TableHead className="font-medium max-w-[200px]">Raw Response</TableHead>
              <TableHead className="font-medium">Parsed Label</TableHead>
              <TableHead className="font-medium">Parsed Index</TableHead>
              <TableHead className="font-medium">Valid</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {!loading && filteredItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  Complete a run to see results.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              filteredItems.map((r) => (
                <React.Fragment key={r.id}>
                  <TableRow
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() =>
                      setExpandedId(expandedId === r.id ? null : r.id)
                    }
                  >
                    <TableCell className="w-8">
                      {expandedId === r.id ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {r.prompt_id}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm">
                      {truncate(r.prompt_text)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">{r.variant}</TableCell>
                    <TableCell className="font-mono text-sm">{r.model_id}</TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm">
                      {truncate(r.raw_response)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {r.parsed_label ?? "—"}
                    </TableCell>
                    <TableCell className="font-mono text-sm tabular-nums">
                      {r.parsed_index != null ? r.parsed_index : "—"}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "font-mono text-sm",
                          r.is_valid === true && "text-green-600 dark:text-green-400",
                          r.is_valid === false && "text-red-600 dark:text-red-400"
                        )}
                      >
                        {r.is_valid === true ? "Yes" : r.is_valid === false ? "No" : "—"}
                      </span>
                    </TableCell>
                  </TableRow>
                  {expandedId === r.id && (
                    <TableRow className="bg-muted/30">
                      <TableCell colSpan={9} className="p-4">
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="font-medium text-muted-foreground">
                              Full prompt text:
                            </span>
                            <p className="mt-1 whitespace-pre-wrap break-words rounded border border-border bg-background p-2 font-mono">
                              {r.prompt_text ?? "—"}
                            </p>
                          </div>
                          <div>
                            <span className="font-medium text-muted-foreground">
                              Full response:
                            </span>
                            <p className="mt-1 whitespace-pre-wrap break-words rounded border border-border bg-background p-2 font-mono">
                              {r.raw_response ?? "—"}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Page {data?.page ?? 1} of {totalPages} · {data?.total ?? 0} total
          {search || validFilter !== "all"
            ? ` (${filteredItems.length} on this page after filter)`
            : ""}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
